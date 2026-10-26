import os, re, time, sqlite3, secrets
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Literal
import jwt
from argon2 import PasswordHasher
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

DB_PATH=os.getenv("DATABASE_PATH","/tmp/liliang-erp-pilot.db")
ADMIN_EMAIL=os.getenv("ADMIN_EMAIL","").lower().strip()
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","")
SECRET_KEY=os.getenv("SECRET_KEY","")
invalid_settings=[]
if not ADMIN_EMAIL:
    invalid_settings.append("ADMIN_EMAIL is missing")
if len(ADMIN_PASSWORD)<12:
    invalid_settings.append("ADMIN_PASSWORD is missing or shorter than 12 characters")
if len(SECRET_KEY)<32:
    invalid_settings.append("SECRET_KEY is missing or shorter than 32 characters")
if invalid_settings:
    raise RuntimeError("Invalid Render Environment Variables: " + "; ".join(invalid_settings) + ". Values are never logged.")
if os.getenv("APP_ENV","pilot")=="production":
    raise RuntimeError("This research pilot cannot run in production mode.")
ph=PasswordHasher()
auth=HTTPBearer(auto_error=False)
ROLES=("admin","sales","technical","manager","gudang")
SESSION_IDLE_SECONDS=900  # 15 minutes of no authenticated API activity
SESSION_ABSOLUTE_SECONDS=8*3600  # hard JWT/session expiry of 8 hours
DEMO=[
 ("FLV-STRAW-01","Strawberry Flavor","Ripe sweet strawberry for dairy beverages","strawberry","dairy"),
 ("FLV-VANI-02","Vanilla Flavor","Creamy vanilla for bakery and dairy","vanilla","bakery"),
 ("FLV-MANG-03","Mango Flavor","Tropical mango for beverages","mango","beverage"),
 ("FLV-CHOCO-04","Chocolate Flavor","Rich chocolate for dairy and bakery","chocolate","dairy"),
 ("FLV-LEMON-05","Lemon Flavor","Citrus lemon for cold beverages","lemon","beverage"),
]
from persistence import connect as connect_database, install_schema, engine_name
def connect():
    return connect_database()
def boot():
    with connect() as db:
        install_schema(db)
        if not db.execute("SELECT id FROM users WHERE email=?",(ADMIN_EMAIL,)).fetchone():
            db.execute("INSERT INTO users(email,name,role,hash) VALUES(?,?,?,?)",(ADMIN_EMAIL,"ERP Administrator","admin",ph.hash(ADMIN_PASSWORD)))
        # An archived reset is a durable marker: do not re-seed demo products on restart.
        archived=db.execute("SELECT 1 FROM reset_archives LIMIT 1").fetchone()
        imported=db.execute("SELECT 1 FROM catalog_import_batches LIMIT 1").fetchone()
        if not archived and not imported:
            for sku,name,desc,profile,application in DEMO:
                db.execute("INSERT OR IGNORE INTO products(sku,name,description,profile,application,stock,source_ref) VALUES(?,?,?,?,?,?,?)",
                           (sku,name,desc,profile,application,0,"DEMO-ONLY"))
def now():return datetime.now(timezone.utc).isoformat()
def audit(db,user,action,entity,id,before=None,after=None):
    db.execute("INSERT INTO audits(actor_id,action,entity,entity_id,at) VALUES(?,?,?,?,?)",(user["id"],action,entity,id,now()))
    from enterprise_ops import append_event
    return append_event(db,user,action,entity,id,before=before,after=after)
def to_dict(row):return dict(row) if row is not None else None
@asynccontextmanager
async def lifespan(app):
    boot()
    yield
app=FastAPI(title="PT Liliang ERP Multi-AI — DEMO PILOT",version="0.5.0",lifespan=lifespan)
def get_db():
    db=connect()
    try: yield db
    finally:db.close()
def current(creds:HTTPAuthorizationCredentials|None=Depends(auth),db:sqlite3.Connection=Depends(get_db)):
    if not creds:raise HTTPException(401,"Login required")
    try:
        claim=jwt.decode(creds.credentials,SECRET_KEY,algorithms=["HS256"])
        sid=claim["sid"]
        uid=int(claim["sub"])
        t=time.time()
        session=db.execute("""SELECT id,user_id,last_seen_at,expires_at,revoked_at
                               FROM user_sessions WHERE id=? AND user_id=?""",(sid,uid)).fetchone()
        if not session or session["revoked_at"] is not None or float(session["expires_at"])<=t:
            raise ValueError("Session was revoked or expired")
        if t-float(session["last_seen_at"])>SESSION_IDLE_SECONDS:
            with db:
                expired=db.execute("UPDATE user_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL",(t,sid))
                if expired.rowcount:
                    actor=db.execute("SELECT id,role FROM users WHERE id=?",(uid,)).fetchone()
                    if actor:
                        audit(db,dict(actor),"SESSION_EXPIRED_IDLE","auth",uid,
                              after={"reason":"SERVER_IDLE_15_MIN","session_ref":secrets.token_hex(8)})
            raise ValueError("Session inactive")
        row=db.execute("SELECT id,email,name,role FROM users WHERE id=?",(uid,)).fetchone()
        if not row:raise ValueError("Account unavailable")
        # Updating last activity is committed to Neon for cross-device revocation and idle expiry.
        with db:
            db.execute("UPDATE user_sessions SET last_seen_at=? WHERE id=? AND revoked_at IS NULL",(t,sid))
        return dict(row)
    except (jwt.PyJWTError,ValueError,KeyError,TypeError):
        raise HTTPException(401,"Session invalid, expired, or inactive. Please log in again.")
def permit(*roles):
    def dependency(u=Depends(current)):
        if u["role"] not in roles:raise HTTPException(403,"Role access denied")
        return u
    return dependency
class Login(BaseModel):
    email:str
    password:str
class NewUser(BaseModel):
    name:str=Field(min_length=2)
    email:str
    password:str=Field(min_length=12)
    role:Literal["admin","sales","technical","manager","gudang"]
class InquiryIn(BaseModel):
    customer_ref:str=Field(default="ANON",max_length=80)
    requirement:str=Field(min_length=5,max_length=3000)
class ReviewIn(BaseModel):
    product_id:int
    decision:Literal["ACCEPT","REJECT","NEEDS_INFO"]
    relevance_label:int=Field(ge=0,le=3)
    rationale:str=Field(min_length=5,max_length=500)
class DecisionIn(BaseModel):
    decision:Literal["APPROVE","RETURN"]
    note:str=Field(min_length=5)
class StockIn(BaseModel):
    stock_qty:float=Field(ge=0)
    # The pilot never assumes an unverified supplier catalog has on-hand stock.
    verification_ref:str=Field(default="",max_length=100)
    physical_count_date:str=Field(default="",max_length=10)
@app.get("/healthz")
def health():return {"status":"ok","environment":"DEMO","persistent_database":engine_name()=="postgresql","database_backend":engine_name()}
@app.get("/readyz")
def ready(db=Depends(get_db)):
    db.execute("SELECT 1").fetchone()
    return {"ready":True,"database_backend":engine_name()}
@app.post("/v1/auth/login")
def login(data:Login,db=Depends(get_db)):
    u=db.execute("SELECT * FROM users WHERE email=?",(data.email.lower().strip(),)).fetchone()
    valid=False
    if u:
        try:
            valid=ph.verify(u["hash"],data.password)
        except Exception:
            valid=False
    if not valid:
        raise HTTPException(401,"Incorrect email or password")
    ts=time.time()
    sid=secrets.token_urlsafe(32)
    expires=ts+SESSION_ABSOLUTE_SECONDS
    token=jwt.encode({"sub":str(u["id"]),"sid":sid,
                      "exp":datetime.fromtimestamp(expires,timezone.utc)},
                     SECRET_KEY,algorithm="HS256")
    with db:
        db.execute("INSERT INTO user_sessions(id,user_id,created_at,last_seen_at,expires_at,revoked_at) VALUES(?,?,?,?,?,NULL)",
                   (sid,u["id"],ts,ts,expires))
        audit(db,u,"LOGIN_SUCCESS","auth",u["id"],after={"role":u["role"],"session_issued":True})
    return {"access_token":token,"token_type":"bearer","expires_in":SESSION_ABSOLUTE_SECONDS,
            "idle_timeout_seconds":SESSION_IDLE_SECONDS,
            "user":{"id":u["id"],"role":u["role"],"name":u["name"]}}
@app.get("/v1/auth/me")
def me(u=Depends(current)):return u
@app.post("/v1/auth/logout")
def logout(request:Request,creds:HTTPAuthorizationCredentials|None=Depends(auth),u=Depends(current),db=Depends(get_db)):
    claim=jwt.decode(creds.credentials,SECRET_KEY,algorithms=["HS256"])
    reason="IDLE" if request.headers.get("X-Logout-Reason")=="IDLE" else "MANUAL"
    with db:
        revoked=db.execute("UPDATE user_sessions SET revoked_at=? WHERE id=? AND user_id=? AND revoked_at IS NULL",
                          (time.time(),claim["sid"],u["id"]))
        if revoked.rowcount:
            audit(db,u,"SESSION_EXPIRED_IDLE" if reason=="IDLE" else "LOGOUT","auth",u["id"],
                  after={"session_revoked":True,"reason":reason})
    return {"logged_out":True,"session_revoked":True}
@app.post("/v1/users",status_code=201)
def add_user(data:NewUser,u=Depends(permit("admin")),db=Depends(get_db)):
    try:
        with db:
            cur=db.execute("INSERT INTO users(email,name,role,hash) VALUES(?,?,?,?)",(data.email.lower().strip(),data.name,data.role,ph.hash(data.password)))
            audit(db,u,"CREATE_USER","user",cur.lastrowid)
        return {"id":cur.lastrowid,"role":data.role}
    except Exception as exc:
        if isinstance(exc, sqlite3.IntegrityError) or getattr(exc,"sqlstate",None)=="23505":
            raise HTTPException(409,"Email already exists")
        raise
@app.get("/v1/users")
def users(u=Depends(permit("admin")),db=Depends(get_db)):
    return [dict(x) for x in db.execute("SELECT id,email,name,role FROM users ORDER BY id").fetchall()]
@app.get("/v1/products")
def products(u=Depends(current),db=Depends(get_db)):
    return [dict(x) for x in db.execute("SELECT * FROM products ORDER BY sku").fetchall()]
@app.patch("/v1/products/{pid}/stock")
def stock(pid:int,data:StockIn,u=Depends(permit("admin","gudang")),db=Depends(get_db)):
    previous=db.execute("SELECT stock,source_ref FROM products WHERE id=?",(pid,)).fetchone()
    if previous is None:raise HTTPException(404,"SKU not found")
    imported=previous["source_ref"]=="CATALOG-PDF-UNVERIFIED"
    if imported:
        # UAT accounts are never allowed to alter operational supplier-catalog stock.
        if u["email"].lower().startswith("uat-"):
            raise HTTPException(403,"UAT account cannot modify unverified company stock")
        ref=data.verification_ref.strip()
        if len(ref)<6 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./#-]{5,99}",ref):
            raise HTTPException(422,"Verified physical count reference is required for company stock")
        try:
            verified_on=datetime.strptime(data.physical_count_date,"%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(422,"Physical count date must be YYYY-MM-DD")
        if verified_on>datetime.now(timezone.utc).date():
            raise HTTPException(422,"Physical count date cannot be in the future")
    with db:
        c=db.execute("UPDATE products SET stock=? WHERE id=?",(data.stock_qty,pid))
        if not c.rowcount:raise HTTPException(404,"SKU not found")
        audit(db,u,"STOCK_UPDATE","product",pid,
              before={"stock":previous["stock"]},
              after={"stock":data.stock_qty,
                     "physical_count_reference":data.verification_ref.strip() if imported else None,
                     "physical_count_date":data.physical_count_date if imported else None,
                     "source":"PHYSICAL_COUNT_DECLARED" if imported else "DEMO_PRODUCT"})
    return {"product_id":pid,"stock_qty":data.stock_qty,
            "verification_recorded":imported}
@app.post("/v1/inquiries",status_code=201)
def new_inquiry(data:InquiryIn,u=Depends(permit("sales","admin")),db=Depends(get_db)):
    with db:
        cur=db.execute("INSERT INTO inquiries(requirement,customer_ref,created_by,status,created_at) VALUES(?,?,?,'NEW',?)",
                (data.requirement,data.customer_ref,u["id"],now()))
        audit(db,u,"NEW_INQUIRY","inquiry",cur.lastrowid,after={"status":"NEW","requirement_recorded":True})
    return {"id":cur.lastrowid,"status":"NEW"}
@app.get("/v1/inquiries")
def inquiries(u=Depends(permit("admin","sales","technical","manager")),db=Depends(get_db)):
    # Warehouse only has catalog/stock authority; inquiry metadata (IDs/status)
    # are also restricted, not merely the free-text customer requirement.
    sql="SELECT * FROM inquiries";params=()
    if u["role"]=="sales":
        sql+=" WHERE created_by=?";params=(u["id"],)
    return [dict(x) for x in db.execute(sql+" ORDER BY id DESC",params).fetchall()]
@app.post("/v1/inquiries/{iid}/match")
def match(iid:int,u=Depends(permit("sales","admin","technical")),db=Depends(get_db)):
    q=db.execute("SELECT * FROM inquiries WHERE id=?",(iid,)).fetchone()
    if not q:raise HTTPException(404,"Inquiry not found")
    if u["role"]=="sales" and q["created_by"]!=u["id"]:raise HTTPException(403,"Not your inquiry")
    if q["status"]!="NEW":
        raise HTTPException(409,"This inquiry was already processed. Open saved candidates; do not rerun matching.")
    from research.inquiry_insights import inquiry_insight
    t=time.monotonic()
    product_catalog=[dict(p) for p in db.execute("SELECT * FROM products").fetchall()]
    candidates=score_products(q["requirement"],product_catalog)
    elapsed=int((time.monotonic()-t)*1000)
    new_status="MATCHED" if candidates else "NO_MATCH"
    with db:
        # Atomic status transition prevents double-click duplicates and changes after review.
        claimed=db.execute("UPDATE inquiries SET status=? WHERE id=? AND status='NEW'",(new_status,iid))
        if claimed.rowcount!=1:
            raise HTTPException(409,"This inquiry was already matched by another request.")
        run=db.execute("INSERT INTO runs(inquiry_id,method,latency_ms,created_at) VALUES(?,'bm25-catalog-constraint-v0.3',?,?)",(iid,elapsed,now()))
        for rank,item in enumerate(candidates,1):
            item["rank"]=rank
            db.execute("INSERT INTO candidates(run_id,product_id,score,rank,unknown) VALUES(?,?,?,?,?)",
                     (run.lastrowid,item["product_id"],item["score"],rank,",".join(item["unknown_attributes"])))
        audit(db,u,"MATCH_BASELINE","run",run.lastrowid,
              after={"method":"BM25_CONSTRAINT_AWARE","candidate_count":len(candidates),"latency_ms":elapsed,
                     "abstained":not bool(candidates)})
    catalog_by_id={p["id"]:p for p in product_catalog}
    enriched=[{**catalog_by_id.get(c["product_id"],{}),**c} for c in candidates]
    return {"run_id":run.lastrowid,"method":"bm25-catalog-constraint-v0.3","latency_ms":elapsed,
            "status":new_status,"abstained":not bool(candidates),
            "candidates":candidates,
            "insight":inquiry_insight(q["requirement"],enriched,"bm25-catalog-constraint-v0.3",new_status),
            "notice":"No candidate is returned when required flavor/form evidence is missing. Scores are uncalibrated BM25, NOT accuracy or suitability probabilities. Technical must validate every candidate."}
@app.get("/v1/inquiries/{iid}/latest-match")
def latest_match(iid:int,u=Depends(permit("admin","sales","technical","manager")),db=Depends(get_db)):
    from research.inquiry_insights import inquiry_insight
    q=db.execute("SELECT id,created_by,status,requirement FROM inquiries WHERE id=?",(iid,)).fetchone()
    if not q:raise HTTPException(404,"Inquiry not found")
    if u["role"]=="sales" and q["created_by"]!=u["id"]:
        raise HTTPException(403,"Not your inquiry")
    run=db.execute("SELECT id,method,latency_ms,created_at FROM runs WHERE inquiry_id=? ORDER BY id DESC LIMIT 1",(iid,)).fetchone()
    if not run:return {"inquiry_id":iid,"status":q["status"],"run_id":None,"candidates":[],
                        "insight":inquiry_insight(q["requirement"],[],"NOT_RUN",q["status"])}
    rows=db.execute("""SELECT c.rank,p.id product_id,p.sku,p.name,p.description,p.application,p.profile,p.source_ref,c.score,c.unknown,
       (SELECT v.decision FROM reviews v WHERE v.run_id=c.run_id AND v.product_id=c.product_id ORDER BY v.id DESC LIMIT 1) AS expert_decision,
       (SELECT v.label FROM reviews v WHERE v.run_id=c.run_id AND v.product_id=c.product_id ORDER BY v.id DESC LIMIT 1) AS expert_relevance,
       (SELECT v.note FROM reviews v WHERE v.run_id=c.run_id AND v.product_id=c.product_id ORDER BY v.id DESC LIMIT 1) AS expert_note
       FROM candidates c JOIN products p ON p.id=c.product_id WHERE c.run_id=? ORDER BY c.rank""",(run["id"],)).fetchall()
    from research.catalog_matcher import _product_form
    candidates=[]
    for row in rows:
        item=dict(row)
        item["product_form"]=_product_form(item) or "UNKNOWN"
        decision=item["expert_decision"]
        label=item["expert_relevance"]
        item["historical_review_conflict"]=bool(
            (decision=="ACCEPT" and label!=3) or
            (decision=="REJECT" and label==3) or
            (label==0 and decision not in (None,"REJECT"))
        )
        candidates.append(item)
    return {"inquiry_id":iid,"status":q["status"],"run_id":run["id"],"method":run["method"],
            "latency_ms":run["latency_ms"],"candidates":candidates,
            "insight":inquiry_insight(q["requirement"],candidates,run["method"],q["status"]),
            "notice":"Candidates require Technical evaluation. The BM25 score is not an accuracy percentage."}

@app.get("/v1/matches/{rid}")
def show_match(rid:int,u=Depends(permit("admin","sales","technical","manager")),db=Depends(get_db)):
    q=db.execute("SELECT r.*,i.created_by FROM runs r JOIN inquiries i ON i.id=r.inquiry_id WHERE r.id=?",(rid,)).fetchone()
    if not q:raise HTTPException(404,"Run not found")
    if u["role"]=="sales" and q["created_by"]!=u["id"]:raise HTTPException(403,"Not authorized")
    rows=db.execute("SELECT c.rank,p.id product_id,p.sku,p.name,c.score,c.unknown FROM candidates c JOIN products p ON p.id=c.product_id WHERE c.run_id=? ORDER BY c.rank",(rid,))
    return {"run_id":rid,"candidates":[dict(x) for x in rows.fetchall()]}
@app.post("/v1/matches/{rid}/review")
def review(rid:int,data:ReviewIn,u=Depends(permit("technical")),db=Depends(get_db)):
    q=db.execute("SELECT r.inquiry_id,c.id candidate_id FROM runs r JOIN candidates c ON c.run_id=r.id WHERE r.id=? AND c.product_id=?",(rid,data.product_id)).fetchone()
    if not q:raise HTTPException(400,"Candidate not in run")
    if data.decision=="ACCEPT" and data.relevance_label!=3:
        raise HTTPException(422,"ACCEPT requires Technical relevance label 3; use NEEDS_INFO for label 2")
    if data.relevance_label==0 and data.decision!="REJECT":
        raise HTTPException(422,"Relevance label 0 must be REJECT")
    if data.relevance_label==3 and data.decision=="REJECT":
        raise HTTPException(422,"Relevance label 3 cannot be REJECT")
    status=db.execute("SELECT status FROM inquiries WHERE id=?",(q["inquiry_id"],)).fetchone()
    if not status or status["status"] in ("APPROVED","RETURNED"):
        raise HTTPException(409,"Inquiry already decided; Technical review is closed")
    with db:
        cur=db.execute("INSERT INTO reviews(run_id,product_id,reviewer_id,decision,label,note) VALUES(?,?,?,?,?,?)",
                       (rid,data.product_id,u["id"],data.decision,data.relevance_label,data.rationale))
        db.execute("UPDATE inquiries SET status='TECH_REVIEWED' WHERE id=?",(q["inquiry_id"],))
        audit(db,u,"EXPERT_REVIEW","review",cur.lastrowid,after={"label":data.relevance_label,"decision":data.decision,"run_id":rid,"product_id":data.product_id})
    return {"review_id":cur.lastrowid,"status":"TECH_REVIEWED"}
@app.post("/v1/inquiries/{iid}/decision")
def decide(iid:int,data:DecisionIn,u=Depends(permit("manager","admin")),db=Depends(get_db)):
    q=db.execute("SELECT id,status FROM inquiries WHERE id=?",(iid,)).fetchone()
    if not q:raise HTTPException(404,"Inquiry not found")
    if q["status"] in ("APPROVED","RETURNED"):
        raise HTTPException(409,"Inquiry already decided; repeat approval is not allowed")
    if q["status"]!="TECH_REVIEWED":
        raise HTTPException(409,"Technical review required before Manager decision")
    if data.decision=="APPROVE":
        accepted=db.execute("""SELECT 1 FROM reviews v JOIN runs r ON r.id=v.run_id
          WHERE r.inquiry_id=? AND v.decision='ACCEPT' AND v.label=3
          AND v.id=(SELECT MAX(v2.id) FROM reviews v2
                    WHERE v2.run_id=v.run_id AND v2.product_id=v.product_id)
          LIMIT 1""",(iid,)).fetchone()
        if not accepted:
            raise HTTPException(409,"Manager approval requires a latest Technical ACCEPT with relevance label 3")
    status="APPROVED" if data.decision=="APPROVE" else "RETURNED"
    with db:
        db.execute("UPDATE inquiries SET status=? WHERE id=?",(status,iid))
        audit(db,u,"MANAGER_"+data.decision,"inquiry",iid,before={"status":q["status"]},after={"status":status})
    return {"status":status}
@app.get("/v1/analytics/summary")
def summary(u=Depends(permit("admin","sales","manager","technical","gudang")),db=Depends(get_db)):
    company_count=db.execute("SELECT COUNT(*) AS n FROM products WHERE source_ref='CATALOG-PDF-UNVERIFIED'").fetchone()["n"]
    return {"product_count":db.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"],
            "inquiry_count":db.execute("SELECT COUNT(*) AS total FROM inquiries").fetchone()["total"],
            "ai_matching":"LEXICAL_BASELINE_ONLY","bundling":"SYNTHETIC_DEMO",
            "forecast":"SYNTHETIC_DEMO",
            "data_classification":"COMPANY_CATALOG_UNVERIFIED" if company_count else "SYNTHETIC_DEMO",
            "catalog_source":"SUPPLIER_PDF_PENDING_TECHNICAL" if company_count else "SYNTHETIC_DEMO",
            "supplier_catalog_products":company_count,
            "stock_unknown_count":db.execute("SELECT COUNT(*) AS n FROM products WHERE stock IS NULL").fetchone()["n"],
            "expert_review_count":db.execute("""SELECT COUNT(*) AS n FROM reviews v JOIN users reviewer ON reviewer.id=v.reviewer_id
                JOIN runs r ON r.id=v.run_id JOIN inquiries i ON i.id=r.inquiry_id
                JOIN users creator ON creator.id=i.created_by
                WHERE LOWER(reviewer.email) NOT LIKE 'uat-%%@liliang.local'
                  AND LOWER(creator.email) NOT LIKE 'uat-%%@liliang.local'
                  AND UPPER(COALESCE(i.customer_ref,'')) NOT LIKE 'UAT-%%'""").fetchone()["n"],
            "uat_review_count":db.execute("""SELECT COUNT(*) AS n FROM reviews v JOIN users u ON u.id=v.reviewer_id
                WHERE LOWER(u.email) LIKE 'uat-%%@liliang.local'""").fetchone()["n"],
            "user_count":db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"],
            "audit_event_count":db.execute("SELECT COUNT(*) AS n FROM transaction_events").fetchone()["n"]}
from multi_ai import mount_ai, score_products
mount_ai(app,current,get_db)
from sales_intelligence import mount_sales_intelligence
mount_sales_intelligence(app,current,get_db,audit)
from demo_readiness import mount_demo_readiness
mount_demo_readiness(app,current,get_db)
from company_model_governance import mount_company_governance
mount_company_governance(app,current,get_db)
from research.evidence import mount_research
mount_research(app,current,get_db)
from enterprise_ops import mount_enterprise
mount_enterprise(app,current,get_db,audit,ph)
from reports import mount_reports
mount_reports(app,current,get_db)
@app.get("/branding/logo",include_in_schema=False)
def official_brand_logo():
    """Serve permanent corporate branding asset included in this deployment."""
    logo_path=Path(__file__).resolve().parent/"static"/"branding"/"liliang-official.jpg"
    return FileResponse(logo_path,media_type="image/jpeg",
        headers={"Cache-Control":"public, max-age=3600, must-revalidate",
                 "X-Content-Type-Options":"nosniff"})

from rich_ui import html_page

# Actual server-side page routes; every navigation has its own fresh HTML response.
# API data remains authoritative in Neon PostgreSQL and is fetched on every load.
PAGE_ROUTES = {
    "/":"hub", "/workspace":"hub", "/ai/hybrid":"hybrid",
    "/ai/evidence":"research", "/ai/status":"systems",
    "/ai/data-readiness":"datareadiness",
    "/learning/center":"learning",
    "/dashboard":"overview", "/inquiries":"inquiries",
    "/catalog":"catalog", "/sales/bundling":"bundling",
    "/inventory/forecast":"forecast", "/admin/users":"users",
    "/admin/roles":"roles", "/admin/catalog-migration":"migration",
    "/admin/audit":"audit", "/reports":"reports"
}

@app.middleware("http")
async def disable_device_cache(request:Request, call_next):
    response=await call_next(request)
    # Record authenticated access-denied / business-conflict attempts without
    # logging request bodies, JWTs or anonymous customer requirements.
    if (response.status_code in (403,409) and request.url.path.startswith("/v1/")
            and not request.url.path.startswith("/v1/auth/")):
        try:
            bearer=request.headers.get("authorization","")
            if bearer.lower().startswith("bearer "):
                claims=jwt.decode(bearer[7:],SECRET_KEY,algorithms=["HS256"])
                with connect() as trace_db:
                    u=trace_db.execute("SELECT id,role FROM users WHERE id=?",
                                       (int(claims["sub"]),)).fetchone()
                    session=trace_db.execute("SELECT id FROM user_sessions WHERE id=? AND user_id=? AND revoked_at IS NULL",
                                             (claims.get("sid"),int(claims["sub"]))).fetchone()
                    if u and session:
                        from enterprise_ops import append_event
                        append_event(trace_db,dict(u),
                          "ACCESS_DENIED_403" if response.status_code==403 else "BUSINESS_CONFLICT_409",
                          "http_request",0,after={"method":request.method,
                          "path":request.url.path,"http_status":response.status_code})
        except Exception:
            # Audit availability must not disrupt the business response.
            pass
    if request.url.path in PAGE_ROUTES or request.url.path.startswith("/v1/"):
        response.headers["Cache-Control"]="private, no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"]="no-cache"
        response.headers["Expires"]="0"
        response.headers["Vary"]="Authorization, Cookie"
    return response

def page_view(page_name:str):
    response=HTMLResponse(html_page())
    response.headers["X-ERP-Page"]=page_name
    response.headers["X-ERP-Data-Source"]="server"
    return response

@app.get("/",response_class=HTMLResponse,include_in_schema=False)
def index():
    return page_view("hub")

@app.get("/workspace",response_class=HTMLResponse,include_in_schema=False)
@app.get("/ai/hybrid",response_class=HTMLResponse,include_in_schema=False)
@app.get("/ai/evidence",response_class=HTMLResponse,include_in_schema=False)
@app.get("/ai/status",response_class=HTMLResponse,include_in_schema=False)
@app.get("/ai/data-readiness",response_class=HTMLResponse,include_in_schema=False)
@app.get("/learning/center",response_class=HTMLResponse,include_in_schema=False)
@app.get("/dashboard",response_class=HTMLResponse,include_in_schema=False)
@app.get("/inquiries",response_class=HTMLResponse,include_in_schema=False)
@app.get("/catalog",response_class=HTMLResponse,include_in_schema=False)
@app.get("/sales/bundling",response_class=HTMLResponse,include_in_schema=False)
@app.get("/inventory/forecast",response_class=HTMLResponse,include_in_schema=False)
@app.get("/admin/users",response_class=HTMLResponse,include_in_schema=False)
@app.get("/admin/roles",response_class=HTMLResponse,include_in_schema=False)
@app.get("/admin/catalog-migration",response_class=HTMLResponse,include_in_schema=False)
@app.get("/admin/audit",response_class=HTMLResponse,include_in_schema=False)
@app.get("/reports",response_class=HTMLResponse,include_in_schema=False)
def all_pages(request:Request):
    return page_view(PAGE_ROUTES[request.url.path])

HTML="""<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PT Liliang | ERP Multi-AI</title><style>
:root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#18324f;background:#f4f7fb}*{box-sizing:border-box}
header{padding:18px 25px;background:#142d56;color:white;display:flex;align-items:center;justify-content:space-between}header b{font-size:20px}header small{display:block;color:#a7d2ff;margin-top:3px}
main{max-width:1150px;margin:28px auto;padding:0 18px}.panel{background:white;border:1px solid #dfebf4;border-radius:14px;padding:23px;margin-bottom:18px;box-shadow:0 4px 22px #193d6510}
h1{font-size:28px}h2{font-size:18px;margin:0 0 16px}.muted{color:#6a8199}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}
label{display:block;font-size:13px;font-weight:600;margin:11px 0 6px}input,textarea,select{width:100%;border:1px solid #c6d8e6;border-radius:8px;padding:11px;font:inherit}textarea{min-height:75px}button{border:0;border-radius:8px;padding:11px 16px;background:#2464ba;color:white;font-weight:600;cursor:pointer;margin-top:12px}button:disabled{opacity:.5}
button.alt{background:#e6effb;color:#205291}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #e6edf5;font-size:13px}th{background:#f3f7fc}.scroll{overflow:auto}
.notice{border-left:4px solid #efa64c;background:#fff9ed;padding:12px;margin:15px 0}nav button{margin:6px 6px 0 0}.error{color:#b32727}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}
</style></head><body><header><div><b>PT LILIANG · ERP Multi-AI</b><small>Research Development Pilot · Synthetic data only</small></div><div id="who"></div></header><main><div class="notice"><strong>DEMO / FREE CLOUD:</strong> No real customer or flavor datasheet data. Database on Render Free ephemeral; restarts may erase changes. AI matching is a lexical baseline, not a validated hybrid model.</div><div id="content"></div></main><script>
let token=sessionStorage.getItem("liliang_token")||"",user=null;
const el=x=>document.getElementById(x),esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function api(path,options={}){const r=await fetch(path,{...options,headers:{"Content-Type":"application/json",...(token?{"Authorization":"Bearer "+token}:{}),...(options.headers||{})}});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==="string"?d.detail:JSON.stringify(d));return d}
function loginView(){el("content").innerHTML='<section class="panel" style="max-width:480px;margin:auto"><h1>Masuk ke ERP</h1><p class="muted">Akun awal dibuat melalui environment server. Admin dapat membuat akun empat role lainnya.</p><form id="form"><label>Email</label><input name="email" type="email" required><label>Password</label><input name="password" type="password" required><button>Login</button></form><p class="error" id="err"></p></section>';el("form").onsubmit=async e=>{e.preventDefault();try{const d=await api("/v1/auth/login",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});token=d.access_token;sessionStorage.setItem("liliang_token",token);user=d.user;show()}catch(err){el("err").textContent=err.message}}}
async function show(){try{user=await api("/v1/auth/me")}catch{token="";sessionStorage.removeItem("liliang_token");loginView();return}
el("who").innerHTML=esc(user.name)+" ("+esc(user.role)+') <button class="alt" onclick="logout()">Keluar</button>';
el("content").innerHTML='<nav><button onclick="dashboard()">Dashboard</button><button onclick="catalog()">Katalog</button><button onclick="work()">Inquiry & Matching</button>'+(user.role==="admin"?'<button onclick="users()">User Management</button>':"")+'</nav><div id="view" style="margin-top:16px"></div>';await dashboard()}
function logout(){sessionStorage.removeItem("liliang_token");token="";user=null;el("who").textContent="";loginView()}
async function dashboard(){try{const s=await api("/v1/analytics/summary");el("view").innerHTML='<h1>Dashboard Operasional</h1><div class="grid"><div class="panel"><h2>Master Flavor</h2><h1>'+s.product_count+'</h1></div><div class="panel"><h2>Customer Inquiries</h2><h1>'+s.inquiry_count+'</h1></div><div class="panel"><h2>AI-02 Matching</h2><p>Lexical baseline</p></div><div class="panel"><h2>AI-03/04</h2><p>Bundling dan forecasting: tahap selanjutnya</p></div></div>'}catch(e){alert(e.message)}}
async function catalog(){try{const p=await api("/v1/products");el("view").innerHTML='<section class="panel"><h2>Product Flavor Catalog</h2><div class="scroll"><table><thead><tr><th>SKU</th><th>Product</th><th>Profile</th><th>Application</th><th>Stock</th><th>Source</th></tr></thead><tbody>'+p.map(x=>'<tr><td>'+esc(x.sku)+'</td><td>'+esc(x.name)+'</td><td>'+esc(x.profile)+'</td><td>'+esc(x.application)+'</td><td>'+x.stock+'</td><td>'+esc(x.source_ref)+'</td></tr>').join("")+'</tbody></table></div></section>'}catch(e){alert(e.message)}}
async function work(){try{const rows=await api("/v1/inquiries");let entry=user.role==="sales"||user.role==="admin"?'<section class="panel"><h2>Customer Inquiry</h2><form id="inq"><label>Customer reference (anonymous)</label><input name="customer_ref" value="ANON" required><label>Kebutuhan flavor</label><textarea name="requirement" required minlength="5" placeholder="Contoh: Butuh strawberry flavor untuk minuman dairy"></textarea><button>Buat Inquiry</button></form></section>':"";
el("view").innerHTML=entry+'<section class="panel"><h2>Inquiry & Workflow</h2><div class="scroll"><table><thead><tr><th>#</th><th>Customer</th><th>Requirement</th><th>Status</th><th>Actions</th></tr></thead><tbody>'+rows.map(x=>'<tr><td>'+x.id+'</td><td>'+esc(x.customer_ref||"Restricted")+'</td><td>'+esc(x.requirement||"Restricted")+'</td><td>'+esc(x.status)+'</td><td><button class="alt" onclick="match('+x.id+')">Match</button> <button class="alt" onclick="approve('+x.id+')">Approval</button></td></tr>').join("")+'</tbody></table></div></section><div id="result"></div>';
if(el("inq"))el("inq").onsubmit=async e=>{e.preventDefault();try{await api("/v1/inquiries",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});await work()}catch(err){alert(err.message)}}}catch(e){alert(e.message)}}
async function match(id){try{const d=await api("/v1/inquiries/"+id+"/match",{method:"POST"});el("result").innerHTML='<section class="panel"><h2>Top-5 Shortlist · Run '+d.run_id+'</h2><p class="muted">'+esc(d.method)+' · '+d.latency_ms+' ms</p><div class="notice">'+esc(d.notice)+'</div><div class="scroll"><table><tr><th>Rank</th><th>SKU</th><th>Product</th><th>Score</th><th>UNKNOWN</th><th>Action</th></tr>'+d.candidates.map(x=>'<tr><td>'+x.rank+'</td><td>'+esc(x.sku)+'</td><td>'+esc(x.name)+'</td><td>'+x.score+'</td><td>'+esc(x.unknown_attributes.join(", "))+'</td><td><button class="alt" onclick="review('+d.run_id+','+x.product_id+')">Technical Review</button></td></tr>').join("")+'</table></div></section>'}catch(e){alert(e.message)}}
async function review(rid,pid){if(user.role!=="technical"){alert("Hanya role Technical");return}const rationale=prompt("Catatan Technical (min 5 karakter):");if(!rationale)return;const label=prompt("Expert relevance label 0-3","3");const decision=prompt("Decision: ACCEPT / REJECT / NEEDS_INFO","ACCEPT");try{await api("/v1/matches/"+rid+"/review",{method:"POST",body:JSON.stringify({product_id:pid,rationale,relevance_label:Number(label),decision})});alert("Expert review tersimpan");await work()}catch(e){alert(e.message)}}
async function approve(id){if(!["manager","admin"].includes(user.role)){alert("Manager/Admin only");return}const decision=prompt("Decision: APPROVE or RETURN","APPROVE");const note=prompt("Catatan keputusan (min 5 karakter)","Technical verified");try{const r=await api("/v1/inquiries/"+id+"/decision",{method:"POST",body:JSON.stringify({decision,note})});alert(r.status);await work()}catch(e){alert(e.message)}}
async function users(){if(user.role!=="admin")return;const list=await api("/v1/users");el("view").innerHTML='<div class="grid"><section class="panel"><h2>Buat Akun Internal</h2><form id="newuser"><label>Nama</label><input name="name" required><label>Email</label><input name="email" type="email" required><label>Password (min 12)</label><input name="password" type="password" minlength="12" required><label>Role</label><select name="role"><option>sales</option><option>technical</option><option>manager</option><option>gudang</option><option>admin</option></select><button>Create User</button></form></section><section class="panel"><h2>Registered Users</h2>'+list.map(x=>'<p>'+esc(x.email)+' · '+esc(x.role)+'</p>').join("")+'</section></div>';el("newuser").onsubmit=async e=>{e.preventDefault();try{await api("/v1/users",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});alert("User created");await users()}catch(err){alert(err.message)}}}
if(token)show();else loginView();
</script></body></html>"""

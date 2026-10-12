import os, re, time, sqlite3
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Literal
import jwt
from argon2 import PasswordHasher
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
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
DEMO=[
 ("FLV-STRAW-01","Strawberry Flavor","Ripe sweet strawberry for dairy beverages","strawberry","dairy"),
 ("FLV-VANI-02","Vanilla Flavor","Creamy vanilla for bakery and dairy","vanilla","bakery"),
 ("FLV-MANG-03","Mango Flavor","Tropical mango for beverages","mango","beverage"),
 ("FLV-CHOCO-04","Chocolate Flavor","Rich chocolate for dairy and bakery","chocolate","dairy"),
 ("FLV-LEMON-05","Lemon Flavor","Citrus lemon for cold beverages","lemon","beverage"),
]
def connect():
    db=sqlite3.connect(DB_PATH,timeout=20)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db
def boot():
    Path(DB_PATH).parent.mkdir(parents=True,exist_ok=True)
    with connect() as db:
        db.executescript("""
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE,name TEXT,description TEXT,profile TEXT,application TEXT,stock REAL DEFAULT 0,source_ref TEXT);
CREATE TABLE IF NOT EXISTS inquiries(id INTEGER PRIMARY KEY,requirement TEXT,customer_ref TEXT,created_by INTEGER,status TEXT DEFAULT 'NEW',created_at TEXT,FOREIGN KEY(created_by) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,inquiry_id INTEGER,method TEXT,latency_ms INTEGER,created_at TEXT,FOREIGN KEY(inquiry_id) REFERENCES inquiries(id));
CREATE TABLE IF NOT EXISTS candidates(id INTEGER PRIMARY KEY,run_id INTEGER,product_id INTEGER,score REAL,rank INTEGER,unknown TEXT,FOREIGN KEY(run_id) REFERENCES runs(id));
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,run_id INTEGER,product_id INTEGER,reviewer_id INTEGER,decision TEXT,label INTEGER,note TEXT);
CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,actor_id INTEGER,action TEXT,entity TEXT,entity_id INTEGER,at TEXT);
""")
        if not db.execute("SELECT id FROM users WHERE email=?",(ADMIN_EMAIL,)).fetchone():
            db.execute("INSERT INTO users(email,name,role,hash) VALUES(?,?,?,?)",(ADMIN_EMAIL,"ERP Administrator","admin",ph.hash(ADMIN_PASSWORD)))
        for sku,name,desc,profile,application in DEMO:
            db.execute("INSERT OR IGNORE INTO products(sku,name,description,profile,application,stock,source_ref) VALUES(?,?,?,?,?,?,?)",
                       (sku,name,desc,profile,application,0,"DEMO-ONLY"))
def now():return datetime.now(timezone.utc).isoformat()
def audit(db,user,action,entity,id):
    db.execute("INSERT INTO audits(actor_id,action,entity,entity_id,at) VALUES(?,?,?,?,?)",(user["id"],action,entity,id,now()))
def to_dict(row):return dict(row) if row is not None else None
@asynccontextmanager
async def lifespan(app):
    boot()
    yield
app=FastAPI(title="PT Liliang ERP Multi-AI — DEMO PILOT",version="0.1.0",lifespan=lifespan)
def get_db():
    db=connect()
    try: yield db
    finally:db.close()
def current(creds:HTTPAuthorizationCredentials|None=Depends(auth),db:sqlite3.Connection=Depends(get_db)):
    if not creds:raise HTTPException(401,"Login required")
    try:
        claim=jwt.decode(creds.credentials,SECRET_KEY,algorithms=["HS256"])
        row=db.execute("SELECT id,email,name,role FROM users WHERE id=?",(int(claim["sub"]),)).fetchone()
        if not row:raise ValueError()
        return dict(row)
    except (jwt.PyJWTError,ValueError,KeyError):
        raise HTTPException(401,"Invalid or expired token")
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
@app.get("/healthz")
def health():return {"status":"ok","environment":"DEMO","persistent_database":False}
@app.get("/readyz")
def ready(db=Depends(get_db)):
    db.execute("SELECT 1").fetchone()
    return {"ready":True}
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
    token=jwt.encode({"sub":str(u["id"]),"exp":datetime.now(timezone.utc)+timedelta(hours=8)},SECRET_KEY,algorithm="HS256")
    return {"access_token":token,"user":{"id":u["id"],"role":u["role"],"name":u["name"]}}
@app.get("/v1/auth/me")
def me(u=Depends(current)):return u
@app.post("/v1/users",status_code=201)
def add_user(data:NewUser,u=Depends(permit("admin")),db=Depends(get_db)):
    try:
        with db:
            cur=db.execute("INSERT INTO users(email,name,role,hash) VALUES(?,?,?,?)",(data.email.lower().strip(),data.name,data.role,ph.hash(data.password)))
            audit(db,u,"CREATE_USER","user",cur.lastrowid)
        return {"id":cur.lastrowid,"role":data.role}
    except sqlite3.IntegrityError:raise HTTPException(409,"Email already exists")
@app.get("/v1/users")
def users(u=Depends(permit("admin")),db=Depends(get_db)):
    return [dict(x) for x in db.execute("SELECT id,email,name,role FROM users ORDER BY id").fetchall()]
@app.get("/v1/products")
def products(u=Depends(current),db=Depends(get_db)):
    return [dict(x) for x in db.execute("SELECT * FROM products ORDER BY sku").fetchall()]
@app.patch("/v1/products/{pid}/stock")
def stock(pid:int,data:StockIn,u=Depends(permit("admin","gudang")),db=Depends(get_db)):
    with db:
        c=db.execute("UPDATE products SET stock=? WHERE id=?",(data.stock_qty,pid))
        if not c.rowcount:raise HTTPException(404,"SKU not found")
        audit(db,u,"STOCK_UPDATE","product",pid)
    return {"product_id":pid,"stock_qty":data.stock_qty}
@app.post("/v1/inquiries",status_code=201)
def new_inquiry(data:InquiryIn,u=Depends(permit("sales","admin")),db=Depends(get_db)):
    with db:
        cur=db.execute("INSERT INTO inquiries(requirement,customer_ref,created_by,status,created_at) VALUES(?,?,?,'NEW',?)",
                (data.requirement,data.customer_ref,u["id"],now()))
        audit(db,u,"NEW_INQUIRY","inquiry",cur.lastrowid)
    return {"id":cur.lastrowid,"status":"NEW"}
@app.get("/v1/inquiries")
def inquiries(u=Depends(current),db=Depends(get_db)):
    sql="SELECT * FROM inquiries";params=()
    if u["role"]=="sales":
        sql+=" WHERE created_by=?";params=(u["id"],)
    records=[dict(x) for x in db.execute(sql+" ORDER BY id DESC",params).fetchall()]
    if u["role"]=="gudang":
        for x in records:x.pop("requirement",None);x.pop("customer_ref",None)
    return records
@app.post("/v1/inquiries/{iid}/match")
def match(iid:int,u=Depends(permit("sales","admin","technical")),db=Depends(get_db)):
    q=db.execute("SELECT * FROM inquiries WHERE id=?",(iid,)).fetchone()
    if not q:raise HTTPException(404,"Inquiry not found")
    if u["role"]=="sales" and q["created_by"]!=u["id"]:raise HTTPException(403,"Not your inquiry")
    t=time.monotonic()
    candidates=score_products(q["requirement"],db.execute("SELECT * FROM products").fetchall())
    elapsed=int((time.monotonic()-t)*1000)
    with db:
        run=db.execute("INSERT INTO runs(inquiry_id,method,latency_ms,created_at) VALUES(?,'bm25-expert-review-demo-v0.2',?,?)",(iid,elapsed,now()))
        for rank,item in enumerate(candidates,1):
            item["rank"]=rank
            db.execute("INSERT INTO candidates(run_id,product_id,score,rank,unknown) VALUES(?,?,?,?,?)",
                     (run.lastrowid,item["product_id"],item["score"],rank,",".join(item["unknown_attributes"])))
        db.execute("UPDATE inquiries SET status='MATCHED' WHERE id=?",(iid,))
        audit(db,u,"MATCH_BASELINE","run",run.lastrowid)
    return {"run_id":run.lastrowid,"method":"bm25-expert-review-demo-v0.2","latency_ms":elapsed,
            "candidates":candidates,"notice":"BM25 lexical retrieval demo only: neural embeddings, factual evidence and validation pending. Technical review required."}
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
    with db:
        cur=db.execute("INSERT INTO reviews(run_id,product_id,reviewer_id,decision,label,note) VALUES(?,?,?,?,?,?)",
                       (rid,data.product_id,u["id"],data.decision,data.relevance_label,data.rationale))
        db.execute("UPDATE inquiries SET status='TECH_REVIEWED' WHERE id=?",(q["inquiry_id"],))
        audit(db,u,"EXPERT_REVIEW","review",cur.lastrowid)
    return {"review_id":cur.lastrowid,"status":"TECH_REVIEWED"}
@app.post("/v1/inquiries/{iid}/decision")
def decide(iid:int,data:DecisionIn,u=Depends(permit("manager","admin")),db=Depends(get_db)):
    q=db.execute("SELECT id,status FROM inquiries WHERE id=?",(iid,)).fetchone()
    if not q:raise HTTPException(404,"Inquiry not found")
    if q["status"]!="TECH_REVIEWED":raise HTTPException(409,"Expert review required")
    if data.decision=="APPROVE":
        accepted=db.execute("""SELECT 1 FROM reviews v JOIN runs r ON r.id=v.run_id
          WHERE r.inquiry_id=? AND v.decision='ACCEPT' LIMIT 1""",(iid,)).fetchone()
        if not accepted:raise HTTPException(409,"At least one accepted Technical review required")
    status="APPROVED" if data.decision=="APPROVE" else "RETURNED"
    with db:
        db.execute("UPDATE inquiries SET status=? WHERE id=?",(status,iid))
        audit(db,u,"MANAGER_"+data.decision,"inquiry",iid)
    return {"status":status}
@app.get("/v1/analytics/summary")
def summary(u=Depends(permit("admin","sales","manager","technical","gudang")),db=Depends(get_db)):
    return {"product_count":db.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "inquiry_count":db.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0],
            "ai_matching":"LEXICAL_BASELINE_ONLY","bundling":"NOT_IMPLEMENTED",
            "forecast":"NOT_IMPLEMENTED","data_classification":"SYNTHETIC_DEMO"}
from multi_ai import mount_ai, score_products
mount_ai(app,current,get_db)
from rich_ui import html_page

@app.get("/",response_class=HTMLResponse,include_in_schema=False)
def index():return html_page()
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

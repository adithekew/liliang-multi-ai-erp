"""Sales-first sample delivery lifecycle for the Liliang research UAT.

Isolated sample stock and all Surat Jalan artifacts are VIRTUAL UAT ONLY.
Do not use this to ship real goods. Existing company product stock is never mutated.
"""
import io
import re
import secrets
from datetime import datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

STATES = ("WAITING_TECHNICAL", "WAITING_MANAGER", "WAITING_WAREHOUSE",
          "WAREHOUSE_READY", "DISPATCHED_UAT", "RETURNED")
STEPS = [
    {"name": "SALES", "subtitle": "Inquiry, AI Top-5 & Submit"},
    {"name": "TECHNICAL", "subtitle": "SKU Review & Submit"},
    {"name": "MANAGER OPERASIONAL", "subtitle": "Review & Approval"},
    {"name": "GUDANG", "subtitle": "Check Stok & Surat Jalan"},
    {"name": "COMPLETED", "subtitle": "Sampel UAT Dispatched"},
]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def install_sample_schema(db):
    """Additive, safe on existing SQLite and Neon/PostgreSQL databases."""
    db.execute("""CREATE TABLE IF NOT EXISTS sample_requests(
      inquiry_id INTEGER PRIMARY KEY,run_id INTEGER NOT NULL,
      product_id INTEGER,qty_kg REAL NOT NULL,recipient TEXT NOT NULL,
      destination TEXT NOT NULL,note TEXT NOT NULL,status TEXT NOT NULL,
      surat_jalan TEXT UNIQUE,dispatched_at TEXT,created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS sample_uat_balances(
      sku TEXT PRIMARY KEY,qty_kg REAL NOT NULL DEFAULT 0)""")
    db.execute("""CREATE TABLE IF NOT EXISTS sample_uat_movements(
      reference TEXT PRIMARY KEY,sku TEXT NOT NULL,
      movement TEXT NOT NULL,qty_kg REAL NOT NULL,
      inquiry_id INTEGER,actor_id INTEGER NOT NULL,at TEXT NOT NULL,note TEXT NOT NULL)""")

class SalesSubmit(BaseModel):
    qty_kg: float = Field(gt=0, le=1000, allow_inf_nan=False)
    recipient: str = Field(min_length=5, max_length=100)
    destination: str = Field(min_length=5, max_length=180)
    note: str = Field(min_length=5, max_length=300)

class TechnicalSubmit(BaseModel):
    product_id: int = Field(gt=0)
    note: str = Field(min_length=5,max_length=300)

class WarehouseStock(BaseModel):
    sku: str = Field(min_length=3,max_length=90)
    qty_kg: float = Field(gt=0,le=10000,allow_inf_nan=False)
    reference: str = Field(min_length=8,max_length=70)
    note: str = Field(min_length=5,max_length=180)
    acknowledge_virtual_only: bool = False

class WarehouseAction(BaseModel):
    note: str = Field(min_length=5, max_length=300)
    acknowledge_virtual_only: bool = False

def _permission(user, inquiry, sample, role=None):
    if role is not None and user["role"] != role:
        raise HTTPException(403, "This step belongs to the assigned role")
    if user["role"] == "sales" and inquiry["created_by"] != user["id"]:
        raise HTTPException(403, "Not your inquiry")
    if user["role"] == "gudang":
        if not sample or sample["status"] not in ("WAITING_WAREHOUSE","WAREHOUSE_READY","DISPATCHED_UAT"):
            raise HTTPException(403, "Warehouse can only see Manager-approved sample work")

def _context(db, iid, user):
    q=db.execute("SELECT * FROM inquiries WHERE id=?",(iid,)).fetchone()
    if not q:raise HTTPException(404,"Inquiry not found")
    s=db.execute("SELECT * FROM sample_requests WHERE inquiry_id=?",(iid,)).fetchone()
    inquiry=dict(q)
    sample=dict(s) if s else None
    _permission(user,inquiry,sample)
    return inquiry,sample

def _latest_run(db,iid):
    r=db.execute("SELECT id,method,latency_ms,created_at FROM runs WHERE inquiry_id=? ORDER BY id DESC LIMIT 1",(iid,)).fetchone()
    return dict(r) if r else None

def _candidates(db,run_id):
    if not run_id:return []
    return [dict(x) for x in db.execute("""SELECT c.rank,p.id product_id,p.sku,p.name,p.source_ref,
           c.score,c.unknown,
           (SELECT v.decision FROM reviews v WHERE v.run_id=c.run_id AND v.product_id=c.product_id ORDER BY v.id DESC LIMIT 1) AS technical_decision,
           (SELECT v.label FROM reviews v WHERE v.run_id=c.run_id AND v.product_id=c.product_id ORDER BY v.id DESC LIMIT 1) AS technical_label,
           (SELECT v.note FROM reviews v WHERE v.run_id=c.run_id AND v.product_id=c.product_id ORDER BY v.id DESC LIMIT 1) AS technical_note
           FROM candidates c JOIN products p ON p.id=c.product_id
           WHERE c.run_id=? ORDER BY c.rank""",(run_id,)).fetchall()]

def _check_accepted(db,run_id,product_id):
    review=db.execute("""SELECT v.decision,v.label FROM reviews v
        WHERE v.run_id=? AND v.product_id=? ORDER BY v.id DESC LIMIT 1""",(run_id,product_id)).fetchone()
    included=db.execute("SELECT 1 FROM candidates WHERE run_id=? AND product_id=?",(run_id,product_id)).fetchone()
    return bool(included and review and review["decision"]=="ACCEPT" and review["label"]==3)

def _balance(db,sku):
    r=db.execute("SELECT qty_kg FROM sample_uat_balances WHERE sku=?",(sku,)).fetchone()
    return round(float(r["qty_kg"]),3) if r else 0.0

def _status_index(inquiry,sample):
    if sample:
        return {"WAITING_TECHNICAL":1,"WAITING_MANAGER":2,"WAITING_WAREHOUSE":3,
                "WAREHOUSE_READY":3,"DISPATCHED_UAT":4,"RETURNED":0}.get(sample["status"],0)
    return {"NEW":0,"NO_MATCH":0,"MATCHED":0,"TECH_REVIEWED":1,
            "APPROVED":3,"RETURNED":0}.get(inquiry["status"],0)

def _as_transaction(db,inquiry,sample,user):
    run=_latest_run(db,inquiry["id"])
    candidates=_candidates(db,run["id"] if run else None) if user["role"]!="gudang" else []
    selected=None
    if sample and sample.get("product_id"):
        row=db.execute("SELECT sku,name,source_ref FROM products WHERE id=?",(sample["product_id"],)).fetchone()
        if row:selected=dict(row)
    stock_reference=None
    if selected:
        reported=db.execute("""SELECT reported_stock,unit,verification_status,source_ref
          FROM catalog_stock_reference WHERE sku=?""",(selected["sku"],)).fetchone()
        if reported:stock_reference=dict(reported)
    events=[dict(x) for x in db.execute("""SELECT action,actor_role,at FROM transaction_events
        WHERE (entity='inquiry' AND entity_id=?) OR (entity='sample_request' AND entity_id=?)
        ORDER BY at DESC LIMIT 30""",(str(inquiry["id"]),str(inquiry["id"]))).fetchall()]
    visible=dict(inquiry)
    if user["role"]=="gudang":
        visible["requirement"]=None
        visible["customer_ref"]="UAT-REDACTED"
    return {
        "inquiry":visible,"sample":sample,"latest_run":run if user["role"]!="gudang" else None,
        "candidates":candidates,"selected_product":selected,
        "virtual_stock_kg":_balance(db,selected["sku"]) if selected else None,
        "csv_stock_reference":stock_reference,
        "timeline": STEPS,"current_step":_status_index(inquiry,sample),
        "activity":events,"scope":"UAT_VIRTUAL_STOCK_NOT_REAL_COMPANY_WAREHOUSE",
        "actual_stock_verified":False,"valid_for_physical_shipment":False,
    }

def _require_uat(value):
    if not str(value).strip().upper().startswith("UAT-"):
        raise HTTPException(422,"Use only UAT- anonymized/fictitious recipient and destination")

def mount_sample_flow(app,current,get_db,audit):
    @app.get("/v1/transactions")
    def transactions(u=Depends(current),db=Depends(get_db)):
        if u["role"]=="sales":
            rs=db.execute("""SELECT i.id,i.created_at,i.status,i.customer_ref,s.status sample_status
              FROM inquiries i LEFT JOIN sample_requests s ON s.inquiry_id=i.id
              WHERE i.created_by=? ORDER BY i.id DESC LIMIT 100""",(u["id"],)).fetchall()
        elif u["role"]=="gudang":
            rs=db.execute("""SELECT i.id,i.created_at,i.status,
              'UAT-REDACTED' customer_ref,s.status sample_status
              FROM inquiries i JOIN sample_requests s ON s.inquiry_id=i.id
              WHERE s.status IN ('WAITING_WAREHOUSE','WAREHOUSE_READY','DISPATCHED_UAT')
              ORDER BY i.id DESC LIMIT 100""").fetchall()
        else:
            rs=db.execute("""SELECT i.id,i.created_at,i.status,i.customer_ref,s.status sample_status
              FROM inquiries i LEFT JOIN sample_requests s ON s.inquiry_id=i.id
              ORDER BY i.id DESC LIMIT 100""").fetchall()
        return {"rows":[dict(x) for x in rs],"role":u["role"],
                "scope":"RESEARCH_PILOT_UAT_SAMPLE_DISPATCH_ONLY"}

    @app.get("/v1/transactions/{iid}")
    def transaction(iid:int,u=Depends(current),db=Depends(get_db)):
        inquiry,sample=_context(db,iid,u)
        return _as_transaction(db,inquiry,sample,u)

    @app.post("/v1/transactions/{iid}/sales-submit")
    def sales_submit(iid:int,data:SalesSubmit,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="sales":
            raise HTTPException(403,"Only Sales submits new sample inquiries")
        inquiry,sample=_context(db,iid,u)
        if inquiry["status"]!="MATCHED":
            raise HTTPException(409,"Sales requires an existing fresh BM25 candidate shortlist")
        _require_uat(data.recipient)
        _require_uat(data.destination)
        if inquiry["customer_ref"] and inquiry["customer_ref"].upper() not in ("ANON","UAT") and not inquiry["customer_ref"].upper().startswith("UAT-"):
            raise HTTPException(422,"This UAT pilot accepts only anonymized UAT customer reference")
        run=_latest_run(db,iid)
        if not run or not _candidates(db,run["id"]):
            raise HTTPException(409,"No Top-5 candidate; ask for clarification instead")
        if sample and sample["status"]!="RETURNED":
            raise HTTPException(409,"Already submitted")
        with db:
            if sample:
                db.execute("""UPDATE sample_requests SET run_id=?,product_id=NULL,qty_kg=?,
                  recipient=?,destination=?,note=?,status='WAITING_TECHNICAL',
                  surat_jalan=NULL,dispatched_at=NULL,updated_at=? WHERE inquiry_id=?""",
                  (run["id"],data.qty_kg,data.recipient,data.destination,data.note,utc_now(),iid))
            else:
                db.execute("""INSERT INTO sample_requests
                 (inquiry_id,run_id,product_id,qty_kg,recipient,destination,note,status,
                  surat_jalan,dispatched_at,created_at,updated_at)
                 VALUES(?,?,NULL,?,?,?,?,'WAITING_TECHNICAL',NULL,NULL,?,?)""",
                 (iid,run["id"],data.qty_kg,data.recipient,data.destination,data.note,utc_now(),utc_now()))
            audit(db,u,"SAMPLE_SALES_SUBMIT","sample_request",iid,
                  after={"run_id":run["id"],"qty_kg":data.qty_kg,
                         "data_scope":"UAT_ONLY","next":"TECHNICAL"})
        return {"inquiry_id":iid,"sample_status":"WAITING_TECHNICAL","run_id":run["id"]}

    @app.post("/v1/transactions/{iid}/technical-submit")
    def tech_submit(iid:int,data:TechnicalSubmit,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="technical":
            raise HTTPException(403,"Only Technical can submit reviewed product")
        inquiry,sample=_context(db,iid,u)
        if not sample or sample["status"]!="WAITING_TECHNICAL" or inquiry["status"]!="TECH_REVIEWED":
            raise HTTPException(409,"Sales submission and Technical review required")
        run=_latest_run(db,iid)
        if not run or run["id"]!=sample["run_id"] or not _check_accepted(db,run["id"],data.product_id):
            raise HTTPException(409,"Selected SKU requires latest-run Technical ACCEPT label 3")
        with db:
            updated=db.execute("""UPDATE sample_requests SET product_id=?,note=?,
                  status='WAITING_MANAGER',updated_at=? WHERE inquiry_id=? AND status='WAITING_TECHNICAL'""",
                  (data.product_id,data.note,utc_now(),iid))
            if updated.rowcount!=1:raise HTTPException(409,"Technical stage already submitted")
            audit(db,u,"SAMPLE_TECHNICAL_SUBMIT","sample_request",iid,
                  after={"product_id":data.product_id,"run_id":run["id"],"next":"MANAGER"})
        return {"inquiry_id":iid,"sample_status":"WAITING_MANAGER",
                "selected_product_id":data.product_id}

    @app.post("/v1/sample-stock/uat-in")
    def stock_in(data:WarehouseStock,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="gudang":
            raise HTTPException(403,"Only Gudang may record virtual sample stock")
        if not data.acknowledge_virtual_only:
            raise HTTPException(422,"Acknowledge virtual UAT stock only")
        if not re.fullmatch(r"UAT-[A-Za-z0-9._/-]{5,66}",data.reference):
            raise HTTPException(422,"UAT- reference required")
        sku=data.sku.strip()
        product=db.execute("SELECT id FROM products WHERE sku=?",(sku,)).fetchone()
        if not product:raise HTTPException(404,"SKU does not exist in catalog")
        if not db.execute("""SELECT 1 FROM sample_requests s JOIN products p ON p.id=s.product_id
            WHERE p.sku=? AND s.status IN ('WAITING_WAREHOUSE','WAREHOUSE_READY') LIMIT 1""",(sku,)).fetchone():
            raise HTTPException(409,"SKU must belong to a Manager-approved sample request")
        if db.execute("SELECT 1 FROM sample_uat_movements WHERE reference=?",(data.reference,)).fetchone():
            raise HTTPException(409,"Duplicate UAT reference")
        with db:
            db.execute("""INSERT INTO sample_uat_balances(sku,qty_kg) VALUES(?,?)
                ON CONFLICT(sku) DO UPDATE SET qty_kg=sample_uat_balances.qty_kg + excluded.qty_kg""",
                (sku,data.qty_kg))
            db.execute("""INSERT INTO sample_uat_movements
                (reference,sku,movement,qty_kg,inquiry_id,actor_id,at,note)
                VALUES(?,?,'IN',?,NULL,?,?,?)""",
                (data.reference,sku,data.qty_kg,u["id"],utc_now(),data.note))
            audit(db,u,"SAMPLE_UAT_STOCK_IN","sample_request",product["id"],
                  after={"sku":sku,"qty_kg":data.qty_kg,"mode":"VIRTUAL_NOT_PHYSICAL"})
        return {"sku":sku,"virtual_balance_kg":_balance(db,sku),
                "changed_real_stock":False}

    @app.post("/v1/transactions/{iid}/warehouse-check")
    def warehouse_check(iid:int,data:WarehouseAction,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="gudang":
            raise HTTPException(403,"Only Gudang checks sample stock")
        if not data.acknowledge_virtual_only:
            raise HTTPException(422,"Virtual UAT stock acknowledgment required")
        inquiry,sample=_context(db,iid,u)
        if not sample or sample["status"]!="WAITING_WAREHOUSE" or inquiry["status"]!="APPROVED":
            raise HTTPException(409,"Manager approval must precede Gudang stock check")
        product=db.execute("SELECT sku FROM products WHERE id=?",(sample["product_id"],)).fetchone()
        if not product:raise HTTPException(409,"No Technical-selected SKU")
        available=_balance(db,product["sku"])
        if available + 1e-8 < float(sample["qty_kg"]):
            raise HTTPException(409,"Insufficient VIRTUAL sample stock; no Surat Jalan allowed")
        with db:
            changed=db.execute("""UPDATE sample_requests SET status='WAREHOUSE_READY',updated_at=?
                WHERE inquiry_id=? AND status='WAITING_WAREHOUSE'""",(utc_now(),iid))
            if changed.rowcount!=1:raise HTTPException(409,"Warehouse stage already changed")
            audit(db,u,"SAMPLE_UAT_STOCK_CHECK","sample_request",iid,
                  after={"sku":product["sku"],"virtual_balance_kg":available,
                         "required_qty_kg":sample["qty_kg"],"verified_physical":False})
        return {"sample_status":"WAREHOUSE_READY","sku":product["sku"],
                "available_virtual_kg":available,"real_stock_checked":False}

    @app.post("/v1/transactions/{iid}/warehouse-dispatch")
    def warehouse_dispatch(iid:int,data:WarehouseAction,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="gudang":
            raise HTTPException(403,"Only Gudang can issue Surat Jalan UAT")
        if not data.acknowledge_virtual_only:
            raise HTTPException(422,"Only virtual UAT documents are available")
        inquiry,sample=_context(db,iid,u)
        if not sample or sample["status"]!="WAREHOUSE_READY" or inquiry["status"]!="APPROVED":
            raise HTTPException(409,"Manager approval and stock readiness are required")
        product=db.execute("SELECT sku FROM products WHERE id=?",(sample["product_id"],)).fetchone()
        if not product:raise HTTPException(409,"Selected SKU missing")
        qty=float(sample["qty_kg"])
        sj="UAT-SJ-%06d-%s"%(iid,secrets.token_hex(3).upper())
        with db:
            stock=db.execute("""UPDATE sample_uat_balances SET qty_kg=qty_kg-?
                WHERE sku=? AND qty_kg>=?""",(qty,product["sku"],qty))
            if stock.rowcount!=1:
                raise HTTPException(409,"Insufficient current virtual balance; re-check required")
            state=db.execute("""UPDATE sample_requests SET status='DISPATCHED_UAT',
                surat_jalan=?,dispatched_at=?,updated_at=?
                WHERE inquiry_id=? AND status='WAREHOUSE_READY'""",
                (sj,utc_now(),utc_now(),iid))
            if state.rowcount!=1:raise HTTPException(409,"Duplicate dispatch prevented")
            db.execute("""INSERT INTO sample_uat_movements
                (reference,sku,movement,qty_kg,inquiry_id,actor_id,at,note)
                VALUES(?,?,'OUT',?,?,?,?,?)""",
                (sj,product["sku"],qty,iid,u["id"],utc_now(),data.note))
            audit(db,u,"SAMPLE_UAT_DISPATCH","sample_request",iid,
                  after={"surat_jalan":sj,"product_id":sample["product_id"],
                         "qty_kg":qty,"physical_shipment":False})
        return {"sample_status":"DISPATCHED_UAT","surat_jalan":sj,
                "virtual_balance_kg":_balance(db,product["sku"]),
                "pdf_url":"/v1/transactions/%d/surat-jalan"%iid,
                "physical_shipment":False}

    @app.get("/v1/transactions/{iid}/surat-jalan")
    def surat_jalan(iid:int,u=Depends(current),db=Depends(get_db)):
        inquiry,sample=_context(db,iid,u)
        if not sample or sample["status"]!="DISPATCHED_UAT":
            raise HTTPException(409,"Surat Jalan only after virtual stock dispatch")
        product=db.execute("SELECT sku,name FROM products WHERE id=?",(sample["product_id"],)).fetchone()
        if not product:raise HTTPException(409,"Selected product unavailable")
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.utils import simpleSplit
        b=io.BytesIO()
        c=Canvas(b,pagesize=A4)
        w,h=A4
        c.setFont("Helvetica-Bold",14)
        c.drawString(50,h-58,"PT. LILIANG INTERNATIONAL - SURAT JALAN UAT")
        c.setFont("Helvetica-Bold",10)
        c.setFillColorRGB(.80,.12,.12)
        c.drawString(50,h-80,"SIMULASI PENELITIAN - TIDAK SAH UNTUK PENGIRIMAN FISIK")
        c.setFillColorRGB(0,0,0)
        lines=[
            ("Nomor Dokumen",sample["surat_jalan"]),
            ("Inquiry",str(iid)),("Tanggal UAT",sample["dispatched_at"][:19]),
            ("Penerima (fiktif)",sample["recipient"]),
            ("Tujuan (fiktif)",sample["destination"]),
            ("SKU",product["sku"]),("Produk",product["name"]),
            ("Jumlah Sampel",str(sample["qty_kg"])+" KG"),
            ("Sumber Stok","VIRTUAL UAT ONLY - BUKAN STOK FISIK"),
            ("Status","DISPATCHED_UAT (simulasi)"),
        ]
        y=h-125
        for label,value in lines:
            c.setFont("Helvetica-Bold",10);c.drawString(50,y,label+" :")
            c.setFont("Helvetica",10)
            for item in simpleSplit(str(value or ""), "Helvetica",10,350):
                c.drawString(205,y,item);y-=14
            y-=12
        c.setFont("Helvetica",9)
        c.drawString(50,130,"Gudang (UAT) : __________________")
        c.drawString(300,130,"Penerima (UAT) : __________________")
        c.setFont("Helvetica-Bold",8)
        c.drawString(50,65,"Validasi stok fisik, invoice dan serah terima pelanggan belum terhubung.")
        c.showPage();c.save()
        return Response(content=b.getvalue(),media_type="application/pdf",
            headers={"Content-Disposition":"attachment; filename="+sample["surat_jalan"]+".pdf",
                     "Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})

    @app.get("/transactions",response_class=HTMLResponse,include_in_schema=False)
    @app.get("/transactions/{iid}",response_class=HTMLResponse,include_in_schema=False)
    def transactions_page(iid:int=None):
        return HTMLResponse(PAGE,headers={"Cache-Control":"private, no-store"})

PAGE = r"""<!DOCTYPE html><html lang="id"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PT Liliang | Sales-to-Sample Workflow</title>
<link rel="icon" href="/branding/logo?v=20261020">
<style>
:root{font:14px/1.55 system-ui,Segoe UI,Arial;color:#1b304c;background:#f4f7fb}
*{box-sizing:border-box}body{margin:0}.layout{display:flex;min-height:100vh}
aside{width:238px;background:#10213a;color:#e1ecfa;flex-shrink:0;padding:20px 14px}
aside img{width:100%;background:black;border-radius:9px;margin-bottom:14px}
aside a{display:block;color:#d6e7fa;text-decoration:none;padding:14px;border-radius:9px;margin:8px 0;font-weight:650}
aside a.active,aside a:hover{background:#244c7b}aside small{color:#a3c2e2}
main{flex:1;min-width:0}.topbar{padding:17px 28px;background:white;border-bottom:1px solid #e3eaf3}
.content{max-width:1450px;margin:0 auto;padding:28px}.eyebrow{font-size:12px;color:#7890a8}
h1{font-size:28px;margin:8px 0 10px}h2{font-size:18px;margin:0 0 13px}
.card{border:1px solid #e1e9f3;border-radius:14px;background:white;padding:24px;margin:16px 0;box-shadow:0 3px 12px #24426508}
.pill{display:inline-block;color:#245c8d;background:#e7f0fa;border-radius:30px;font-size:11px;font-weight:800;padding:5px 12px}
.warn{border-left:4px solid #edaa43;background:#fff7e7;padding:11px 15px;color:#75521e}
.timeline{display:flex;position:relative;margin:25px 0 10px;gap:7px}
.timeline:before{content:"";position:absolute;left:8%;right:8%;top:19px;height:5px;background:#e7edf6;z-index:0}
.step{flex:1;text-align:center;position:relative;z-index:1}.dot{background:#edf1f7;border:3px solid #fff;
box-shadow:0 0 0 1px #dbe3ec;border-radius:50%;width:41px;height:41px;display:grid;place-items:center;margin:auto auto 10px;
font-size:17px;color:#8193a8}.done .dot{background:#10a46c;color:white;box-shadow:0 0 0 1px #10a46c}
.active .dot{background:#226db1;color:white;box-shadow:0 0 0 1px #226db1}
.step b{font-size:11px;display:block}.step small{display:block;font-size:10px;color:#8292a6;padding:0 5px}
.tabs{display:flex;gap:25px;border-bottom:1px solid #dfe8f3;margin-top:14px}
.tab{border:0;background:transparent;color:#58738e;padding:13px 2px;font-weight:700;cursor:pointer}
.tab.active{border-bottom:3px solid #256aaf;color:#1d5e9a}
.cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
label{display:block;font-weight:700;color:#4e647e;margin:9px 0 4px}
input,textarea,select{width:100%;padding:11px;border:1px solid #cfdaea;border-radius:9px;font:inherit}
textarea{min-height:65px}.btn{background:#2264ae;color:white;border:0;padding:10px 14px;border-radius:9px;
cursor:pointer;font:inherit;font-size:13px;font-weight:700;margin:7px 8px 7px 0}
.btn.alt{background:#edf3fa;color:#245783}.btn:disabled{opacity:.5}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:12px;border-bottom:1px solid #e7edf5}
th{background:#f4f7fb}a{color:#2265a7}pre{white-space:pre-wrap;word-break:break-word;font-size:12px}
.muted{font-size:12px;color:#7b8da4}.buttons{display:flex;gap:5px;flex-wrap:wrap}
#message{color:#196441;font-weight:700}#message.error{color:#ab3941}
@media(max-width:900px){aside{width:165px}.content{padding:16px}.timeline{flex-wrap:wrap}.step{min-width:30%}.cols{grid-template-columns:1fr}}
@media(max-width:650px){aside{display:none}.step{min-width:100%;display:flex;text-align:left;align-items:center}.dot{margin:5px 14px 5px 0}}
</style></head><body><div class="layout"><aside>
<img alt="PT Liliang" src="/branding/logo?v=20261020"><small>ERP · MULTI-AI</small>
<a href="/workspace">◈ Multi-AI Workspace</a><a href="/transactions" class="active">▤ Transaksi & Approval</a>
<a href="/inquiries">☷ Inquiry & Matching</a><a href="/wms/sandbox">▣ WMS UAT Sandbox</a>
<a href="/reports">▤ Reports</a><a href="/ai/agent-pilot">✧ AI Agent Rp0</a></aside>
<main><header class="topbar"><b>PT Liliang International</b> · B2B Flavor Research ERP</header>
<div class="content"><div class="eyebrow"><a href="/workspace">Dashboard</a> ›
<a href="/transactions">Transaksi & Approval</a> <span id="crumb"></span></div>
<div class="warn"><b>RESEARCH PILOT:</b> Surat Jalan dan stok di halaman ini adalah simulasi UAT; belum terhubung ke stok fisik perusahaan. Tidak untuk pengiriman nyata.</div>
<div id="view"></div><p id="message" role="status"></p></div></main></div>
<script>
const tok=sessionStorage.getItem("liliang_token")||"";
const path=location.pathname.split("/").filter(Boolean),iid=path[1]||null;
const $=id=>document.getElementById(id);
const esc=v=>String(v===null||v===undefined?"":v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let actor=null,detail=null;
async function api(p,m="GET",body=null){
 const r=await fetch(p,{method:m,cache:"no-store",headers:{"Authorization":"Bearer "+tok,
 "Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
 let x=await r.json();if(!r.ok)throw Error(typeof x.detail==="string"?x.detail:"Request failed");return x;
}
function message(s,bad=false){$("message").textContent=s;$("message").className=bad?"error":""}
function form(id,html,button){return '<form id="'+id+'">'+html+'<button class="btn" type="submit">'+button+'</button></form>'}
function field(n,label,type="text",v="",min=""){return '<label>'+label+'</label><input name="'+n+'" type="'+type+'" value="'+esc(v)+'" '+(min?'min="'+min+'"':'')+' required>'}
function tab(name,tab){return '<button class="tab '+(name===tab?"active":"")+'" onclick="showTab(\''+name+'\')">'+
 ({overview:"Overview",matching:"AI Matching",shipment:"Surat Jalan",audit:"Audit Trail"}[name])+'</button>'}
let currentTab="overview";
function showTab(k){currentTab=k;renderDetail()}
async function init(){if(!tok){message("Login ERP terlebih dahulu melalui /workspace.",true);return}
try{actor=await api("/v1/auth/me");await refresh()}catch(e){message("Sesi tidak valid: "+e.message,true)}}
async function refresh(){if(iid){detail=await api("/v1/transactions/"+iid);renderDetail()}
 else await renderList()}
async function renderList(){
 const x=await api("/v1/transactions");
 const add=actor.role==="sales"?'<section class="card"><h2>Sales · Buat Customer Inquiry</h2>'+
 form("newInquiry",field("customer_ref","Customer reference anonim (UAT-)","text","UAT-CUSTOMER")+
 '<label>Kebutuhan customer</label><textarea name="requirement" required minlength="5" placeholder="Kebutuhan flavor, aplikasi, bentuk, kondisi produk"></textarea>',
 'Buat Inquiry')+'</section>':"";
 const rows=x.rows.map(r=>'<tr><td><a href="/transactions/'+r.id+'">INQ-'+r.id+'</a></td><td>'+
 esc(r.created_at?.slice(0,19))+'</td><td>'+esc(r.customer_ref)+'</td><td>'+esc(r.sample_status||r.status)+
 '</td><td><a href="/transactions/'+r.id+'">Buka Detail →</a></td></tr>').join("");
 $("view").innerHTML='<h1>Transaksi & Approval</h1><p class="muted">Sales → Technical → Manager Operasional → Gudang → Completed (UAT).</p>'+
 add+'<section class="card"><h2>Daftar Transaksi</h2><table><tr><th>Inquiry</th><th>Tanggal</th>'+
 '<th>Customer</th><th>Tahap</th><th>Detail</th></tr>'+rows+'</table></section>';
 const f=$("newInquiry");if(f)f.onsubmit=async e=>{e.preventDefault();try{
 const b=Object.fromEntries(new FormData(f));let a=await api("/v1/inquiries","POST",b);
 location.assign("/transactions/"+a.id)}catch(er){message(er.message,true)}};
}
function badgeState(stage){return '<span class="pill">'+esc(stage)+'</span>'}
function renderDetail(){
 if(!detail)return;const d=detail,q=d.inquiry,s=d.sample,run=d.latest_run,selected=d.selected_product;
 const stage=s?.status||q.status, role=actor.role;
 $("crumb").textContent=" › INQ-"+q.id;
 let timeline='<div class="timeline">'+d.timeline.map((x,i)=>{
 let cl=i<d.current_step?"done":i===d.current_step?"active":"";
 return '<div class="step '+cl+'"><div class="dot">'+(i<d.current_step?"✓":i+1)+'</div><b>'+
 esc(x.name)+'</b><small>'+esc(x.subtitle)+'</small></div>'}).join("")+'</div>';
 let content="";
 if(currentTab==="overview"){
 content='<div class="cols"><section class="card"><h2>Inquiry Information</h2><p><b>Customer:</b> '+esc(q.customer_ref)+
 '</p><p><b>Kebutuhan:</b> '+esc(q.requirement||"Restricted for Gudang")+'</p>'+
 '<p><b>Created:</b> '+esc(q.created_at)+'</p><p><b>Status Matching:</b> '+esc(q.status)+'</p></section>'+
 '<section class="card"><h2>Sample Request</h2><p><b>SKU Terpilih:</b> '+esc(selected?.sku||"Menunggu Technical")+
 '</p><p><b>Qty:</b> '+esc(s?.qty_kg||"—")+' KG</p><p><b>Penerima:</b> '+esc(s?.recipient||"—")+
 '</p><p><b>Tujuan:</b> '+esc(s?.destination||"—")+'</p><p><b>Stok virtual:</b> '+
 esc(d.virtual_stock_kg??"Belum tersedia")+' KG (UAT)</p><p><b>Stok laporan CSV:</b> '+
 esc(d.csv_stock_reference?.reported_stock??"Tidak tercatat")+
 ' (satuan belum ditentukan; UNVERIFIED)</p><p class="muted"><a href="/stock/reference">Lihat semua stok referensi CSV →</a></p></section></div>';
 }else if(currentTab==="matching"){
 content='<section class="card"><h2>AI-02 Candidate Top-5 · BM25</h2><p class="muted">Nilai BM25 bukan probabilitas kelayakan. Technical ACCEPT wajib label 3.</p>'+
 '<table><tr><th>Rank</th><th>SKU</th><th>Produk</th><th>Score</th><th>Technical</th></tr>'+
 (d.candidates||[]).map(x=>'<tr><td>'+esc(x.rank)+'</td><td>'+esc(x.sku)+'</td><td>'+
 esc(x.name)+'</td><td>'+esc(x.score)+'</td><td>'+esc(x.technical_decision||"PENDING")+' / '+esc(x.technical_label??"–")+
 '</td></tr>').join("")+'</table></section>';
 }else if(currentTab==="shipment"){
 content='<section class="card"><h2>Surat Jalan Sampel (UAT)</h2><p><b>Nomor:</b> '+esc(s?.surat_jalan||"Belum diterbitkan")+
 '</p><p><b>Stok virtual SKU:</b> '+esc(d.virtual_stock_kg??"–")+
 ' KG</p><p class="warn">Tidak sah untuk pengiriman fisik PT Liliang.</p>'+
 (s?.surat_jalan?'<button class="btn" onclick="printSj()">Download / Cetak Surat Jalan PDF UAT</button>':"")+'</section>';
 }else if(currentTab==="audit"){
 content='<section class="card"><h2>Riwayat Proses</h2><table><tr><th>Tanggal</th><th>Role</th><th>Tindakan</th></tr>'+
 (d.activity||[]).map(x=>'<tr><td>'+esc(x.at)+'</td><td>'+esc(x.actor_role)+'</td><td>'+esc(x.action)+'</td></tr>').join("")+
 '</table></section>';
 }
 let action="";
 if(role==="sales"&&q.status==="NEW"){
 action='<section class="card"><h2>Sales · Jalankan Top-5 AI Matching</h2><p class="muted">Simpan hasil BM25 yang baru sebelum submit kepada Technical.</p>'+
 '<button class="btn" onclick="simpleAction(\'/v1/inquiries/'+q.id+'/match\')">Jalankan AI-02 Matching</button></section>';
 }else if(role==="sales"&&q.status==="MATCHED"&&(!s||s.status==="RETURNED")){
 action='<section class="card"><h2>Sales · Submit ke Technical</h2>'+
 form("salesSubmit",field("qty_kg","Jumlah Sampel (KG)","number","1","0.001")+
 field("recipient","Nama Penerima UAT","text","UAT-PENERIMA")+
 field("destination","Tujuan Pengiriman UAT","text","UAT-LOKASI-SIMULASI")+
 field("note","Catatan Sales","text","UAT kirim sampel flavor"),
 "Submit Sales ke Technical")+'</section>';
 }else if(role==="technical"&&s?.status==="WAITING_TECHNICAL"&&run){
 const opts=(d.candidates||[]).map(x=>'<option value="'+x.product_id+'">'+esc(x.sku)+" - "+esc(x.name)+'</option>').join("");
 action='<section class="card"><h2>Technical · Review dan Submit</h2>'+
 form("technicalReview",'<label>Pilih Kandidat untuk ACCEPT label 3</label><select name="product_id">'+opts+
 '</select>'+field("rationale","Alasan Validasi Technical","text","UAT review Technical berbasis katalog"),
 "Simpan Review")+
 form("technicalSubmit",'<label>SKU (setelah review ACCEPT label 3)</label><select name="product_id">'+opts+
 '</select>'+field("note","Catatan Submit ke Manager","text","UAT Technical sudah review"),
 "Submit Technical ke Manager")+'</section>';
 }else if(role==="manager"&&s?.status==="WAITING_MANAGER"){
 action='<section class="card"><h2>Manager Operasional · Approval</h2>'+
 form("managerSubmit",'<label>Keputusan</label><select name="decision"><option value="APPROVE">APPROVE - lanjut Gudang</option>'+
 '<option value="RETURN">RETURN - revisi Sales</option></select>'+
 field("note","Catatan Manager","text","UAT persetujuan pengiriman sampel"),
 "Submit Keputusan Manager")+'</section>';
 }else if(role==="gudang"&&s&&["WAITING_WAREHOUSE","WAREHOUSE_READY"].includes(s.status)){
 action='<section class="card"><h2>Gudang · Ketersediaan Sampel</h2>'+
 '<p class="warn">Ini stok VIRTUAL UAT. Tidak merepresentasikan stok perusahaan.</p>'+
 form("stockIn",field("qty_kg","Tambahkan Stok Virtual (KG)","number","2","0.001")+
 field("reference","Referensi UAT Unik","text","UAT-STOCK-"+q.id+"-"+Date.now())+
 field("note","Catatan","text","UAT stok fiktif untuk simulasi"),
 "Input Virtual Stock")+
 (s.status==="WAITING_WAREHOUSE"?'<button class="btn" onclick="warehouseStep(\'warehouse-check\')">Cek Stok Virtual</button>':
 '<button class="btn" onclick="warehouseStep(\'warehouse-dispatch\')">Generate Surat Jalan UAT & Dispatch</button>')+
 '</section>';
 }else if(role==="sales"&&q.status==="RETURNED"){
 action='<section class="card"><h2>Sales · Revisi Inquiry</h2>'+
 form("salesRevise",'<label>Revisi Requirement</label><textarea name="requirement" minlength="5" required>'+
 esc(q.requirement)+'</textarea>','Revisi & Matching Ulang')+'</section>';
 }
 $("view").innerHTML='<h1>INQ-'+q.id+' '+badgeState(stage)+'</h1><p class="muted">Drafted by Sales · Online research workflow</p>'+
 '<div class="tabs">'+["overview","matching","shipment","audit"].map(t=>tab(t,currentTab)).join("")+'</div>'+
 '<section class="card"><h2>Approval Timeline</h2>'+timeline+'</section>'+content+action;
 bindActions();
}
async function simpleAction(url){try{await api(url,"POST",{});message("Tahap berhasil diperbarui.");await refresh()}catch(e){message(e.message,true)}}
async function warehouseStep(step){try{await api("/v1/transactions/"+iid+"/"+step,"POST",{
 note:"UAT Gudang memproses stok simulasi",acknowledge_virtual_only:true});
 message("Gudang UAT selesai: "+step);await refresh()}catch(e){message(e.message,true)}}
function bindActions(){
 const f=$("salesSubmit");if(f)f.onsubmit=async e=>{e.preventDefault();try{
 let b=Object.fromEntries(new FormData(f));b.qty_kg=Number(b.qty_kg);
 await api("/v1/transactions/"+iid+"/sales-submit","POST",b);message("Sales telah submit.");await refresh()}catch(er){message(er.message,true)}};
 const r=$("technicalReview");if(r)r.onsubmit=async e=>{e.preventDefault();try{
 let b=Object.fromEntries(new FormData(r));await api("/v1/matches/"+detail.latest_run.id+"/review","POST",{
 product_id:Number(b.product_id),decision:"ACCEPT",relevance_label:3,rationale:b.rationale});
 message("Review Technical tercatat. Lanjut Submit ke Manager.");await refresh()}catch(er){message(er.message,true)}};
 const t=$("technicalSubmit");if(t)t.onsubmit=async e=>{e.preventDefault();try{
 let b=Object.fromEntries(new FormData(t));await api("/v1/transactions/"+iid+"/technical-submit","POST",{
 product_id:Number(b.product_id),note:b.note});
 message("Technical telah submit ke Manager.");await refresh()}catch(er){message(er.message,true)}};
 const m=$("managerSubmit");if(m)m.onsubmit=async e=>{e.preventDefault();try{
 await api("/v1/inquiries/"+iid+"/decision","POST",Object.fromEntries(new FormData(m)));
 message("Manager telah submit keputusan.");await refresh()}catch(er){message(er.message,true)}};
 const a=$("stockIn");if(a)a.onsubmit=async e=>{e.preventDefault();try{
 let b=Object.fromEntries(new FormData(a));await api("/v1/sample-stock/uat-in","POST",{
 sku:detail.selected_product.sku,qty_kg:Number(b.qty_kg),reference:b.reference,note:b.note,
 acknowledge_virtual_only:true});
 message("Stok virtual ditambahkan.");await refresh()}catch(er){message(er.message,true)}};
 const v=$("salesRevise");if(v)v.onsubmit=async e=>{e.preventDefault();try{
 await api("/v1/inquiries/"+iid+"/revise","POST",Object.fromEntries(new FormData(v)));
 message("Revisi tersimpan. Jalankan matching baru.");await refresh()}catch(er){message(er.message,true)}};
}
async function printSj(){try{
 const r=await fetch("/v1/transactions/"+iid+"/surat-jalan",{headers:{
 "Authorization":"Bearer "+tok},cache:"no-store"});if(!r.ok)throw Error("Surat Jalan belum tersedia");
 const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");
 a.href=url;a.download=detail.sample.surat_jalan+".pdf";document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),3000);}catch(e){message(e.message,true)}}
init();
</script></body></html>"""

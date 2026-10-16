"""Admin-controlled research-pilot reset, private catalog import and UAT role provisioning.

No customer catalog data or passwords are stored in the public source repository.
Destructive reset can only be initiated by an authenticated Admin with a deliberate
confirmation phrase, and only while the active product catalog is entirely DEMO.
"""
import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from typing import Literal

from persistence import engine_name

def stamp():
    return datetime.now(timezone.utc).isoformat()

def json_text(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":"))

def append_event(db, actor, action, entity, entity_id, before=None, after=None):
    """Append an atomic, low-PII audit event in the same transaction as the change."""
    old=json_text(before if before is not None else {})
    new=json_text(after if after is not None else {})
    digest=hashlib.sha256((old+"\n"+new).encode("utf-8")).hexdigest()
    event_id=str(uuid.uuid4())
    db.execute("""INSERT INTO transaction_events
      (id,actor_id,actor_role,action,entity,entity_id,at,request_id,before_json,after_json,payload_sha256)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (event_id,actor["id"],actor["role"],action,entity,str(entity_id),stamp(),event_id,old,new,digest))
    return event_id

class ConfirmReset(BaseModel):
    confirmation: Literal["RESET DEMO ONLY"]

class CatalogManifest(BaseModel):
    version: str=Field(min_length=1,max_length=25)
    source_file_sha256: str=Field(pattern=r"^[a-f0-9]{64}$")
    source_file_name: str=Field(min_length=3,max_length=260)
    catalog_version: str=Field(min_length=3,max_length=80)
    source_records: int=Field(ge=1,le=100000)
    ready_records: int=Field(ge=1,le=100000)
    quarantined_records: int=Field(ge=0,le=100000)
    source_kind: str
    claims: list[str]=Field(default_factory=list)

class CatalogProduct(BaseModel):
    number: int=Field(ge=1,le=200000)
    sku: str=Field(min_length=2,max_length=90)
    name: str=Field(min_length=2,max_length=400)
    product_type: str=Field(min_length=2,max_length=100)
    application: str=Field(min_length=1,max_length=2400)
    composition_text: str=Field(max_length=600)
    source_page: int=Field(ge=1,le=10000)
    source_number: int=Field(ge=1,le=200000)

class CatalogPayload(BaseModel):
    manifest: CatalogManifest
    products: list[CatalogProduct]=Field(min_length=1,max_length=10000)

class UATRequest(BaseModel):
    confirmation: Literal["CREATE UAT ROLES"]

UAT_ROLES=[
    ("sales","Sales Research UAT","uat-sales@liliang.local"),
    ("technical","Technical Research UAT","uat-technical@liliang.local"),
    ("manager","Manager Operasional UAT","uat-manager@liliang.local"),
    ("gudang","Gudang Research UAT","uat-gudang@liliang.local")
]

def batches(seq,n=60):
    for start in range(0,len(seq),n):
        yield seq[start:start+n]

def multi_insert(db, table, columns, rows):
    if not rows:return
    placeholders="("+",".join("?" for _ in columns)+")"
    sql="INSERT INTO "+table+"("+",".join(columns)+") VALUES"+",".join([placeholders]*len(rows))
    values=tuple(item for row in rows for item in row)
    db.execute(sql,values)

def mount_enterprise(app,current,get_db,audit,ph):
    def admin(u=Depends(current)):
        if u["role"]!="admin":raise HTTPException(403,"Admin access required")
        return u

    @app.get("/v1/admin/catalog/reset-preview")
    def reset_preview(u=Depends(admin),db=Depends(get_db)):
        counts={}
        for table in ("products","inquiries","runs","candidates","reviews","audits","catalog_import_batches","reset_archives","transaction_events"):
            counts[table]=db.execute("SELECT COUNT(*) AS total FROM "+table).fetchone()["total"]
        non_demo=db.execute("SELECT COUNT(*) AS total FROM products WHERE source_ref IS NULL OR source_ref<>'DEMO-ONLY'").fetchone()["total"]
        permitted=not non_demo and not counts["catalog_import_batches"]
        return {"counts":counts,"non_demo_products":non_demo,"demo_reset_allowed":permitted,
                "requires_confirmation":"RESET DEMO ONLY",
                "safety":"Only products/inquiries/runs/candidates/reviews will be archived and then reset. All users and audit logs remain. Never reset imported catalog through this endpoint."}

    @app.post("/v1/admin/catalog/reset-demo")
    def reset_demo(body:ConfirmReset,u=Depends(admin),db=Depends(get_db)):
        with db:
            # Serialize the intent by using a transaction; recheck on the same connection.
            has_real=db.execute("SELECT COUNT(*) AS n FROM products WHERE source_ref IS NULL OR source_ref<>'DEMO-ONLY'").fetchone()["n"]
            imports=db.execute("SELECT COUNT(*) AS n FROM catalog_import_batches").fetchone()["n"]
            if has_real or imports:
                raise HTTPException(409,"Refusing reset: company catalog or non-demo products exist")
            archive={}
            for table in ("products","inquiries","runs","candidates","reviews"):
                archive[table]=[dict(row) for row in db.execute("SELECT * FROM "+table+" ORDER BY id").fetchall()]
            if not any(archive.values()):
                return {"already_clean":True,"archive_id":None,"counts":{x:0 for x in archive}}
            counts={k:len(v) for k,v in archive.items()}
            raw=json_text(archive)
            checksum=hashlib.sha256(raw.encode("utf-8")).hexdigest()
            archive_id=str(uuid.uuid4())
            db.execute("""INSERT INTO reset_archives(id,actor_id,at,counts_json,archive_json,payload_sha256)
              VALUES(?,?,?,?,?,?)""",(archive_id,u["id"],stamp(),json_text(counts),raw,checksum))
            for table in ("reviews","candidates","runs","inquiries","products"):
                db.execute("DELETE FROM "+table)
            audit(db,u,"DEMO_RESET_ARCHIVED","reset",0,after={"archive_id":archive_id,"counts":counts,"sha256":checksum})
        return {"archive_id":archive_id,"counts":counts,"sha256":checksum,"users_preserved":True,"audit_logs_preserved":True}

    @app.post("/v1/admin/uat/bootstrap")
    def bootstrap_roles(body:UATRequest,response:Response,u=Depends(admin),db=Depends(get_db)):
        from app import ROLES
        results=[]
        response.headers["Cache-Control"]="no-store"
        with db:
            for role,name,email in UAT_ROLES:
                if role not in ROLES:raise HTTPException(500,"Unexpected role")
                row=db.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone()
                if row:
                    results.append({"email":email,"role":role,"status":"ALREADY_EXISTS_NO_PASSWORD_DISCLOSURE"})
                    continue
                password=secrets.token_urlsafe(24)
                cur=db.execute("INSERT INTO users(email,name,role,hash) VALUES(?,?,?,?)",
                               (email,name,role,ph.hash(password)))
                audit(db,u,"CREATE_UAT_USER","user",cur.lastrowid)
                results.append({"email":email,"role":role,"status":"CREATED","password_once":password})
        return {"accounts_type":"SYNTHETIC_UAT_ONLY","credentials_displayed_once":True,
                "warning":"Store passwords privately. They cannot be recovered; Admin must reset them if lost. These .local identities cannot receive email.",
                "roles":results}

    @app.get("/v1/admin/audit-events")
    def audit_events(limit:int=Query(default=100,ge=1,le=500),u=Depends(admin),db=Depends(get_db)):
        rows=db.execute("""SELECT id,actor_id,actor_role,action,entity,entity_id,at,request_id,payload_sha256
                           FROM transaction_events ORDER BY at DESC LIMIT ?""",(limit,)).fetchall()
        return {"events":[dict(r) for r in rows],"fields_excluded":["passwords","full inquiry free text","catalog content"],
                "append_only":True,"note":"The event hash documents what was recorded, not independent proof that upstream source inputs were accurate."}

    @app.get("/v1/admin/catalog/imports")
    def imports(u=Depends(admin),db=Depends(get_db)):
        rows=db.execute("""SELECT id,source_sha256,source_file,catalog_version,items_imported,at,source_classification
                           FROM catalog_import_batches ORDER BY at DESC""").fetchall()
        return {"imports":[dict(r) for r in rows]}

    @app.post("/v1/admin/catalog/import",status_code=201)
    def import_catalog(payload:CatalogPayload,u=Depends(admin),db=Depends(get_db)):
        m=payload.manifest
        if m.source_kind!="COMPANY_PRODUCT_CATALOG":
            raise HTTPException(422,"Unsupported catalog manifest source")
        if m.ready_records!=len(payload.products) or m.source_records!=m.ready_records+m.quarantined_records:
            raise HTTPException(422,"Catalog QA totals do not reconcile")
        if len(payload.products)>4000:
            raise HTTPException(413,"Upload at most 4000 catalog products per file")
        if len({x.sku.strip().upper() for x in payload.products})!=len(payload.products):
            raise HTTPException(422,"Duplicate SKU in import-ready dataset")
        if len({x.source_number for x in payload.products})!=len(payload.products):
            raise HTTPException(422,"Duplicate source row number")
        for x in payload.products:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9#._/-]*",x.sku.strip()):
                raise HTTPException(422,"Invalid SKU syntax in source catalog")
        with db:
            existing=db.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"]
            if existing:
                raise HTTPException(409,"Nonempty active catalog. Archive/reset pilot first; company catalog cannot be replaced by this operation.")
            if db.execute("SELECT 1 FROM catalog_import_batches WHERE source_sha256=?",(m.source_file_sha256,)).fetchone():
                raise HTTPException(409,"This PDF catalog was imported previously")
            batch=str(uuid.uuid4())
            product_rows=[]
            details=[]
            for x in payload.products:
                sku=x.sku.strip()
                # Source is catalog text, NOT a verified food formulation or inventory balance.
                desc=f"Type: {x.product_type.strip()}; Applications: {x.application.strip()}; Catalog percentage text: {x.composition_text.strip()}"
                product_rows.append((sku,x.name.strip(),desc,"",x.application.strip(),None,"CATALOG-PDF-UNVERIFIED"))
                details.append((sku,x.product_type.strip(),x.application.strip(),x.composition_text.strip(),
                                x.source_page,x.source_number,m.source_file_sha256,batch))
            for group in batches(product_rows):
                multi_insert(db,"products",("sku","name","description","profile","application","stock","source_ref"),group)
            for group in batches(details):
                multi_insert(db,"catalog_product_details",
                             ("sku","product_type","application_raw","composition_raw","source_page","source_number","source_sha256","batch_id"),group)
            db.execute("""INSERT INTO catalog_import_batches
                       (id,source_sha256,source_file,catalog_version,items_imported,actor_id,at,source_classification)
                       VALUES(?,?,?,?,?,?,?,?)""",
                       (batch,m.source_file_sha256,m.source_file_name,m.catalog_version,len(details),u["id"],stamp(),"PENDING_TECHNICAL_VERIFICATION"))
            audit(db,u,"CATALOG_IMPORTED","catalog",0,
                  after={"batch_id":batch,"products":len(details),"source_sha256":m.source_file_sha256,
                         "source_rows_quarantined":m.quarantined_records,"source_classification":"PENDING_TECHNICAL_VERIFICATION"})
        return {"import_batch_id":batch,"imported_count":len(details),"quarantined_source_rows":m.quarantined_records,
                "stock":"UNKNOWN","halal_and_regulatory":"UNKNOWN",
                "technical_validation":"PENDING","source_sha256":m.source_file_sha256}

    @app.get("/v1/catalog/products")
    def catalog_products(q:str=Query(default="",max_length=200),
                         page:int=Query(default=1,ge=1,le=10000),
                         size:int=Query(default=50,ge=1,le=150),
                         u=Depends(current),db=Depends(get_db)):
        where="";args=()
        if q.strip():
            where=" WHERE LOWER(p.sku) LIKE ? OR LOWER(p.name) LIKE ? OR LOWER(p.application) LIKE ?"
            pat="%"+q.lower().strip()+"%"
            args=(pat,pat,pat)
        count=db.execute("SELECT COUNT(*) AS total FROM products p"+where,args).fetchone()["total"]
        rows=db.execute("""SELECT p.id,p.sku,p.name,p.application,p.source_ref,p.stock,
                                 d.product_type,d.composition_raw,d.source_page,d.source_number
                          FROM products p LEFT JOIN catalog_product_details d ON d.sku=p.sku"""+where+
                        " ORDER BY p.sku LIMIT ? OFFSET ?",args+(size,(page-1)*size)).fetchall()
        return {"total":count,"page":page,"size":size,"items":[dict(r) for r in rows]}


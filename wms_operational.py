"""Operational warehouse ledger, isolated from demo movements and gated by an explicit feature flag.

The ledger is append-only. It is not enabled by default; activation requires a
current, reconciled physical count, verified UoM mappings, warehouse UAT and
owner approval. All quantities retain their source unit; no implicit conversion.
"""
from __future__ import annotations
import os, re, uuid
from datetime import datetime, timezone, date
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

ROLES_READ={"admin","manager","gudang","sales","technical"}
ROLES_WRITE={"admin","gudang"}

def enabled():
    return os.getenv("WMS_OPERATIONAL_ENABLED","false").strip().lower()=="true"

def install_operational_wms_schema(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS wms_operational_warehouses(
      warehouse_id TEXT PRIMARY KEY, warehouse_name TEXT NOT NULL,
      status TEXT NOT NULL, created_at TEXT NOT NULL, created_by INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS wms_operational_bins(
      warehouse_id TEXT NOT NULL, bin_id TEXT NOT NULL, status TEXT NOT NULL,
      created_at TEXT NOT NULL, created_by INTEGER NOT NULL,
      PRIMARY KEY(warehouse_id,bin_id),
      FOREIGN KEY(warehouse_id) REFERENCES wms_operational_warehouses(warehouse_id)
    );
    CREATE TABLE IF NOT EXISTS wms_operational_movements(
      movement_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
      movement_type TEXT NOT NULL, adjustment_direction TEXT,
      sku TEXT NOT NULL, lot_batch TEXT, expiry_date TEXT, qty REAL NOT NULL,
      unit TEXT NOT NULL, from_warehouse TEXT, from_bin TEXT,
      to_warehouse TEXT, to_bin TEXT, reference_document TEXT NOT NULL,
      actor_id INTEGER NOT NULL, created_at TEXT NOT NULL, note TEXT NOT NULL,
      status TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_wms_ops_sku ON wms_operational_movements(sku,unit,status);
    CREATE INDEX IF NOT EXISTS idx_wms_ops_location ON wms_operational_movements(from_warehouse,from_bin,to_warehouse,to_bin);
    CREATE TABLE IF NOT EXISTS wms_operational_reservations(
      reservation_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
      sku TEXT NOT NULL, lot_batch TEXT, warehouse_id TEXT NOT NULL, bin_id TEXT,
      qty REAL NOT NULL, unit TEXT NOT NULL, reference_document TEXT NOT NULL,
      actor_id INTEGER NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL,
      FOREIGN KEY(warehouse_id) REFERENCES wms_operational_warehouses(warehouse_id)
    );
    CREATE INDEX IF NOT EXISTS idx_wms_ops_reservation ON wms_operational_reservations(sku,warehouse_id,bin_id,status);
    CREATE TABLE IF NOT EXISTS wms_operational_opening_snapshots(
      snapshot_id TEXT PRIMARY KEY, source_count_ref TEXT UNIQUE NOT NULL,
      as_of_datetime TEXT NOT NULL, item_count INTEGER NOT NULL,
      created_by INTEGER NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL
    );
    """)

def _safe_id(value,label):
    v=str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{1,79}",v):
        raise ValueError(label+" must be a stable non-personal identifier")
    return v

def _now():
    return datetime.now(timezone.utc).isoformat()

class WarehouseIn(BaseModel):
    warehouse_id:str=Field(min_length=2,max_length=80)
    warehouse_name:str=Field(min_length=2,max_length=120)

class BinIn(BaseModel):
    warehouse_id:str=Field(min_length=2,max_length=80)
    bin_id:str=Field(min_length=1,max_length=80)

class OpeningItem(BaseModel):
    sku:str=Field(min_length=3,max_length=80)
    bin_id:str|None=None
    lot_batch:str|None=None
    expiry_date:date|None=None
    quantity:float=Field(ge=0,le=100000000,allow_inf_nan=False)
    unit:str=Field(min_length=1,max_length=24)
    uom_verified:Literal[True]
    uom_evidence_ref:str=Field(min_length=8,max_length=120)

class OpeningBalanceIn(BaseModel):
    snapshot_id:str=Field(min_length=3,max_length=80)
    source_count_ref:str=Field(min_length=8,max_length=120)
    as_of_datetime:datetime
    warehouse_id:str=Field(min_length=2,max_length=80)
    physical_count_confirmed:Literal[True]
    items:list[OpeningItem]=Field(min_length=1,max_length=5000)

class MovementIn(BaseModel):
    movement_id:str=Field(default_factory=lambda:"MOV-"+uuid.uuid4().hex[:20].upper())
    idempotency_key:str=Field(min_length=8,max_length=120)
    movement_type:Literal["RECEIPT","TRANSFER","PICK","DISPATCH","RETURN","ADJUSTMENT"]
    adjustment_direction:Literal["IN","OUT"]|None=None
    sku:str=Field(min_length=3,max_length=80)
    lot_batch:str|None=None
    expiry_date:date|None=None
    quantity:float=Field(gt=0,le=100000000,allow_inf_nan=False)
    unit:str=Field(min_length=1,max_length=24)
    from_warehouse:str|None=None
    from_bin:str|None=None
    to_warehouse:str|None=None
    to_bin:str|None=None
    reference_document:str=Field(min_length=8,max_length=120)
    uom_verified:Literal[True]
    uom_evidence_ref:str=Field(min_length=8,max_length=120)
    note:str=Field(min_length=5,max_length=300)

class ReservationIn(BaseModel):
    reservation_id:str=Field(default_factory=lambda:"RSV-"+uuid.uuid4().hex[:20].upper())
    idempotency_key:str=Field(min_length=8,max_length=120)
    sku:str=Field(min_length=3,max_length=80)
    lot_batch:str|None=None
    warehouse_id:str=Field(min_length=2,max_length=80)
    bin_id:str|None=None
    quantity:float=Field(gt=0,le=100000000,allow_inf_nan=False)
    unit:str=Field(min_length=1,max_length=24)
    reference_document:str=Field(min_length=8,max_length=120)
    uom_verified:Literal[True]
    uom_evidence_ref:str=Field(min_length=8,max_length=120)

def _check_product(db,sku,unit,uom_evidence_ref):
    p=db.execute("SELECT sku FROM products WHERE sku=?",(sku,)).fetchone()
    if not p: raise HTTPException(422,"SKU is not present in the product master")
    # Existing packaging register is authoritative when it has a row. A pending
    # package/UoM must not become dispatchable merely because a caller selected KG.
    try:
        ref=db.execute("SELECT dispatch_uom_status,package_uom FROM physical_inventory_stock WHERE sku=?",(sku,)).fetchone()
    except Exception:
        ref=None
    if ref and ref["dispatch_uom_status"]!="UNIT_DEFINED":
        raise HTTPException(409,"SKU package UoM is pending; resolve and verify packaging before WMS posting")
    if not uom_evidence_ref.strip():
        raise HTTPException(422,"UoM evidence reference is required")
    return True

def _lock_sku(db,sku):
    # Serialize concurrent balance checks for a SKU. PostgreSQL locks the product
    # master row; SQLite uses BEGIN IMMEDIATE for a write transaction.
    if hasattr(db,"_raw"):
        db.execute("SELECT id FROM products WHERE sku=? FOR UPDATE",(sku,)).fetchone()
    elif not db.in_transaction:
        db.execute("BEGIN IMMEDIATE")

def _location(db,warehouse,bin_id):
    w=db.execute("SELECT status FROM wms_operational_warehouses WHERE warehouse_id=?",(warehouse,)).fetchone()
    if not w or w["status"]!="ACTIVE": raise HTTPException(422,"Warehouse is missing or inactive")
    if bin_id:
        b=db.execute("SELECT status FROM wms_operational_bins WHERE warehouse_id=? AND bin_id=?",(warehouse,bin_id)).fetchone()
        if not b or b["status"]!="ACTIVE": raise HTTPException(422,"Bin is missing or inactive")

def _balance(db,sku,warehouse,bin_id,lot,unit):
    row=db.execute("""SELECT COALESCE(SUM(
      CASE WHEN to_warehouse=? AND COALESCE(to_bin,'')=COALESCE(?,'') THEN qty
           WHEN from_warehouse=? AND COALESCE(from_bin,'')=COALESCE(?,'') THEN -qty
           ELSE 0 END),0) AS on_hand
      FROM wms_operational_movements
      WHERE sku=? AND COALESCE(lot_batch,'')=COALESCE(?,'') AND unit=? AND status='POSTED'""",
      (warehouse,bin_id,warehouse,bin_id,sku,lot,unit)).fetchone()
    return float(row["on_hand"] or 0)

def _reserved(db,sku,warehouse,bin_id,lot,unit):
    row=db.execute("""SELECT COALESCE(SUM(qty),0) AS qty FROM wms_operational_reservations
       WHERE sku=? AND warehouse_id=? AND COALESCE(bin_id,'')=COALESCE(?,'')
       AND COALESCE(lot_batch,'')=COALESCE(?,'') AND unit=? AND status='ACTIVE'""",
       (sku,warehouse,bin_id,lot,unit)).fetchone()
    return float(row["qty"] or 0)

def stock_rows(db,sku=None):
    moves=db.execute("""SELECT sku,lot_batch,expiry_date,qty,unit,from_warehouse,from_bin,
        to_warehouse,to_bin FROM wms_operational_movements WHERE status='POSTED' ORDER BY created_at""").fetchall()
    totals={}
    for r in moves:
        x=dict(r)
        for warehouse,bin_id,sign in ((x["from_warehouse"],x["from_bin"],-1),(x["to_warehouse"],x["to_bin"],1)):
            if not warehouse: continue
            key=(x["sku"],warehouse,bin_id or "",x["lot_batch"] or "",x["unit"])
            totals[key]=totals.get(key,0.0)+sign*float(x["qty"])
    reservations=db.execute("SELECT sku,warehouse_id,bin_id,lot_batch,unit,qty FROM wms_operational_reservations WHERE status='ACTIVE'").fetchall()
    reserved={}
    for r in reservations:
        x=dict(r);key=(x["sku"],x["warehouse_id"],x["bin_id"] or "",x["lot_batch"] or "",x["unit"])
        reserved[key]=reserved.get(key,0.0)+float(x["qty"])
    output=[]
    for key,on_hand in sorted(totals.items()):
        if sku and key[0]!=sku: continue
        r=reserved.get(key,0.0)
        output.append({"sku":key[0],"warehouse_id":key[1],"bin_id":key[2] or None,
          "lot_batch":key[3] or None,"unit":key[4],"on_hand":round(on_hand,6),
          "reserved":round(r,6),"available":round(on_hand-r,6)})
    return output

def mount_operational_wms(app,current,get_db,audit):
    @app.get("/v1/wms/operational/status")
    def operational_status(u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ROLES_READ: raise HTTPException(403,"Role access denied")
        return {"feature_enabled":enabled(),"mode":"OPERATIONAL_LEDGER_GATED",
          "physical_stock_mutation_allowed":enabled(),
          "warehouse_count":db.execute("SELECT COUNT(*) AS n FROM wms_operational_warehouses").fetchone()["n"],
          "movement_count":db.execute("SELECT COUNT(*) AS n FROM wms_operational_movements WHERE status='POSTED'").fetchone()["n"],
          "reservation_count":db.execute("SELECT COUNT(*) AS n FROM wms_operational_reservations WHERE status='ACTIVE'").fetchone()["n"],
          "go_live_requirements":["Current approved physical stock count","All dispatched SKU UoM mappings verified",
          "Warehouse/bin master and lot/expiry rules signed off","Role-based UAT and reconciliation","Owner approval and WMS_OPERATIONAL_ENABLED=true"]}

    @app.get("/v1/wms/operational/stock")
    def operational_stock(sku:str|None=None,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ROLES_READ: raise HTTPException(403,"Role access denied")
        return {"mode":"OPERATIONAL_LEDGER","feature_enabled":enabled(),"rows":stock_rows(db,sku.upper() if sku else None),
          "note":"Balances are derived from posted append-only movements; unit buckets are never silently converted."}

    @app.post("/v1/admin/wms/warehouses",status_code=201)
    def create_warehouse(data:WarehouseIn,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="admin": raise HTTPException(403,"Admin required")
        if not enabled(): raise HTTPException(503,"Operational WMS feature flag is disabled")
        wid=_safe_id(data.warehouse_id,"warehouse_id")
        with db:
            db.execute("INSERT INTO wms_operational_warehouses(warehouse_id,warehouse_name,status,created_at,created_by) VALUES(?,?,?,?,?)",
              (wid,data.warehouse_name.strip(),"ACTIVE",_now(),u["id"]))
            audit(db,u,"WMS_WAREHOUSE_CREATE","wms_warehouse",wid,after={"status":"ACTIVE"})
        return {"warehouse_id":wid,"status":"ACTIVE"}

    @app.post("/v1/admin/wms/bins",status_code=201)
    def create_bin(data:BinIn,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="admin": raise HTTPException(403,"Admin required")
        if not enabled(): raise HTTPException(503,"Operational WMS feature flag is disabled")
        wid=_safe_id(data.warehouse_id,"warehouse_id");bid=_safe_id(data.bin_id,"bin_id")
        _location(db,wid,None)
        with db:
            db.execute("INSERT INTO wms_operational_bins(warehouse_id,bin_id,status,created_at,created_by) VALUES(?,?,?,?,?)",
              (wid,bid,"ACTIVE",_now(),u["id"]))
            audit(db,u,"WMS_BIN_CREATE","wms_bin",bid,after={"warehouse_id":wid,"status":"ACTIVE"})
        return {"warehouse_id":wid,"bin_id":bid,"status":"ACTIVE"}

    @app.post("/v1/admin/wms/opening-balance",status_code=201)
    def opening_balance(data:OpeningBalanceIn,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="admin": raise HTTPException(403,"Admin required")
        if not enabled(): raise HTTPException(503,"Operational WMS feature flag is disabled")
        if data.as_of_datetime.tzinfo is None: raise HTTPException(422,"as_of_datetime must include timezone")
        sid=_safe_id(data.snapshot_id,"snapshot_id");wid=_safe_id(data.warehouse_id,"warehouse_id")
        if db.execute("SELECT 1 FROM wms_operational_opening_snapshots WHERE snapshot_id=? OR source_count_ref=?",(sid,data.source_count_ref)).fetchone():
            raise HTTPException(409,"Opening snapshot or stock count reference already imported")
        _location(db,wid,None)
        keys=set()
        for item in data.items:
            sku=_safe_id(item.sku,"SKU");_check_product(db,sku,item.unit,item.uom_evidence_ref)
            if item.bin_id: _location(db,wid,_safe_id(item.bin_id,"bin_id"))
            key=(sku,item.bin_id,item.lot_batch,item.unit)
            if key in keys: raise HTTPException(422,"Duplicate SKU/bin/lot/unit in opening snapshot")
            keys.add(key)
        stamp=_now()
        with db:
            db.execute("INSERT INTO wms_operational_opening_snapshots(snapshot_id,source_count_ref,as_of_datetime,item_count,created_by,created_at,status) VALUES(?,?,?,?,?,?,?)",
              (sid,data.source_count_ref,data.as_of_datetime.isoformat(),len(data.items),u["id"],stamp,"POSTED"))
            for i,item in enumerate(data.items):
                sku=item.sku.strip().upper()
                db.execute("""INSERT INTO wms_operational_movements
                  (movement_id,idempotency_key,movement_type,sku,lot_batch,expiry_date,qty,unit,to_warehouse,to_bin,
                   reference_document,actor_id,created_at,note,status)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  ("OPEN-"+uuid.uuid4().hex[:18].upper(),f"OPEN:{sid}:{i}", "OPENING_BALANCE",sku,item.lot_batch,
                   item.expiry_date.isoformat() if item.expiry_date else None,item.quantity,item.unit.upper(),wid,item.bin_id,
                   data.source_count_ref,u["id"],stamp,"Approved physical opening count "+sid,"POSTED"))
            audit(db,u,"WMS_OPENING_BALANCE_POST","wms_opening_snapshot",sid,
              after={"item_count":len(data.items),"source_count_ref":data.source_count_ref,"physical_count_confirmed":True})
        return {"status":"OPENING_BALANCE_POSTED","snapshot_id":sid,"item_count":len(data.items),
          "note":"Opening balance is derived from the submitted dated physical count. Reconciliation and sign-off remain auditable."}

    @app.post("/v1/wms/operational/movements",status_code=201)
    def create_movement(data:MovementIn,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ROLES_WRITE: raise HTTPException(403,"Admin or Gudang required")
        if not enabled(): raise HTTPException(503,"Operational WMS feature flag is disabled")
        sku=_safe_id(data.sku,"SKU");_check_product(db,sku,data.unit,data.uom_evidence_ref)
        fw=data.from_warehouse.strip().upper() if data.from_warehouse else None
        tw=data.to_warehouse.strip().upper() if data.to_warehouse else None
        fb=data.from_bin.strip().upper() if data.from_bin else None
        tb=data.to_bin.strip().upper() if data.to_bin else None
        if data.movement_type in ("PICK","DISPATCH") and (not fw or tw): raise HTTPException(422,"PICK/DISPATCH require only a source location")
        if data.movement_type in ("RECEIPT","RETURN") and (not tw or fw): raise HTTPException(422,"RECEIPT/RETURN require only a destination location")
        if data.movement_type=="TRANSFER" and (not fw or not tw or (fw==tw and fb==tb)): raise HTTPException(422,"TRANSFER requires distinct source and destination")
        if data.movement_type=="ADJUSTMENT":
            if u["role"]!="admin": raise HTTPException(403,"Only Admin may post stock adjustments")
            if data.adjustment_direction=="IN" and not tw: raise HTTPException(422,"Adjustment IN requires destination")
            if data.adjustment_direction=="OUT" and not fw: raise HTTPException(422,"Adjustment OUT requires source")
            if data.adjustment_direction not in ("IN","OUT"): raise HTTPException(422,"Adjustment direction required")
        for loc in ((fw,fb),(tw,tb)):
            if loc[0]: _location(db,loc[0],loc[1])
        stamp=_now()
        with db:
            _lock_sku(db,sku)
            if db.execute("SELECT 1 FROM wms_operational_movements WHERE idempotency_key=? OR movement_id=?",
                          (data.idempotency_key,data.movement_id)).fetchone():
                raise HTTPException(409,"Duplicate movement ID or idempotency key")
            if data.movement_type in ("PICK","DISPATCH","TRANSFER") or (data.movement_type=="ADJUSTMENT" and data.adjustment_direction=="OUT"):
                available=_balance(db,sku,fw,fb,data.lot_batch,data.unit)
                reserved=_reserved(db,sku,fw,fb,data.lot_batch,data.unit)
                if data.quantity>available-reserved+1e-9:
                    raise HTTPException(409,"Insufficient available stock after active reservations")
            db.execute("""INSERT INTO wms_operational_movements
              (movement_id,idempotency_key,movement_type,adjustment_direction,sku,lot_batch,expiry_date,qty,unit,
               from_warehouse,from_bin,to_warehouse,to_bin,reference_document,actor_id,created_at,note,status)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (data.movement_id,data.idempotency_key,data.movement_type,data.adjustment_direction,sku,data.lot_batch,
               data.expiry_date.isoformat() if data.expiry_date else None,data.quantity,data.unit.upper(),fw,fb,tw,tb,
               data.reference_document,u["id"],stamp,data.note,"POSTED"))
            audit(db,u,"WMS_"+data.movement_type,"wms_movement",data.movement_id,
              after={"sku":sku,"quantity":data.quantity,"unit":data.unit.upper(),"from":fw,"to":tw,
                     "reference_document":data.reference_document,"idempotency_key":data.idempotency_key})
        return {"movement_id":data.movement_id,"status":"POSTED","type":data.movement_type,
          "sku":sku,"quantity":data.quantity,"unit":data.unit.upper(),
          "source_balance_after":round(_balance(db,sku,fw,fb,data.lot_batch,data.unit),6) if fw else None,
          "destination_balance_after":round(_balance(db,sku,tw,tb,data.lot_batch,data.unit),6) if tw else None}

    @app.post("/v1/wms/operational/reservations",status_code=201)
    def reserve_stock(data:ReservationIn,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ROLES_WRITE: raise HTTPException(403,"Admin or Gudang required")
        if not enabled(): raise HTTPException(503,"Operational WMS feature flag is disabled")
        sku=_safe_id(data.sku,"SKU");wid=_safe_id(data.warehouse_id,"warehouse_id")
        _check_product(db,sku,data.unit,data.uom_evidence_ref);_location(db,wid,data.bin_id)
        with db:
            _lock_sku(db,sku)
            if db.execute("SELECT 1 FROM wms_operational_reservations WHERE idempotency_key=? OR reservation_id=?",
                          (data.idempotency_key,data.reservation_id)).fetchone():
                raise HTTPException(409,"Duplicate reservation ID or idempotency key")
            on_hand=_balance(db,sku,wid,data.bin_id,data.lot_batch,data.unit)
            reserved=_reserved(db,sku,wid,data.bin_id,data.lot_batch,data.unit)
            if data.quantity>on_hand-reserved+1e-9: raise HTTPException(409,"Insufficient available stock to reserve")
            db.execute("""INSERT INTO wms_operational_reservations
              (reservation_id,idempotency_key,sku,lot_batch,warehouse_id,bin_id,qty,unit,reference_document,actor_id,created_at,status)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
              (data.reservation_id,data.idempotency_key,sku,data.lot_batch,wid,data.bin_id,data.quantity,
               data.unit.upper(),data.reference_document,u["id"],_now(),"ACTIVE"))
            audit(db,u,"WMS_RESERVE","wms_reservation",data.reservation_id,
              after={"sku":sku,"quantity":data.quantity,"unit":data.unit.upper(),"warehouse_id":wid})
        return {"reservation_id":data.reservation_id,"status":"ACTIVE","available_after":round(on_hand-reserved-data.quantity,6)}

    @app.post("/v1/wms/operational/reservations/{reservation_id}/release")
    def release_reservation(reservation_id:str,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ROLES_WRITE: raise HTTPException(403,"Admin or Gudang required")
        if not enabled(): raise HTTPException(503,"Operational WMS feature flag is disabled")
        row=db.execute("SELECT status FROM wms_operational_reservations WHERE reservation_id=?",(reservation_id,)).fetchone()
        if not row: raise HTTPException(404,"Reservation not found")
        if row["status"]!="ACTIVE": raise HTTPException(409,"Only active reservation can be released")
        with db:
            db.execute("UPDATE wms_operational_reservations SET status='RELEASED' WHERE reservation_id=?",(reservation_id,))
            audit(db,u,"WMS_RESERVATION_RELEASE","wms_reservation",reservation_id,after={"status":"RELEASED"})
        return {"reservation_id":reservation_id,"status":"RELEASED"}

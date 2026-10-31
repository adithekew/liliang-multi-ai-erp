"""Isolated demo-only warehouse movement ledger.

This is NOT the company's WMS or available-to-promise stock.
Transactions use imaginary UAT-WMS-* SKUs only and never update products.stock.
"""
import re
from datetime import datetime,timezone
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel,Field,field_validator
from typing import Literal

DEMO_SKUS=("UAT-WMS-STRAW","UAT-WMS-VANILLA","UAT-WMS-MANGO")
DEMO_NAME={
    "UAT-WMS-STRAW":"Strawberry flavor UAT",
    "UAT-WMS-VANILLA":"Vanilla flavor UAT",
    "UAT-WMS-MANGO":"Mango flavor UAT"
}

class MovementIn(BaseModel):
    reference:str=Field(min_length=8,max_length=70)
    sku:Literal["UAT-WMS-STRAW","UAT-WMS-VANILLA","UAT-WMS-MANGO"]
    movement:Literal["IN","OUT"]
    qty_kg:float=Field(gt=0,le=100000,allow_inf_nan=False)
    note:str=Field(min_length=5,max_length=180)
    @field_validator("reference")
    @classmethod
    def safe_reference(cls,ref):
        ref=ref.strip().upper()
        if not re.fullmatch(r"UAT-[A-Z0-9][A-Z0-9._/-]{4,66}",ref):
            raise ValueError("Reference must start UAT- and contain only safe characters")
        return ref

def install_wms_demo(db):
    db.execute("""CREATE TABLE IF NOT EXISTS wms_demo_movements(
        id INTEGER PRIMARY KEY,reference TEXT UNIQUE NOT NULL,
        sku TEXT NOT NULL,movement TEXT NOT NULL,qty_kg REAL NOT NULL,
        actor_id INTEGER NOT NULL,at TEXT NOT NULL,note TEXT NOT NULL)""".replace(
        "id INTEGER PRIMARY KEY","id BIGSERIAL PRIMARY KEY"
        ) if hasattr(db,"_raw") else
        """CREATE TABLE IF NOT EXISTS wms_demo_movements(
        id INTEGER PRIMARY KEY,reference TEXT UNIQUE NOT NULL,
        sku TEXT NOT NULL,movement TEXT NOT NULL,qty_kg REAL NOT NULL,
        actor_id INTEGER NOT NULL,at TEXT NOT NULL,note TEXT NOT NULL)""")

def ledger(db):
    rows=db.execute("""SELECT id,reference,sku,movement,qty_kg,actor_id,at,note
          FROM wms_demo_movements ORDER BY id DESC LIMIT 100""").fetchall()
    balances={}
    for sku in DEMO_SKUS:
        a=db.execute("""SELECT COALESCE(SUM(CASE WHEN movement='IN' THEN qty_kg ELSE -qty_kg END),0)
                        AS balance FROM wms_demo_movements WHERE sku=?""",(sku,)).fetchone()
        balances[sku]={"sku":sku,"name":DEMO_NAME[sku],"virtual_on_hand_kg":round(float(a["balance"]),3)}
    return {"mode":"UAT_SANDBOX_ONLY","not_company_stock":True,
        "separate_from_products_table":True,
        "skus":list(balances.values()),
        "movements":[dict(row) for row in rows]}

def mount_wms_demo(app,current,get_db,audit):
    @app.get("/v1/wms/demo")
    def read_demo(u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","manager","gudang"):
            raise HTTPException(403,"Only Admin, Manager or Gudang may view WMS demo")
        return ledger(db)

    @app.post("/v1/wms/demo/movements",status_code=201)
    def create_demo_movement(data:MovementIn,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","gudang"):
            raise HTTPException(403,"Only Admin or Gudang may enter UAT WMS demo movements")
        if db.execute("SELECT 1 FROM wms_demo_movements WHERE reference=?",(data.reference,)).fetchone():
            raise HTTPException(409,"Duplicate UAT movement reference")
        current_balance=db.execute("""SELECT COALESCE(SUM(CASE WHEN movement='IN' THEN qty_kg ELSE -qty_kg END),0)
                   AS total FROM wms_demo_movements WHERE sku=?""",(data.sku,)).fetchone()
        available=float(current_balance["total"])
        if data.movement=="OUT" and data.qty_kg>available+1e-9:
            raise HTTPException(409,"UAT virtual stock insufficient; record IN first")
        # Never modify live company stock; the isolated ledger is its own UAT fixture.
        with db:
            cur=db.execute("""INSERT INTO wms_demo_movements
                (reference,sku,movement,qty_kg,actor_id,at,note)
                VALUES(?,?,?,?,?,?,?)""",
                (data.reference,data.sku,data.movement,data.qty_kg,u["id"],
                 datetime.now(timezone.utc).isoformat(),data.note))
            audit(db,u,"WMS_UAT_"+data.movement,"wms_demo_movement",cur.lastrowid,
                  after={"sku":data.sku,"direction":data.movement,
                         "qty_kg":data.qty_kg,"data_scope":"UAT_SANDBOX_ONLY"})
        return {"id":cur.lastrowid,"reference":data.reference,
                "mode":"UAT_SANDBOX_ONLY","changed_real_stock":False,
                "balance_kg":round(available+(data.qty_kg if data.movement=="IN" else -data.qty_kg),3)}

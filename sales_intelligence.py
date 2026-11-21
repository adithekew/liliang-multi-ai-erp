"""Opt-in, auditable SALES FACTS pipeline for AI-03 and AI-04.

Never invent company orders, backfill missing weeks with zero, or treat an
administrator's documentary attestation as independent external verification.
Historical facts live in the configured private database, never source control.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from math import sin
from typing import Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator

SOURCE="COMPANY_ATTESTED"
MIN_BASKETS=10
MIN_CONTIGUOUS_WEEKS=24

class Item(BaseModel):
    sku: str=Field(min_length=3,max_length=80)
    qty: float=Field(gt=0,le=10000000)
    unit: str=Field(min_length=1,max_length=24)
    qty_kg_verified: float|None=Field(default=None,ge=0,le=10000000)
    return_qty_kg: float=Field(default=0,ge=0,le=10000000)
    line_status: Literal["CONFIRMED","CANCELLED","RETURNED","PARTIAL","OTHER"]="CONFIRMED"
    kg_conversion_evidence_ref: str|None=Field(default=None,max_length=120)
    @field_validator("sku")
    @classmethod
    def valid_sku(cls,v):
        v=v.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{2,79}",v):
            raise ValueError("Invalid SKU format")
        return v
    @field_validator("unit")
    @classmethod
    def valid_unit(cls,v):
        v=v.strip().upper()
        if not re.fullmatch(r"[A-Z0-9._/-]{1,24}",v): raise ValueError("Invalid source unit")
        return v
    @model_validator(mode="after")
    def verify_kg_conversion(self):
        if self.unit=="KG":
            if self.qty_kg_verified is None: self.qty_kg_verified=self.qty
            elif abs(self.qty_kg_verified-self.qty)>1e-6:
                raise ValueError("KG source quantity must equal verified KG quantity")
        elif self.qty_kg_verified is not None and not self.kg_conversion_evidence_ref:
            raise ValueError("Non-KG conversion requires an evidence reference")
        if self.return_qty_kg>0 and self.qty_kg_verified is None:
            raise ValueError("Return quantity requires verified KG conversion")
        if self.qty_kg_verified is not None and self.return_qty_kg>self.qty_kg_verified:
            raise ValueError("Return KG cannot exceed verified gross KG")
        return self

class OrderFact(BaseModel):
    order_ref: str=Field(min_length=5,max_length=80)
    order_date: date
    status: Literal["CONFIRMED","FULFILLED","CANCELLED","RETURNED","PARTIAL"]
    lines: list[Item]=Field(min_length=1,max_length=100)
    @field_validator("order_ref")
    @classmethod
    def valid_ref(cls,v):
        v=v.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{4,79}",v):
            raise ValueError("Use pseudonymous order references without customer names")
        return v
    @field_validator("lines")
    @classmethod
    def distinct_skus(cls,v):
        if len({item.sku for item in v})!=len(v):
            raise ValueError("Duplicate SKU in order; aggregate quantity before importing")
        return v

class ImportFacts(BaseModel):
    confirmation: Literal["IMPORT COMPANY ATTESTED SALES FACTS"]
    source_document_ref: str=Field(min_length=8,max_length=100)
    finance_reconciliation_ref: str=Field(min_length=8,max_length=120)
    finance_verifier_id: str=Field(min_length=3,max_length=80)
    source_authorized: Literal[True]
    orders: list[OrderFact]=Field(min_length=1,max_length=200)
    @field_validator("source_document_ref")
    @classmethod
    def source_ref(cls,v):
        v=v.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/#-]{7,99}",v):
            raise ValueError("A source document register ID is required, not a filename or customer name")
        return v
    @field_validator("finance_reconciliation_ref")
    @classmethod
    def finance_ref(cls,v):
        v=v.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/#-]{7,119}",v):
            raise ValueError("Finance reconciliation register reference is required")
        return v
    @field_validator("finance_verifier_id")
    @classmethod
    def finance_actor(cls,v):
        v=v.strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,80}",v):
            raise ValueError("Use a pseudonymous Finance verifier ID")
        return v
    @field_validator("orders")
    @classmethod
    def refs_unique(cls,v):
        if len({x.order_ref for x in v})!=len(v):
            raise ValueError("Duplicate order_ref in import batch")
        return v

class WeeklyDemandItem(BaseModel):
    sku:str=Field(min_length=3,max_length=80)
    week_start:date
    week_end:date
    gross_sales_kg:float=Field(ge=0,le=100000000)
    return_kg:float=Field(default=0,ge=0,le=100000000)
    net_demand_kg:float=Field(ge=0,le=100000000)
    missing_data_flag:Literal["NONE","PARTIAL_WEEK","DATA_MISSING","STOCKOUT","SKU_INACTIVE","OTHER"]
    source_document_ref:str=Field(min_length=8,max_length=120)
    unit_definition_version:str=Field(min_length=2,max_length=80)
    @field_validator("sku")
    @classmethod
    def valid_sku(cls,v):
        v=v.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{2,79}",v): raise ValueError("Invalid SKU")
        return v
    @model_validator(mode="after")
    def complete_week_and_net(self):
        if self.week_start.weekday()!=0 or self.week_end!=self.week_start+timedelta(days=6):
            raise ValueError("Demand records must use Monday-to-Sunday calendar weeks")
        if self.return_kg>self.gross_sales_kg:
            raise ValueError("Return KG cannot exceed gross sales KG")
        if abs(self.net_demand_kg-(self.gross_sales_kg-self.return_kg))>1e-6:
            raise ValueError("Net demand must equal gross sales KG minus return KG")
        return self

class ImportWeeklyDemand(BaseModel):
    confirmation:Literal["IMPORT FINANCE VERIFIED WEEKLY DEMAND"]
    finance_reconciliation_ref:str=Field(min_length=8,max_length=120)
    finance_verifier_id:str=Field(min_length=3,max_length=80)
    source_authorized:Literal[True]
    records:list[WeeklyDemandItem]=Field(min_length=1,max_length=10000)
    @field_validator("finance_reconciliation_ref")
    @classmethod
    def finance_ref(cls,v):
        v=v.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/#-]{7,119}",v): raise ValueError("Finance reconciliation reference required")
        return v
    @field_validator("finance_verifier_id")
    @classmethod
    def finance_actor(cls,v):
        v=v.strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,80}",v): raise ValueError("Use pseudonymous Finance verifier ID")
        return v
    @field_validator("records")
    @classmethod
    def unique_sku_weeks(cls,v):
        keys=[(x.sku,x.week_start) for x in v]
        if len(keys)!=len(set(keys)): raise ValueError("Duplicate SKU/week in batch")
        return v

def install_sales_schema(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS ai_sales_orders(
       order_ref TEXT PRIMARY KEY, order_date TEXT NOT NULL, status TEXT NOT NULL,
       source_classification TEXT NOT NULL, source_document_ref TEXT NOT NULL,
       finance_reconciliation_ref TEXT NOT NULL DEFAULT '',
       finance_verifier_id TEXT NOT NULL DEFAULT '',
       created_by INTEGER NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS ai_sales_lines(
       order_ref TEXT NOT NULL, sku TEXT NOT NULL, qty REAL NOT NULL, unit TEXT NOT NULL,
       qty_kg REAL, return_qty_kg REAL NOT NULL DEFAULT 0,
       line_status TEXT NOT NULL DEFAULT 'CONFIRMED',
       kg_conversion_evidence_ref TEXT,
       PRIMARY KEY(order_ref,sku),
       FOREIGN KEY(order_ref) REFERENCES ai_sales_orders(order_ref)
    );
    CREATE TABLE IF NOT EXISTS ai_sales_weekly_demand(
       sku TEXT NOT NULL, week_start TEXT NOT NULL, week_end TEXT NOT NULL,
       gross_sales_kg REAL NOT NULL, return_kg REAL NOT NULL, net_demand_kg REAL NOT NULL,
       missing_data_flag TEXT NOT NULL, source_document_ref TEXT NOT NULL,
       finance_reconciliation_ref TEXT NOT NULL, finance_verifier_id TEXT NOT NULL,
       unit_definition_version TEXT NOT NULL, source_classification TEXT NOT NULL,
       created_by INTEGER NOT NULL, created_at TEXT NOT NULL,
       PRIMARY KEY(sku,week_start)
    );
    """)
    # Idempotent schema evolution for databases created by earlier pilot releases.
    if hasattr(db,"_raw"):
        order_cols={r["column_name"] for r in db.execute(
          "SELECT column_name FROM information_schema.columns WHERE table_name='ai_sales_orders'").fetchall()}
        line_cols={r["column_name"] for r in db.execute(
          "SELECT column_name FROM information_schema.columns WHERE table_name='ai_sales_lines'").fetchall()}
    else:
        order_cols={r["name"] for r in db.execute("PRAGMA table_info(ai_sales_orders)").fetchall()}
        line_cols={r["name"] for r in db.execute("PRAGMA table_info(ai_sales_lines)").fetchall()}
    for col,ddl in (("finance_reconciliation_ref","TEXT NOT NULL DEFAULT ''"),("finance_verifier_id","TEXT NOT NULL DEFAULT ''")):
        if col not in order_cols: db.execute("ALTER TABLE ai_sales_orders ADD COLUMN "+col+" "+ddl)
    for col,ddl in (("qty_kg","REAL"),("return_qty_kg","REAL NOT NULL DEFAULT 0"),
                    ("line_status","TEXT NOT NULL DEFAULT 'CONFIRMED'"),("kg_conversion_evidence_ref","TEXT")):
        if col not in line_cols: db.execute("ALTER TABLE ai_sales_lines ADD COLUMN "+col+" "+ddl)

def _rows(db):
    return [dict(r) for r in db.execute(
        """SELECT o.order_ref,o.order_date,o.status,o.source_classification,
                  l.sku,l.qty,l.unit,l.qty_kg,l.return_qty_kg,l.line_status
           FROM ai_sales_orders o JOIN ai_sales_lines l ON l.order_ref=o.order_ref
           WHERE o.source_classification=? AND o.status IN ('CONFIRMED','FULFILLED','PARTIAL')
             AND l.line_status NOT IN ('CANCELLED','RETURNED')
           ORDER BY o.order_date,o.order_ref,l.sku""",(SOURCE,)).fetchall()]

def _eligible(db):
    rows=_rows(db)
    by_order=defaultdict(set)
    weekly=defaultdict(lambda:defaultdict(float))
    for r in rows:
        if float(r["qty"])>0: by_order[r["order_ref"]].add(r["sku"])
        # Forecast only from explicit verified KG values. Original non-KG units
        # remain eligible for basket mining but never get silently converted.
        if r["qty_kg"] is not None:
            d=date.fromisoformat(r["order_date"])
            monday=d-timedelta(days=d.weekday())
            net=max(0.0,float(r["qty_kg"])-float(r["return_qty_kg"] or 0))
            weekly[r["sku"]][monday]+=net
    return rows,by_order,weekly

def bundling_actual(db):
    rows,by_order,weekly=_eligible(db)
    n=len(by_order)
    if n<MIN_BASKETS:
        return {"status":"NOT_READY","data_classification":SOURCE,
          "basket_count":n,"required_baskets":MIN_BASKETS,"rules":[],
          "reason":"Need >=10 distinct eligible confirmed/fulfilled order references. No synthetic fallback."}
    counts=Counter(sku for basket in by_order.values() for sku in basket)
    pairs=Counter((a,b) for basket in by_order.values() for a in basket for b in basket if a!=b)
    rules=[]
    for (a,b),c in pairs.items():
        sup=c/n
        conf=c/counts[a]
        lift=conf/(counts[b]/n)
        if sup>=.12 and conf>=.35:
            rules.append({"antecedent_sku":a,"recommended_sku":b,
                          "co_occurrences":c,"support":round(sup,3),
                          "confidence":round(conf,3),"lift":round(lift,3)})
    rules.sort(key=lambda x:(-x["lift"],-x["confidence"],x["antecedent_sku"],x["recommended_sku"]))
    return {"status":"COMPANY_FACTS_ATTESTED_NOT_SCIENTIFICALLY_VALIDATED",
         "data_classification":SOURCE,"basket_count":n,"rules":rules[:10],
         "auto_sell":False,"source":"Private admin-attested sales order facts. Evidence and cancellations require Finance review."}

def forecasting_actual(db,sku:str,horizon:int):
    weekly_rows=db.execute("""SELECT week_start,net_demand_kg FROM ai_sales_weekly_demand
       WHERE sku=? AND source_classification=? AND missing_data_flag='NONE'
       ORDER BY week_start""",(sku,SOURCE)).fetchall()
    points={date.fromisoformat(r["week_start"]):float(r["net_demand_kg"]) for r in weekly_rows}
    if not points:
        return {"status":"NOT_READY","sku":sku,"weekly_points":0,
                "required_contiguous_weeks":MIN_CONTIGUOUS_WEEKS,
                "data_classification":SOURCE,
                "reason":"No explicitly Finance-reconciled complete weekly KG demand series imported. Order-line gaps are not assumed to be zero."}
    end=max(points)
    expected=[end-timedelta(weeks=i) for i in reversed(range(MIN_CONTIGUOUS_WEEKS))]
    if any(d not in points for d in expected):
        return {"status":"NOT_READY","sku":sku,"weekly_points":len(points),
                "required_contiguous_weeks":MIN_CONTIGUOUS_WEEKS,
                "data_classification":SOURCE,
                "reason":"Missing observed weekly sales records. No zero-imputation; reconcile incomplete periods before forecasting."}
    # Use contiguous observed history extending backward from latest week.
    dates=[end]
    cursor=end-timedelta(weeks=1)
    while cursor in points:
        dates.append(cursor);cursor-=timedelta(weeks=1)
    dates=list(reversed(dates))
    values=[float(points[d]) for d in dates]
    backtest=[(values[i],sum(values[i-4:i])/4) for i in range(4,len(values))]
    mae=sum(abs(a-p) for a,p in backtest)/len(backtest)
    wmape=100*sum(abs(a-p) for a,p in backtest)/max(1,sum(abs(a) for a,p in backtest))
    predicted=round(sum(values[-4:])/4,2)
    forecast=[{"week":(end+timedelta(weeks=i)).isoformat(),"predicted_units":predicted}
              for i in range(1,horizon+1)]
    return {"status":"COMPANY_FACTS_ATTESTED_NOT_SCIENTIFICALLY_VALIDATED",
       "data_classification":SOURCE,"sku":sku,
       "method":"4-week moving average","weekly_points":len(values),
       "history":[{"week":d.isoformat(),"units":round(v,2)} for d,v in zip(dates,values)],
       "forecast":forecast,
       "metrics":{"rolling_mae_units":round(mae,2),"rolling_wmape_pct":round(wmape,2)},
       "units":"kg / completed calendar week (source KG required)",
       "cautions":["Missing weeks are not assumed to mean zero sales.",
                   "Partial latest weeks, returns, stockouts, lead time and mix of units must be reconciled.",
                   "Model not independently validated for production purchasing."]}

def readiness(db):
    rows,orders,weekly=_eligible(db)
    weekly_skus=[r["sku"] for r in db.execute(
        "SELECT DISTINCT sku FROM ai_sales_weekly_demand WHERE source_classification=?",(SOURCE,)).fetchall()]
    forecast_ready=[sku for sku in weekly_skus if forecasting_actual(db,sku,1)["status"]!="NOT_READY"]
    all_orders=db.execute("SELECT COUNT(*) AS n FROM ai_sales_orders").fetchone()["n"]
    return {"stored_order_count":all_orders,"eligible_order_count":len(orders),
            "eligible_line_count":len(rows),"sku_count":len(weekly_skus),
            "bundling_ready":len(orders)>=MIN_BASKETS,
            "forecast_ready_sku_count":len(forecast_ready),
            "forecast_ready_skus":sorted(forecast_ready)[:50],
            "source_status":SOURCE,"needs_finance_validation":True,
            "company_models_scientifically_validated":False,
            "missing_for_real_evaluation":["Finance reconciliation (June, cancellations and returns)",
               "Verified kilogram quantities and source unit conversion evidence","Temporal train/test backtest",
               "Stockout and receipt/lead-time data for replenishment decisions"]}

class ProxyGroup(BaseModel):
    group_id: str=Field(min_length=3,max_length=80)
    month: str=Field(pattern=r"^2025-(0[1-9]|1[0-2])$")
    skus: list[str]=Field(min_length=1,max_length=20)  # limit pair-count amplification

class ProxyPreview(BaseModel):
    assumption: Literal["USER_ASSUMED_CO_PURCHASE_PROXY"]
    acknowledge_not_invoice_verified: Literal[True]
    groups: list[ProxyGroup]=Field(min_length=1,max_length=1000)

def preview_proxy_baskets(payload:ProxyPreview):
    # Local upload only, not committed as invoice-grade sales facts.
    basket={}
    excluded=0
    for row in payload.groups:
        if row.month=="2025-06":
            excluded+=1
            continue
        if row.group_id in basket:
            raise HTTPException(422,"Duplicate proxy group ID")
        unique={sku.strip().upper() for sku in row.skus if sku.strip()}
        if not unique or any(len(s)>100 for s in unique):
            raise HTTPException(422,"Malformed proxy SKU")
        basket[row.group_id]=unique
    n=len(basket)
    if not n:raise HTTPException(422,"No eligible non-June basket groups")
    from collections import Counter
    counts=Counter(s for group in basket.values() for s in group)
    pairs=Counter((a,b) for group in basket.values() for a in group for b in group if a!=b)
    rules=[]
    for (a,b),num in pairs.items():
        support=num/n
        confidence=num/counts[a]
        lift=confidence/(counts[b]/n)
        if num>=2 and support>=.003 and confidence>=.20:
            rules.append({"antecedent_sku":a,"recommended_sku":b,
                          "proxy_co_groups":num,"support":round(support,5),
                          "confidence":round(confidence,5),"lift":round(lift,4)})
    rules.sort(key=lambda r:(-r["proxy_co_groups"],-r["lift"],r["antecedent_sku"],r["recommended_sku"]))
    return {"status":"EXPLORATORY_USER_ASSUMED_PROXY_NOT_INVOICE_VERIFIED",
            "excluded_june_groups":excluded,
            "eligible_proxy_groups":n,"multi_sku_groups":sum(len(v)>1 for v in basket.values()),
            "rule_count":len(rules),"rules":rules[:30],
            "scientific_accuracy_validated":False,
            "auto_sell":False,"persisted":False,
            "warning":"Document grouping was assumed to indicate co-purchase. No original invoice ID or order date is verified. These rules are not company-validated historical transaction associations."}

def mount_sales_intelligence(app,current,get_db,audit):
    @app.get("/v1/ai/sales-readiness")
    def sales_ready(u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","sales","manager","gudang"):
            raise HTTPException(403,"Role access denied")
        return readiness(db)

    @app.post("/v1/admin/ai-sales-facts/import")
    def import_sales_facts(data:ImportFacts,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="admin":raise HTTPException(403,"Admin required")
        if str(u["email"]).lower().startswith("uat-"):
            raise HTTPException(403,"UAT account cannot attest real company transactions")
        if any(o.order_date>date.today() for o in data.orders):
            raise HTTPException(422,"Future-dated sales orders are not permitted")
        # Fail the whole batch if *any* product or order ref cannot be validated.
        refs=[o.order_ref for o in data.orders]
        existing=db.execute(
             "SELECT order_ref FROM ai_sales_orders WHERE order_ref IN ("+",".join("?" for _ in refs)+")",tuple(refs)).fetchall()
        if existing:
            raise HTTPException(409,"Order reference already exists; import is append-only")
        skus=sorted({x.sku for order in data.orders for x in order.lines})
        found={row["sku"] for row in db.execute(
           "SELECT sku FROM products WHERE sku IN ("+",".join("?" for _ in skus)+")",tuple(skus)).fetchall()}
        unknown=sorted(set(skus)-found)
        if unknown:
            raise HTTPException(422,"Unknown catalog SKU(s): "+", ".join(unknown[:10]))
        stamp=datetime.now(timezone.utc).isoformat()
        with db:
            for o in data.orders:
                db.execute("""INSERT INTO ai_sales_orders
                     (order_ref,order_date,status,source_classification,source_document_ref,
                      finance_reconciliation_ref,finance_verifier_id,created_by,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                     (o.order_ref,o.order_date.isoformat(),o.status,SOURCE,
                      data.source_document_ref,data.finance_reconciliation_ref,
                      data.finance_verifier_id,u["id"],stamp))
                for item in o.lines:
                    db.execute("""INSERT INTO ai_sales_lines
                      (order_ref,sku,qty,unit,qty_kg,return_qty_kg,line_status,kg_conversion_evidence_ref)
                      VALUES(?,?,?,?,?,?,?,?)""",
                      (o.order_ref,item.sku,item.qty,item.unit,item.qty_kg_verified,
                       item.return_qty_kg,item.line_status,item.kg_conversion_evidence_ref))
            audit(db,u,"IMPORT_AI_SALES_FACTS","ai_sales_batch",0,
                  after={"orders":len(data.orders),"lines":sum(len(o.lines) for o in data.orders),
                         "source_document_ref":data.source_document_ref,
                         "attestation_not_independent_verification":True})
        return {"status":"IMPORTED_COMPANY_ATTESTED_NOT_VALIDATED",
                "orders":len(data.orders),"lines":sum(len(o.lines) for o in data.orders),
                "note":"Immutable order facts saved to private ERP database; no automatic retraining."}

    @app.post("/v1/admin/ai-demand-weekly/import")
    def import_weekly_demand(data:ImportWeeklyDemand,u=Depends(current),db=Depends(get_db)):
        if u["role"]!="admin": raise HTTPException(403,"Admin required")
        if str(u["email"]).lower().startswith("uat-"):
            raise HTTPException(403,"UAT account cannot attest company demand facts")
        today=date.today()
        if any(r.week_end>=today for r in data.records):
            raise HTTPException(422,"Only completed historical calendar weeks can be imported")
        skus=sorted({r.sku for r in data.records})
        found={r["sku"] for r in db.execute("SELECT sku FROM products WHERE sku IN ("+",".join("?" for _ in skus)+")",tuple(skus)).fetchall()}
        if set(skus)-found: raise HTTPException(422,"Unknown catalog SKU in weekly demand import")
        refs=[(r.sku,r.week_start.isoformat()) for r in data.records]
        existing=[]
        for sku,week in refs:
            if db.execute("SELECT 1 FROM ai_sales_weekly_demand WHERE sku=? AND week_start=?",(sku,week)).fetchone():
                existing.append((sku,week))
        if existing: raise HTTPException(409,"SKU/week already exists; weekly demand import is append-only")
        stamp=datetime.now(timezone.utc).isoformat()
        with db:
            for row in data.records:
                db.execute("""INSERT INTO ai_sales_weekly_demand
                  (sku,week_start,week_end,gross_sales_kg,return_kg,net_demand_kg,missing_data_flag,
                   source_document_ref,finance_reconciliation_ref,finance_verifier_id,
                   unit_definition_version,source_classification,created_by,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (row.sku,row.week_start.isoformat(),row.week_end.isoformat(),row.gross_sales_kg,
                   row.return_kg,row.net_demand_kg,row.missing_data_flag,row.source_document_ref,
                   data.finance_reconciliation_ref,data.finance_verifier_id,row.unit_definition_version,
                   SOURCE,u["id"],stamp))
            audit(db,u,"IMPORT_AI_WEEKLY_DEMAND","ai_sales_weekly_batch",0,
              after={"records":len(data.records),"skus":len(skus),
                     "finance_reconciliation_ref":data.finance_reconciliation_ref,
                     "finance_verifier_id":data.finance_verifier_id,
                     "attestation_not_independent_verification":True})
        return {"status":"IMPORTED_COMPANY_ATTESTED_NOT_INDEPENDENTLY_VERIFIED",
          "weekly_records":len(data.records),"sku_count":len(skus),
          "note":"Only records marked missing_data_flag=NONE enter forecasting. No zero-fill is performed."}

    @app.post("/v1/ai/bundling-proxy-preview")
    def proxy_preview(data:ProxyPreview,u=Depends(current)):
        if u["role"] not in ("admin","manager"):
            raise HTTPException(403,"Only Admin/Manager can preview unverified commercial groupings")
        return preview_proxy_baskets(data)

    @app.get("/v1/ai/bundling-company")
    def real_bundling(u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","sales","manager"):
            raise HTTPException(403,"Role access denied")
        return bundling_actual(db)

    @app.get("/v1/ai/forecast-company")
    def real_forecast(sku:str=Query(min_length=3,max_length=80),
                      horizon:int=Query(default=4,ge=1,le=8),u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","sales","manager","gudang"):
            raise HTTPException(403,"Role access denied")
        return forecasting_actual(db,sku.upper().strip(),horizon)

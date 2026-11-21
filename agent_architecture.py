"""Private, deterministic, role-aware orchestration across company-backed ERP tools.

No external LLM/provider is called. Tools are read-only; the agent cannot approve,
reserve, dispatch, adjust stock, or mutate sales/finance facts. Each run records
hashes and tool provenance without persisting raw inquiry text.
"""
from __future__ import annotations
import hashlib,json,os,time,uuid
from datetime import datetime,timezone
from typing import Literal
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field

ROLES={"admin","sales","technical","manager","gudang"}

class AgentRequest(BaseModel):
    task:Literal["INQUIRY","BUNDLING","FORECAST","STOCK","OVERVIEW"]
    query:str|None=Field(default=None,min_length=5,max_length=3000)
    sku:str|None=Field(default=None,min_length=3,max_length=80)
    horizon:int=Field(default=4,ge=1,le=8)
    top_k:int=Field(default=10,ge=1,le=30)

def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _trace(db,user,task,query,tools,result,elapsed,status):
    trace_id="AGT-"+uuid.uuid4().hex[:20].upper()
    payload=json.dumps(result,ensure_ascii=False,sort_keys=True,default=str)
    db.execute("""INSERT INTO agent_tool_traces
      (trace_id,actor_id,actor_role,task,query_sha256,tools_json,result_sha256,elapsed_ms,created_at,status)
      VALUES(?,?,?,?,?,?,?,?,?,?)""",
      (trace_id,user["id"],user["role"],task,_sha(query) if query else None,
       json.dumps(tools),_sha(payload),int(elapsed),datetime.now(timezone.utc).isoformat(),status))
    return trace_id

def install_agent_schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS agent_tool_traces(
      trace_id TEXT PRIMARY KEY,actor_id INTEGER NOT NULL,actor_role TEXT NOT NULL,
      task TEXT NOT NULL,query_sha256 TEXT,tools_json TEXT NOT NULL,result_sha256 TEXT NOT NULL,
      elapsed_ms INTEGER NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL)""")

def execute_agent(data,user,db):
    if data.task=="INQUIRY" and user["role"] not in {"admin","sales","technical","manager"}:
        raise HTTPException(403,"Role access denied for inquiry analysis")
    if data.task=="BUNDLING" and user["role"] not in {"admin","sales","manager"}:
        raise HTTPException(403,"Role access denied for bundling analytics")
    if data.task=="FORECAST" and user["role"] not in {"admin","sales","manager","gudang"}:
        raise HTTPException(403,"Role access denied for forecasting")
    if data.task=="STOCK" and user["role"] not in {"admin","manager","gudang","sales","technical"}:
        raise HTTPException(403,"Role access denied for stock lookup")
    start=time.perf_counter();tools=[];result={}
    if data.task=="INQUIRY":
        if not data.query: raise HTTPException(422,"query is required for INQUIRY")
        from multi_ai import interpret,score_products
        tools.append("AI01_REQUIREMENT_INTERPRETER")
        ai01=interpret(data.query)
        rows=[dict(r) for r in db.execute("""SELECT p.id,p.sku,p.name,p.description,p.profile,p.application,p.source_ref,
                  d.product_type,d.application_raw,d.composition_raw
                  FROM products p LEFT JOIN catalog_product_details d ON d.sku=p.sku ORDER BY p.sku""").fetchall()]
        tools.append("AI02_PRODUCT_RETRIEVAL")
        neural_enabled=bool(os.getenv("LILIANG_NEURAL_MODEL_PATH") and os.getenv("LILIANG_NEURAL_INDEX_PATH"))
        if neural_enabled:
            try:
                from research.neural_retrieval import retrieve
                ai02=retrieve(data.query,rows,data.top_k)
            except Exception:
                # Fail closed to the explicit lexical baseline; never invent a
                # neural result or suppress the model/index fault in provenance.
                ai02={"method":"BM25_FALLBACK_NEURAL_UNAVAILABLE","results":score_products(data.query,rows),
                      "neural_status":"UNAVAILABLE_OR_STALE","scientifically_validated":False}
        else:
            ai02={"method":"BM25_LEXICAL_BASELINE","results":score_products(data.query,rows),
                  "neural_status":"NOT_CONFIGURED","scientifically_validated":False}
        result={"task":"INQUIRY","AI01":ai01,"AI02":ai02,
          "human_gate":"TECHNICAL_REVIEW_REQUIRED","agent_decision":"ADVISORY_ONLY",
          "company_data_sent_to_external_provider":False}
    elif data.task=="BUNDLING":
        from sales_intelligence import bundling_actual
        tools.append("AI03_COMPANY_ORDER_ASSOCIATIONS")
        result={"task":"BUNDLING","AI03":bundling_actual(db),"agent_decision":"ADVISORY_ONLY","auto_sell":False}
    elif data.task=="FORECAST":
        if not data.sku: raise HTTPException(422,"sku is required for FORECAST")
        from sales_intelligence import forecasting_actual
        tools.append("AI04_COMPANY_DEMAND_FORECAST")
        result={"task":"FORECAST","AI04":forecasting_actual(db,data.sku.strip().upper(),data.horizon),
                "agent_decision":"ADVISORY_ONLY","auto_reorder":False}
    elif data.task=="STOCK":
        from wms_operational import stock_rows,enabled
        tools.append("WMS_OPERATIONAL_STOCK_READ")
        result={"task":"STOCK","feature_enabled":enabled(),
                "rows":stock_rows(db,data.sku.strip().upper() if data.sku else None),
                "agent_decision":"READ_ONLY","stock_mutated":False}
    else:
        from company_model_governance import company_gates
        tools.append("COMPANY_MODEL_READINESS_GATES")
        result={"task":"OVERVIEW","readiness":company_gates(db),
                "agent_decision":"READ_ONLY"}
    elapsed=(time.perf_counter()-start)*1000
    trace_id=_trace(db,user,data.task,data.query,tools,result,elapsed,"COMPLETED")
    return {"trace_id":trace_id,"task":data.task,"tools_called":tools,
      "elapsed_ms":round(elapsed,2),"result":result,
      "trace_policy":"Stores query/result hashes and tool names only; raw inquiry text is not persisted.",
      "external_llm_used":False,"external_company_data_egress":False,
      "write_actions_performed":False,
      "limitations":["Agent is deterministic orchestration, not an autonomous business decision maker.",
       "Technical/Manager approval remains mandatory.",
       "No stock, order, finance, reservation, or dispatch mutations are available through this endpoint."]}

def mount_company_agent(app,current,get_db):
    @app.post("/v1/agent/execute")
    def run_agent(data:AgentRequest,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ROLES: raise HTTPException(403,"Role access denied")
        try:return execute_agent(data,u,db)
        except HTTPException: raise
        except Exception:
            raise HTTPException(503,"Agent tool execution failed; no business mutation was performed") from None

    @app.get("/v1/agent/traces")
    def agent_traces(limit:int=20,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in {"admin","manager","technical"}: raise HTTPException(403,"Role access denied")
        rows=db.execute("""SELECT trace_id,actor_role,task,query_sha256,tools_json,result_sha256,
             elapsed_ms,created_at,status FROM agent_tool_traces ORDER BY created_at DESC LIMIT ?""",(limit,)).fetchall()
        return {"traces":[dict(r) for r in rows],"raw_prompts_stored":False}

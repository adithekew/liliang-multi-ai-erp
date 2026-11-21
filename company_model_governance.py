"""Explicit company data/model readiness gates. Read-only; never fabricate validation metrics."""
import os
from pathlib import Path
from fastapi import Depends,HTTPException

def company_gates(db):
    product=db.execute("""SELECT COUNT(*) AS n,
               SUM(CASE WHEN source_ref='CATALOG-PDF-UNVERIFIED' THEN 1 ELSE 0 END) AS unverified,
               SUM(CASE WHEN stock IS NULL THEN 1 ELSE 0 END) AS missing_stock
               FROM products""").fetchone()
    orders=db.execute("SELECT COUNT(*) AS n FROM ai_sales_orders").fetchone()["n"]
    rows=db.execute("SELECT COUNT(*) AS n FROM ai_sales_lines").fetchone()["n"]
    finance_refs=db.execute("""SELECT COUNT(*) AS n FROM ai_sales_orders
       WHERE COALESCE(finance_reconciliation_ref,'')<>'' AND COALESCE(finance_verifier_id,'')<>''""").fetchone()["n"]
    labelled=db.execute("""SELECT COUNT(*) AS n
         FROM reviews r JOIN users u ON u.id=r.reviewer_id
         JOIN runs q ON q.id=r.run_id JOIN inquiries i ON i.id=q.inquiry_id
         WHERE LOWER(u.email) NOT LIKE 'uat-%%@liliang.local'
           AND UPPER(COALESCE(i.customer_ref,'')) NOT LIKE 'UAT-%%'
           AND r.label BETWEEN 0 AND 3""").fetchone()["n"]
    try:
        from sales_intelligence import readiness as sales_readiness
        sales=sales_readiness(db)
    except Exception:
        sales={"eligible_order_count":0,"forecast_ready_sku_count":0,"forecast_ready_skus":[]}
    model_dir=Path(os.getenv("LILIANG_NEURAL_MODEL_PATH","")).expanduser()
    index_path=Path(os.getenv("LILIANG_NEURAL_INDEX_PATH","")).expanduser()
    neural_artifacts_available=bool(os.getenv("LILIANG_NEURAL_MODEL_PATH") and os.getenv("LILIANG_NEURAL_INDEX_PATH")
                                    and model_dir.is_dir() and index_path.is_file())
    wms_enabled=os.getenv("WMS_OPERATIONAL_ENABLED","false").lower()=="true"
    try:agent_traces=db.execute("SELECT COUNT(*) AS n FROM agent_tool_traces").fetchone()["n"]
    except Exception:agent_traces=0
    gates=[
      {"id":"AI-01","target":"CUSTOMER_INTENT_INTERPRETER",
       "candidate_label_records":0,"ready_for_company_training":False,
       "reason":"Need authorized anonymized inquiries, intent/entity gold labels, adjudication and held-out evaluation; current interpreter remains a deterministic baseline."},
      {"id":"AI-02","target":"FULL_CATALOG_NEURAL_RRF",
       "candidate_legacy_review_records":labelled,"private_neural_artifacts_available":neural_artifacts_available,
       "ready_for_company_validation":False,
       "reason":"Need complete current verified catalog, authorized free-text inquiries, two independent Technical reviewers, adjudication and frozen held-out paired BM25/dense/RRF evaluation."},
      {"id":"AI-03","target":"COMPANY_ORDER_ASSOCIATIONS",
       "candidate_order_records":orders,"finance_reconciliation_references":finance_refs,
       "eligible_company_attested_baskets":sales.get("eligible_order_count",0),
       "minimum_10_baskets_for_exploration":sales.get("eligible_order_count",0)>=10,
       "ready_for_scientific_validation":False,
       "reason":"10 baskets are only an exploratory threshold. Finance must independently reconcile true order/invoice baskets, returns, cancellations and future temporal holdout."},
      {"id":"AI-04","target":"COMPANY_DEMAND_FORECAST",
       "candidate_order_lines":rows,"forecast_ready_sku_count":sales.get("forecast_ready_sku_count",0),
       "forecast_ready_skus":sales.get("forecast_ready_skus",[]),
       "ready_for_scientific_validation":False,
       "reason":"Requires at least 24 contiguous complete Finance-reconciled KG weeks per SKU, rolling-origin evaluation and comparison with baselines."},
      {"id":"AGENT","target":"ROLE_AWARE_TOOL_ORCHESTRATION",
       "recorded_tool_traces":agent_traces,"ready_for_release":False,
       "reason":"Must pass held-out tool-selection, grounding, role policy, failure recovery and zero unauthorized-action tests."},
      {"id":"WMS","target":"OPERATIONAL_STOCK_LEDGER",
       "operational_feature_flag_enabled":wms_enabled,
       "ready_for_physical_stock_mutation":False,
       "reason":"Requires current approved physical count, verified UoM, lot/expiry rules, warehouse UAT, reconciliation and explicit owner go-live approval."}
    ]
    return {
      "status":"COMPANY_MODELS_NOT_VALIDATED",
      "company_catalog_products":int(product["n"] or 0),
      "supplier_catalog_unverified":int(product["unverified"] or 0),
      "company_order_records":orders,"company_order_lines":rows,
      "finance_reconciliation_references":finance_refs,
      "pilot_nonuat_relevance_labels":labelled,
      "private_neural_artifacts_available":neural_artifacts_available,
      "operational_wms_feature_enabled":wms_enabled,
      "agent_tool_trace_count":agent_traces,
      "independent_review_proven":False,
      "all_models_trained_or_validated_on_company_data":False,
      "auto_retraining_enabled":False,
      "production_ready":False,
      "gates":gates,
      "next_steps":["Supplier/Technical: complete current SKU mapping and link current TDS/COA/SDS evidence",
        "Sales: provide authorized de-identified free-text inquiry corpus",
        "Technical: complete independent AI-02 labels and adjudication",
        "Finance: reconcile invoice/order facts, returns, original UoM and KG conversions",
        "Finance: supply 24+ contiguous complete weekly demand series per SKU",
        "Warehouse: perform current physical stock count and verify package UoM/lot rules",
        "Research: freeze train/validation/test sets and execute reproducible held-out metrics",
        "Owner: approve production compute, security, UAT and go-live only after evidence review"],
      "no_external_customer_data_exposed":True
    }

def mount_company_governance(app,current,get_db):
    @app.get("/v1/research/company-data-gates")
    def get_company_gates(u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","technical","manager"):
            raise HTTPException(403,"Role access denied")
        return company_gates(db)

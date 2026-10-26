"""Explicit company model/dataset gates. Read-only: no fake training metrics."""
from fastapi import Depends,HTTPException

def company_gates(db):
    product=db.execute("""SELECT COUNT(*) AS n,
               SUM(CASE WHEN source_ref='CATALOG-PDF-UNVERIFIED' THEN 1 ELSE 0 END) AS unverified,
               SUM(CASE WHEN stock IS NULL THEN 1 ELSE 0 END) AS missing_stock
               FROM products""").fetchone()
    orders=db.execute("SELECT COUNT(*) AS n FROM ai_sales_orders").fetchone()["n"]
    rows=db.execute("SELECT COUNT(*) AS n FROM ai_sales_lines").fetchone()["n"]
    labelled=db.execute("""SELECT COUNT(*) AS n
         FROM reviews r JOIN users u ON u.id=r.reviewer_id
         JOIN runs q ON q.id=r.run_id JOIN inquiries i ON i.id=q.inquiry_id
         WHERE LOWER(u.email) NOT LIKE 'uat-%%@liliang.local'
           AND UPPER(COALESCE(i.customer_ref,'')) NOT LIKE 'UAT-%%'
           AND r.label BETWEEN 0 AND 3""").fetchone()["n"]
    # A non-UAT label is only a candidate. Independent annotation,
    # consent, adjudication, split and evaluator audit still mandatory.
    gates=[
      {"id":"AI-01","target":"CUSTOMER_INTENT_MODEL",
       "candidate_label_records":0,"ready_for_company_training":False,
       "reason":"Need authorized anonymized inquiry + independently verified intent labels; current parser is rule-based"},
      {"id":"AI-02","target":"DOMAIN_FINETUNED_MINILM",
       "candidate_label_records":labelled,"ready_for_company_training":False,
       "reason":"Non-UAT reviews do not prove independent double-labelled gold data, frozen train/dev/test or consent"},
      {"id":"AI-03","target":"ORDER_ASSOCIATION_RULES",
       "candidate_order_count":orders,"ready_for_company_training":False,
       "reason":"Only Finance-reconciled order/invoice baskets with true order IDs, cancellations and SKU master can support validated results"},
      {"id":"AI-04","target":"COMPANY_SPECIFIC_FORECAST",
       "candidate_line_count":rows,"ready_for_company_training":False,
       "reason":"Need >=24 contiguous complete calendar weeks per SKU, KG, reconciliation and independent Finance validation"},
      {"id":"WMS","target":"PHYSICAL_STOCK_VERIFICATION",
       "sku_stock_unknown":int(product["missing_stock"] or 0),"ready_for_stock_based_planning":False,
       "reason":"Stock count, movements, batch/lot and stockout-adjusted demand remain independent warehouse gates"}
    ]
    return {
      "status":"COMPANY_MODELS_NOT_VALIDATED",
      "company_catalog_products":int(product["n"] or 0),
      "supplier_catalog_unverified":int(product["unverified"] or 0),
      "company_order_records":orders,
      "company_order_lines":rows,
      "pilot_nonuat_relevance_labels":labelled,
      "independent_review_proven":False,
      "all_models_trained_on_validated_company_data":False,
      "auto_retraining_enabled":False,
      "all_stock_required_before_retrieval_training":False,
      "warehouse_stock_gate":"PENDING_INDEPENDENT_VERIFICATION",
      "gates":gates,
      "next_steps":["Finance: validate SO/invoice, dates, returns, KG unit and June 2025",
                    "Technical: independent 0-3 judgements and matching datasheets",
                    "Research: freeze group/time held-out test and model comparison",
                    "Warehouse: stock opname and movement audit for availability/replenishment"],
      "no_external_customer_data_exposed":True
    }

def mount_company_governance(app,current,get_db):
    @app.get("/v1/research/company-data-gates")
    def get_company_gates(u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","technical","manager"):
            raise HTTPException(403,"Role access denied")
        return company_gates(db)

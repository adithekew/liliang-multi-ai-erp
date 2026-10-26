"""Read-only preflight for a defensible, repeatable five-role ERP demo."""
from fastapi import Depends, HTTPException

def check_readiness(db):
    from multi_ai import interpret,bundling_rules,forecast_baseline
    from research.catalog_matcher import score_products
    from sales_intelligence import readiness
    from research.hybrid_demo import load_fixture
    catalog=[dict(x) for x in db.execute("SELECT * FROM products").fetchall()]
    parser=interpret("Butuh stroberi bubuk untuk bakery")
    ai01=(parser.get("flavor")=="strawberry" and parser.get("form")=="powder" and
          parser.get("application")=="bakery")
    # A smoke-test of selected corpus candidates; no claim about scientific precision.
    a=score_products("strawberry flavor for bakery",catalog)
    catalog_loaded=len(catalog)>0
    ai02=bool(a)
    bundling=bundling_rules()
    simulated=forecast_baseline("FLV-STRAW-01",4)
    data=readiness(db)
    fixture=load_fixture()
    module=[
      {"id":"AI-01","status":"DEMO_READY" if ai01 else "ATTENTION",
       "mode":"ONLINE_RULE_BASED","note":"Bilingual parser smoke verified; not trained NLP"},
      {"id":"AI-02","status":"DEMO_READY" if ai02 else "ATTENTION",
       "mode":"ONLINE_BM25","note":"Nonempty Top-5 smoke on current catalog; NOT a precision/recall score"},
      {"id":"AI-02-NEURAL","status":"FIXED_LAB_READY" if fixture else "ATTENTION",
       "mode":"OFFLINE_SYNTHETIC_FIXED_QUERIES","note":"NOT online arbitrary-input neural retrieval"},
      {"id":"AI-03","status":"SYNTHETIC_DEMO_READY" if bundling else "ATTENTION",
       "mode":"SYNTHETIC_BASKETS","note":"Synthetic association-rule demonstration; company facts separate"},
      {"id":"AI-04","status":"SYNTHETIC_DEMO_READY" if len(simulated["forecast"])==4 else "ATTENTION",
       "mode":"SYNTHETIC_WEEKLY_SERIES","note":"Synthetic forecasting demonstration, not real stock replenishment"}
    ]
    return {
      "demo_preflight_pass":all(x["status"]!="ATTENTION" for x in module),
      "company_ai_scientifically_validated":False,
      "models_fine_tuned_to_company":False,
      "catalog_sku_count":len(catalog),
      "candidate_smoke_count":len(a),
      "modules":module,
      "company_fact_readiness":data,
      "role_workflow_gate":"Run separate five-role UAT; preflight does not test real browser interactions",
      "dataset_gate":"Expert annotations and approved transaction data must be validated separately",
      "operational_warning":"No guaranteed error-free demo; test each role and the live Render revision",
    }

def mount_demo_readiness(app,current,get_db):
    @app.get("/v1/ai/demo-readiness")
    def preview(u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","manager","technical"):
            raise HTTPException(403,"Role access denied")
        return check_readiness(db)

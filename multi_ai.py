"""Research pilot AI demonstrations. All commercial data below is SYNTHETIC.

No runtime LLM, online free-text neural encoder, validated datasheet evidence,
or real company sales history is connected. Real pretrained multilingual
neural embeddings exist for the ten fixed synthetic research queries.
"""
from collections import Counter
from datetime import date, timedelta
from math import log, sin
import re
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

ALIASES = {
    "stroberi":"strawberry","strawberi":"strawberry","stoberi":"strawberry",
    "vanila":"vanilla","vanili":"vanilla","coklat":"chocolate",
    "mangga":"mango","jeruk":"lemon","lemon":"lemon",
    "susu":"dairy","milk":"dairy","yogurt":"dairy",
    "minuman":"beverage","drink":"beverage","drinks":"beverage",
    "roti":"bakery","kue":"bakery","cake":"bakery",
    "es":"cold","segar":"fresh","manis":"sweet"
}
FLAVORS={"strawberry","vanilla","mango","chocolate","lemon"}
APPLICATIONS={"dairy","beverage","bakery"}
MODEL_VERSION="bm25-catalog-constraint-v0.3"

def tokens(text):
    from research.catalog_matcher import normalized_tokens
    return normalized_tokens(text)

def interpret(text):
    from research.catalog_matcher import query_intent
    intent=query_intent(text)
    f=intent["flavors"][0] if intent["flavors"] else None
    a=intent["applications"][0] if intent["applications"] else None
    form=intent["forms"][0] if intent["forms"] else None
    return {
        "flavor":f,
        "application":a,
        "form":form,
        "identified_flavors":intent["flavors"],
        "identified_applications":intent["applications"],
        "attributes":{
            "flavor":{"value":f,"status":"EXTRACTED_UNVERIFIED" if f else "UNKNOWN"},
            "application":{"value":a,"status":"EXTRACTED_UNVERIFIED" if a else "UNKNOWN"},
            "product_form":{"value":form,"status":"EXTRACTED_UNVERIFIED" if form else "UNKNOWN"},
            "regulatory":{"value":None,"status":"UNKNOWN"},
            "halal_status":{"value":None,"status":"UNKNOWN"}
        },
        "raw_text":text,
        "method":"Rule-based bilingual entity normalizer with typo correction; not trained ML",
        "evidence_status":"No independently verified datasheet evidence or expert labels",
        "data_classification":"USER_PROVIDED_UNVERIFIED"
    }

def score_products(query,products):
    from research.catalog_matcher import score_products as rank_catalog
    return rank_catalog(query,products)

# Synthetic historical order baskets. No company sales or customer data.
BASKETS=[
    ["FLV-STRAW-01","FLV-VANI-02"],["FLV-STRAW-01","FLV-VANI-02"],
    ["FLV-MANG-03","FLV-LEMON-05"],["FLV-CHOCO-04","FLV-VANI-02"],
    ["FLV-STRAW-01","FLV-VANI-02","FLV-CHOCO-04"],["FLV-MANG-03","FLV-LEMON-05"],
    ["FLV-CHOCO-04","FLV-VANI-02"],["FLV-STRAW-01","FLV-VANI-02"],
    ["FLV-MANG-03","FLV-LEMON-05"],["FLV-STRAW-01","FLV-CHOCO-04"],
    ["FLV-CHOCO-04","FLV-VANI-02"],["FLV-MANG-03","FLV-LEMON-05"],
    ["FLV-STRAW-01","FLV-VANI-02"],["FLV-MANG-03","FLV-LEMON-05"],
    ["FLV-CHOCO-04","FLV-VANI-02"],["FLV-STRAW-01","FLV-VANI-02"]
]
def bundling_rules():
    counts=Counter(sku for basket in BASKETS for sku in set(basket))
    pairs=Counter((a,b) for basket in BASKETS for a in set(basket) for b in set(basket) if a!=b)
    total=len(BASKETS)
    result=[]
    for (a,b),pair_count in pairs.items():
        support=pair_count/total
        confidence=pair_count/counts[a]
        lift=confidence/(counts[b]/total)
        if support>=.12 and confidence>=.35:
            result.append({"antecedent_sku":a,"recommended_sku":b,
                "co_occurrences":pair_count,"support":round(support,3),
                "confidence":round(confidence,3),"lift":round(lift,3)})
    return sorted(result,key=lambda x:(-x["lift"],-x["confidence"],x["antecedent_sku"]))[:10]

def synthetic_series(sku, weeks=24):
    codes=["FLV-STRAW-01","FLV-VANI-02","FLV-MANG-03","FLV-CHOCO-04","FLV-LEMON-05"]
    index=codes.index(sku)
    start=date(2026,3,23)
    return [{"week":(start+timedelta(weeks=i)).isoformat(),
       "units":round(45+index*9+.65*i+8*sin((i+index)*.7)+(i%4-1.5)*2)}
             for i in range(weeks)]

def forecast_baseline(sku,horizon=4):
    values=synthetic_series(sku)
    actual=[row["units"] for row in values]
    # Point-in-time backtest: each prediction sees only earlier observations.
    backtest=[]
    for i in range(8,len(actual)):
        pred=sum(actual[i-4:i])/4
        backtest.append((actual[i],pred))
    mae=sum(abs(a-p) for a,p in backtest)/len(backtest)
    wmape=sum(abs(a-p) for a,p in backtest)/max(1,sum(abs(a) for a,p in backtest))*100
    base=round(sum(actual[-4:])/4)
    next_day=date.fromisoformat(values[-1]["week"])+timedelta(weeks=1)
    return {"sku":sku,"method":"4-week moving-average baseline",
       "history":values,"forecast":[{"week":(next_day+timedelta(weeks=i)).isoformat(),
       "predicted_units":base} for i in range(horizon)],
       "metrics":{"rolling_mae_units":round(mae,2),"rolling_wmape_pct":round(wmape,2)},
       "units":"synthetic units / SKU-week","disclaimer":"Simulation only: no company transactions, inventory, stockout, or seasonal ground truth.",
       "data_classification":"SYNTHETIC_PILOT"}

CAPABILITIES=[
  {"id":"AI-01","title":"Requirement Interpreter","method":"Rule-based bilingual NLP","status":"BASELINE_DEMO","dataset":"Demo text","research_role":"Primary pipeline input"},
  {"id":"AI-02","title":"Product Matching","method":"BM25 lexical ranking + expert validation","status":"BASELINE_DEMO","dataset":"5 synthetic flavor SKUs","research_role":"Primary research target; fixed-query neural demonstration available; online neural inference and expert evaluation pending"},
  {"id":"AI-03","title":"Product Bundling","method":"Association rules: support, confidence, lift","status":"SYNTHETIC_DEMO","dataset":"16 synthetic order baskets","research_role":"Secondary evaluation"},
  {"id":"AI-04","title":"Demand Forecasting","method":"Rolling-origin 4-week moving average","status":"SYNTHETIC_DEMO","dataset":"24 synthetic SKU-weeks per flavor","research_role":"Secondary evaluation"}
]

class RequirementRequest(BaseModel):
    text:str=Field(min_length=5,max_length=3000)
def mount_ai(app,current,get_db):
    @app.get("/v1/ai/capabilities")
    def get_capabilities(u=Depends(current),db=Depends(get_db)):
        from research.hybrid_demo import load_fixture
        modules=[dict(x) for x in CAPABILITIES]
        company_count=db.execute("SELECT COUNT(*) AS n FROM products WHERE source_ref='CATALOG-PDF-UNVERIFIED'").fetchone()["n"]
        if company_count:
            modules[1]["dataset"]=str(company_count)+" supplier-catalog SKUs (pending Technical validation)"
            modules[1]["status"]="BM25_ONLINE_COMPANY_CATALOG_UNVERIFIED"
        if load_fixture():
            modules[1]["method"]="Online BM25 lexical ranking; separate MiniLM 384d + RRF fixed synthetic benchmark"
            modules[1]["research_role"]="Primary research target; online neural inference and company expert labels pending"
        return {"modules":modules,"all_models_validated":False,
                "data_scope":"COMPANY_CATALOG_UNVERIFIED_WITH_SYNTHETIC_AI03_AI04" if company_count else "SYNTHETIC_PILOT",
                "scientific_note":"Supplier catalog is not verified suitability evidence. Neural lab uses synthetic fixtures; no company relevance/accuracy claims."}

    @app.get("/v1/ai/system-status")
    def system_status(u=Depends(current),db=Depends(get_db)):
        """Live truthful capability inventory: neither accuracy nor production certification."""
        from persistence import engine_name
        from research.hybrid_demo import public_cases
        fixture=public_cases()
        counts=db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
        inquiry_count=db.execute("SELECT COUNT(*) AS n FROM inquiries").fetchone()["n"]
        reviews=db.execute("""SELECT COUNT(*) AS n FROM reviews v JOIN users reviewer ON reviewer.id=v.reviewer_id
            JOIN runs r ON r.id=v.run_id JOIN inquiries i ON i.id=r.inquiry_id
            JOIN users creator ON creator.id=i.created_by
            WHERE LOWER(reviewer.email) NOT LIKE 'uat-%%@liliang.local'
              AND LOWER(creator.email) NOT LIKE 'uat-%%@liliang.local'
              AND UPPER(COALESCE(i.customer_ref,'')) NOT LIKE 'UAT-%%'""").fetchone()["n"]
        uat_reviews=db.execute("""SELECT COUNT(*) AS n FROM reviews v JOIN users u ON u.id=v.reviewer_id
            WHERE LOWER(u.email) LIKE 'uat-%%@liliang.local'""").fetchone()["n"]
        company_products=db.execute("SELECT COUNT(*) AS n FROM products WHERE source_ref='CATALOG-PDF-UNVERIFIED'").fetchone()["n"]
        backend=engine_name()
        return {
            "environment":"RESEARCH_PILOT",
            "database_backend":backend,
            "persistent_database":backend=="postgresql",
            "product_count":counts,
            "inquiry_count":inquiry_count,
            "expert_review_count":reviews,
            "uat_review_count_excluded_from_research":uat_reviews,
            "model_validated_for_company":False,
            "company_fine_tuning_completed":False,
            "production_ready":False,
            "data_source":"COMPANY_CATALOG_UNVERIFIED" if company_products else "SYNTHETIC_DEMO",
            "company_catalog_products":company_products,
            "components":[
                {"id":"AI-01","method":"Bilingual normalization and deterministic requirement extraction","mode":"ONLINE_RULE_BASED","data":"User-entered inquiry","trained_ml_model":False},
                {"id":"AI-02","method":"Flavor-gated multilingual BM25 Top-5 with typo normalization, form and application evidence","mode":"ONLINE_CONSTRAINT_AWARE_BM25","data":"Catalog PDF (unverified)" if company_products else "Synthetic pilot products","trained_ml_model":False},
                {"id":"AI-02-NEURAL","method":fixture.get("model_id") if fixture.get("available") else "Neural fixture unavailable","mode":"OFFLINE_PRECOMPUTED_FIXED_SYNTHETIC_CASES" if fixture.get("available") else "NEURAL_ASSET_UNAVAILABLE",
                 "data":str(len(fixture.get("cases",[])))+" developer-authored example inquiries",
                 "trained_ml_model":bool(fixture.get("available")),
                 "embedding_dimensions":fixture.get("dimensions") if fixture.get("available") else None},
                {"id":"AI-03","method":"Association rules (support, confidence, lift)","mode":"ONLINE_STATISTICAL_SYNTHETIC_DEMO","data":"16 synthetic order baskets","trained_ml_model":False},
                {"id":"AI-04","method":"4-week moving average and rolling backtest","mode":"ONLINE_FORECAST_BASELINE_SYNTHETIC_DEMO","data":"24 synthetic SKU-week points per item","trained_ml_model":False}
            ],
            "limitations":[
                "No online neural encoder for arbitrary free-text inquiries; current production matcher is rule-constrained lexical retrieval.",
                "Pretrained neural vectors exist only for the versioned fixed synthetic benchmark.",
                "No company-trained or expert-validated models; relevance scores are not accuracy percentages.",
                "No verified halal, regulatory, datasheet, or real sales history source.",
                "No LLM or autonomous business decisions."
            ]
        }

    @app.get("/v1/ai/hybrid-cases")
    def hybrid_cases(u=Depends(current)):
        if u["role"] not in ("admin","sales","technical","manager"):
            raise HTTPException(403,"Role access denied")
        from research.hybrid_demo import public_cases
        return public_cases()

    @app.get("/v1/ai/hybrid-evaluate")
    def hybrid_evaluate(case_id:str=Query(default="Q01",min_length=3,max_length=6),u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","sales","technical","manager"):
            raise HTTPException(403,"Role access denied")
        from research.hybrid_demo import evaluate_case
        try:
            # Never apply cached synthetic product embeddings to a distinct company catalog.
            # Evaluate a separate, fixed synthetic benchmark even after PDF import.
            from app import DEMO
            fixture_rows=[{"id":i,"sku":sku,"name":name,"description":desc,
                           "profile":profile,"application":application,"stock":0,
                           "source_ref":"FIXED_SYNTHETIC_NEURAL_BENCHMARK"}
                          for i,(sku,name,desc,profile,application) in enumerate(DEMO,1)]
            result=evaluate_case(case_id,fixture_rows)
            result["catalog_isolation"]="SYNTHETIC_BENCHMARK_ONLY_NOT_COMPANY_CATALOG"
            return result
        except KeyError:
            raise HTTPException(404,"Synthetic benchmark case not found")
        except FileNotFoundError:
            raise HTTPException(503,"Neural benchmark assets are not ready")
        except ValueError as exc:
            raise HTTPException(409,str(exc))

    @app.post("/v1/ai/requirements")
    def requirement(data:RequirementRequest,u=Depends(current)):
        if u["role"] not in ("admin","sales","technical","manager"):
            raise HTTPException(403,"Role access denied")
        return interpret(data.text)

    @app.post("/v1/ai/match-preview")
    def preview(data:RequirementRequest,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","sales","technical","manager"):
            raise HTTPException(403,"Role access denied")
        rows=db.execute("SELECT * FROM products ORDER BY sku").fetchall()
        return {"method":MODEL_VERSION,"mode":"lexical-only",
            "parsed_requirement":interpret(data.text),
            "candidates":score_products(data.text,rows),
            "next_step":"Persist inquiry then Technical expert review (0-3).",
            "validated_relevance":False,"dataset":"SYNTHETIC_PILOT"}

    @app.get("/v1/ai/bundling")
    def bundling(u=Depends(current)):
        if u["role"] not in ("admin","sales","manager"):
            raise HTTPException(403,"Role access denied")
        return {"method":"frequent item-pair association rules",
            "basket_count":len(BASKETS),"rules":bundling_rules(),
            "notes":"Derived exclusively from synthetic orders. Human review required.",
            "data_classification":"SYNTHETIC_PILOT","auto_sell":False}

    @app.get("/v1/ai/forecast")
    def forecast(sku:str=Query(default="FLV-STRAW-01"),horizon:int=Query(default=4,ge=1,le=8),u=Depends(current)):
        if u["role"] not in ("admin","sales","manager","gudang"):
            raise HTTPException(403,"Role access denied")
        if sku not in ("FLV-STRAW-01","FLV-VANI-02","FLV-MANG-03","FLV-CHOCO-04","FLV-LEMON-05"):
            raise HTTPException(404,"SKU not in synthetic forecast set")
        return forecast_baseline(sku,horizon)

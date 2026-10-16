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
MODEL_VERSION="bm25-expert-review-demo-v0.2"

def tokens(text):
    return [ALIASES.get(t,t) for t in re.findall(r"[a-z0-9]+",str(text).lower())]

def interpret(text):
    ts=tokens(text)
    found_flavor=sorted(set(ts)&FLAVORS)
    found_app=sorted(set(ts)&APPLICATIONS)
    return {
        "flavor":found_flavor[0] if found_flavor else None,
        "application":found_app[0] if found_app else None,
        "attributes":{"flavor":{"value":found_flavor[0] if found_flavor else None,
                                 "status":"EXTRACTED_UNVERIFIED" if found_flavor else "UNKNOWN"},
                      "application":{"value":found_app[0] if found_app else None,
                                     "status":"EXTRACTED_UNVERIFIED" if found_app else "UNKNOWN"},
                      "regulatory":{"value":None,"status":"UNKNOWN"},
                      "halal_status":{"value":None,"status":"UNKNOWN"}},
        "raw_text":text,
        "method":"rule-based bilingual NLP baseline",
        "evidence_status":"No verified product datasheets or expert labels attached",
        "data_classification":"SYNTHETIC_PILOT"
    }

def score_products(query, products):
    """BM25 lexical retrieval. NOT hybrid semantic neural retrieval."""
    q=tokens(query)
    docs=[]
    for item in products:
        p=dict(item)
        docs.append((p,tokens(" ".join(str(p.get(k,"")) for k in ("sku","name","description","profile","application")))))
    n=len(docs)
    if not n: return []
    frequencies=Counter(token for _,doc in docs for token in set(doc))
    avgdl=sum(len(doc) for _,doc in docs)/n or 1
    qtokens=Counter(q)
    parsed=interpret(query)
    candidates=[]
    for p,doc in docs:
        freq=Counter(doc)
        raw=0.0
        for word,query_count in qtokens.items():
            f=freq[word]
            if f<=0: continue
            idf=log(1+(n-frequencies[word]+.5)/(frequencies[word]+.5))
            raw+=idf * f*2.2/(f+1.2*(.25+.75*len(doc)/avgdl)) * min(query_count,2)
        if parsed["flavor"] and parsed["flavor"]==p.get("profile"):
            raw+=1.0
        if parsed["application"] and parsed["application"]==p.get("application"):
            raw+=.4
        candidates.append({
            "product_id":p["id"],"sku":p["sku"],"name":p["name"],
            "score":round(raw,4),"source_ref":p.get("source_ref","DEMO-ONLY"),
            "unknown_attributes":["regulatory","halal_status"],
            "evidence_verified":False,"profile":p.get("profile"),
            "application":p.get("application"),
            "explanation":{
                "matched_terms":sorted(set(q)&set(doc))[:12],
                "flavor_tag_match":bool(parsed["flavor"] and parsed["flavor"]==p.get("profile")),
                "application_tag_match":bool(parsed["application"] and parsed["application"]==p.get("application")),
                "limitations":"Lexical/domain-tag evidence only; no verified datasheet or suitability assessment."
            }
        })
    candidates.sort(key=lambda x:(-x["score"],x["sku"]))
    for rank,c in enumerate(candidates[:5],1):c["rank"]=rank
    return candidates[:5]

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
    def get_capabilities(u=Depends(current)):
        from research.hybrid_demo import load_fixture
        modules=[dict(x) for x in CAPABILITIES]
        if load_fixture():
            modules[1]["method"]="BM25 + real multilingual dense embeddings + RRF (fixed-query demo)"
            modules[1]["status"]="NEURAL_FIXED_QUERY_DEMO"
            modules[1]["research_role"]="Primary research target; online inference and expert validation pending"
        return {"modules":modules,"all_models_validated":False,
                "data_scope":"SYNTHETIC_PILOT",
                "scientific_note":"Results are demonstrations, not measured findings for PT Liliang."}

    @app.get("/v1/ai/system-status")
    def system_status(u=Depends(current),db=Depends(get_db)):
        """Live truthful capability inventory: neither accuracy nor production certification."""
        from persistence import engine_name
        from research.hybrid_demo import public_cases
        fixture=public_cases()
        counts=db.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
        inquiry_count=db.execute("SELECT COUNT(*) AS n FROM inquiries").fetchone()["n"]
        reviews=db.execute("SELECT COUNT(*) AS n FROM reviews").fetchone()["n"]
        backend=engine_name()
        return {
            "environment":"RESEARCH_PILOT",
            "database_backend":backend,
            "persistent_database":backend=="postgresql",
            "product_count":counts,
            "inquiry_count":inquiry_count,
            "expert_review_count":reviews,
            "model_validated_for_company":False,
            "company_fine_tuning_completed":False,
            "production_ready":False,
            "data_source":"SYNTHETIC_DEMO",
            "components":[
                {"id":"AI-01","method":"Bilingual normalization and deterministic requirement extraction","mode":"ONLINE_RULE_BASED","data":"User-entered inquiry","trained_ml_model":False},
                {"id":"AI-02","method":"BM25 lexical Top-5 with evidence explanations","mode":"ONLINE_BM25_ONLY","data":"Current pilot product catalog","trained_ml_model":False},
                {"id":"AI-02-NEURAL","method":fixture.get("model_id") if fixture.get("available") else "Neural fixture unavailable","mode":"OFFLINE_PRECOMPUTED_FIXED_SYNTHETIC_CASES" if fixture.get("available") else "NEURAL_ASSET_UNAVAILABLE",
                 "data":str(len(fixture.get("cases",[])))+" developer-authored example inquiries",
                 "trained_ml_model":bool(fixture.get("available")),
                 "embedding_dimensions":fixture.get("dimensions") if fixture.get("available") else None},
                {"id":"AI-03","method":"Association rules (support, confidence, lift)","mode":"ONLINE_STATISTICAL_SYNTHETIC_DEMO","data":"16 synthetic order baskets","trained_ml_model":False},
                {"id":"AI-04","method":"4-week moving average and rolling backtest","mode":"ONLINE_FORECAST_BASELINE_SYNTHETIC_DEMO","data":"24 synthetic SKU-week points per item","trained_ml_model":False}
            ],
            "limitations":[
                "No online neural encoder for arbitrary free-text inquiries.",
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
            return evaluate_case(case_id,db.execute("SELECT * FROM products ORDER BY sku").fetchall())
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

"""Research evaluation reporting from persisted Technical expert relevance labels.

Strict boundaries:
- The operational model currently writes BM25 runs; these are not paired hybrid trials.
- A fully labelled run is not automatically a held-out test or a publication result.
- "ACCEPT"/"REJECT" approval is NOT an objective ground-truth relevance judgment.
- No inquiry texts, customer IDs, passwords, or raw reviewer notes leave these endpoints.
"""
from collections import Counter, defaultdict

from research.metrics import ndcg_at_k, reciprocal_rank

RUBRIC = {
    "0": "Not relevant: wrong flavor/application or incompatible requirement.",
    "1": "Weak: partial relation, expert would not recommend without changes.",
    "2": "Relevant with caveats: plausible candidate, needs qualification.",
    "3": "Highly relevant: directly meets documented requirement (subject to verified evidence)."
}
METHODS = [
    {"name": "BM25", "trained_on_company_data": False, "mechanism": "Lexical ranking with token frequencies, IDF and bilingual normalization", "deployment": "FREE_TEXT_WORKFLOW"},
    {"name": "Multilingual MiniLM SentenceTransformer", "trained_on_company_data": False, "mechanism": "Pretrained 384-d embedding model; cosine dense retrieval", "deployment": "OFFLINE_FIXED_QUERY_SYNTHETIC_DEMO"},
    {"name": "Hybrid RRF(k=60)", "trained_on_company_data": False, "mechanism": "Deterministic rank-level fusion; does not itself learn weights", "deployment": "OFFLINE_FIXED_QUERY_SYNTHETIC_DEMO"},
    {"name": "Domain fine-tuned bi-encoder", "trained_on_company_data": False, "mechanism": "Proposed supervised contrastive learning after consent and expert-labelled pairs", "deployment": "NOT_TRAINED"}
]

def read_labels(db):
    # Exclude synthetic-UAT identities and UAT-prefixed inquiries from
    # research denominators. Their operational events remain in Audit Transactions.
    rows = db.execute("""SELECT r.id AS run_id,r.method,c.rank,c.product_id,p.sku
                        FROM runs r JOIN inquiries i ON i.id=r.inquiry_id
                        JOIN users creator ON creator.id=i.created_by
                        JOIN candidates c ON c.run_id=r.id
                        JOIN products p ON p.id=c.product_id
                        WHERE LOWER(creator.email) NOT LIKE 'uat-%%@liliang.local'
                        AND UPPER(COALESCE(i.customer_ref,'')) NOT LIKE 'UAT-%%'
                        ORDER BY r.id,c.rank""").fetchall()
    reviews=db.execute("""SELECT v.id,v.run_id,v.product_id,v.reviewer_id,v.label,v.decision
                          FROM reviews v JOIN users reviewer ON reviewer.id=v.reviewer_id
                          WHERE LOWER(reviewer.email) NOT LIKE 'uat-%%@liliang.local'
                          ORDER BY v.id""").fetchall()
    runs=defaultdict(list)
    for row in rows:
        a=dict(row);runs[a["run_id"]].append(a)
    latest={}
    reviewer_pairs=defaultdict(set)
    for v in reviews:
        r=dict(v);key=(r["run_id"],r["product_id"])
        latest[key]=r
        reviewer_pairs[key].add(r["reviewer_id"])
    ready=[];partial=[];total_candidates=0;judged_candidates=0;conflict_count=0
    for rid,cands in sorted(runs.items()):
        judgments={}
        conflicts=[]
        for c in cands:
            total_candidates+=1
            v=latest.get((rid,c["product_id"]))
            if v is None:continue
            judged_candidates+=1
            label=v["label"];decision=v["decision"]
            if label is None or type(label) is not int or label not in (0,1,2,3):
                conflicts.append("INVALID_LABEL")
                continue
            if decision=="NEEDS_INFO" or (decision=="ACCEPT" and label==0) or (decision=="REJECT" and label==3):
                conflicts.append("DECISION_LABEL_INCONSISTENT")
                continue
            judgments[c["sku"]]=label
        if conflicts:conflict_count+=1
        if cands and len(judgments)==len(cands) and not conflicts:
            ranked=[c["sku"] for c in cands]
            ready.append({"run_id":rid,"method":cands[0]["method"],"ranked":ranked,
                          "judgments":judgments,
                          "has_multiple_experts":any(len(reviewer_pairs[(rid,c["product_id"])])>=2 for c in cands)})
        else:
            partial.append({"run_id":rid,"judged":len(judgments),"candidate_count":len(cands),
                            "issues":list(sorted(set(conflicts))) or ["MISSING_RELEVANCE_LABELS"]})
    return {"runs":runs,"ready":ready,"partial":partial,
            "candidate_count":total_candidates,"reviewed_candidates":judged_candidates,
            "conflicted_runs":conflict_count,
            "reviewed_by_multiple_experts":sum(1 for r in ready if r["has_multiple_experts"])}

def readiness(db):
    d=read_labels(db)
    count=len(d["runs"])
    return {
        "status":"EVALUATION_READY_FOR_EXPLORATION" if d["ready"] else "INSUFFICIENT_EXPERT_LABELS",
        "pilot_data_only":True,
        "uat_records_excluded_from_research":True,
        "evaluation_runs_total":count,
        "fully_labelled_runs":len(d["ready"]),
        "incomplete_runs":len(d["partial"]),
        "candidate_pairs_total":d["candidate_count"],
        "candidate_pairs_with_a_review":d["reviewed_candidates"],
        "candidate_label_coverage_pct":round(100*d["reviewed_candidates"]/d["candidate_count"],2) if d["candidate_count"] else 0,
        "decision_label_conflicts":d["conflicted_runs"],
        "multi_expert_runs":d["reviewed_by_multiple_experts"],
        "expert_rubric":RUBRIC,
        "gates":{
            "all_evaluation_candidates_judged":len(d["partial"])==0 and count>0,
            "independent_expert_review_proven":False,
            "heldout_split_verified":False,
            "label_adjudication_completed":False,
            "representative_company_dataset_available":False,
            "paired_bm25_dense_hybrid_same_queries":False
        },
        "scientific_readiness":"NOT_VALIDATED",
        "uat_records_excluded_from_research":True,
        "data_provenance":"Pilot records; not an authorized representative test corpus",
        "next_action":"Technical should score each candidate 0-3, then independently adjudicate and lock a held-out test set before comparative evaluation."
    }

def evaluation(db):
    d=read_labels(db)
    by_method=defaultdict(list)
    for case in d["ready"]:
        labels=case["judgments"]; ranked=case["ranked"]
        by_method[case["method"]].append({
            "run_id":case["run_id"],"ndcg_at_5":ndcg_at_k(ranked,labels,5),
            "reciprocal_rank_at_5":reciprocal_rank(ranked,labels,5)
        })
    out=[]
    for method,items in sorted(by_method.items()):
        n=len(items)
        out.append({"method":method,"fully_judged_runs":n,
                    "exploratory_mean_ndcg_at_5":round(sum(x["ndcg_at_5"] for x in items)/n,4),
                    "exploratory_mrr_at_5":round(sum(x["reciprocal_rank_at_5"] for x in items)/n,4)})
    return {
        "status":"EXPLORATORY_ONLY" if out else "NO_COMPLETE_EXPERT_JUDGMENTS",
        "model_comparison_valid":False,
        "scientific_readiness":"NOT_VALIDATED",
        "results":out,
        "fully_judged_runs":len(d["ready"]),
        "incomplete_runs":len(d["partial"]),
        "warnings":[
           "Scores are descriptive of manually reviewed pilot runs, NOT held-out effectiveness or generalizable accuracy.",
           "Paired comparison needs matching inquiry IDs with BM25, dense-only and hybrid runs.",
           "The separate neural benchmark has five synthetic SKUs; its Recall@5 is not evidence of accuracy on the imported supplier catalog.",
           "No expert calibration, independence, adjudication, or locked train/dev/test has been established."
        ]
    }

def methodology():
    return {
        "primary_research":"AI-Assisted Semantic Product Matching for B2B Flavor Inquiries",
        "pipeline":["Source and consent","Product/inquiry profiling and cleansing","Anonymization review","Expert relevance labels (0-3)","Group/time leakage-safe split","BM25 baseline","Frozen pretrained dense embeddings","RRF fusion","Evidence-aware reranking and UNKNOWN","Held-out evaluation + human-in-the-loop"],
        "models":METHODS,
        "training_status":"PRETRAINED_EXTERNAL_MODEL_ONLY_NO_LILIANG_FINE_TUNING",
        "training_plan":{
           "data":"Approved inquiry-SKU pairs with 0-3 expert relevance and evidence provenance",
           "fine_tune_algorithm":"Contrastive bi-encoder fine-tuning, e.g. MultipleNegativesRankingLoss, with qualified positive pairs and checked negatives",
           "training_split":"Group by customer/project and use temporal holdout; never include a test inquiry paraphrase in train",
           "baseline":"Frozen multilingual MiniLM and BM25 must be reported before fine-tuning",
           "checkpoint":"Record model sha, corpus snapshot, hyperparameters, seed, loss, epochs, device, and run duration",
           "decision":"Deploy fine-tuned model only after it improves held-out performance without violating constraints"
        },
        "evaluation":{
            "primary":["nDCG@5","MRR@5","Recall@5 when corpus > 5 SKUs"],
            "operations":["P50/P95 end-to-end latency","time-to-shortlist vs manual search","expert agreement","UNKNOWN and constraint violation rates"],
            "statistical":"Paired bootstrap CIs or appropriate paired test across the same test inquiries; do not compare different query pools."
        },
        "publication_claim_status":"NOT_YET_ESTABLISHED",
        "training_honesty":"Pretrained model learning occurred upstream; no model weights have been fine-tuned on PT Liliang data."
    }

def synthetic_quality_report():
    """Auditable 5-SKU/10-inquiry cleaning demonstration (not company data)."""
    from research.hybrid_demo import load_fixture
    from research.data_pipeline import prepare_synthetic, grouped_split
    data=load_fixture()
    if not data:
        return {"status":"NEURAL_SYNTHETIC_FIXTURE_UNAVAILABLE","company_data_used":False}
    catalog=[{**p,"data_classification":"SYNTHETIC_EXAMPLES_ONLY"} for p in data["products"]]
    inquiries=[{"requirement":q["text"],"created_at":f"2026-01-{i+1:02d}",
                "project_group":"demo-"+q["id"],
                "data_classification":"SYNTHETIC_EXAMPLES_ONLY"}
               for i,q in enumerate(data["queries"])]
    result=prepare_synthetic(catalog,inquiries)
    cleaned=result["inquiries"]["clean"]
    split=grouped_split(cleaned) if len(cleaned)>=3 else None
    return {
        "status":"SYNTHETIC_QA_ONLY",
        "product_quality":result["products"]["quality"],
        "inquiry_quality":result["inquiries"]["quality"],
        "split_counts":split["record_counts"] if split else None,
        "split_policy":split["policy"] if split else "INCOMPLETE",
        "company_data_used":False,
        "warning":"Demo quality scores on developer-authored records are NOT evidence of actual company data quality or model accuracy."
    }

def mount_research(app,current,get_db):
    from fastapi import Depends, HTTPException
    def permit_research(u):
        if u["role"] not in ("admin","manager","technical"):
            raise HTTPException(403,"Research evaluation access denied")
    @app.get("/v1/research/training-readiness")
    def research_training_readiness(u=Depends(current),db=Depends(get_db)):
        permit_research(u)
        supplier_count=db.execute("""SELECT COUNT(*) AS n FROM products
               WHERE source_ref='CATALOG-PDF-UNVERIFIED'""").fetchone()["n"]
        imported_batches=db.execute("SELECT COUNT(*) AS n FROM catalog_import_batches").fetchone()["n"]
        # UAT role labels and UAT-prefixed customer refs are not research ground truth.
        labels=db.execute("""SELECT COUNT(*) AS n FROM reviews v
            JOIN runs r ON r.id=v.run_id
            JOIN inquiries i ON i.id=r.inquiry_id
            JOIN users reviewer ON reviewer.id=v.reviewer_id
            JOIN users creator ON creator.id=i.created_by
            WHERE v.label BETWEEN 0 AND 3
              AND substr(lower(reviewer.email),1,4)<>'uat-'
              AND substr(lower(creator.email),1,4)<>'uat-'
              AND substr(upper(COALESCE(i.customer_ref,'')),1,4)<>'UAT-'""").fetchone()["n"]
        qualified_pairs=0  # No independent adjudication / locked holdout is established yet.
        gates=[
            {"stage":"1. Product corpus","ready":bool(supplier_count),
             "requirement":str(supplier_count)+" unverified catalog SKU candidates; no claim of verified product suitability."},
            {"stage":"2. Authorization and provenance","ready":False,
             "requirement":"Written company authorization for research use of customer inquiries, labels, and approved datasheet evidence."},
            {"stage":"3. Inquiry cleansing","ready":False,
             "requirement":"Real approved inquiries, PII quarantine, normalization, dedup, and row-level lineage."},
            {"stage":"4. Expert labels (0–3)","ready":False,
             "requirement":str(labels)+" pilot labels; independent double review and adjudication still unverified. UAT excluded."},
            {"stage":"5. Group/time heldout split","ready":False,
             "requirement":"Lock train/dev/test by customer/project and time, prevent paraphrase and SKU leakage."},
            {"stage":"6. Baseline / fine-tuning","ready":False,
             "requirement":"Compare BM25, frozen MiniLM dense and RRF on the same heldout inquiries before domain fine-tuning."},
            {"stage":"7. Publishable evaluation","ready":False,
             "requirement":"Heldout nDCG@5, MRR@5, Recall@5, latency, expert agreement and provenance audit."}
        ]
        return {
            "status":"DATA_COLLECTION_REQUIRED",
            "catalog_sku_count":supplier_count,
            "catalog_import_batches":imported_batches,
            "qualified_expert_labels":qualified_pairs,
            "observed_non_uat_pilot_labels":labels,
            "locked_heldout_test":False,
            "company_fine_tuned_model_count":0,
            "data_source":"UNVERIFIED_SUPPLIER_CATALOG" if supplier_count else "DEMO_ONLY",
            "training_method":"Proposed multilingual MiniLM contrastive bi-encoder fine-tuning; NOT STARTED",
            "training_runtime":"OFFLINE_PRIVATE_COMPUTE_REQUIRED_NOT_RENDER_FREE",
            "model_weight_updates_performed":False,
            "research_accuracy_available":False,
            "gates":gates,
            "scientific_warning":"Product SKU catalog alone cannot train or validate supervised semantic matching. UAT labels are excluded."
        }

    @app.get("/v1/research/methodology")
    def research_methodology(u=Depends(current)):
        permit_research(u)
        return methodology()
    @app.get("/v1/research/readiness")
    def research_readiness(u=Depends(current),db=Depends(get_db)):
        permit_research(u)
        return readiness(db)
    @app.get("/v1/research/quality-demo")
    def research_quality(u=Depends(current)):
        permit_research(u)
        return synthetic_quality_report()
    @app.get("/v1/research/evaluation")
    def research_evaluation(u=Depends(current),db=Depends(get_db)):
        permit_research(u)
        return evaluation(db)

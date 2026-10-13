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
    rows = db.execute("""SELECT r.id AS run_id,r.method,c.rank,c.product_id,p.sku
                        FROM runs r JOIN candidates c ON c.run_id=r.id
                        JOIN products p ON p.id=c.product_id
                        ORDER BY r.id,c.rank""").fetchall()
    reviews=db.execute("""SELECT id,run_id,product_id,reviewer_id,label,decision
                          FROM reviews ORDER BY id""").fetchall()
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
           "With only five demo SKUs, Recall@5 is trivially saturated and not persuasive.",
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

def mount_research(app,current,get_db):
    from fastapi import Depends, HTTPException
    def permit_research(u):
        if u["role"] not in ("admin","manager","technical"):
            raise HTTPException(403,"Research evaluation access denied")
    @app.get("/v1/research/methodology")
    def research_methodology(u=Depends(current)):
        permit_research(u)
        return methodology()
    @app.get("/v1/research/readiness")
    def research_readiness(u=Depends(current),db=Depends(get_db)):
        permit_research(u)
        return readiness(db)
    @app.get("/v1/research/evaluation")
    def research_evaluation(u=Depends(current),db=Depends(get_db)):
        permit_research(u)
        return evaluation(db)

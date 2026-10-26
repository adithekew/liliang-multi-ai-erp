"""Strict offline ranking evaluation on a LOCKED human-judged candidate pool.

Never infer relevance=0 for unjudged SKUs. Reports graded nDCG@5,
MRR@5/Recall@5 at relevance>=2, and observed retrieval latency when
provided. This is judged-pool evaluation, NOT full 1,452-SKU corpus accuracy.
"""
import argparse,json,math,statistics
from collections import defaultdict
from pathlib import Path

def read_jsonl(path):
    with open(path,encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]

def evaluate(qrels,predictions,k=5):
    if k!=5:raise ValueError("This capstone evaluation uses fixed @5 metrics")
    judged=defaultdict(dict)
    for r in qrels:
        qid=str(r.get("query_id",""))
        sku=str(r.get("sku","")).upper()
        value=r.get("relevance_label")
        if type(value) is not int or value not in (0,1,2,3):
            raise ValueError("Unqualified 0-3 Technical label")
        if not qid or not sku or sku in judged[qid]:
            raise ValueError("Missing or duplicate query/SKU judgement")
        if r.get("label_source")!="TWO_INDEPENDENT_TECHNICAL_REVIEWERS":
            raise ValueError("Gold source is not independent double Technical review")
        judged[qid][sku]=value
    if not judged:raise ValueError("Empty gold evaluation set")
    actual={}
    for entry in predictions:
        qid=str(entry.get("query_id",""))
        if not qid or qid in actual:raise ValueError("Missing/duplicate retrieval query")
        ranked=entry.get("ranked_skus",[])
        if not isinstance(ranked,list) or not ranked or any(not isinstance(x,str) for x in ranked):
            raise ValueError("Predictions require ordered ranked_skus")
        ranked=[s.upper() for s in ranked]
        if len(ranked)!=len(set(ranked)):raise ValueError("Duplicate SKU in ranking")
        actual[qid]=(ranked,entry.get("retrieval_latency_ms"))
    if set(judged)!=set(actual):
        raise ValueError("Locked qrels and retrieval queries differ")
    per_query=[]
    for qid,grades in sorted(judged.items()):
        ordered,latency=actual[qid]
        if set(ordered)-set(grades):
            raise ValueError("UNJUDGED_CANDIDATES_PRESENT: cannot assume they are irrelevant")
        if len(grades)<2:raise ValueError("Too few expert-judged SKU candidates for inquiry")
        top=ordered[:k]
        dcg=sum((2**grades[sku]-1)/math.log2(i+2) for i,sku in enumerate(top))
        ideal=sorted(grades.values(),reverse=True)[:k]
        idcg=sum((2**g-1)/math.log2(i+2) for i,g in enumerate(ideal))
        ndcg=dcg/idcg if idcg else 1.0
        positives={sku for sku,g in grades.items() if g>=2}
        # Exclude no-positive cases from success rate or report explicitly.
        rank=next((i+1 for i,sku in enumerate(top) if sku in positives),None)
        mrr=1/rank if rank else 0.
        recall=len(positives.intersection(top))/len(positives) if positives else None
        if latency is not None:
            if not isinstance(latency,(int,float)) or not math.isfinite(latency) or latency<0:
                raise ValueError("Invalid latency")
        per_query.append({"query_id":qid,"judged_skus":len(grades),
            "ndcg_at_5":round(ndcg,6),"mrr_at_5":round(mrr,6),
            "recall_at_5":round(recall,6) if recall is not None else None,
            "has_relevant_gold":bool(positives),"retrieval_latency_ms":latency})
    latencies=sorted(r["retrieval_latency_ms"] for r in per_query if r["retrieval_latency_ms"] is not None)
    p95=latencies[math.ceil(.95*len(latencies))-1] if latencies else None
    relevant=[r for r in per_query if r["has_relevant_gold"]]
    return {"status":"JUDGED_POOL_HELDOUT_EVALUATION",
       "query_count":len(per_query),"with_positive_gold":len(relevant),
       "ndcg_at_5":round(statistics.mean(r["ndcg_at_5"] for r in per_query),4),
       "mrr_at_5_relevant_queries":round(statistics.mean(r["mrr_at_5"] for r in relevant),4) if relevant else None,
       "recall_at_5_relevant_queries":round(statistics.mean(r["recall_at_5"] for r in relevant),4) if relevant else None,
       "p95_retrieval_latency_ms":p95,
       "latency_samples":len(latencies),
       "scope":"ONLY_EXPERT_JUDGED_POOL_NOT_FULL_CATALOG",
       "not_scientific_validation_alone":True,
       "per_query":per_query,
       "cautions":["Prediction ranking must be generated without seeing test labels.",
                   "Every returned SKU must be judged or evaluation stops.",
                   "P95 retrieval-only latency is not end-to-end page/login time.",
                   "All-zero relevance inquiries have nDCG=1 but are excluded from MRR/Recall averages.",
                   "Confidence intervals, baseline comparison and data quality sign-off are separate tasks."]}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--locked-qrels",required=True)
    a.add_argument("--rankings",required=True)
    a.add_argument("--out",required=True)
    args=a.parse_args()
    result=evaluate(read_jsonl(args.locked_qrels),read_jsonl(args.rankings))
    out=Path(args.out).resolve()
    if any((p/".git").exists() for p in (out.parent,*out.parent.parents)):
        raise SystemExit("Output must stay outside public Git repository")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("per_query","cautions")}))

if __name__=="__main__":main()

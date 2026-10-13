"""Offline retrieval metric implementations for held-out expert judgments.

Unjudged candidates are not implicitly irrelevant; each metric call requires
a complete relevance mapping for the evaluation candidate pool. Never train,
tune, or select a model on a held-out test split.
"""
from math import log2

def reciprocal_rank(ranked, relevance, k=5):
    _validate(ranked,relevance,k)
    return next((1.0/i for i,sku in enumerate(ranked[:k],1) if relevance[sku]>0),0.0)

def dcg_at_k(ranked, relevance, k=5):
    _validate(ranked,relevance,k)
    return sum((2**relevance[s]-1)/log2(i+1) for i,s in enumerate(ranked[:k],1))

def ndcg_at_k(ranked, relevance, k=5):
    _validate(ranked,relevance,k)
    actual=dcg_at_k(ranked,relevance,k)
    ideal=sorted(relevance, key=lambda sku:(-relevance[sku],str(sku)))
    best=dcg_at_k(ideal,relevance,k)
    return actual/best if best else 0.0

def _validate(ranked,relevance,k):
    if not isinstance(k,int) or k<1:raise ValueError("k must be a positive integer")
    if not ranked or len(set(ranked))!=len(ranked):
        raise ValueError("A ranked result must be non-empty and contain unique IDs")
    unknown=set(ranked)-set(relevance)
    if unknown:raise ValueError("Missing expert judgment for ranked items: "+", ".join(sorted(map(str,unknown))))
    if not relevance or any(type(v) is not int or v<0 or v>3 for v in relevance.values()):
        raise ValueError("Expert relevance labels must be integers 0-3")

def aggregate_cases(results,judgments,k=5):
    """results maps inquiry_id -> ranked SKU ids; judgments must cover all candidates."""
    if set(results)!=set(judgments):
        raise ValueError("Results and judgments must contain identical inquiry sets")
    if not results:raise ValueError("No evaluation cases")
    per_case=[{"inquiry_id":qid,"ndcg_at_k":ndcg_at_k(ranked,judgments[qid],k),
               "rr_at_k":reciprocal_rank(ranked,judgments[qid],k)}
              for qid,ranked in sorted(results.items())]
    return {
        "cases":len(per_case),"k":k,
        "mean_ndcg":sum(x["ndcg_at_k"] for x in per_case)/len(per_case),
        "mrr":sum(x["rr_at_k"] for x in per_case)/len(per_case),
        "details":per_case,
        "warning":"Metric interpretation requires representative held-out expert labels; synthetic checks alone are NOT paper results."
    }

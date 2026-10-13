"""Research-only hybrid retrieval primitives (offline).

No benchmark accuracy claims are made here. Neural embeddings must be supplied
by a separately executed encoder and evaluated with expert-labelled inquiries.
"""
from collections import defaultdict

def rrf_fusion(lexical_ranked, dense_ranked, k=60):
    """Fuse ordered product IDs with reciprocal rank fusion.

    Item IDs must be unique within each ranking. Fixed k must be tuned using
    a development split only; final held-out test data stays unseen.
    """
    if k<=0:raise ValueError("RRF k must be positive")
    scores=defaultdict(float)
    for ranked in (lexical_ranked,dense_ranked):
        if len(ranked)!=len(set(ranked)):
            raise ValueError("Duplicate candidate IDs in a ranking")
        for rank,sku in enumerate(ranked,1):
            scores[sku]+=1.0/(k+rank)
    return sorted(scores,key=lambda sku:(-scores[sku],str(sku))),scores

def assess_candidate(candidate,required):
    """Evidence-aware constraint inspection: missing != mismatching."""
    issues=[]
    evidence=candidate.get("attributes") or {}
    for attribute,expected in required.items():
        if expected is None:
            continue
        actual=evidence.get(attribute)
        if actual is None or actual.get("status") in ("UNKNOWN",None):
            issues.append({"attribute":attribute,"status":"UNKNOWN",
                           "reason":"No verified evidence; cannot claim compatibility."})
        elif actual.get("value")!=expected:
            issues.append({"attribute":attribute,"status":"MISMATCH",
                           "reason":"Verified evidence contradicts requirement."})
    return {"product_id":candidate.get("id"),"constraint_status":
            "MISMATCH" if any(x["status"]=="MISMATCH" for x in issues) else
            "UNKNOWN" if issues else "PASS",
            "findings":issues}

def candidate_order(fused_ids,product_map,required):
    """Never silently promote known mismatches. Preserve UNKNOWN explicitly."""
    output=[]
    for rid,sku in enumerate(fused_ids,1):
        if sku not in product_map:continue
        inspection=assess_candidate(product_map[sku],required)
        output.append({"sku":sku,"retrieval_rank":rid,**inspection})
    priority={"PASS":0,"UNKNOWN":1,"MISMATCH":2}
    output.sort(key=lambda c:(priority[c["constraint_status"]],c["retrieval_rank"]))
    return output

"""Evaluation metrics for the four AI modules and the role-aware agent.

This module does not create labels or infer missing ground truth. Callers must
supply frozen, authorized, held-out cases and preserve the dataset manifest.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from math import log2,sqrt
import random

def _retrieval_case(ranked,labels,k):
    if not ranked or len(ranked)!=len(set(ranked)):raise ValueError("Ranked SKUs must be non-empty and unique")
    if any(s not in labels for s in ranked[:k]):raise ValueError("Every retrieved Top-K SKU must have an expert label")
    if any(type(v) is not int or v not in (0,1,2,3) for v in labels.values()):raise ValueError("Relevance labels must be integers 0-3")
    dcg=sum((2**labels[s]-1)/log2(i+2) for i,s in enumerate(ranked[:k]))
    ideal=sorted(labels.values(),reverse=True)[:k]
    idcg=sum((2**v-1)/log2(i+2) for i,v in enumerate(ideal))
    ndcg=dcg/idcg if idcg else 0.0
    rr=next((1/(i+1) for i,s in enumerate(ranked[:k]) if labels[s]>=2),0.0)
    relevant=sum(1 for v in labels.values() if v>=2)
    recall=(sum(1 for s in ranked[:k] if labels[s]>=2)/relevant) if relevant else None
    return {"ndcg_at_k":ndcg,"mrr_at_k":rr,"recall_at_k":recall,"relevant_in_label_pool":relevant}

def _bootstrap_ci(values,seed=42,iterations=2000):
    if len(values)<2:return {"lower":None,"upper":None,"method":"NOT_ESTIMABLE_FEWER_THAN_2_CASES"}
    rng=random.Random(seed);means=[]
    for _ in range(iterations):
        sample=[values[rng.randrange(len(values))] for __ in values]
        means.append(sum(sample)/len(sample))
    means.sort()
    return {"lower":means[int(.025*iterations)],"upper":means[min(iterations-1,int(.975*iterations))],
            "method":"PERCENTILE_BOOTSTRAP_CASE_LEVEL","iterations":iterations,"seed":seed}

def evaluate_retrieval(cases,k=5,catalog_sku_count=None):
    """cases: [{inquiry_id, ranked_by_method:{method:[sku]}, labels:{sku:0..3}, pool_complete:bool}]"""
    if not cases:raise ValueError("No held-out retrieval cases supplied")
    methods=sorted({m for c in cases for m in c.get("ranked_by_method",{})})
    out={}
    for method in methods:
        rows=[]
        for case in cases:
            ranked=case.get("ranked_by_method",{}).get(method)
            if not ranked:continue
            labels=case.get("labels",{})
            m=_retrieval_case(ranked,labels,k)
            rows.append({"inquiry_id":case["inquiry_id"],**m,
                         "recall_eligible":bool(case.get("pool_complete"))})
        if not rows:continue
        out[method]={
          "evaluated_cases":len(rows),
          "mean_ndcg_at_k":sum(x["ndcg_at_k"] for x in rows)/len(rows),
          "mrr_at_k":sum(x["mrr_at_k"] for x in rows)/len(rows),
          "ndcg_ci_95":_bootstrap_ci([x["ndcg_at_k"] for x in rows]),
          "mrr_ci_95":_bootstrap_ci([x["mrr_at_k"] for x in rows]),
          "recall_at_k":(sum(x["recall_at_k"] for x in rows if x["recall_eligible"] and x["recall_at_k"] is not None)/
             max(1,sum(1 for x in rows if x["recall_eligible"] and x["recall_at_k"] is not None))),
          "recall_eligible_cases":sum(1 for x in rows if x["recall_eligible"] and x["recall_at_k"] is not None),
          "case_metrics":rows}
    return {"status":"HELD_OUT_EXPERIMENTAL_METRICS","k":k,"catalog_sku_count":catalog_sku_count,
      "methods":out,"paired_comparison_requires_identical_inquiry_ids":True,
      "scientific_validation":False,
      "warning":"Only use adjudicated held-out labels. Recall@K is reportable only when the relevance pool covers the complete eligible catalog."}

def mine_association_rules(baskets,min_support=.01,min_confidence=.1):
    clean=[set(x) for x in baskets if x]
    if not clean:raise ValueError("No training baskets")
    n=len(clean);counts=Counter(s for b in clean for s in b)
    pairs=Counter((a,b) for basket in clean for a in basket for b in basket if a!=b)
    rules=defaultdict(list)
    for (a,b),count in pairs.items():
        support=count/n;confidence=count/counts[a];lift=confidence/(counts[b]/n)
        if support>=min_support and confidence>=min_confidence:
            rules[a].append({"sku":b,"support":support,"confidence":confidence,"lift":lift})
    for a in rules:rules[a].sort(key=lambda x:(-x["lift"],-x["confidence"],x["sku"]))
    return rules,counts

def evaluate_bundling(train_baskets,test_baskets,k=3):
    """Temporal evaluation: rules/popularity from train only; evaluate future baskets."""
    if len(train_baskets)<10 or not test_baskets:raise ValueError("Need >=10 training baskets and a non-empty temporal test set")
    rules,popularity=mine_association_rules(train_baskets)
    popular=[sku for sku,_ in popularity.most_common()]
    methods={"ASSOCIATION_RULES":lambda a:[x["sku"] for x in rules.get(a,[])[:k]],
             "POPULARITY_BASELINE":lambda a:[x for x in popular if x!=a][:k]}
    out={}
    for name,recommend in methods.items():
        hits=0;predicted=0;relevant=0;covered=0;case_count=0
        for basket in test_baskets:
            basket=set(basket)
            for antecedent in basket:
                truth=basket-{antecedent}
                if not truth:continue
                rec=recommend(antecedent)
                if rec:covered+=1
                predicted+=len(rec);relevant+=len(truth)
                hits+=len(set(rec)&truth);case_count+=1
        out[name]={"antecedent_cases":case_count,"coverage":covered/max(1,case_count),
          "precision_at_k":hits/max(1,predicted),"recall_at_k":hits/max(1,relevant),
          "hit_rate_at_k":sum(1 for b in test_baskets for a in b if (set(recommend(a))&(set(b)-{a})))/max(1,sum(max(0,len(set(b))-1) for b in test_baskets))}
    return {"status":"TEMPORAL_HOLDOUT_ASSOCIATION_EVALUATION","train_baskets":len(train_baskets),
      "test_baskets":len(test_baskets),"k":k,"results":out,"causal_claim":False,
      "warning":"Association rules are descriptive co-purchase patterns, not causal effects or supervised neural training."}

def evaluate_agent(cases):
    if not cases:raise ValueError("No agent evaluation cases supplied")
    n=len(cases)
    correct=sum(bool(x.get("tool_call_correct")) for x in cases)
    compliant=sum(bool(x.get("policy_compliant")) for x in cases)
    unauthorized=sum(bool(x.get("unauthorized_action_attempted")) for x in cases)
    grounded=[float(x["groundedness_score_1_5"]) for x in cases if x.get("groundedness_score_1_5") is not None]
    return {"cases":n,"tool_call_accuracy":correct/n,"policy_compliance_rate":compliant/n,
      "unauthorized_action_attempt_count":unauthorized,
      "mean_groundedness_1_5":sum(grounded)/len(grounded) if grounded else None,
      "pass_count":sum(str(x.get("outcome")).upper()=="PASS" for x in cases),
      "scientific_validation":False,
      "warning":"Agent release must fail on any unauthorized action attempt, regardless of aggregate accuracy."}

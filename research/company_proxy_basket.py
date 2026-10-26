"""Exploratory grouping analysis of locally-held, authorized 2025 sales extracts.

Only operates on the analyst's private files. No source records in GitHub.
June is excluded. Source paragraph groups are treated as PROXY baskets by
explicit user modelling assumption, never invoice-verified transactions.
"""
import argparse,csv,json,math,hashlib
from pathlib import Path
from collections import Counter,defaultdict

def read(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def grouped_rules(lines,min_count=2,min_support=.003,min_confidence=.2):
    selected=[r for r in lines if r.get("month_label")!="2025-06"
        and r.get("manual_sku_review_needed")=="FALSE"
        and r.get("basket_proxy_id") and r.get("sku_compare_key")]
    baskets=defaultdict(set)
    for r in selected:
        try:q=float(r.get("quantity_kg",""))
        except (TypeError,ValueError):continue
        if not math.isfinite(q) or q<=0:continue
        baskets[r["basket_proxy_id"]].add(r["sku_compare_key"])
    total=len(baskets)
    sku_frequency=Counter()
    pair_frequency=Counter()
    for candidates in baskets.values():
        sku_frequency.update(candidates)
        for a in candidates:
            for b in candidates:
                if a!=b:pair_frequency[(a,b)]+=1
    rules=[]
    for (a,b),n in pair_frequency.items():
        support=n/total if total else 0
        confidence=n/sku_frequency[a]
        lift=confidence/(sku_frequency[b]/total)
        if n>=min_count and support>=min_support and confidence>=min_confidence:
            rules.append({"antecedent_sku":a,"consequent_sku":b,
                "co_group_count":n,"support":round(support,5),
                "confidence":round(confidence,5),"lift":round(lift,4),
                "source_type":"USER_ASSUMED_PROXY","invoice_verified":False})
    rules.sort(key=lambda x:(-x["co_group_count"],-x["lift"],x["antecedent_sku"],x["consequent_sku"]))
    return {"status":"EXPLORATORY_PROXY_NOT_VALIDATED_INVOICE",
      "eligible_group_count":total,
      "multi_sku_group_count":sum(len(v)>1 for v in baskets.values()),
      "rules":rules,"source_type":"USER_ASSUMED_PROXY",
      "excluded_month":"2025-06","invoice_verified":False,
      "not_for_company_auto_recommendation":True}

def run(lines_path,output):
    records=read(lines_path)
    report=grouped_rules(records)
    # Do not publish raw company details. Output to a restricted local directory.
    out=Path(output).expanduser().resolve()
    if any((parent/".git").exists() for parent in (out.parent,*out.parent.parents)):
        raise ValueError("Private output cannot be saved inside Git repo")
    out.parent.mkdir(parents=True,exist_ok=True)
    report["source_sha256"]=hashlib.sha256(Path(lines_path).read_bytes()).hexdigest()
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--deidentified-lines",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    result=run(args.deidentified_lines,args.out)
    print(json.dumps({"status":result["status"],"eligible_group_count":result["eligible_group_count"],
      "multi_sku_group_count":result["multi_sku_group_count"],"rules":len(result["rules"])}))

if __name__=="__main__":main()

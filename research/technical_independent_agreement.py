"""Independent Technical grade 0..3 reconciliation, no customer data in logs.

Two distinct human reviewers must independently submit keyed pairs; never
auto-create gold labels or silently resolve disagreements using AI scores.
"""
import argparse,csv,json,hashlib
from collections import Counter,defaultdict
from pathlib import Path

GRADE={0,1,2,3}
def load(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def validate(rows,expected_reviewer):
    by={}
    if not rows:raise ValueError("No reviewer labels")
    for r in rows:
        pair=r.get("pair_id","").strip()
        if not pair:continue  # blank template rows are not evidence
        if pair in by:raise ValueError("Duplicate pair ID")
        if r.get("reviewer_id","").strip()!=expected_reviewer:
            raise ValueError("Reviewer identity mismatch")
        if not r.get("datasheet_reference","").strip():
            raise ValueError("Missing datasheet evidence reference")
        if len(r.get("rationale","").strip())<10:
            raise ValueError("Each grade requires a specific reason (>=10 chars)")
        try:grade=int(r.get("label_0_3",""))
        except ValueError:raise ValueError("Missing Technical grade")
        if grade not in GRADE:raise ValueError("Label outside 0..3")
        by[pair]={"grade":grade,"sku":r.get("sku","").strip().upper(),
                  "inquiry_id":r.get("inquiry_id","").strip(),
                  "evidence_ref":r["datasheet_reference"].strip(),
                  "project_group":r.get("project_group","").strip()}
        if not all(by[pair][k] for k in ("sku","inquiry_id","project_group")):
            raise ValueError("Missing SKU, inquiry or project group")
    if not by:raise ValueError("No labelled pairs in reviewer file")
    return by

def agreement(rows_a,rows_b):
    aa=validate(rows_a,"TECHNICAL_A")
    bb=validate(rows_b,"TECHNICAL_B")
    if set(aa)!=set(bb):raise ValueError("Reviewer assignments differ; require locked identical tasks")
    for key in aa:
        if any(aa[key][x]!=bb[key][x] for x in ("sku","inquiry_id","project_group")):
            raise ValueError("Reviewer pair metadata mismatch")
    ids=sorted(aa)
    # quadratic-weighted Cohen's kappa, robustly handle degenerate marginals.
    pa=Counter(aa[p]["grade"] for p in ids)
    pb=Counter(bb[p]["grade"] for p in ids)
    n=len(ids)
    observed=sum(((aa[p]["grade"]-bb[p]["grade"])**2)/9 for p in ids)/n
    expected=sum(((a-b)**2)/9*(pa[a]/n)*(pb[b]/n) for a in GRADE for b in GRADE)
    kappa=(1-observed/expected) if expected>0 else (1. if observed==0 else None)
    contradictions=[p for p in ids if aa[p]["grade"]!=bb[p]["grade"]]
    return {"status":"ADJUDICATION_REQUIRED" if contradictions else "DOUBLE_REVIEW_COMPLETE",
      "reviewed_pair_count":n,"exact_agreement_count":n-len(contradictions),
      "disagreements_count":len(contradictions),"weighted_cohen_kappa":round(kappa,4) if kappa is not None else None,
      "disagreement_pair_ids":contradictions,
      "labels_finalized":False,
      "notes":["Disagreement requires human adjudication; kappa is a diagnostic, not gold-label evidence.",
               "Separate consent, PII, datasheet provenance, and group/time split checks must still pass."]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--review-a",required=True)
    ap.add_argument("--review-b",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    result=agreement(load(a.review_a),load(a.review_b))
    out=Path(a.out).resolve()
    if any((p/".git").exists() for p in (out.parent,*out.parent.parents)):
        raise ValueError("Save private reviewer outcomes outside Git repo")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="disagreement_pair_ids"}))

if __name__=="__main__":main()

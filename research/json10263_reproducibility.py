"""JSON #10263: fail-closed saved-ranking audit, NOT a model-weight rerun.
Private real data never belongs in this public repository or its CI.
"""
import argparse, csv, hashlib, json, math, random
from collections import defaultdict
from pathlib import Path

METHODS=("BM25","MiniLM","RRF")
TEST=tuple(f"RQ{x:03d}" for x in range(41,51))
PUBLISHED={"BM25":(.9208,.8167,1.0),"MiniLM":(.9341,.8833,1.0),"RRF":(.9437,.9000,1.0)}

def read_csv(path, required):
    with open(path,encoding="utf-8-sig",newline="") as fp:
        reader=csv.DictReader(fp)
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError("Missing columns in "+Path(path).name)
        result=list(reader)
    if not result:raise ValueError("Empty input file")
    return result

def read_ranks(path):
    items=defaultdict(dict)
    records=read_csv(path,("inquiry_id","sku_id","method","rank","score"))
    for row in records:
        qid=row["inquiry_id"].strip();sku=row["sku_id"].strip();method=row["method"].strip()
        if not qid or not sku or method not in METHODS:raise ValueError("Unknown query/SKU/method")
        rank=int(row["rank"]);score=float(row["score"])
        if not math.isfinite(score) or sku in items[(qid,method)]:
            raise ValueError("Nonfinite score or duplicate SKU")
        items[(qid,method)][sku]=(rank,score)
    inquiries=sorted({qid for qid,_ in items})
    if len(records)!=3000 or len(inquiries)!=50:
        raise ValueError("Expected 50 inquiries x 20 SKU x 3 methods = 3000 rows")
    for qid in inquiries:
        sets=[]
        for method in METHODS:
            candidates=items.get((qid,method))
            if not candidates or len(candidates)!=20:
                raise ValueError("Missing or incomplete 20-SKU method pool")
            ordered=sorted(candidates.values())
            if [v[0] for v in ordered]!=list(range(1,21)):
                raise ValueError("Ranks must be unique 1-20")
            if any(ordered[i][1]<ordered[i+1][1]-1e-9 for i in range(19)):
                raise ValueError("Scores must descend with rank")
            sets.append(set(candidates))
        if not sets[0]==sets[1]==sets[2]:
            raise ValueError("Methods use different candidate universes")
    return items,len(records)

def read_gold(path,items):
    gold=defaultdict(dict)
    records=read_csv(path,("inquiry_id","sku_id","grade"))
    for row in records:
        qid=row["inquiry_id"].strip();sku=row["sku_id"].strip();grade=row["grade"].strip()
        if not qid or not sku or grade not in ("0","1","2","3") or sku in gold[qid]:
            raise ValueError("Invalid or duplicate relevance judgment")
        gold[qid][sku]=int(grade)
    for qid in TEST:
        if len(gold[qid])!=20 or set(gold[qid])!=set(items[(qid,"BM25")]):
            raise ValueError("Missing fully judged held-out query "+qid)
    return gold,len(records)

def metric(candidates,gold):
    if len(candidates)!=20 or set(candidates)!=set(gold):
        raise ValueError("Unjudged ranking candidate")
    order=sorted(candidates,key=lambda sku:candidates[sku][0])
    grade=[gold[sku] for sku in order]
    weights=lambda gs:sum((2**g-1)/math.log2(i+2) for i,g in enumerate(gs[:5]))
    ideal=weights(sorted(grade,reverse=True))
    if not ideal or 3 not in grade:
        raise ValueError("Undefined grade-3 held-out denominator")
    first=next((i+1 for i,g in enumerate(grade[:5]) if g==3),None)
    return (weights(grade)/ideal,1/first if first else 0.,
            sum(g==3 for g in grade[:5])/sum(g==3 for g in grade))

def check_rrf(items):
    mismatches=0;count=0;max_error=0.
    for qid in {q for q,m in items}:
        bm=items[(qid,"BM25")];dn=items[(qid,"MiniLM")];rr=items[(qid,"RRF")]
        for sku,(_,actual) in rr.items():
            score=bm[sku][1]
            comp_rank=15 if score==0 else min(15,1+sum(x[1]>score for x in bm.values()))
            expected=1/(60+comp_rank)+1/(60+dn[sku][0])
            count+=1
            error=abs(expected-actual);max_error=max(error,max_error)
            if error>0.00000051:mismatches+=1
    return {"compared_fusion_scores":count,"mismatches_6_decimal":mismatches,
            "max_absolute_error":round(max_error,9)}

def bootstrap(data,seed=20261029):
    rng=random.Random(seed);n=len(data)
    means=sorted(sum(data[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
    def pct(p):
        x=(len(means)-1)*p;lo=int(x);hi=min(lo+1,len(means)-1)
        return means[lo]+(means[hi]-means[lo])*(x-lo)
    return [pct(.025),pct(.975)]

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as fp:
        for block in iter(lambda:fp.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def audit(ranks_path,gold_path):
    ranked,n=read_ranks(ranks_path)
    gold,nlabels=read_gold(gold_path,ranked)
    data={m:[metric(ranked[(qid,m)],gold[qid]) for qid in TEST] for m in METHODS}
    means={m:tuple(sum(x[j] for x in data[m])/10 for j in range(3)) for m in METHODS}
    matches={m:all(round(x,4)==ref for x,ref in zip(means[m],PUBLISHED[m])) for m in METHODS}
    differences=[a[0]-b[0] for a,b in zip(data["RRF"],data["BM25"])]
    fusion=check_rrf(ranked)
    passed=all(matches.values()) and fusion["mismatches_6_decimal"]==0
    return {"status":"PASS_OUTPUT_REPLAY" if passed else "FAILED_OR_INCONSISTENT_OUTPUT_REPLAY",
        "is_full_encoder_rerun":False,
        "source_checksums_sha256":{"ranks":digest(ranks_path),"labels":digest(gold_path)},
        "input_record_counts":{"rankings":n,"labels":nlabels,"heldout_queries":10},
        "metrics":{"method_names":METHODS,"values_ndcg_mrr_grade3_recall_grade3":means},
        "published_4dp_matches":matches,
        "paired_rrf_minus_bm25":{"mean_ndcg":sum(differences)/10,
            "ci95_python_random":bootstrap(differences),"resamples":10000,"seed":20261029},
        "fusion_audit":fusion,
        "interpretation":"Saved-output replay only. Full MiniLM inference requires local authenticated weights, original prepared texts, software/preprocessing manifest and model revision."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--rankings",required=True)
    p.add_argument("--labels",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    out=Path(a.output).resolve()
    result=audit(a.rankings,a.labels)
    if not out.parent.exists() or any(x.name==".git" for part in [out.parent,*out.parent.parents] for x in [part]):
        raise ValueError("Output must go into preexisting authorized private directory, not Git")
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(result["status"])
    if result["status"].startswith("FAILED"):raise SystemExit(2)

if __name__=="__main__":main()

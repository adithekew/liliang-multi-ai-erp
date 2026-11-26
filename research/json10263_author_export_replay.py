"""Adapter for the original 26 November JSON #10263 author CSV column names.

Privacy: locally supplied company CSV files MUST NOT be uploaded to public Git.
This verifies SAVED OUTPUTS only; not a fresh neural model-weight rerun.

Usage:
  pip install numpy
  python -m research.json10263_author_export_replay \
    --rankings /secure/rankings.csv --labels /secure/labels.csv \
    --out /secure/replay.json
"""
import argparse,csv,hashlib,json,tempfile
from pathlib import Path
from research.json10263_reproducibility import audit,read_ranks,read_gold,metric

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):h.update(part)
    return h.hexdigest()

def convert_rankings(source,destination):
    with open(source,encoding="utf-8-sig",newline="") as f:
        rdr=csv.DictReader(f)
        needed={"Inquiry_ID","SKU","Method","Rank","Score","Split","Run_ID","Catalog_Version_Hash"}
        if not needed.issubset(rdr.fieldnames or []):
            raise ValueError("Expected original author rankings CSV schema")
        rows=list(rdr)
    if len(rows)!=3000 or len({x["Run_ID"] for x in rows})!=1 or len({x["Catalog_Version_Hash"] for x in rows})!=1:
        raise ValueError("Expected one 3000-row run and one catalog revision")
    splits={}
    for x in rows:
        q=x["Inquiry_ID"]
        if q in splits and splits[q]!=x["Split"]:
            raise ValueError("Query has conflicting train/dev/test split")
        splits[q]=x["Split"]
    if sorted([list(splits.values()).count(v) for v in ("train","dev","test")])!=[10,10,30]:
        raise ValueError("Unexpected split sizes")
    with open(destination,"w",newline="",encoding="utf-8") as out:
        w=csv.DictWriter(out,fieldnames=["inquiry_id","sku_id","method","rank","score"])
        w.writeheader()
        for x in rows:
            w.writerow({"inquiry_id":x["Inquiry_ID"],"sku_id":x["SKU"],"method":x["Method"],"rank":x["Rank"],"score":x["Score"]})
    return {"rows":len(rows),"run_id":rows[0]["Run_ID"],"catalog_id":rows[0]["Catalog_Version_Hash"]}

def convert_labels(source,destination):
    with open(source,encoding="utf-8-sig",newline="") as f:
        rdr=csv.DictReader(f)
        required={"Inquiry_ID","SKU","Relevance_0_to_3","Relevance_0_to_3_T01","Relevance_0_to_3_T02","Label_Status","Adjudication_Record"}
        if not required.issubset(rdr.fieldnames or []):
            raise ValueError("Expected original independent Technical label schema")
        rows=list(rdr)
    if len(rows)!=200:raise ValueError("Expected 200 frozen held-out labels")
    agreed=adjudicated=0
    with open(destination,"w",newline="",encoding="utf-8") as out:
        w=csv.DictWriter(out,fieldnames=["inquiry_id","sku_id","grade"])
        w.writeheader()
        for x in rows:
            g=int(x["Relevance_0_to_3"]);a=int(x["Relevance_0_to_3_T01"]);b=int(x["Relevance_0_to_3_T02"])
            if not all(z in (0,1,2,3) for z in (g,a,b)):
                raise ValueError("Invalid 0..3 Technical label")
            if x["Label_Status"]=="AGREED":
                if not (g==a==b):raise ValueError("Agreement mismatch")
                agreed+=1
            elif x["Label_Status"]=="ADJUDICATED":
                if a==b or not x["Adjudication_Record"].strip():raise ValueError("Missing disagreement record")
                adjudicated+=1
            else:raise ValueError("Unrecognized reviewer status")
            w.writerow({"inquiry_id":x["Inquiry_ID"],"sku_id":x["SKU"],"grade":g})
    return {"agreed":agreed,"adjudication_references":adjudicated}

def main():
    p=argparse.ArgumentParser()
    for name in ("rankings","labels","out"):p.add_argument("--"+name,required=True)
    args=p.parse_args();path=Path(args.out).resolve()
    if not path.parent.is_dir() or any((a/".git").exists() for a in (path.parent,*path.parent.parents)):
        raise ValueError("Output must be written to authorized private directory outside Git")
    with tempfile.TemporaryDirectory() as tmp:
        ranks=Path(tmp)/"rankings_normalized.csv";labels=Path(tmp)/"labels_normalized.csv"
        source=convert_rankings(args.rankings,ranks)
        reviews=convert_labels(args.labels,labels)
        result=audit(str(ranks),str(labels))
        # Original manuscript used numpy Generator PCG64, not Python random.Random.
        try:
            import numpy as np
        except ImportError as e:
            raise RuntimeError("Install numpy in the private research environment") from e
        ranking_data,_=read_ranks(str(ranks))
        gold,_=read_gold(str(labels),ranking_data)
        qids=[f"RQ{i:03d}" for i in range(41,51)]
        diffs=np.array([metric(ranking_data[(q,"RRF")],gold[q])[0]-
                        metric(ranking_data[(q,"BM25")],gold[q])[0] for q in qids])
        rng=np.random.default_rng(20261029)
        resamples=rng.choice(diffs,size=(10000,10),replace=True).mean(axis=1)
        ci=np.quantile(resamples,[0.025,0.975])
        published=np.array([-0.0968,0.1469])
        if not np.allclose(np.round(ci,4),published,atol=0):
            raise ValueError("Bootstrap does not reproduce manuscript interval")
        result["original_csv_schema"]={"rankings":source,"labels":reviews}
        result["original_sha256"]={"rankings":sha256(args.rankings),"labels":sha256(args.labels)}
        result["paired_ci95_numpy_pcg64"]=[float(x) for x in ci]
        result["model_weights_independently_rerun"]=False
        if result.get("status")!="PASS_OUTPUT_REPLAY":
            raise ValueError("Underlying metrics or RRF disagree with the manuscript")
        path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print("PASS: saved-output metrics, fusion scores and NumPy PCG64 bootstrap. Full MiniLM rerun NOT verified.")
if __name__=="__main__":main()

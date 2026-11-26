"""Private/offline MiniLM score replay for JSON #10263.
No raw prepared texts, vectors, model weights, or proprietary records are
embedded in this public repository, uploaded or written to GitHub Actions.
"""
import argparse,csv,hashlib,json,os,re,tempfile
from pathlib import Path
from research.json10263_reproducibility import read_ranks
from research.json10263_author_export_replay import convert_rankings


def author_aware_rankings(path):
    """Accept the uploaded original CSV schema without changing original evidence."""
    with open(path,encoding="utf-8-sig",newline="") as f:
        names=csv.DictReader(f).fieldnames or []
    if "Inquiry_ID" not in names:
        return read_ranks(path)
    with tempfile.TemporaryDirectory() as temp:
        converted=Path(temp)/"rankings_normalized.csv"
        convert_rankings(path,converted)
        return read_ranks(converted)

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def prepared_texts(path, key):
    with open(path,encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if not {key,"encoder_text"}.issubset(reader.fieldnames or []):
            raise ValueError("Required prepared-text columns missing")
        result={}
        for rec in reader:
            uid=rec[key].strip()
            if not uid or uid in result or not rec["encoder_text"].strip():
                raise ValueError("Duplicate or empty prepared encoder text")
            result[uid]=rec["encoder_text"]
    return result

def weights_sha(checkpoint):
    weights=sorted(p for p in checkpoint.rglob("*")
                   if p.is_file() and p.suffix in (".safetensors",".bin"))
    if not weights:raise ValueError("No checkpoint weight file found")
    return {str(p.relative_to(checkpoint)):digest(p) for p in weights}

def rerun(rankings,query_csv,sku_csv,checkpoint,full_commit,tolerance=1e-5):
    if not re.fullmatch("[0-9a-fA-F]{40}",full_commit):
        raise ValueError("Full 40-digit model revision is required")
    checkpoint=Path(checkpoint).resolve()
    if not checkpoint.is_dir():raise ValueError("Missing local model checkpoint")
    labels,qcount=author_aware_rankings(rankings)
    q=prepared_texts(query_csv,"inquiry_id")
    products=prepared_texts(sku_csv,"sku_id")
    if len(q)!=50 or len(products)!=20:
        raise ValueError("Prepared texts must cover exactly 50 inquiries and 20 products")
    if set(q)!={qid for qid,_ in labels} or set(products)!=set(labels[(sorted(q)[0],"MiniLM")]):
        raise ValueError("Prepared input IDs do not match the original ranking export")
    if tolerance<=0:raise ValueError("Tolerance must be positive")
    # Force offline loading on an authorized workstation; no model download.
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TOKENIZERS_PARALLELISM"]="false"
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise RuntimeError("Install sentence-transformers and numpy locally") from e
    model=SentenceTransformer(str(checkpoint),device="cpu",local_files_only=True)
    qids=sorted(q);skus=sorted(products)
    qv=model.encode([q[x] for x in qids],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
    pv=model.encode([products[x] for x in skus],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
    if qv.shape!=(50,384) or pv.shape!=(20,384):
        raise ValueError("Unexpected encoder vector count or dimension")
    similarities=np.asarray(qv @ pv.T)
    different_scores=0;max_score_error=0.;different_ranks=0
    for qi,qid in enumerate(qids):
        measured={sku:float(similarities[qi,si]) for si,sku in enumerate(skus)}
        # Original tie handling is not independently known; compare recorded
        # ranks separately from numerical score agreement.
        ordered=sorted(skus,key=lambda sku:(-measured[sku],sku))
        for ri,sku in enumerate(ordered,1):
            if labels[(qid,"MiniLM")][sku][0]!=ri:different_ranks+=1
        for sku,val in measured.items():
            err=abs(val-labels[(qid,"MiniLM")][sku][1])
            max_score_error=max(max_score_error,err)
            if err>tolerance:different_scores+=1
    return {"status":"PASS_LOCAL_DENSE_SCORE_REPLAY" if different_scores==0 and different_ranks==0 else "FAILED_LOCAL_DENSE_SCORE_REPLAY",
      "is_proof_of_original_checkpoint":False,
      "original_model_revision_provenance_verified":False,
      "full_commit_sha_claimed":full_commit,
      "checkpoint_sha256":weights_sha(checkpoint),
      "input_sha256":{"rankings":digest(rankings),"queries":digest(query_csv),"products":digest(sku_csv)},
      "scores_checked":1000,"scores_outside_tolerance":different_scores,
      "rank_mismatches":different_ranks,"max_absolute_score_error":round(max_score_error,9),
      "cosine_tolerance":tolerance,
      "caveats":["Authenticity of local checkpoint must be independently established against publisher commit. The source CSV Model_Revision_Hash may be an internal run identifier, not the full upstream commit.",
                 "The original tie-breaking and preprocessing must be separately authenticated.",
                 "This is a dense encoder replay, not BM25/full-stack reproducibility or supplier evidence verification."]}

def main():
    ap=argparse.ArgumentParser()
    for key in ("rankings","query-texts","sku-texts","model-dir","commit-sha","output"):
        ap.add_argument("--"+key,required=True)
    ap.add_argument("--tolerance",type=float,default=1e-5)
    a=ap.parse_args()
    out=Path(a.output).resolve()
    if not out.parent.is_dir() or any((p/".git").exists() for p in [out.parent,*out.parent.parents]):
        raise ValueError("Output must be in a private directory outside Git")
    result=rerun(a.rankings,a.query_texts,a.sku_texts,a.model_dir,a.commit_sha,a.tolerance)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result["status"])
    if result["status"].startswith("FAILED"):raise SystemExit(2)

if __name__=="__main__":main()

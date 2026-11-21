"""Private full-catalog neural + BM25 + RRF retrieval for arbitrary inquiry text.

Model/index are private opt-in artifacts. Dense similarity is not suitability.
The module applies hard flavor/application/form constraints, then fuses dense
and lexical ranks with RRF. Human Technical review remains mandatory.
"""
from __future__ import annotations
import hashlib, json, math, os, threading
from pathlib import Path
from time import perf_counter
from pydantic import BaseModel, Field

MODEL_ENV="LILIANG_NEURAL_MODEL_PATH"
INDEX_ENV="LILIANG_NEURAL_INDEX_PATH"
EXPECTED_MODEL_ID="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RRF_K=60
_lock=threading.Lock()
_cache={"signature":None,"model":None,"index":None}

def product_text(row):
    fields=("name","description","profile","application","product_type","application_raw","composition_raw")
    return " ".join(str(row.get(k) or "").strip() for k in fields).strip()

def text_sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _load_index(path):
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version")!=1 or data.get("model_id")!=EXPECTED_MODEL_ID:
        raise ValueError("Unsupported neural index schema/model")
    rows=data.get("products"); dim=data.get("dimensions")
    if not isinstance(rows,list) or not rows or not isinstance(dim,int) or dim<128:
        raise ValueError("Neural catalog index is empty or has invalid dimensions")
    seen=set()
    for row in rows:
        sku=str(row.get("sku") or "").strip().upper()
        vec=row.get("embedding")
        if not sku or sku in seen or not isinstance(vec,list):
            raise ValueError("Invalid or duplicate SKU/vector in neural catalog index")
        if len(vec)!=dim:
            raise ValueError("Neural embedding dimensions mismatch")
        if row.get("text_sha256")!=text_sha256(str(row.get("text") or "")):
            raise ValueError("Neural index text fingerprint mismatch")
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in vec):
            raise ValueError("Non-finite neural vector")
        norm=math.sqrt(sum(float(v)*float(v) for v in vec))
        if not .98<=norm<=1.02: raise ValueError("Catalog embeddings must be L2-normalized")
        seen.add(sku)
    return data

def _resources():
    model_dir=os.getenv(MODEL_ENV,"").strip()
    index_file=os.getenv(INDEX_ENV,"").strip()
    if not model_dir or not index_file:
        raise RuntimeError("Neural retrieval is disabled: private model and index paths are required")
    model_path,index_path=Path(model_dir),Path(index_file)
    if not model_path.is_dir() or not index_path.is_file():
        raise RuntimeError("Private neural model or catalog index is unavailable")
    signature=(str(model_path.resolve()),str(index_path.resolve()),index_path.stat().st_mtime_ns,index_path.stat().st_size)
    with _lock:
        if _cache["signature"]!=signature:
            from sentence_transformers import SentenceTransformer
            model=SentenceTransformer(str(model_path),device="cpu",local_files_only=True,trust_remote_code=False)
            index=_load_index(index_path)
            if model.get_sentence_embedding_dimension()!=index["dimensions"]:
                raise ValueError("Encoder and catalog embedding dimensions differ")
            _cache.update(signature=signature,model=model,index=index)
        return _cache["model"],_cache["index"]

def _constraint_filter(query, products):
    from research.catalog_matcher import query_intent, normalized_tokens, FLAVORS, _product_form, _product_application
    intent=query_intent(query)
    allowed=[]
    for product in products:
        p=dict(product)
        tokens=set(normalized_tokens(product_text(p)))
        # Explicit flavor requirements are hard constraints, not soft similarity.
        if intent["flavors"] and not (set(intent["flavors"]) & (tokens & FLAVORS)):
            continue
        form=_product_form(p)
        if intent["forms"] and form and form not in intent["forms"]:
            continue
        app=_product_application(p)
        if intent["applications"] and app and app!={"vape"} and not (set(intent["applications"]) & app):
            continue
        if app=={"vape"} and "vape" not in intent["applications"]:
            continue
        allowed.append(p)
    return allowed,intent

def retrieve(query, products, top_k=20):
    query=str(query or "").strip()
    if len(query)<5 or len(query)>3000: raise ValueError("Inquiry text must contain 5–3000 characters")
    if not 1<=top_k<=100: raise ValueError("top_k must be between 1 and 100")
    model,index=_resources()
    live={str(p["sku"]).strip().upper():dict(p) for p in products}
    indexed={str(p["sku"]).strip().upper():p for p in index["products"]}
    if set(live)!=set(indexed): raise RuntimeError("Catalog/index SKU coverage mismatch; rebuild the private index")
    for sku,p in live.items():
        if text_sha256(product_text(p))!=indexed[sku]["text_sha256"]:
            raise RuntimeError("Stale neural index for SKU "+sku)
    start=perf_counter()
    eligible,intent=_constraint_filter(query,list(live.values()))
    if not eligible:
        return {"method":"BM25_DENSE_RRF","results":[],"catalog_sku_count":len(indexed),
                "eligible_catalog_sku_count":0,"scope":"FULL_CURRENT_CATALOG_SNAPSHOT",
                "scientifically_validated":False,"abstained":True,
                "warning":"No catalog SKU passed explicit inquiry constraints; ask for clarification."}
    qv=model.encode([query],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)[0]
    dense=[]
    for p in eligible:
        sku=str(p["sku"]).upper()
        vec=indexed[sku]["embedding"]
        score=sum(float(a)*float(b) for a,b in zip(qv,vec))
        dense.append((score,sku))
    dense.sort(key=lambda x:(-x[0],x[1]))
    dense_scores=dict(dense)
    dense_rank={sku:i for i,(_,sku) in enumerate(dense,1)}
    from research.catalog_matcher import score_products
    lexical=score_products(query,eligible)
    lexical_rank={row["sku"]:row["rank"] for row in lexical}
    rrf={}
    for _,sku in dense:
        rrf[sku]=1.0/(RRF_K+dense_rank[sku])
    for sku,rank in lexical_rank.items():
        rrf[sku]=rrf.get(sku,0.0)+1.0/(RRF_K+rank)
    ranked=sorted(rrf,key=lambda sku:(-rrf[sku],-next(x[0] for x in dense if x[1]==sku),sku))
    dense_scores=dict(dense)
    elapsed=round((perf_counter()-start)*1000,3)
    return {
      "method":"MULTILINGUAL_MINILM_DENSE_PLUS_BM25_RRF",
      "model_id":index["model_id"],"model_revision":index["model_revision"],
      "catalog_version":index["catalog_version"],"rrf_k":RRF_K,
      "catalog_sku_count":len(indexed),"indexed_sku_count":len(indexed),
      "eligible_catalog_sku_count":len(eligible),"bm25_candidate_count":len(lexical),
      "query_inference_and_ranking_ms":elapsed,
      "parsed_constraints":{"flavors":intent["flavors"],"applications":intent["applications"],"forms":intent["forms"]},
      "results":[
        {"rank":i,"sku":sku,"name":live[sku].get("name"),
         "dense_cosine":round(dense_scores[sku],6),"bm25_rank":lexical_rank.get(sku),
         "rrf_score":round(rrf[sku],8),"source_ref":live[sku].get("source_ref"),
         "technical_fit":"UNKNOWN","datasheet_verified":False}
        for i,sku in enumerate(ranked[:top_k],1)
      ],
      "scope":"FULL_CURRENT_CATALOG_SNAPSHOT","scientifically_validated":False,
      "warning":"Dense/RRF ranks are retrieval evidence, not technical suitability, regulatory/halal status, or calibrated probability. Technical review remains mandatory."
    }

class NeuralMatchRequest(BaseModel):
    query:str=Field(min_length=5,max_length=3000)
    top_k:int=Field(default=20,ge=1,le=100)

def mount_neural_retrieval(app,current,get_db):
    from fastapi import Depends,HTTPException
    @app.post("/v1/ai/neural-match")
    def neural_match(data:NeuralMatchRequest,u=Depends(current),db=Depends(get_db)):
        if u["role"] not in ("admin","sales","technical","manager"):
            raise HTTPException(403,"Role access denied")
        rows=[dict(r) for r in db.execute("""SELECT p.id,p.sku,p.name,p.description,p.profile,p.application,p.source_ref,
                 d.product_type,d.application_raw,d.composition_raw
                 FROM products p LEFT JOIN catalog_product_details d ON d.sku=p.sku ORDER BY p.sku""").fetchall()]
        try:return retrieve(data.query,rows,data.top_k)
        except (RuntimeError,ValueError,OSError) as exc:raise HTTPException(503,str(exc)) from None

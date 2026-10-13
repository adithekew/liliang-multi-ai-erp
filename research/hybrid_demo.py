"""Fixed-query hybrid BM25+dense-neural+RRF demo on synthetic, offline-encoded data.

Production query embedding inference is NOT available in the Render Free service.
Neural vector assets are generated externally in GitHub Actions with the actual
multilingual Sentence Transformers model, then served as static research data.
"""
import json
import math
from functools import lru_cache
from pathlib import Path
from time import perf_counter

from multi_ai import score_products
from research.hybrid import rrf_fusion, candidate_order

ASSET=Path(__file__).resolve().parent/"fixtures"/"neural_synthetic_v1.json"

@lru_cache(maxsize=1)
def load_fixture():
    if not ASSET.exists():
        return None
    data=json.loads(ASSET.read_text(encoding="utf-8"))
    if data["data_scope"]!="SYNTHETIC_EXAMPLES_ONLY" or data["schema_version"]!=1:
        raise ValueError("Refusing an unknown embedding data source")
    dim=data["dimensions"]
    if dim<128 or not data["model_revision"]:
        raise ValueError("Invalid neural embedding provenance")
    skus=[p["sku"] for p in data["products"]]
    cases=[q["id"] for q in data["queries"]]
    if len(skus)!=len(set(skus)) or len(cases)!=len(set(cases)):
        raise ValueError("Duplicate identifiers in neural fixture")
    for row in data["products"]+data["queries"]:
        v=row["embedding"]
        if len(v)!=dim or not all(math.isfinite(f) for f in v):
            raise ValueError("Missing/nonfinite embeddings")
        norm=math.sqrt(sum(f*f for f in v))
        if not .98<=norm<=1.02:
            raise ValueError("Neural fixture vector is not normalized")
    return data

def public_cases():
    fixture=load_fixture()
    if not fixture:return {"available":False,"cases":[],"mode":"OFFLINE_NEURAL_ASSET_MISSING"}
    return {
        "available":True,
        "mode":fixture["encoding_mode"],
        "encoder_type":fixture["encoder_type"],
        "model_id":fixture["model_id"],
        "model_revision":fixture["model_revision"],
        "dimensions":fixture["dimensions"],
        "data_scope":fixture["data_scope"],
        "cases":[{"id":q["id"],"text":q["text"]} for q in fixture["queries"]],
        "notice":"Fixed synthetic queries only. Arbitrary live neural encoding, real customer data and expert evaluation are NOT provided."
    }

def evaluate_case(case_id, rows):
    fixture=load_fixture()
    if not fixture:
        raise FileNotFoundError("Real neural assets not generated yet")
    cases={q["id"]:q for q in fixture["queries"]}
    if case_id not in cases:raise KeyError("Unknown synthetic query case")
    q=cases[case_id]
    products=[dict(p) for p in rows]
    if len(products)!=len(fixture["products"]):
        raise ValueError("Demo catalog differs from the neural embedding source; reindex first")
    assetmap={p["sku"]:p for p in fixture["products"]}
    for item in products:
        ref=assetmap.get(item["sku"])
        if ref is None:raise ValueError("An SKU is absent from the neural index")
        text=" ".join(str(item[k]) for k in ("name","description","profile","application"))
        if text!=ref["text"]:
            raise ValueError("Stale neural index for SKU "+item["sku"])
    t0=perf_counter()
    lexical=score_products(q["text"],products)
    lexical_order=[p["sku"] for p in lexical]
    neural_scores={}
    for p in fixture["products"]:
        neural_scores[p["sku"]]=sum(a*b for a,b in zip(q["embedding"],p["embedding"]))
    dense_order=sorted(neural_scores,key=lambda s:(-neural_scores[s],s))
    fused,rrf_scores=rrf_fusion(lexical_order,dense_order,k=60)
    # Product evidences are unknown because no verified datasheet is attached.
    enriched={}
    for p in products:
        enriched[p["sku"]]={"id":p["id"],"attributes":{
            "halal_status":{"value":None,"status":"UNKNOWN"},
            "regulatory":{"value":None,"status":"UNKNOWN"}}}
    checked=candidate_order(fused,enriched,{"halal_status":"certified"})
    bm25_rank={sku:i+1 for i,sku in enumerate(lexical_order)}
    dense_rank={sku:i+1 for i,sku in enumerate(dense_order)}
    output=[]
    for rank,row in enumerate(checked,1):
        sku=row["sku"]
        output.append({"rank":rank,"sku":sku,"bm25_rank":bm25_rank.get(sku),
            "dense_rank":dense_rank[sku],"dense_cosine":round(neural_scores[sku],5),
            "rrf_score":round(rrf_scores[sku],7),
            "constraint_status":row["constraint_status"],
            "unknown_attributes":["halal_status","regulatory"],
            "datasheet_evidence_verified":False})
    retrieval_only_ms=round((perf_counter()-t0)*1000,3)
    return {
        "case_id":case_id,"query":q["text"],
        "developer_authored_expected_sku":q["gold_sku"],
        "encoder_type":fixture["encoder_type"],
        "model_id":fixture["model_id"],"model_revision":fixture["model_revision"],
        "embedding_dimensions":fixture["dimensions"],
        "inference_mode":fixture["encoding_mode"],
        "lexical_method":"BM25_ALIASES_BASELINE",
        "fusion_method":"RRF_K60",
        "lexical_skus":lexical_order,
        "dense_skus":dense_order,
        "hybrid_skus":[c["sku"] for c in output],
        "ranked_candidates":output,
        "retrieval_only_latency_ms":retrieval_only_ms,
        "end_to_end_latency_ms":None,
        "data_scope":"SYNTHETIC_EXAMPLES_ONLY",
        "validated_by_technical":False,
        "notes":"Real pretrained multilingual embeddings, computed offline on synthetic queries. No live encoder; developer-authored targets are not expert relevance judgements. No verified halal/datasheet claims."
    }

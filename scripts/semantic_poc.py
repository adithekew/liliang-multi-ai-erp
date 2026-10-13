"""Run a *real* multilingual neural encoder locally for synthetic retrieval.

Never run with customer/private data without authorization. Heavy optional
dependencies are intentionally NOT installed on Render Free.
Install locally: pip install -r requirements-ai-local.txt
Run: python scripts/semantic_poc.py
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.hybrid import rrf_fusion, candidate_order
from multi_ai import score_products

PRODUCTS=[
    {"id":1,"sku":"FLV-STRAW-01","name":"Strawberry Flavor","description":"Sweet red berry flavour for dairy milk","profile":"strawberry","application":"dairy"},
    {"id":2,"sku":"FLV-VANI-02","name":"Vanilla Flavor","description":"Vanilla cream for bakery","profile":"vanilla","application":"bakery"},
    {"id":3,"sku":"FLV-MANG-03","name":"Mango Flavor","description":"Tropical mango fruity drink","profile":"mango","application":"beverage"},
    {"id":4,"sku":"FLV-CHOCO-04","name":"Chocolate Flavor","description":"Chocolate cocoa for dairy","profile":"chocolate","application":"dairy"},
    {"id":5,"sku":"FLV-LEMON-05","name":"Lemon Flavor","description":"Fresh citrus for beverage","profile":"lemon","application":"beverage"}
]
QUERY="Saya mencari rasa stroberi untuk minuman susu."
def run():
    from sentence_transformers import SentenceTransformer
    model=SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    docs=[p["name"]+" "+p["description"]+" "+p["application"] for p in PRODUCTS]
    vecs=model.encode([QUERY]+docs,normalize_embeddings=True)
    dense_order=sorted(range(len(PRODUCTS)),
                       key=lambda i:-float(vecs[0]@vecs[i+1]))
    dense_skus=[PRODUCTS[i]["sku"] for i in dense_order]
    lexical_skus=[p["sku"] for p in score_products(QUERY,PRODUCTS)]
    fused,scores=rrf_fusion(lexical_skus,dense_skus)
    for p in PRODUCTS:
        p["attributes"]={"application":{"value":p["application"],"status":"SYNTHETIC_UNVERIFIED"},
                         "halal_status":{"value":None,"status":"UNKNOWN"}}
    candidates=candidate_order(fused,{p["sku"]:p for p in PRODUCTS},
                               {"halal_status":"certified"})
    print("RESEARCH PROOF-OF-CONCEPT ONLY; NOT ACCURACY-VALIDATED")
    print("Lexical",lexical_skus)
    print("Neural dense",dense_skus)
    print("Hybrid RRF",fused)
    print("Guarded candidates",candidates)
if __name__=="__main__":run()

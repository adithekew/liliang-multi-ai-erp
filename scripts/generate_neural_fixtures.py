"""Generate REAL multilingual neural embeddings for a synthetic B2B-flavor research fixture.

Executed on GitHub Actions (not Render Free) with sentence-transformers.
Only synthetic SKU descriptions and researcher-authored example inquiries.
There is no real customer data, expert ground truth, or runtime LLM service.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from huggingface_hub import HfApi
from sentence_transformers import SentenceTransformer

ROOT=Path(__file__).resolve().parents[1]
MODEL_ID="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CATALOG=[
 {"sku":"FLV-STRAW-01","name":"Strawberry Flavor","description":"Ripe sweet strawberry for dairy beverages","profile":"strawberry","application":"dairy"},
 {"sku":"FLV-VANI-02","name":"Vanilla Flavor","description":"Creamy vanilla for bakery and dairy","profile":"vanilla","application":"bakery"},
 {"sku":"FLV-MANG-03","name":"Mango Flavor","description":"Tropical mango for beverages","profile":"mango","application":"beverage"},
 {"sku":"FLV-CHOCO-04","name":"Chocolate Flavor","description":"Rich chocolate for dairy and bakery","profile":"chocolate","application":"dairy"},
 {"sku":"FLV-LEMON-05","name":"Lemon Flavor","description":"Citrus lemon for cold beverages","profile":"lemon","application":"beverage"}
]
CASES=[
 {"id":"Q01","text":"Saya mencari rasa stroberi untuk minuman susu.","gold_sku":"FLV-STRAW-01"},
 {"id":"Q02","text":"Butuh perisa vanilla creamy untuk roti dan kue.","gold_sku":"FLV-VANI-02"},
 {"id":"Q03","text":"Tropical mango flavor for refreshing cold drinks.","gold_sku":"FLV-MANG-03"},
 {"id":"Q04","text":"Aroma coklat yang kaya untuk minuman susu.","gold_sku":"FLV-CHOCO-04"},
 {"id":"Q05","text":"Fresh citrus lemon notes for a beverage.","gold_sku":"FLV-LEMON-05"},
 {"id":"Q06","text":"Mencari sensasi mangga tropis untuk minuman.","gold_sku":"FLV-MANG-03"},
 {"id":"Q07","text":"Creamy vanilla flavour for pastry or dessert.","gold_sku":"FLV-VANI-02"},
 {"id":"Q08","text":"Perisa stroberi manis untuk yogurt.","gold_sku":"FLV-STRAW-01"},
 {"id":"Q09","text":"Chocolate taste suitable for a bakery product.","gold_sku":"FLV-CHOCO-04"},
 {"id":"Q10","text":"Rasa jeruk lemon segar bagi minuman dingin.","gold_sku":"FLV-LEMON-05"}
]

def canonical_product_text(p):
    return " ".join(str(p[k]) for k in ("name","description","profile","application"))

def main():
    model_info=HfApi().model_info(MODEL_ID)
    revision=model_info.sha
    if not revision or len(revision)<25:raise RuntimeError("Model revision is unavailable")
    model=SentenceTransformer(MODEL_ID,revision=revision,device="cpu",trust_remote_code=False)
    texts=[canonical_product_text(p) for p in CATALOG]+[q["text"] for q in CASES]
    vectors=model.encode(texts,batch_size=16,normalize_embeddings=True,show_progress_bar=False)
    dimension=int(vectors.shape[1])
    if dimension<128:raise RuntimeError("Unexpectedly small embedding dimension")
    def compact(v):return [round(float(x),8) for x in v]
    result={
        "schema_version":1,
        "data_scope":"SYNTHETIC_EXAMPLES_ONLY",
        "encoder_type":"REAL_PRETRAINED_NEURAL_MULTILINGUAL_SENTENCE_TRANSFORMER",
        "model_id":MODEL_ID,
        "model_revision":revision,
        "dimensions":dimension,
        "created_at":datetime.now(timezone.utc).isoformat(),
        "encoding_mode":"OFFLINE_PRECOMPUTED_NO_RUNTIME_QUERY_ENCODER",
        "evaluation_warning":"Gold SKU IDs are developer-authored examples, NOT expert ground truth or actual PT Liliang performance.",
        "products":[{**p,"text":canonical_product_text(p),"embedding":compact(vec)} for p,vec in zip(CATALOG,vectors[:len(CATALOG)])],
        "queries":[{**q,"embedding":compact(vec)} for q,vec in zip(CASES,vectors[len(CATALOG):])]
    }
    output=ROOT/"research"/"fixtures"/"neural_synthetic_v1.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("Created synthetic neural embedding fixture",{"products":len(CATALOG),"queries":len(CASES),"dim":dimension,"model_revision":revision,"bytes":output.stat().st_size})
if __name__=="__main__":main()

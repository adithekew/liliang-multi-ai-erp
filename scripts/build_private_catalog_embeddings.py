"""Build a private embedding index from the current ERP product catalog.

Run only in an approved private environment. The output contains SKU/name text
and vectors and must never be committed to GitHub or public CI artifacts.
"""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

from persistence import connect
from research.neural_retrieval import EXPECTED_MODEL_ID, product_text, text_sha256

MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inside_git(path):
    return any((p / ".git").exists() for p in (path, *path.parents))


def build(output, authorization_record):
    auth = Path(authorization_record).expanduser().resolve()
    dest = Path(output).expanduser().resolve()
    if not auth.is_file() or auth.stat().st_size < 20:
        raise ValueError("Written catalog/data-use authorization is required")
    if inside_git(dest):
        raise ValueError("Private catalog embeddings must be stored outside Git repositories")
    with connect() as db:
        rows = [dict(r) for r in db.execute(
            "SELECT sku,name,description,profile,application,source_ref FROM products ORDER BY sku"
        ).fetchall()]
    if not rows:
        raise ValueError("No catalog products available")
    if len({str(r["sku"]).upper() for r in rows}) != len(rows):
        raise ValueError("Duplicate catalog SKU")
    texts = [product_text(row) for row in rows]
    if any(not text for text in texts):
        raise ValueError("Catalog contains an empty product text; resolve before indexing")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EXPECTED_MODEL_ID, revision=MODEL_REVISION,
                                device="cpu", trust_remote_code=False)
    vectors = model.encode(texts, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=True)
    products = []
    for row, text, vector in zip(rows, texts, vectors):
        products.append({
            "sku": str(row["sku"]).upper(),
            "name": row["name"],
            "text": text,
            "text_sha256": text_sha256(text),
            "source_ref": row["source_ref"],
            "embedding": [float(v) for v in vector],
        })
    catalog_payload = "\n".join(
        f'{p["sku"]}\t{p["text_sha256"]}\t{p["source_ref"] or ""}' for p in products
    )
    index = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": EXPECTED_MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": int(vectors.shape[1]),
        "catalog_version": hashlib.sha256(catalog_payload.encode()).hexdigest(),
        "catalog_sku_count": len(products),
        "catalog_source_counts": {},
        "authorization_sha256": sha256_file(auth),
        "products": products,
        "scientifically_validated": False,
        "warning": "Private full-catalog retrieval index. Embeddings are not expert relevance labels or technical suitability evidence."
    }
    for row in rows:
        source = str(row["source_ref"] or "UNKNOWN")
        index["catalog_source_counts"][source] = index["catalog_source_counts"].get(source, 0) + 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n",
                    encoding="utf-8")
    model_dir = dest.parent / "multilingual-minilm-l12-v2"
    model.save(str(model_dir))
    return {"status": "PRIVATE_INDEX_BUILT_NOT_VALIDATED", "catalog_sku_count": len(products),
            "dimensions": index["dimensions"], "catalog_version": index["catalog_version"],
            "index_path": str(dest), "model_path": str(model_dir),
            "authorization_sha256": index["authorization_sha256"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Private JSON index path outside Git")
    parser.add_argument("--authorization-record", required=True,
                        help="Local written approval for catalog embedding processing")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.authorization_record), indent=2))


if __name__ == "__main__":
    main()

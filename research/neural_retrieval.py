"""Private full-catalog dense retrieval for arbitrary free-text inquiries.

This module is deliberately opt-in. It loads only a privately provisioned model
and a privately stored catalog index; it never downloads models or writes
company text/embeddings to the public repository. Dense similarity is retrieval
evidence, not technical suitability or a probability of correctness.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
from pathlib import Path
from time import perf_counter

MODEL_ENV = "LILIANG_NEURAL_MODEL_PATH"
INDEX_ENV = "LILIANG_NEURAL_INDEX_PATH"
EXPECTED_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_lock = threading.Lock()
_cache = {"signature": None, "model": None, "index": None}


def product_text(row: dict) -> str:
    """Stable text contract shared by index builder and online retrieval."""
    fields = ("name", "description", "profile", "application")
    return " ".join(str(row.get(k) or "").strip() for k in fields).strip()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_index(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported neural catalog index schema")
    if data.get("model_id") != EXPECTED_MODEL_ID:
        raise ValueError("Neural index encoder does not match the configured model")
    rows = data.get("products")
    dim = data.get("dimensions")
    if not isinstance(rows, list) or not rows or not isinstance(dim, int) or dim < 128:
        raise ValueError("Neural catalog index is empty or has invalid dimensions")
    seen = set()
    for row in rows:
        sku = str(row.get("sku") or "").strip().upper()
        vector = row.get("embedding")
        if not sku or sku in seen or not isinstance(vector, list) or len(vector) != dim:
            raise ValueError("Invalid or duplicate SKU/vector in neural catalog index")
        if row.get("text_sha256") != text_sha256(str(row.get("text") or "")):
            raise ValueError("Neural index text fingerprint mismatch")
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector):
            raise ValueError("Non-finite neural vector")
        norm = math.sqrt(sum(float(v) * float(v) for v in vector))
        if not 0.98 <= norm <= 1.02:
            raise ValueError("Catalog embeddings must be L2-normalized")
        seen.add(sku)
    return data


def _resources():
    model_dir = os.getenv(MODEL_ENV, "").strip()
    index_file = os.getenv(INDEX_ENV, "").strip()
    if not model_dir or not index_file:
        raise RuntimeError("Neural retrieval is disabled: private model and index paths are required")
    model_path, index_path = Path(model_dir), Path(index_file)
    if not model_path.is_dir() or not index_path.is_file():
        raise RuntimeError("Private neural model or catalog index is unavailable")
    signature = (str(model_path.resolve()), str(index_path.resolve()),
                 index_path.stat().st_mtime_ns, index_path.stat().st_size)
    with _lock:
        if _cache["signature"] != signature:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(str(model_path), device="cpu",
                                        local_files_only=True, trust_remote_code=False)
            index = _load_index(index_path)
            if model.get_sentence_embedding_dimension() != index["dimensions"]:
                raise ValueError("Encoder and catalog embedding dimensions differ")
            _cache.update(signature=signature, model=model, index=index)
        return _cache["model"], _cache["index"]


def retrieve(query: str, products: list[dict], top_k: int = 20) -> dict:
    """Embed arbitrary free text and rank the complete indexed catalog."""
    query = str(query or "").strip()
    if len(query) < 5 or len(query) > 3000:
        raise ValueError("Inquiry text must contain 5–3000 characters")
    if not 1 <= top_k <= 100:
        raise ValueError("top_k must be between 1 and 100")
    model, index = _resources()
    live = {str(p["sku"]).strip().upper(): p for p in products}
    indexed = {str(p["sku"]).strip().upper(): p for p in index["products"]}
    if set(live) != set(indexed):
        raise RuntimeError("Catalog/index SKU coverage mismatch; rebuild the private index")
    for sku, product in live.items():
        if text_sha256(product_text(product)) != indexed[sku]["text_sha256"]:
            raise RuntimeError("Stale neural index for SKU " + sku)
    start = perf_counter()
    qv = model.encode([query], normalize_embeddings=True,
                      convert_to_numpy=True, show_progress_bar=False)[0]
    scored = []
    for row in index["products"]:
        score = sum(float(a) * float(b) for a, b in zip(qv, row["embedding"]))
        scored.append((score, row["sku"]))
    scored.sort(key=lambda x: (-x[0], x[1]))
    elapsed = round((perf_counter() - start) * 1000, 3)
    return {
        "method": "MULTILINGUAL_MINILM_DENSE_COSINE",
        "model_id": index["model_id"],
        "model_revision": index["model_revision"],
        "catalog_version": index["catalog_version"],
        "catalog_sku_count": len(index["products"]),
        "indexed_sku_count": len(index["products"]),
        "query_inference_and_ranking_ms": elapsed,
        "results": [
            {"rank": i, "sku": sku, "name": live[sku].get("name"),
             "dense_cosine": round(score, 6),
             "source_ref": live[sku].get("source_ref"),
             "technical_fit": "UNKNOWN",
             "datasheet_verified": False}
            for i, (score, sku) in enumerate(scored[:top_k], 1)
        ],
        "scope": "FULL_CURRENT_CATALOG_SNAPSHOT",
        "scientifically_validated": False,
        "warning": "Dense similarity is not technical suitability, regulatory compliance, halal status, or a calibrated probability. Technical review remains mandatory."
    }


def mount_neural_retrieval(app, current, get_db):
    from fastapi import Depends, HTTPException, Query

    @app.get("/v1/ai/neural-match")
    def neural_match(q: str = Query(min_length=5, max_length=3000),
                     top_k: int = Query(default=20, ge=1, le=100),
                     u=Depends(current), db=Depends(get_db)):
        if u["role"] not in ("admin", "sales", "technical", "manager"):
            raise HTTPException(403, "Role access denied")
        rows = [dict(r) for r in db.execute(
            "SELECT id,sku,name,description,profile,application,source_ref FROM products ORDER BY sku"
        ).fetchall()]
        try:
            return retrieve(q, rows, top_k)
        except (RuntimeError, ValueError, OSError) as exc:
            raise HTTPException(503, str(exc)) from None

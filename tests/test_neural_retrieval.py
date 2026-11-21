import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research import neural_retrieval as nr


class FakeModel:
    def encode(self, texts, **kwargs):
        return [[1.0] + [0.0] * 127 for _ in texts]


def product(sku, name):
    row = {"sku": sku, "name": name, "description": "flavor powder",
           "profile": "strawberry", "application": "beverage", "source_ref": "TEST"}
    return row


def fixture(products):
    rows = []
    for p, vector in zip(products, ([1.0] + [0.0] * 127, [0.0, 1.0] + [0.0] * 126)):
        text = nr.product_text(p)
        rows.append({"sku": p["sku"], "name": p["name"], "text": text,
                     "text_sha256": nr.text_sha256(text), "embedding": vector})
    return {"schema_version": 1, "model_id": nr.EXPECTED_MODEL_ID,
            "model_revision": "test-revision", "dimensions": 128,
            "catalog_version": "test-catalog", "products": rows}


class NeuralRetrievalTests(unittest.TestCase):
    def test_index_rejects_bad_dimensions(self):
        data = fixture([product("SKU-001", "Strawberry"), product("SKU-002", "Vanilla")])
        data["products"][0]["embedding"] = [1.0]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dimensions"):
                nr._load_index(path)

    def test_index_rejects_text_fingerprint_mismatch(self):
        data = fixture([product("SKU-001", "Strawberry"), product("SKU-002", "Vanilla")])
        data["products"][0]["text"] = "altered"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                nr._load_index(path)

    def test_arbitrary_query_ranks_full_catalog(self):
        products = [product("SKU-001", "Strawberry"), product("SKU-002", "Vanilla")]
        data = fixture(products)
        with patch.object(nr, "_resources", return_value=(FakeModel(), data)):
            result = nr.retrieve("Need strawberry flavor for beverage", products, 2)
        self.assertEqual(result["catalog_sku_count"], 2)
        self.assertEqual(result["results"][0]["sku"], "SKU-001")
        self.assertEqual(result["scope"], "FULL_CURRENT_CATALOG_SNAPSHOT")
        self.assertFalse(result["scientifically_validated"])
        self.assertEqual(result["results"][0]["technical_fit"], "UNKNOWN")

    def test_stale_catalog_is_rejected(self):
        products = [product("SKU-001", "Strawberry"), product("SKU-002", "Vanilla")]
        data = fixture(products)
        changed = [dict(x) for x in products]
        changed[0]["description"] = "new supplier description"
        with patch.object(nr, "_resources", return_value=(FakeModel(), data)):
            with self.assertRaisesRegex(RuntimeError, "Stale neural index"):
                nr.retrieve("Need strawberry flavor for beverage", changed, 2)

    def test_missing_catalog_sku_is_rejected(self):
        products = [product("SKU-001", "Strawberry"), product("SKU-002", "Vanilla")]
        data = fixture(products)
        with patch.object(nr, "_resources", return_value=(FakeModel(), data)):
            with self.assertRaisesRegex(RuntimeError, "SKU coverage mismatch"):
                nr.retrieve("Need strawberry flavor for beverage", products[:1], 2)


if __name__ == "__main__":
    unittest.main()

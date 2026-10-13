import unittest
from unittest.mock import patch
from research import hybrid_demo

PRODUCTS=[
 {"id":1,"sku":"FLV-STRAW-01","name":"Strawberry Flavor","description":"Ripe sweet strawberry for dairy beverages","profile":"strawberry","application":"dairy"},
 {"id":2,"sku":"FLV-VANI-02","name":"Vanilla Flavor","description":"Creamy vanilla for bakery and dairy","profile":"vanilla","application":"bakery"}
]
def fake_fixture():
    # Unit-test vectors are fabricated and MUST NOT be presented as neural models.
    v1=[1.0]+[0.0]*127
    v2=[0.0,1.0]+[0.0]*126
    return {
       "model_id":"UNIT_TEST_ONLY","model_revision":"a"*40,
       "encoder_type":"UNIT_TEST_FAKE_VECTORS",
       "encoding_mode":"UNIT_TEST_ONLY","data_scope":"SYNTHETIC_EXAMPLES_ONLY",
       "dimensions":128,
       "products":[
           {**PRODUCTS[0],"text":"Strawberry Flavor Ripe sweet strawberry for dairy beverages strawberry dairy","embedding":v1},
           {**PRODUCTS[1],"text":"Vanilla Flavor Creamy vanilla for bakery and dairy vanilla bakery","embedding":v2}],
       "queries":[{"id":"Q01","text":"strawberry milk flavor","gold_sku":"FLV-STRAW-01","embedding":v1}]
    }
class HybridDemoTests(unittest.TestCase):
    def test_missing_fixture_is_reported_not_silently_substituted(self):
        with patch.object(hybrid_demo,"load_fixture",return_value=None):
            d=hybrid_demo.public_cases()
            self.assertFalse(d["available"])
            self.assertEqual(d["cases"],[])
            with self.assertRaises(FileNotFoundError):
                hybrid_demo.evaluate_case("Q01",PRODUCTS)
    def test_rankings_keep_unknown_labels_and_no_end_to_end_latency_claim(self):
        with patch.object(hybrid_demo,"load_fixture",return_value=fake_fixture()):
            report=hybrid_demo.evaluate_case("Q01",PRODUCTS)
        self.assertEqual(report["hybrid_skus"][0],"FLV-STRAW-01")
        self.assertEqual(report["dense_skus"][0],"FLV-STRAW-01")
        self.assertEqual(report["end_to_end_latency_ms"],None)
        self.assertFalse(report["validated_by_technical"])
        self.assertTrue(all(x["constraint_status"]=="UNKNOWN" for x in report["ranked_candidates"]))
        self.assertTrue(all(x["datasheet_evidence_verified"] is False for x in report["ranked_candidates"]))
    def test_index_fingerprint_checks_description(self):
        stale=[dict(x) for x in PRODUCTS]
        stale[0]["description"]="changed to another recipe"
        with patch.object(hybrid_demo,"load_fixture",return_value=fake_fixture()):
            with self.assertRaisesRegex(ValueError,"Stale neural index"):
                hybrid_demo.evaluate_case("Q01",stale)
    def test_unknown_case_is_not_a_live_query(self):
        with patch.object(hybrid_demo,"load_fixture",return_value=fake_fixture()):
            with self.assertRaises(KeyError):
                hybrid_demo.evaluate_case("freeform",PRODUCTS)
if __name__=="__main__":
    unittest.main()

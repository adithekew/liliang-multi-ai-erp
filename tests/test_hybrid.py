import unittest
from research.hybrid import rrf_fusion,assess_candidate,candidate_order

class HybridDesignTest(unittest.TestCase):
    def test_rrf_fuses_lexical_and_dense_without_fake_accuracy(self):
        fused,scores=rrf_fusion(["A","B","C"],["B","A","C"])
        self.assertEqual(fused[:2],["A","B"])
        self.assertAlmostEqual(scores["A"],scores["B"])
    def test_rrf_parameter_validation(self):
        with self.assertRaises(ValueError):rrf_fusion(["A"],["A"],k=0)
        with self.assertRaises(ValueError):rrf_fusion(["A","A"],["B"])
    def test_unknown_not_mismatch(self):
        c={"id":8,"attributes":{"halal_status":{"status":"UNKNOWN","value":None}}}
        z=assess_candidate(c,{"halal_status":"certified"})
        self.assertEqual(z["constraint_status"],"UNKNOWN")
    def test_verified_incompatibility_flagged(self):
        c={"id":8,"attributes":{"application":{"status":"VERIFIED","value":"bakery"}}}
        z=assess_candidate(c,{"application":"dairy"})
        self.assertEqual(z["constraint_status"],"MISMATCH")
    def test_constraint_order_keeps_unknown_not_falsely_compatible(self):
        d={"U":{"id":1,"attributes":{}},
           "P":{"id":2,"attributes":{"flavor":{"status":"VERIFIED","value":"mango"}}},
           "M":{"id":3,"attributes":{"flavor":{"status":"VERIFIED","value":"lemon"}}}}
        out=candidate_order(["M","U","P"],d,{"flavor":"mango"})
        self.assertEqual([v["sku"] for v in out],["P","U","M"])
        self.assertEqual([v["constraint_status"] for v in out],["PASS","UNKNOWN","MISMATCH"])
if __name__=="__main__":unittest.main()

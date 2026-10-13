import unittest
from research.metrics import ndcg_at_k,reciprocal_rank,aggregate_cases

class RetrievalMetricsTest(unittest.TestCase):
    def test_ndcg_perfect_ranking(self):
        labels={"A":3,"B":2,"C":0}
        self.assertAlmostEqual(ndcg_at_k(["A","B","C"],labels,3),1.0)
        self.assertLess(ndcg_at_k(["C","B","A"],labels,3),1.0)
    def test_mrr_first_relevant_at_second(self):
        self.assertEqual(reciprocal_rank(["B","A","C"],{"A":3,"B":0,"C":0}),.5)
    def test_no_implicit_zero_for_unjudged_items(self):
        with self.assertRaisesRegex(ValueError,"Missing expert judgment"):
            ndcg_at_k(["A","B"],{"A":3})
    def test_reject_duplicate_and_bad_relevance(self):
        with self.assertRaises(ValueError):ndcg_at_k(["A","A"],{"A":3})
        with self.assertRaises(ValueError):ndcg_at_k(["A"],{"A":4})
        with self.assertRaises(ValueError):ndcg_at_k(["A"],{"A":True})
    def test_aggregate_cases(self):
        r=aggregate_cases({"Q01":["A","B"],"Q02":["B","A"]},
                          {"Q01":{"A":3,"B":0},"Q02":{"A":3,"B":0}},2)
        self.assertEqual(r["cases"],2)
        self.assertAlmostEqual(r["mrr"],.75)
        self.assertIn("held-out expert",r["warning"])
if __name__=="__main__":unittest.main()

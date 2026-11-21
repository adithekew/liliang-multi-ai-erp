import unittest
from research.validation_metrics import evaluate_retrieval, evaluate_bundling, evaluate_agent

class ValidationMetricTests(unittest.TestCase):
    def test_retrieval_requires_judgments_for_topk(self):
        cases=[{"inquiry_id":"I1","ranked_by_method":{"BM25":["A","B"]},"labels":{"A":3}}]
        with self.assertRaisesRegex(ValueError,"expert label"):
            evaluate_retrieval(cases,k=2)
    def test_retrieval_reports_recall_only_for_complete_pool(self):
        cases=[{"inquiry_id":"I1","ranked_by_method":{"BM25":["A","B"]},
                "labels":{"A":3,"B":0,"C":2},"pool_complete":True}]
        r=evaluate_retrieval(cases,k=2)
        self.assertEqual(r["methods"]["BM25"]["recall_eligible_cases"],1)
        self.assertAlmostEqual(r["methods"]["BM25"]["recall_at_k"],0.5)
    def test_association_rules_are_evaluated_on_future_baskets(self):
        train=[["A","B"],["A","B"],["A","C"],["A","B"],["A","B"],["A","B"],["A","C"],["A","B"],["A","B"],["A","B"]]
        test=[["A","B"],["A","C"]]
        r=evaluate_bundling(train,test,k=2)
        self.assertEqual(r["train_baskets"],10)
        self.assertIn("POPULARITY_BASELINE",r["results"])
        self.assertFalse(r["causal_claim"])
    def test_agent_unauthorized_action_is_counted(self):
        r=evaluate_agent([{"tool_call_correct":True,"policy_compliant":False,
            "unauthorized_action_attempted":True,"groundedness_score_1_5":2,"outcome":"FAIL"}])
        self.assertEqual(r["unauthorized_action_attempt_count"],1)
        self.assertEqual(r["policy_compliance_rate"],0)

if __name__=="__main__":unittest.main()

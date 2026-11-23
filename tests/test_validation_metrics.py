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
    def test_unmeasurable_recall_is_null(self):
        case = {"inquiry_id": "Q", "ranked_by_method": {"BM25": ["A"]}, "labels": {"A": 3}}
        result = evaluate_retrieval([case])["methods"]["BM25"]
        self.assertIsNone(result["recall_at_k"])
        self.assertEqual(result["recall_eligible_cases"], 0)

    def test_bundling_hit_rate_counts_each_eligible_antecedent_once(self):
        training = [["A", "B"]] * 10
        result = evaluate_bundling(training, [["A", "A", "B"], ["A"], ["A", "C"]])
        rules = result["results"]["ASSOCIATION_RULES"]
        self.assertEqual(rules["antecedent_cases"], 4)
        self.assertEqual(rules["hit_rate_at_k"], 0.5)

    def test_agent_reads_workbook_boolean_choices(self):
        case = {"tool_call_correct": "FALSE", "policy_compliant": "TRUE",
                "unauthorized_action_attempted": "FALSE"}
        result = evaluate_agent([case])
        self.assertEqual(result["tool_call_accuracy"], 0)
        self.assertEqual(result["policy_compliance_rate"], 1)
        self.assertEqual(result["unauthorized_action_attempt_count"], 0)
        with self.assertRaisesRegex(ValueError, "tool_call_correct"):
            evaluate_agent([{**case, "tool_call_correct": None}])

    def test_agent_unauthorized_action_is_counted(self):
        r=evaluate_agent([{"tool_call_correct":True,"policy_compliant":False,
            "unauthorized_action_attempted":True,"groundedness_score_1_5":2,"outcome":"FAIL"}])
        self.assertEqual(r["unauthorized_action_attempt_count"],1)
        self.assertEqual(r["policy_compliance_rate"],0)

if __name__=="__main__":unittest.main()

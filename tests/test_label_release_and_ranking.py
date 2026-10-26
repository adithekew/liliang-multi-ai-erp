"""Only synthetic CI data. Real Technical A/B files are currently UNFILLED."""
import unittest
from research.label_release import build_release,adjudicate
from research.ranking_evaluation import evaluate

def fixtures(project_count=65):
    pool=[];a=[];b=[]
    for gi in range(project_count):
        qid=f"INQ-AUTHORIZED-{gi:03}"
        project=f"PROJECT-{gi:03}"
        query=f"Flavor compatibility requested for bakery application group {gi}"
        for si in range(6):
            pid=f"PAIR-{gi:03}-{si}"
            sku=f"SKU-{gi:03}-{si}"
            grade=(3 if si<3 else {3:2,4:1,5:0}[si])
            p={"pair_id":pid,"inquiry_id":qid,"project_group":project,
               "query":query,"document":f"Verified product description flavor series {gi} candidate {si} for bakery",
               "sku":sku,"authorization_ref":"AUTH-SYNTHETIC-TEST-ONLY",
               "data_classification":"AUTHORIZED_ANONYMIZED","expert_validated":True}
            pool.append(p)
            base={"pair_id":pid,"inquiry_id":qid,"project_group":project,
                 "sku":sku,"datasheet_reference":f"SYNTH-DATASHEET-{gi:03}-{si}",
                 "label_0_3":str(grade),
                 "rationale":"Synthetic test reviewer explains form flavor and application",
                 "query_anonymized":query}
            a.append(dict(base,reviewer_id="TECHNICAL_A"))
            b.append(dict(base,reviewer_id="TECHNICAL_B"))
    return pool,a,b

class ResearchGateTest(unittest.TestCase):
    def test_valid_human_gate_synthetic_fixture_release_and_metrics(self):
        pool,a,b=fixtures()
        manifest,train,judged=build_release(pool,a,b,[],"c"*64)
        self.assertEqual(manifest["status"],"FROZEN_OFFLINE_RESEARCH_DATASET",
                         manifest["problems"])
        self.assertGreaterEqual(len(train["train"]),50)
        self.assertGreaterEqual(len(train["dev"]),10)
        self.assertGreaterEqual(len(judged["test"]),10)
        self.assertGreaterEqual(manifest["heldout_inquiries"],5)
        self.assertFalse(manifest["model_trained"])
        self.assertFalse(manifest["auto_deploy"])
        # Build synthetic rankings independent of actual ML, to check evaluator.
        grouped={}
        for r in judged["test"]:
            grouped.setdefault(r["query_id"],[]).append(r)
        prediction=[]
        for qid,entries in grouped.items():
            rank=sorted(entries,key=lambda x:-x["relevance_label"])
            prediction.append({"query_id":qid,"ranked_skus":[r["sku"] for r in rank],
                               "retrieval_latency_ms":12.5})
        result=evaluate(judged["test"],prediction)
        self.assertEqual(result["scope"],"ONLY_EXPERT_JUDGED_POOL_NOT_FULL_CATALOG")
        self.assertEqual(result["ndcg_at_5"],1.)
        self.assertEqual(result["mrr_at_5_relevant_queries"],1.)
        self.assertEqual(result["recall_at_5_relevant_queries"],1.)
        self.assertEqual(result["p95_retrieval_latency_ms"],12.5)

    def test_reviewer_disagreement_must_be_adjudicated(self):
        _,a,b=fixtures(1)
        b[0]["label_0_3"]="0"
        with self.assertRaisesRegex(ValueError,"disagreements"):
            adjudicate(a,b,[])
        x={"pair_id":a[0]["pair_id"],"adjudicator_id":"SENIOR-TECHNICAL",
           "datasheet_reference":"REVIEW-DOC-001","label_0_3":"2",
           "rationale":"Synthetic consensus based on signed independent judgement"}
        final,stats=adjudicate(a,b,[x])
        self.assertEqual(stats["disagreements_count"],1)
        self.assertEqual(final[a[0]["pair_id"]]["grade"],2)

    def test_test_leakage_and_unjudged_predictions_rejected(self):
        pool,a,b=fixtures()
        # Normalized query content in two projects and distinct splits is leakage.
        groups={p["project_group"]:p for p in pool}
        from research.label_release import assign_splits
        group_splits=assign_splits((p["project_group"] for p in pool),"liliang-ai02-research-v1")
        first=next(p for p in pool if group_splits[p["project_group"]]=="train")
        other=next(p for p in pool if group_splits[p["project_group"]]=="test")
        for p in pool:
            if p["inquiry_id"]==other["inquiry_id"]:p["query"]=first["query"]
        manifest,_,_=build_release(pool,a,b,[],"a"*64)
        self.assertIn("NORMALIZED_QUERY_TEXT_LEAKAGE",manifest["problems"])
        gold=[{"query_id":"I1","sku":"SKU-A","relevance_label":3,"label_source":"TWO_INDEPENDENT_TECHNICAL_REVIEWERS"},
              {"query_id":"I1","sku":"SKU-B","relevance_label":0,"label_source":"TWO_INDEPENDENT_TECHNICAL_REVIEWERS"}]
        with self.assertRaisesRegex(ValueError,"UNJUDGED"):
            evaluate(gold,[{"query_id":"I1","ranked_skus":["SKU-X","SKU-A"]}])
        with self.assertRaisesRegex(ValueError,"[Dd]uplicate"):
            evaluate(gold,[{"query_id":"I1","ranked_skus":["SKU-A","SKU-A"]}])

if __name__=="__main__":unittest.main()

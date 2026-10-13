import unittest
from research.training_gate import check_training_pairs

def rows(prefix,n):
    return [{"query":f"Sample flavor requirement {prefix} {i} for dairy",
             "document":f"Synthetic example product profile {i%20}",
             "project_group":f"group-{prefix}-{i}",
             "sku":f"SKU-{i%20:03}",
             "relevance_label":3,
             "expert_validated":True,
             "data_classification":"AUTHORIZED_ANONYMIZED"}
            for i in range(n)]

class DomainFineTuneGateTest(unittest.TestCase):
    def test_five_demo_skus_cannot_pass(self):
        tr=rows("train",20)
        dev=rows("dev",10)
        r=check_training_pairs(tr,dev)
        self.assertFalse(r["ready"])
        self.assertIn("INSUFFICIENT_TRAIN_POSITIVES_FOR_PROPOSED_PILOT",r["problems"])
    def test_representative_authorized_pairs_can_pass_engineering_gate(self):
        r=check_training_pairs(rows("train",50),rows("dev",10))
        self.assertTrue(r["ready"],r["problems"])
        self.assertEqual(r["distinct_train_skus"],20)
    def test_dataset_leakage_rejected(self):
        tr=rows("train",50);dev=rows("dev",10)
        dev[0]["query"]=tr[0]["query"]
        dev[1]["project_group"]=tr[1]["project_group"]
        r=check_training_pairs(tr,dev)
        self.assertIn("PROJECT_GROUP_LEAKAGE",r["problems"])
        self.assertIn("QUERY_LEAKAGE_ACROSS_SPLITS",r["problems"])
    def test_unapproved_and_low_grade_rejected(self):
        tr=rows("train",50);dev=rows("dev",10)
        tr[0]["expert_validated"]=False
        tr[1]["relevance_label"]=1
        tr[2]["data_classification"]="SYNTHETIC_PILOT"
        r=check_training_pairs(tr,dev)
        self.assertIn("NOT_EXPERT_VALIDATED_train",r["problems"])
        self.assertIn("NOT_QUALIFIED_POSITIVE_train",r["problems"])
        self.assertIn("SOURCE_NOT_AUTHORIZED_train",r["problems"])
if __name__=="__main__":unittest.main()

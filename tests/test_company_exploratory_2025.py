"""No customer documents in CI. Test June exclusion, provisional baskets and Technical gates."""
import unittest
from research.company_proxy_basket import grouped_rules
from research.monthly_experiment_2025 import experiment
from research.technical_independent_agreement import agreement

class ExploratoryCompanyDataTests(unittest.TestCase):
    def test_june_never_enters_basket_model(self):
        rows=[]
        for i in range(10):
            for sku in ("SKU-A","SKU-B"):
                rows.append({"month_label":"2025-09","manual_sku_review_needed":"FALSE",
                     "basket_proxy_id":f"PX{i:03}","sku_compare_key":sku,"quantity_kg":"1"})
        for i in range(50):
            rows.append({"month_label":"2025-06","manual_sku_review_needed":"FALSE",
                 "basket_proxy_id":f"JUNE{i:03}","sku_compare_key":"SKU-FALSE","quantity_kg":"3"})
        # unanswered SKU codes never enter rules
        rows.append({"month_label":"2025-09","manual_sku_review_needed":"TRUE",
                     "basket_proxy_id":"UNKNOWN","sku_compare_key":"SKU-WRONG","quantity_kg":"1"})
        r=grouped_rules(rows)
        self.assertEqual(r["eligible_group_count"],10)
        self.assertTrue(r["rules"])
        self.assertEqual(r["rules"][0]["source_type"],"USER_ASSUMED_PROXY")
        self.assertFalse(r["rules"][0]["invoice_verified"])
        self.assertNotIn("SKU-FALSE",str(r))

    def test_monthly_training_does_not_use_june_and_preserves_holdout(self):
        data=[]
        for sku in ("SKU-A","SKU-B","SKU-C","SKU-D","SKU-E"):
            for i,m in enumerate(range(7,13)):
                data.append({"month_label":f"2025-{m:02}","sku_compare_key":sku,
                    "quantity_kg":str(10+i+(ord(sku[-1])-65)),"sku_review_needed":"NO"})
            data.append({"month_label":"2025-06","sku_compare_key":sku,
                "quantity_kg":"999999","sku_review_needed":"NO"})
        r=experiment(data)
        self.assertEqual(r["tested_skus"],5)
        self.assertEqual(r["training_examples"],10)
        self.assertEqual(r["holdout_month"],"2025-12")
        self.assertFalse(r["finance_validated"])
        self.assertFalse(r["deployed_to_erp"])

    def test_independent_labels_no_silent_adjudication(self):
        base=lambda grade,reviewer:{
         "pair_id":"PAIR-001","reviewer_id":reviewer,
         "datasheet_reference":"DATASHEET-REFER-001",
         "rationale":"Measured form and flavor compatibility",
         "label_0_3":str(grade),"sku":"SKU-001","inquiry_id":"INQ-1",
         "project_group":"PROJECT-01"}
        s=agreement([base(2,"TECHNICAL_A")],[base(3,"TECHNICAL_B")])
        self.assertEqual(s["status"],"ADJUDICATION_REQUIRED")
        self.assertEqual(s["disagreements_count"],1)
        self.assertFalse(s["labels_finalized"])
        with self.assertRaisesRegex(ValueError,"datasheet"):
            t=base(3,"TECHNICAL_B");t["datasheet_reference"]=""
            agreement([base(3,"TECHNICAL_A")],[t])

if __name__=="__main__":
    unittest.main()

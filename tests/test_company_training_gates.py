"""No company data in CI: synthetic fixtures for documentary and training gates."""
import csv,json,tempfile,unittest
from pathlib import Path
from datetime import date,timedelta
from research.company_sales_audit import evaluate
from research.private_demand_training import read_weekly,run

class CompanyQualityTest(unittest.TestCase):
    def write(self,path,header,rows):
        with open(path,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=header);w.writeheader();w.writerows(rows)

    def test_extracted_monthly_document_stays_preliminary(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            items=root/"items.csv";lines=root/"lines.csv";monthly=root/"monthly.csv";baskets=root/"baskets.csv"
            self.write(items,["basis","month_label","extract_decision","date_granularity"],[
                {"basis":"SALES_LIST","month_label":"2025-01","extract_decision":"PRELIMINARY","date_granularity":"MONTH_ONLY"},
                {"basis":"PAYMENT_DUE_LIST","month_label":"2025-06","extract_decision":"EXCLUDE_JUNE","date_granularity":"MONTH_ONLY"}])
            self.write(lines,["line_id","month_label","basket_validated_order_id","date_granularity","manual_sku_review_needed"],[
                {"line_id":"L001","month_label":"2025-01","basket_validated_order_id":"NO","date_granularity":"MONTH_ONLY","manual_sku_review_needed":"FALSE"}])
            self.write(monthly,["month_label","sku_compare_key","sku_review_needed","date_granularity"],[
                {"month_label":"2025-01","sku_compare_key":"SKU-TEST","sku_review_needed":"NO","date_granularity":"MONTH_ONLY"}])
            self.write(baskets,["basket_proxy_id","confirmed_invoice_id","transaction_date_available","valid_for_association_rule_ground_truth"],[
                {"basket_proxy_id":"PARA-01","confirmed_invoice_id":"NO","transaction_date_available":"NO","valid_for_association_rule_ground_truth":"NO"}])
            r=evaluate(items,lines,monthly,baskets)
            self.assertEqual(r["counts"]["payment_due_rows"],1)
            self.assertEqual(r["counts"]["verified_order_baskets"],0)
            self.assertFalse(r["ready_for_company_model_training"])
            self.assertTrue(r["gates"]["AI03_REAL_BASKET_ASSOCIATIONS"].startswith("BLOCKED"))
            self.assertNotIn("SKU-TEST",json.dumps(r))

    def test_train_requires_24_contiguous_finance_verified_weeks(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            csvpath=root/"series.csv"
            columns=["sku","week_start","qty_kg","source_status","week_complete","source_doc_sha256"]
            start=date(2025,1,6)
            rows=[{"sku":"SKU-SYNTHETIC","week_start":(start+timedelta(weeks=i)).isoformat(),
                   "qty_kg":str(70+i*1.5),"source_status":"FINANCE_VERIFIED",
                   "week_complete":"YES","source_doc_sha256":"a"*64} for i in range(30)]
            self.write(csvpath,columns,rows)
            authorization=root/"approval.pdf";authorization.write_bytes(b"synthetic test document for algorithm only")
            finance=root/"signoff.pdf";finance.write_bytes(b"synthetic test signed record for tests only")
            report=run(csvpath,authorization,finance,root/"secure_out")
            self.assertEqual(report["training_sku_count"],1)
            self.assertFalse(report["automatically_deployed"])
            self.assertFalse(report["scientific_validation"])
            m=report["model_cards"]["SKU-SYNTHETIC"]
            self.assertEqual(m["heldout_weeks"],4)
            self.assertGreater(m["train_examples"],0)
            self.assertTrue((root/"secure_out"/"training_manifest.json").exists())
            rows[0]["source_status"]="PRELIMINARY_COMPANY_SOURCE"
            self.write(csvpath,columns,rows)
            with self.assertRaisesRegex(ValueError,"Unverified"):read_weekly(csvpath)
            rows[0]["source_status"]="FINANCE_VERIFIED"
            rows.pop(10)
            self.write(csvpath,columns,rows)
            with self.assertRaisesRegex(ValueError,"Noncontiguous"):read_weekly(csvpath)

    def test_no_deployment_without_source_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/"unused.csv";source.write_text("not a valid series")
            with self.assertRaisesRegex(ValueError,"Independent"):
                run(source,root/"no-auth",root/"no-finance",root/"out")

if __name__=="__main__":unittest.main()

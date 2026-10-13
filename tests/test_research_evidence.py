import sqlite3
import unittest
from persistence import SCHEMA
from research.evidence import readiness,evaluation,methodology
from research.data_pipeline import clean_catalog,clean_inquiries,grouped_split

def fixture_db():
    db=sqlite3.connect(":memory:")
    db.row_factory=sqlite3.Row
    db.executescript(SCHEMA)
    db.execute("INSERT INTO users(id,email,name,role,hash) VALUES(1,'test@pilot.local','Tester','technical','hash')")
    for n in range(1,6):
        db.execute("INSERT INTO products(id,sku,name,profile,application) VALUES(?,?,?,?,?)",
                   (n,f'FLV-{n}',f'Flavor {n}',f'taste{n}','beverage'))
    db.execute("INSERT INTO inquiries(id,created_by,requirement,customer_ref) VALUES(1,1,'Test flavor','SYNTHETIC')")
    db.execute("INSERT INTO runs(id,inquiry_id,method) VALUES(1,1,'bm25-test')")
    for n in range(1,6):
        db.execute("INSERT INTO candidates(run_id,product_id,rank,score) VALUES(1,?,?,?)",
                   (n,n,6-n))
    db.commit()
    return db

class ExpertEvaluationTests(unittest.TestCase):
    def test_no_label_means_no_accuracy(self):
        db=fixture_db()
        try:
            r=readiness(db)
            self.assertEqual(r["candidate_pairs_total"],5)
            self.assertEqual(r["fully_labelled_runs"],0)
            self.assertEqual(r["scientific_readiness"],"NOT_VALIDATED")
            m=evaluation(db)
            self.assertEqual(m["results"],[])
            self.assertFalse(m["model_comparison_valid"])
        finally: db.close()
    def test_full_labels_generate_exploratory_metrics_only(self):
        db=fixture_db()
        try:
            for n,label in enumerate((3,2,1,0,0),1):
                decision="ACCEPT" if label>=2 else "REJECT"
                db.execute("INSERT INTO reviews(run_id,product_id,reviewer_id,decision,label,note) VALUES(1,?,?,?,?,?)",
                           (n,1,decision,label,"Synthetic review only"))
            db.commit()
            r=readiness(db);e=evaluation(db)
            self.assertEqual(r["fully_labelled_runs"],1)
            self.assertEqual(r["candidate_label_coverage_pct"],100)
            self.assertFalse(r["gates"]["heldout_split_verified"])
            self.assertEqual(e["status"],"EXPLORATORY_ONLY")
            self.assertFalse(e["model_comparison_valid"])
            self.assertEqual(e["results"][0]["exploratory_mean_ndcg_at_5"],1.0)
            self.assertEqual(e["results"][0]["exploratory_mrr_at_5"],1.0)
        finally: db.close()
    def test_decision_label_conflict_excluded(self):
        db=fixture_db()
        try:
            for n in range(1,6):
                db.execute("INSERT INTO reviews(run_id,product_id,reviewer_id,decision,label,note) VALUES(1,?,1,'ACCEPT',0,'Synthetic')",(n,))
            db.commit()
            self.assertEqual(readiness(db)["fully_labelled_runs"],0)
            self.assertEqual(readiness(db)["decision_label_conflicts"],1)
            self.assertEqual(evaluation(db)["results"],[])
        finally: db.close()
    def test_training_status_untrained(self):
        d=methodology()
        self.assertEqual(d["training_status"],"PRETRAINED_EXTERNAL_MODEL_ONLY_NO_LILIANG_FINE_TUNING")
        self.assertTrue(all(not x["trained_on_company_data"] for x in d["models"]))

class CleaningTest(unittest.TestCase):
    def test_catalog_missing_and_duplicate_quarantined(self):
        rows=[{"sku":"FLV-123","name":"Mango Flavor","profile":"mangga","application":"minuman","data_classification":"SYNTHETIC_PILOT"},
              {"sku":"FLV-123","name":"Mango duplicate","profile":"mangga","application":"minuman","data_classification":"SYNTHETIC_PILOT"},
              {"sku":"FLV-124","name":"","profile":"vanila","application":"bakery","data_classification":"SYNTHETIC_PILOT"}]
        d=clean_catalog(rows)
        self.assertEqual(d["quality"]["accepted"],1)
        self.assertEqual(d["quality"]["quarantined"],2)
        self.assertEqual(d["clean"][0]["profile"],"mango")
        self.assertEqual(d["clean"][0]["halal_status"],"UNKNOWN")
    def test_inquiry_normalization_pii_duplicate(self):
        items=[
          {"requirement":"BUTUH mangga untuk minuman","project_group":"A","created_at":"2026-01-01","data_classification":"SYNTHETIC_EXAMPLES_ONLY"},
          {"requirement":"butuh mango untuk beverage","project_group":"B","created_at":"2026-01-02","data_classification":"SYNTHETIC_EXAMPLES_ONLY"},
          {"requirement":"Call me +6281234567890 for mango flavor","project_group":"C","created_at":"2026-01-03","data_classification":"SYNTHETIC_EXAMPLES_ONLY"}]
        out=clean_inquiries(items)
        self.assertEqual(out["quality"]["accepted"],1)
        self.assertEqual(out["quality"]["issue_counts"]["DUPLICATE_NORMALIZED_INQUIRY"],1)
        self.assertEqual(out["quality"]["issue_counts"]["POTENTIAL_PII"],1)
    def test_group_split_without_overlap(self):
        rows=[{"inquiry_fingerprint":str(i),"project_group":f"project-{i//2}","created_at":f"2026-01-{i//2+1:02d}"} for i in range(20)]
        x=grouped_split(rows)
        self.assertEqual(sum(x["record_counts"].values()),20)
        ids=[{r["project_group"] for r in x["splits"][k]} for k in ("train","dev","test")]
        self.assertFalse(ids[0]&ids[1]);self.assertFalse(ids[0]&ids[2]);self.assertFalse(ids[1]&ids[2])
    def test_unauthorized_real_records_never_cleaned(self):
        p=clean_catalog([{"sku":"SKU-001","name":"Commercial flavor","profile":"apple","application":"bakery","data_classification":"REAL_COMPANY"}])
        self.assertEqual(p["quality"]["accepted"],0)
        self.assertIn("UNAUTHORIZED_SOURCE_NOT_ALLOWED",p["quality"]["issue_counts"])
if __name__=="__main__":unittest.main()

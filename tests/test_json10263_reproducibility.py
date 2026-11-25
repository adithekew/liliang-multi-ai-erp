import csv
import tempfile
import unittest
from pathlib import Path
from research.json10263_reproducibility import metric,check_rrf,read_gold,bootstrap,read_ranks
class TestJSON10263Audit(unittest.TestCase):
    def test_grade2_not_hit(self):
        d={f"S{i}":(i,20-i) for i in range(1,21)}
        g={s:0 for s in d};g["S1"]=2;g["S3"]=3
        self.assertAlmostEqual(metric(d,g)[1],1/3)
    def test_missing_judgment_rejected(self):
        d={f"S{i}":(i,20-i) for i in range(1,21)}
        with self.assertRaises(ValueError):metric(d,{"S1":3})
    def test_zero_score_competition_capped(self):
        b={f"S{i}":(i,10. if i==1 else 0.) for i in range(1,21)}
        d={f"S{i}":(i,1/i) for i in range(1,21)}
        r={f"S{i}":(i,1/(60+(1 if i==1 else 15))+1/(60+i)) for i in range(1,21)}
        self.assertEqual(check_rrf({("RQ041","BM25"):b,("RQ041","MiniLM"):d,("RQ041","RRF"):r})["mismatches_6_decimal"],0)
    def test_bootstrap_determinism(self):
        self.assertEqual(bootstrap([0.1,0.0,-0.2],seed=20261029),
                         bootstrap([0.1,0.0,-0.2],seed=20261029))
    def test_reject_201_labels(self):
        rows=[{"inquiry_id":f"RQ{i:03d}","sku_id":f"S{j:02d}","grade":"0"}
              for i in range(41,51) for j in range(1,21)]
        rows.append({"inquiry_id":"EXTRA","sku_id":"S01","grade":"0"})
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"labels.csv"
            with p.open("w",newline="",encoding="utf-8") as out:
                w=csv.DictWriter(out,fieldnames=["inquiry_id","sku_id","grade"])
                w.writeheader();w.writerows(rows)
            with self.assertRaisesRegex(ValueError,"Exactly 200"):
                read_gold(p,{})
    def test_reject_incomplete_3000_ranking_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"ranks.csv"
            with p.open("w",newline="",encoding="utf-8") as out:
                w=csv.DictWriter(out,fieldnames=["inquiry_id","sku_id","method","rank","score"])
                w.writeheader()
                w.writerow({"inquiry_id":"RQ041","sku_id":"S01","method":"BM25","rank":1,"score":1.})
            with self.assertRaisesRegex(ValueError,"Expected 50 inquiries"):
                read_ranks(p)
if __name__=="__main__":unittest.main()

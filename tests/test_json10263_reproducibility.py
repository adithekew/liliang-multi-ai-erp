import unittest
from research.json10263_reproducibility import metric,check_rrf
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
if __name__=="__main__":unittest.main()

"""Schema/identity checks only; no real-company records or model downloads."""
import csv
import tempfile
import unittest
from pathlib import Path
from research.json10263_encoder_replay import author_aware_rankings

class TestAuthorCSVCompat(unittest.TestCase):
    def test_original_author_ranking_3000_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            filename=Path(directory)/"rankings.csv"
            cols=["Inquiry_ID","SKU","Split","Method","Rank","Score","Run_ID","Catalog_Version_Hash"]
            with filename.open("w",encoding="utf-8",newline="") as fp:
                writer=csv.DictWriter(fp,fieldnames=cols)
                writer.writeheader()
                for n in range(1,51):
                    qid=f"RQ{n:03d}"
                    split="train" if n<=30 else "dev" if n<=40 else "test"
                    for method in ("BM25","MiniLM","RRF"):
                        for rank in range(1,21):
                            writer.writerow(dict(Inquiry_ID=qid,SKU=f"S{rank:03d}",Split=split,
                              Method=method,Rank=rank,Score=f"{21-rank:.5f}",
                              Run_ID="TEST-NOT-REAL",Catalog_Version_Hash="SYNTHETIC"))
            groups,records=author_aware_rankings(filename)
            self.assertEqual(records,3000)
            self.assertEqual(len(groups),150)
            self.assertEqual(len(groups[("RQ041","MiniLM")]),20)
if __name__=="__main__": unittest.main()

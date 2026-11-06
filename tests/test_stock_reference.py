"""Read-only catalog-stock import data contract: no false physical availability."""
import os, tempfile, unittest, subprocess, shutil
from pathlib import Path
from fastapi.testclient import TestClient
from app import app, ADMIN_EMAIL, ADMIN_PASSWORD
from persistence import connect
from catalog_stock_reference import SOURCE_SHA, STOCK_PAGE

class CatalogStockReferenceTests(unittest.TestCase):
    def test_reference_in_db_does_not_change_real_stock_or_virtual_sample_stock(self):
        before=os.environ.get("DATABASE_PATH")
        with tempfile.TemporaryDirectory(prefix="stock_reference_ci_") as temp:
            os.environ["DATABASE_PATH"]=str(Path(temp)/"db.sqlite")
            try:
                with TestClient(app) as client:
                    self.assertEqual(client.get("/v1/catalog/stock-reference").status_code,401)
                    login=client.post("/v1/auth/login",json={"email":ADMIN_EMAIL,"password":ADMIN_PASSWORD})
                    self.assertEqual(login.status_code,200,login.text)
                    h={"Authorization":"Bearer "+login.json()["access_token"]}
                    initial=client.get("/v1/catalog/stock-reference",headers=h)
                    self.assertEqual(initial.status_code,200,initial.text)
                    self.assertEqual(initial.json()["sku_count"],0)
                    self.assertFalse(initial.json()["dispatch_eligible"])
                    with connect() as db:
                        item=db.execute("SELECT sku,stock FROM products ORDER BY sku LIMIT 1").fetchone()
                        sku=item["sku"];real_stock=item["stock"]
                        db.execute("""INSERT INTO catalog_stock_import_batches
                          (source_sha256,filename,source_label,source_generated_at,row_count,recorded_sum,
                          units_status,verification_status,imported_at)
                          VALUES(?,?,?,?,1,321,'UNSPECIFIED','UNVERIFIED',?)""",
                          (SOURCE_SHA,"test-fixture.csv","SUPPLIER_CATALOG_PDF_UNVERIFIED","2026-10-30T03:28:46Z","2026-11-06T04:00:00Z"))
                        db.execute("""INSERT INTO catalog_stock_reference
                          (sku,reported_stock,unit,source_ref,source_sha256,pdf_page,pdf_row,verification_status,imported_at)
                          VALUES(?,321,'UNSPECIFIED','CATALOG-PDF-UNVERIFIED',?,1,2,'UNVERIFIED',?)""",
                          (sku,SOURCE_SHA,"2026-11-06T04:00:00Z"))
                    result=client.get("/v1/catalog/stock-reference",headers=h)
                    self.assertEqual(result.status_code,200,result.text)
                    data=result.json()
                    self.assertEqual(data["sku_count"],1)
                    self.assertEqual(float(data["reported_total"]),321)
                    self.assertEqual(data["unverified_skus"],1)
                    self.assertEqual(data["rows"][0]["sku"],sku)
                    self.assertEqual(data["rows"][0]["unit"],"UNSPECIFIED")
                    self.assertEqual(data["rows"][0]["legacy_product_stock"],real_stock)
                    self.assertEqual(data["stock_status"],"REFERENCE_ONLY_NOT_PHYSICAL")
                    self.assertFalse(data["changes_company_stock"])
                    self.assertFalse(data["dispatch_eligible"])
                    no_match=client.get("/v1/catalog/stock-reference?search=not-existing",headers=h)
                    self.assertEqual(no_match.json()["total_matching"],0)
                    html=client.get("/stock/reference")
                    self.assertEqual(html.status_code,200)
                    self.assertIn("Belum diverifikasi",html.text)
                    with connect() as db:
                        self.assertEqual(db.execute("SELECT stock FROM products WHERE sku=?",(sku,)).fetchone()["stock"],real_stock)
                        self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM sample_uat_balances").fetchone()["n"],0)
            finally:
                if before is None:os.environ.pop("DATABASE_PATH",None)
                else:os.environ["DATABASE_PATH"]=before

    def test_stock_reference_page_javascript(self):
        if not shutil.which("node"):self.skipTest("Node unavailable")
        js=STOCK_PAGE.split("<script>",1)[1].split("</script>",1)[0]
        with tempfile.TemporaryDirectory(prefix="reference_js_") as temp:
            script=Path(temp)/"stock.js"
            script.write_text(js,encoding="utf-8")
            check=subprocess.run(["node","--check",str(script)],capture_output=True,text=True)
            self.assertEqual(check.returncode,0,check.stderr)

if __name__=="__main__":unittest.main()

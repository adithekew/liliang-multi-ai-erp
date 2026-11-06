"""Physical inventory package UoM and updates must stay coherent with ERP stock."""
import os, tempfile, unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app import app, ADMIN_EMAIL, ADMIN_PASSWORD
from persistence import connect
from catalog_stock_reference import SOURCE_SHA

class PhysicalStockPackagingTests(unittest.TestCase):
    def test_package_uom_and_live_product_stock_sync(self):
        previous=os.environ.get("DATABASE_PATH")
        try:
            with tempfile.TemporaryDirectory(prefix="packaging_ci_") as td:
                os.environ["DATABASE_PATH"]=str(Path(td)/"pilot.db")
                with TestClient(app) as c:
                    login=c.post("/v1/auth/login",json={"email":ADMIN_EMAIL,"password":ADMIN_PASSWORD})
                    self.assertEqual(login.status_code,200,login.text)
                    h={"Authorization":"Bearer "+login.json()["access_token"]}
                    with connect() as db:
                        seed=[dict(row) for row in db.execute("SELECT id,sku FROM products ORDER BY sku LIMIT 4")]
                        self.assertEqual(len(seed),4)
                        types=[
                            ("Powder","unit",300,"gram","UNIT_DEFINED"),
                            ("Paste","botol",200,"ml","UNIT_DEFINED"),
                            ("Liquid","dirigen",500,"ml","UNIT_DEFINED"),
                            ("Oil","UNSPECIFIED",None,None,"UOM_PENDING"),
                        ]
                        db.execute("""INSERT INTO catalog_stock_import_batches
                            (source_sha256,filename,source_label,source_generated_at,
                            row_count,recorded_sum,units_status,verification_status,imported_at)
                            VALUES(?,?,?,NULL,4,110,'USER_CONFIRMED_PHYSICAL',
                            'USER_CONFIRMED_PHYSICAL','2026-11-06')""",
                            (SOURCE_SHA,"research-file.csv","CATALOG-PDF-UNVERIFIED"))
                        for i,(item,rule) in enumerate(zip(seed,types)):
                            name,uom,content,content_unit,uom_status=rule
                            qty=20+i*5
                            db.execute("UPDATE products SET stock=? WHERE id=?",(qty,item["id"]))
                            db.execute("""INSERT INTO catalog_product_details
                                (sku,product_type,application_raw,composition_raw,source_page,source_number,source_sha256,batch_id)
                                VALUES(?,?,?,'',1,1,?,'UAT')""",
                                (item["sku"],name,"Research test",SOURCE_SHA))
                            db.execute("""INSERT INTO catalog_stock_reference
                                (sku,reported_stock,unit,source_ref,source_sha256,pdf_page,pdf_row,
                                verification_status,imported_at)
                                VALUES(?,?,?,'CATALOG-PDF-UNVERIFIED',?,1,1,'USER_CONFIRMED_PHYSICAL','2026-11-06')""",
                                (item["sku"],qty,uom,SOURCE_SHA))
                            db.execute("""INSERT INTO physical_inventory_stock
                                (sku,product_type,qty_packages,package_uom,package_content,content_uom,
                                dispatch_uom_status,confirmation_status,source_sha256,confirmed_at)
                                VALUES(?,?,?,?,?,? ,?,'USER_CONFIRMED_PHYSICAL',?,'2026-11-06')""",
                                (item["sku"],name,qty,uom,content,content_unit,uom_status,SOURCE_SHA))
                    response=c.get("/v1/catalog/stock-reference",headers=h)
                    self.assertEqual(response.status_code,200,response.text)
                    data=response.json()
                    self.assertEqual(data["physical_confirmed_skus"],4)
                    self.assertEqual(data["physical_uom_defined_skus"],3)
                    self.assertEqual(data["physical_uom_pending_skus"],1)
                    self.assertEqual(data["stock_status"],"USER_CONFIRMED_PHYSICAL")
                    self.assertFalse(data["dispatch_eligible"]) # UAT dispatch remains virtual.
                    items={x["sku"]:x for x in data["rows"]}
                    for item,rule in zip(seed,types):
                        r=items[item["sku"]]
                        self.assertEqual(r["package_uom"],rule[1])
                        self.assertEqual(r["package_content"],rule[2])
                        self.assertEqual(r["content_uom"],rule[3])
                        self.assertEqual(r["dispatch_uom_status"],rule[4])
                    cat=c.get("/v1/catalog/products",headers=h).json()
                    self.assertTrue(any(x["package_uom"]=="dirigen" for x in cat["items"]))
                    pid=seed[0]["id"]
                    bad=c.patch(f"/v1/products/{pid}/stock",headers=h,json={"stock_qty":10.25})
                    self.assertEqual(bad.status_code,422)
                    fixed=c.patch(f"/v1/products/{pid}/stock",headers=h,json={"stock_qty":10})
                    self.assertEqual(fixed.status_code,200,fixed.text)
                    with connect() as db:
                        sku=seed[0]["sku"]
                        physical=db.execute("SELECT qty_packages FROM physical_inventory_stock WHERE sku=?",(sku,)).fetchone()
                        stock=db.execute("SELECT stock FROM products WHERE sku=?",(sku,)).fetchone()
                        self.assertEqual(float(physical["qty_packages"]),10)
                        self.assertEqual(float(stock["stock"]),10)
                        self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM sample_uat_movements").fetchone()["n"],0)
        finally:
            if previous is None:os.environ.pop("DATABASE_PATH",None)
            else:os.environ["DATABASE_PATH"]=previous

if __name__=="__main__":unittest.main()

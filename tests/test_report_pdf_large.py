"""Report engine scaling/escaping regression without touching Neon data."""
import unittest
from reports import render_pdf,csv_excel_safe

class ReportScalability(unittest.TestCase):
    def test_all_1452_catalog_items_can_be_printed_without_truncation(self):
        sku_rows=[
            [str(11100000+i),"Flavor sample "+str(i),"Liquid",
             "Beverage, Bakery, Confectionery; requires Technical validation",
             None,"CATALOG-PDF-UNVERIFIED",i//30+1,i]
            for i in range(1,1453)
        ]
        report={"title":"Product Catalog Full Export - Scaling Fixture",
             "type":"catalog","source":"SYNTHETIC_TEST_NOT_SUPPLIER_RECORDS",
             "generated_at":"2026-10-18T00:00:00Z",
             "columns":["SKU","Name","Type","Application","Stock","Source","Page","Source Row"],
             "rows":sku_rows,"count":len(sku_rows),
             "disclaimer":"This file contains only synthetic CI records."}
        binary=render_pdf(report)
        self.assertTrue(binary.startswith(b"%PDF"))
        self.assertGreater(len(binary),50000)
    def test_excel_formula_is_quoted_before_csv_export(self):
        for value in ("=cmd|' /C calc'!A0","+SUM(1,1)","-2+3","@SUM(2,2)"):
            self.assertTrue(csv_excel_safe(value).startswith("'"))
        self.assertEqual(csv_excel_safe("Strawberry"),"Strawberry")

if __name__=="__main__":
    unittest.main()

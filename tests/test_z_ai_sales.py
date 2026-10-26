"""No company records: disposable database tests for AI03/AI04 fact pipelines."""
import os
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
from fastapi.testclient import TestClient

from app import app,ADMIN_EMAIL,ADMIN_PASSWORD
from persistence import connect

class SalesFactAITests(unittest.TestCase):
    def test_gated_real_company_facts_and_demo_preflight(self):
        previous=os.environ.get("DATABASE_PATH")
        with tempfile.TemporaryDirectory(prefix="liliang_ai_facts_ci_") as tmp:
            os.environ["DATABASE_PATH"]=str(Path(tmp)/"test.db")
            try:
                with TestClient(app) as c:
                    login=c.post("/v1/auth/login",json={"email":ADMIN_EMAIL,"password":ADMIN_PASSWORD})
                    self.assertEqual(login.status_code,200,login.text)
                    headers={"Authorization":"Bearer "+login.json()["access_token"]}
                    ready=c.get("/v1/ai/demo-readiness",headers=headers)
                    self.assertEqual(ready.status_code,200,ready.text)
                    self.assertTrue(ready.json()["demo_preflight_pass"])
                    self.assertFalse(ready.json()["company_ai_scientifically_validated"])
                    before=c.get("/v1/ai/sales-readiness",headers=headers).json()
                    self.assertEqual(before["stored_order_count"],0)
                    self.assertFalse(before["bundling_ready"])
                    bundling=c.get("/v1/ai/bundling-company",headers=headers).json()
                    self.assertEqual(bundling["status"],"NOT_READY")
                    self.assertEqual(bundling["rules"],[])
                    forecast=c.get("/v1/ai/forecast-company?sku=FLV-STRAW-01",headers=headers).json()
                    self.assertEqual(forecast["status"],"NOT_READY")
                    self.assertEqual(c.get("/v1/ai/forecast?sku=FLV-STRAW-01",headers=headers).status_code,200)
                    # A company-attested import requires an explicit documentary source.
                    invalid=c.post("/v1/admin/ai-sales-facts/import",headers=headers,json={
                        "confirmation":"IMPORT COMPANY ATTESTED SALES FACTS",
                        "source_document_ref":"DOC-2026-001","source_authorized":True,
                        "orders":[{"order_ref":"SRC-TEST-1","order_date":"2026-01-05",
                             "status":"FULFILLED","lines":[{"sku":"NOT-IN-CATALOG","qty":3,"unit":"KG"}]}]})
                    self.assertEqual(invalid.status_code,422)
                    with connect() as db:
                        self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM ai_sales_orders").fetchone()["n"],0)
                    d=date(2026,1,5)
                    orders=[]
                    for i in range(10):
                        orders.append({"order_ref":f"DOCTEST-{i:03d}",
                            "order_date":(d+timedelta(weeks=i)).isoformat(),
                            "status":"FULFILLED",
                            "lines":[{"sku":"FLV-STRAW-01","qty":40+i,"unit":"KG"},
                                     {"sku":"FLV-VANI-02","qty":20+i,"unit":"KG"}]})
                    body={"confirmation":"IMPORT COMPANY ATTESTED SALES FACTS",
                          "source_document_ref":"FIN-REGISTER-2026-001",
                          "source_authorized":True,"orders":orders}
                    added=c.post("/v1/admin/ai-sales-facts/import",headers=headers,json=body)
                    self.assertEqual(added.status_code,200,added.text)
                    self.assertEqual(added.json()["orders"],10)
                    duplicate=c.post("/v1/admin/ai-sales-facts/import",headers=headers,json=body)
                    self.assertEqual(duplicate.status_code,409)
                    summary=c.get("/v1/ai/sales-readiness",headers=headers).json()
                    self.assertEqual(summary["stored_order_count"],10)
                    self.assertTrue(summary["bundling_ready"])
                    self.assertGreaterEqual(summary["forecast_ready_sku_count"],2)
                    rules=c.get("/v1/ai/bundling-company",headers=headers).json()
                    self.assertEqual(rules["basket_count"],10)
                    self.assertEqual(rules["status"],"COMPANY_FACTS_ATTESTED_NOT_SCIENTIFICALLY_VALIDATED")
                    self.assertEqual(rules["rules"][0]["confidence"],1)
                    pred=c.get("/v1/ai/forecast-company?sku=FLV-STRAW-01&horizon=4",headers=headers)
                    self.assertEqual(pred.status_code,200,pred.text)
                    self.assertEqual(pred.json()["status"],"COMPANY_FACTS_ATTESTED_NOT_SCIENTIFICALLY_VALIDATED")
                    self.assertEqual(len(pred.json()["forecast"]),4)
                    for kind in ("ai_sales_facts","ai_bundling_company","ai_forecast_company"):
                        output=c.get("/v1/reports/"+kind+"?format=json",headers=headers)
                        self.assertEqual(output.status_code,200,(kind,output.text[:600]))
                        self.assertGreater(len(output.json()["rows"]),0)
                    # Same endpoint must not imply training success merely because sales exist.
                    again=c.get("/v1/ai/demo-readiness",headers=headers).json()
                    self.assertFalse(again["company_ai_scientifically_validated"])
                    # Missing recent weeks must not be silently interpreted as 0.
                    missing=c.get("/v1/ai/forecast-company?sku=FLV-MANG-03",headers=headers)
                    self.assertEqual(missing.json()["status"],"NOT_READY")
            finally:
                if previous is None:os.environ.pop("DATABASE_PATH",None)
                else:os.environ["DATABASE_PATH"]=previous

if __name__=="__main__":
    unittest.main()

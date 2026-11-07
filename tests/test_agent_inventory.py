"""Test Agent read-only inventory, RBAC, no external data transfer or stock mutations."""
import os
import asyncio
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

# Disposable credentials for local CI only; must be set before importing app.
os.environ.setdefault("APP_ENV","pilot")
os.environ.setdefault("ADMIN_EMAIL","admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD","ci-unique-demo-12345")
os.environ.setdefault("SECRET_KEY","CI-only-strong-nonproduction-signing-key-0123456789")

from fastapi.testclient import TestClient
from app import app, ADMIN_EMAIL, ADMIN_PASSWORD
from persistence import connect
from agent_dashboard_ui import PAGE


class AgentLocalInventoryTests(unittest.TestCase):
    def test_pydantic_agent_instrumentation_reports_actual_four_tools(self):
        """No external Groq request; verifies instrumentation only."""
        import pydantic_ai
        from agent_pilot import groq_explain, snapshot
        class FakeAgent:
            def __init__(self,*args,**kwargs):
                self.called=[]
            def tool(self,fn):
                self.called.append(fn)
                return fn
            async def run(self,*args,**kwargs):
                for tool in self.called:
                    tool(None)
                return SimpleNamespace(output="Empat fungsi AI berhasil dipanggil")
        with patch.object(pydantic_ai,"Agent",FakeAgent):
            got=asyncio.run(groq_explain(snapshot("STRAWBERRY_DAIRY")))
        self.assertEqual(got["tool_calls"],["AI-01","AI-02","AI-03","AI-04"])
        self.assertTrue(got["all_four_tools_called"])
        self.assertIn("Empat fungsi",got["explanation"])

    def test_real_catalog_preview_and_inventory_are_read_only(self):
        old=os.environ.get("DATABASE_PATH")
        old_external=os.environ.get("AI_AGENT_EXTERNAL_ENABLED")
        try:
            os.environ["AI_AGENT_EXTERNAL_ENABLED"]="false"
            with tempfile.TemporaryDirectory(prefix="liliang_agent_stock_ci_") as folder:
                os.environ["DATABASE_PATH"]=str(Path(folder)/"test.db")
                with TestClient(app) as client:
                    response=client.post("/v1/agent/catalog-preview",json={"case_id":"STRAWBERRY_DAIRY"})
                    self.assertEqual(response.status_code,401)
                    login=client.post("/v1/auth/login",json={"email":ADMIN_EMAIL,"password":ADMIN_PASSWORD})
                    self.assertEqual(login.status_code,200,login.text)
                    header={"Authorization":"Bearer "+login.json()["access_token"]}
                    with connect() as db:
                        product=db.execute("SELECT sku,stock FROM products ORDER BY sku LIMIT 1").fetchone()
                        sku=product["sku"];stock=product["stock"]
                        db.execute("""INSERT INTO physical_inventory_stock
                            (sku,product_type,qty_packages,package_uom,package_content,
                             content_uom,dispatch_uom_status,confirmation_status,
                             source_sha256,confirmed_at)
                            VALUES(?, 'Powder', 11, 'unit', 300, 'gram',
                                   'UNIT_DEFINED','USER_CONFIRMED_PHYSICAL','CI_TEST','2026-11-07')""",(sku,))
                        before={table:db.execute("SELECT COUNT(*) AS n FROM "+table).fetchone()["n"]
                                for table in ("products","inquiries","runs","candidates",
                                              "reviews","sample_uat_movements")}
                    with patch("agent_pilot.groq_explain",side_effect=AssertionError("Groq must not be called")):
                        result=client.post("/v1/agent/catalog-preview",
                            json={"case_id":"STRAWBERRY_DAIRY"},headers=header)
                        self.assertEqual(result.status_code,200,result.text)
                        data=result.json()
                        self.assertEqual(data["ranker"],"BM25_CATALOG_BASELINE")
                        self.assertFalse(data["company_data_sent_to_groq"])
                        self.assertFalse(data["database_mutated"])
                        self.assertTrue(data["catalog_rows_considered"]>=5)
                        self.assertFalse(any(item["technical_fit_verified"] for item in data["candidates"]))
                        stock_result=client.get("/v1/agent/stock/"+sku,headers=header)
                        self.assertEqual(stock_result.status_code,200,stock_result.text)
                        self.assertEqual(stock_result.json()["stock_packages"],11)
                        self.assertEqual(stock_result.json()["pack_size"],300)
                        self.assertEqual(stock_result.json()["package_uom"],"unit")
                        self.assertFalse(stock_result.json()["company_data_sent_to_groq"])
                        readiness=client.get("/v1/agent/readiness",headers=header)
                        self.assertEqual(readiness.status_code,200,readiness.text)
                        self.assertTrue(readiness.json()["baseline_functional_checks_passed"])
                        self.assertEqual(readiness.json()["physical_stock_skus"],1)
                        self.assertFalse(readiness.json()["remote_inference_checked"])
                    self.assertEqual(client.get("/v1/agent/stock/DOES-NOT-EXIST",headers=header).status_code,404)
                    self.assertEqual(client.post("/v1/agent/catalog-preview",json={
                        "case_id":"PRIVATE_REAL_CUSTOMER"},headers=header).status_code,422)
                    page=client.get("/ai/agent-pilot")
                    self.assertEqual(page.status_code,200)
                    self.assertIn("Analisis Kandidat & Ketersediaan Stok ERP",page.text)
                    self.assertIn("tidak mengirim produk, SKU, atau stok ke Groq",page.text)
                    with connect() as db:
                        for table,n in before.items():
                            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM "+table).fetchone()["n"],n,table)
                        self.assertEqual(db.execute("SELECT stock FROM products WHERE sku=?",(sku,)).fetchone()["stock"],stock)
                        self.assertEqual(float(db.execute("SELECT qty_packages FROM physical_inventory_stock WHERE sku=?",(sku,)).fetchone()["qty_packages"]),11)
        finally:
            if old is None:os.environ.pop("DATABASE_PATH",None)
            else:os.environ["DATABASE_PATH"]=old
            if old_external is None:os.environ.pop("AI_AGENT_EXTERNAL_ENABLED",None)
            else:os.environ["AI_AGENT_EXTERNAL_ENABLED"]=old_external

    def test_gudang_cannot_request_agent_stock_or_catalog_data(self):
        old=os.environ.get("DATABASE_PATH")
        try:
            with tempfile.TemporaryDirectory(prefix="agent_stock_roles_") as folder:
                os.environ["DATABASE_PATH"]=str(Path(folder)/"ci.db")
                with TestClient(app) as client:
                    login=client.post("/v1/auth/login",json={"email":ADMIN_EMAIL,"password":ADMIN_PASSWORD})
                    header={"Authorization":"Bearer "+login.json()["access_token"]}
                    created=client.post("/v1/users",headers=header,json={
                        "name":"Warehouse Test","email":"gudang.inventory@example.local",
                        "password":"ci-warehouse-password-only","role":"gudang"})
                    self.assertEqual(created.status_code,201,created.text)
                    wh=client.post("/v1/auth/login",json={
                        "email":"gudang.inventory@example.local","password":"ci-warehouse-password-only"})
                    self.assertEqual(wh.status_code,200,wh.text)
                    h={"Authorization":"Bearer "+wh.json()["access_token"]}
                    self.assertEqual(client.get("/v1/agent/readiness",headers=h).status_code,403)
                    self.assertEqual(client.post("/v1/agent/catalog-preview",json={
                        "case_id":"STRAWBERRY_DAIRY"},headers=h).status_code,403)
                    self.assertEqual(client.get("/v1/agent/stock/FLV-STRAW-01",headers=h).status_code,403)
        finally:
            if old is None:os.environ.pop("DATABASE_PATH",None)
            else:os.environ["DATABASE_PATH"]=old


if __name__=="__main__":
    unittest.main()

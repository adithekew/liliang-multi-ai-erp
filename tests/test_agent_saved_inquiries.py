"""End-to-end read-only Sales Inquiry Intelligence Advisor acceptance tests."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV","pilot")
os.environ.setdefault("ADMIN_EMAIL","admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD","ci-unique-demo-12345")
os.environ.setdefault("SECRET_KEY","CI-only-strong-nonproduction-signing-key-0123456789")

from app import app, ADMIN_EMAIL, ADMIN_PASSWORD
from persistence import connect
from agent_inquiry_ui import PAGE


class SavedInquiryAdvisorTests(unittest.TestCase):
    def test_sales_to_manager_advice_no_write_and_latest_run(self):
        old=os.environ.get("DATABASE_PATH")
        try:
            with tempfile.TemporaryDirectory(prefix="saved_advisor_ci_") as folder:
                os.environ["DATABASE_PATH"]=str(Path(folder)/"test.db")
                with TestClient(app) as client:
                    def login(email,password):
                        r=client.post("/v1/auth/login",json={"email":email,"password":password})
                        self.assertEqual(r.status_code,200,r.text)
                        return {"Authorization":"Bearer "+r.json()["access_token"]}
                    admin=login(ADMIN_EMAIL,ADMIN_PASSWORD)
                    people={}
                    for role in ("sales","technical","manager","gudang"):
                        email=role+".advisory@uat.local"
                        pw="ci-saved-advisory-12345"
                        created=client.post("/v1/users",json={
                            "name":"UAT "+role,"email":email,"password":pw,"role":role
                        },headers=admin)
                        self.assertEqual(created.status_code,201,created.text)
                        people[role]=login(email,pw)
                    sales2="sales2.advisory@uat.local"
                    other=client.post("/v1/users",json={"name":"UAT Sales Two",
                        "email":sales2,"password":"ci-second-sales-12345","role":"sales"},headers=admin)
                    self.assertEqual(other.status_code,201,other.text)
                    other_sales=login(sales2,"ci-second-sales-12345")
                    self.assertEqual(client.get("/v1/agent/inquiries").status_code,401)
                    self.assertEqual(client.get("/v1/agent/inquiry/1/advice").status_code,401)
                    self.assertEqual(client.get("/v1/agent/inquiries",headers=people["gudang"]).status_code,403)
                    request=client.post("/v1/inquiries",headers=people["sales"],json={
                        "customer_ref":"UAT-SALES-123",
                        "requirement":"Butuh strawberry flavor untuk minuman susu dairy"
                    })
                    self.assertEqual(request.status_code,201,request.text)
                    iid=request.json()["id"]
                    self.assertEqual(client.get(f"/v1/agent/inquiry/{iid}/advice",headers=other_sales).status_code,403)
                    self.assertEqual(client.get(f"/v1/agent/inquiry/{iid}/advice",headers=people["gudang"]).status_code,403)
                    listing=client.get("/v1/agent/inquiries",headers=people["sales"]).json()
                    self.assertIn(iid,[x["id"] for x in listing["rows"]])
                    self.assertEqual(client.get("/v1/agent/inquiries",headers=other_sales).json()["rows"],[])
                    with patch("agent_pilot.groq_explain",side_effect=AssertionError("ERP data must never call Groq")):
                        fresh=client.get(f"/v1/agent/inquiry/{iid}/advice",headers=people["sales"])
                        self.assertEqual(fresh.status_code,200,fresh.text)
                        self.assertEqual(fresh.json()["candidate_count"],0)
                        self.assertEqual(fresh.json()["next_actor"],"SALES")
                        self.assertIsNone(fresh.json()["latest_run_id"])
                        self.assertEqual(fresh.json()["attributes"]["flavor"],"strawberry")
                    matched=client.post(f"/v1/inquiries/{iid}/match",headers=people["sales"])
                    self.assertEqual(matched.status_code,200,matched.text)
                    self.assertTrue(matched.json()["candidates"])
                    run=matched.json()["run_id"]
                    pid=matched.json()["candidates"][0]["product_id"]
                    sku=matched.json()["candidates"][0]["sku"]
                    with connect() as db:
                        before_stock=db.execute("SELECT stock FROM products WHERE sku=?",(sku,)).fetchone()["stock"]
                        db.execute("""INSERT INTO physical_inventory_stock
                            (sku,product_type,qty_packages,package_uom,package_content,
                             content_uom,dispatch_uom_status,confirmation_status,source_sha256,confirmed_at)
                            VALUES(?, 'Powder',11,'unit',300,'gram','UNIT_DEFINED',
                                   'USER_CONFIRMED_PHYSICAL','CI_TEST','2026-11-07')""",(sku,))
                        before={t:db.execute("SELECT COUNT(*) AS n FROM "+t).fetchone()["n"]
                                for t in ("inquiries","runs","candidates","reviews","sample_requests",
                                          "sample_uat_movements","transaction_events")}
                    with patch("agent_pilot.groq_explain",side_effect=AssertionError("No external LLM allowed")):
                        data=client.get(f"/v1/agent/inquiry/{iid}/advice",headers=people["sales"]).json()
                        self.assertEqual(data["latest_run_id"],run)
                        self.assertGreaterEqual(data["candidate_count"],1)
                        best=data["candidates"][0]
                        self.assertEqual(best["sku"],sku)
                        self.assertEqual(best["stock_packages"],11)
                        self.assertEqual(best["pack_size"],300)
                        self.assertEqual(best["package_uom"],"unit")
                        self.assertIn("DATASHEET_UNVERIFIED",best["risk_flags"])
                        self.assertFalse(best["technical_suitability_proven"])
                        self.assertFalse(data["company_data_sent_to_groq"])
                        self.assertFalse(data["database_mutated"])
                        self.assertFalse(data["approval_created"])
                        self.assertEqual(data["next_actor"],"SALES")
                    with connect() as db:
                        for table,old_count in before.items():
                            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM "+table).fetchone()["n"],old_count,table)
                        self.assertEqual(db.execute("SELECT stock FROM products WHERE sku=?",(sku,)).fetchone()["stock"],before_stock)
                        self.assertEqual(db.execute("SELECT qty_packages FROM physical_inventory_stock WHERE sku=?",(sku,)).fetchone()["qty_packages"],11)
                    sales_submit=client.post(f"/v1/transactions/{iid}/sales-submit",headers=people["sales"],json={
                        "qty_kg":1,"recipient":"UAT-CUSTOMER","destination":"UAT-SITE",
                        "note":"UAT request for test"})
                    self.assertEqual(sales_submit.status_code,200,sales_submit.text)
                    pending=client.get(f"/v1/agent/inquiry/{iid}/advice",headers=people["technical"]).json()
                    self.assertEqual(pending["next_actor"],"TECHNICAL")
                    self.assertEqual(pending["sample_status"],"WAITING_TECHNICAL")
                    review=client.post(f"/v1/matches/{run}/review",headers=people["technical"],json={
                        "product_id":pid,"decision":"ACCEPT","relevance_label":3,
                        "rationale":"UAT only, expert label is separate from technical datasheet"})
                    self.assertEqual(review.status_code,200,review.text)
                    tech_submit=client.post(f"/v1/transactions/{iid}/technical-submit",
                        headers=people["technical"],json={
                            "product_id":pid,"note":"UAT Technical selection to Manager"})
                    self.assertEqual(tech_submit.status_code,200,tech_submit.text)
                    manager=client.get(f"/v1/agent/inquiry/{iid}/advice",headers=people["manager"])
                    self.assertEqual(manager.status_code,200,manager.text)
                    value=manager.json()
                    self.assertEqual(value["next_actor"],"MANAGER")
                    self.assertEqual(value["sample_status"],"WAITING_MANAGER")
                    self.assertTrue(value["candidates"][0]["technical_relevance_accepted"])
                    self.assertFalse(value["candidates"][0]["technical_suitability_proven"])
                    self.assertEqual(client.get(f"/v1/agent/inquiry/{iid+9000}/advice",headers=people["manager"]).status_code,404)
                    view=client.get("/ai/inquiry-advisor")
                    self.assertEqual(view.status_code,200)
                    self.assertIn("Sales Inquiry Intelligence Advisor",view.text)
                    self.assertIn("tidak mengirim isi inquiry",view.text)

        finally:
            if old is None:os.environ.pop("DATABASE_PATH",None)
            else:os.environ["DATABASE_PATH"]=old

    def test_revision_ignores_old_rankings(self):
        from agent_inquiry import inquiry_advice
        from types import SimpleNamespace
        class FakeDB:
            def execute(self,sql,args):
                if "FROM inquiries WHERE id" in sql:
                    return SimpleNamespace(fetchone=lambda:{
                        "id":4,"created_by":1,"status":"NEW",
                        "requirement":"Need revised vanilla","created_at":"2026-11-07"})
                if "FROM runs" in sql:
                    return SimpleNamespace(fetchone=lambda:{
                        "id":77,"method":"BM25","latency_ms":2,"created_at":"2026-11-06"})
                if "FROM sample_requests" in sql:
                    return SimpleNamespace(fetchone=lambda:None)
                raise AssertionError("Old run candidates must not be queried after a revision")
        result=inquiry_advice(FakeDB(),4,{"id":1,"role":"sales"})
        self.assertTrue(result["previous_run_ignored"])
        self.assertIsNone(result["latest_run_id"])
        self.assertEqual(result["candidate_count"],0)
        self.assertEqual(result["next_actor"],"SALES")


if __name__=="__main__":
    unittest.main()

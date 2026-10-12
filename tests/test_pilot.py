import os, tempfile, unittest
from pathlib import Path
os.environ["DATABASE_PATH"]=str(Path(tempfile.mkdtemp(prefix="liliang_ci_"))/"test.db")
os.environ["APP_ENV"]="pilot"
os.environ["ADMIN_EMAIL"]="admin@test.local"
os.environ["ADMIN_PASSWORD"]="ci-unique-demo-12345"
os.environ["SECRET_KEY"]="CI-only-strong-nonproduction-signing-key-0123456789"
from fastapi.testclient import TestClient
from app import app

class PilotFlow(unittest.TestCase):
    def test_end_to_end(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/healthz").status_code,200)
            self.assertTrue(client.get("/readyz").json()["ready"])
            self.assertEqual(client.get("/v1/products").status_code,401)
            self.assertEqual(client.post("/v1/auth/login",json={"email":"admin@test.local","password":"WRONG"}).status_code,401)
            login=client.post("/v1/auth/login",json={"email":"admin@test.local","password":"ci-unique-demo-12345"})
            self.assertEqual(login.status_code,200,login.text)
            admin={"Authorization":"Bearer "+login.json()["access_token"]}
            self.assertEqual(len(client.get("/v1/products",headers=admin).json()),5)
            # Regression for Render HTTP 500:
            # FastAPI may initialize the SQLite dependency in a different
            # worker thread than the synchronous endpoint handler.
            summary_response=client.get("/v1/analytics/summary",headers=admin)
            self.assertEqual(summary_response.status_code,200,summary_response.text)
            self.assertEqual(summary_response.headers["content-type"].split(";")[0],"application/json")
            summary=summary_response.json()
            self.assertEqual(summary["product_count"],5)
            self.assertEqual(summary["inquiry_count"],0)
            self.assertEqual(summary["bundling"],"SYNTHETIC_DEMO")
            self.assertEqual(summary["forecast"],"SYNTHETIC_DEMO")
            from concurrent.futures import ThreadPoolExecutor
            def dashboard_status(_):
                result=client.get("/v1/analytics/summary",headers=admin)
                if result.status_code!=200:
                    return result.status_code
                return 200 if result.json().get("product_count")==5 else 999
            with ThreadPoolExecutor(max_workers=6) as executor:
                statuses=list(executor.map(dashboard_status,range(36)))
            self.assertEqual(statuses,[200]*36)
            roles={}
            for role in ("sales","technical","manager","gudang"):
                r=client.post("/v1/users",json={"name":role.title(),"email":role+"@test.local",
                  "password":"demo-test-password-1234","role":role},headers=admin)
                self.assertEqual(r.status_code,201,r.text)
                token=client.post("/v1/auth/login",json={"email":role+"@test.local",
                  "password":"demo-test-password-1234"}).json()["access_token"]
                roles[role]={"Authorization":"Bearer "+token}
            self.assertEqual(client.get("/v1/users",headers=roles["sales"]).status_code,403)
            self.assertEqual(client.patch("/v1/products/1/stock",json={"stock_qty":4},headers=roles["sales"]).status_code,403)
            self.assertEqual(client.patch("/v1/products/1/stock",json={"stock_qty":4},headers=roles["gudang"]).status_code,200)
            inquiry=client.post("/v1/inquiries",json={"customer_ref":"TEST-ANON",
                "requirement":"strawberry dairy beverage flavor"},headers=roles["sales"])
            self.assertEqual(inquiry.status_code,201,inquiry.text)
            iid=inquiry.json()["id"]
            run=client.post(f"/v1/inquiries/{iid}/match",headers=roles["sales"])
            self.assertEqual(run.status_code,200,run.text)
            self.assertEqual(run.json()["candidates"][0]["sku"],"FLV-STRAW-01")
            rid=run.json()["run_id"]
            self.assertEqual(client.post(f"/v1/inquiries/{iid}/decision",
                json={"decision":"APPROVE","note":"Before expert review"},headers=roles["manager"]).status_code,409)
            self.assertEqual(client.post(f"/v1/matches/{rid}/review",json={
                "product_id":1,"decision":"REJECT","relevance_label":0,"rationale":"Not appropriate"},
                headers=roles["technical"]).status_code,200)
            self.assertEqual(client.post(f"/v1/inquiries/{iid}/decision",
                json={"decision":"APPROVE","note":"Rejected only"},headers=roles["manager"]).status_code,409)
            self.assertEqual(client.post(f"/v1/matches/{rid}/review",json={
                "product_id":1,"decision":"ACCEPT","relevance_label":3,"rationale":"Approved by Technical"},
                headers=roles["technical"]).status_code,200)
            self.assertEqual(client.post(f"/v1/inquiries/{iid}/decision",
                json={"decision":"APPROVE","note":"Technical recommended"},headers=roles["manager"]).status_code,200)
            warehouse=client.get("/v1/inquiries",headers=roles["gudang"]).json()[0]
            self.assertNotIn("requirement",warehouse)
            self.assertNotIn("customer_ref",warehouse)
            # Multi-AI workspace is visible and accurately labeled as demo.
            homepage=client.get("/")
            self.assertEqual(homepage.status_code,200)
            self.assertIn("Multi-AI Workspace",homepage.text)
            caps=client.get("/v1/ai/capabilities",headers=admin)
            self.assertEqual(caps.status_code,200,caps.text)
            self.assertEqual(len(caps.json()["modules"]),4)
            self.assertFalse(caps.json()["all_models_validated"])
            req=client.post("/v1/ai/requirements",
                json={"text":"Butuh stroberi untuk minuman susu"},
                headers=roles["sales"])
            self.assertEqual(req.status_code,200,req.text)
            self.assertEqual(req.json()["flavor"],"strawberry")
            self.assertEqual(req.json()["attributes"]["halal_status"]["status"],"UNKNOWN")
            self.assertEqual(client.post("/v1/ai/requirements",
                json={"text":"strawberry beverage flavor"},
                headers=roles["gudang"]).status_code,403)
            preview=client.post("/v1/ai/match-preview",
                json={"text":"strawberry flavor untuk minuman susu"},headers=roles["sales"])
            self.assertEqual(preview.status_code,200,preview.text)
            self.assertEqual(preview.json()["mode"],"lexical-only")
            self.assertEqual(preview.json()["candidates"][0]["sku"],"FLV-STRAW-01")
            rules=client.get("/v1/ai/bundling",headers=roles["sales"])
            self.assertEqual(rules.status_code,200,rules.text)
            self.assertEqual(rules.json()["basket_count"],16)
            self.assertGreater(len(rules.json()["rules"]),0)
            self.assertEqual(client.get("/v1/ai/bundling",headers=roles["gudang"]).status_code,403)
            fc=client.get("/v1/ai/forecast?sku=FLV-STRAW-01&horizon=4",headers=roles["gudang"])
            self.assertEqual(fc.status_code,200,fc.text)
            self.assertEqual(len(fc.json()["forecast"]),4)
            self.assertEqual(len(fc.json()["history"]),24)
            self.assertGreater(fc.json()["metrics"]["rolling_mae_units"],0)
            self.assertEqual(client.get("/v1/ai/forecast?sku=INVALID",headers=admin).status_code,404)
            self.assertEqual(client.get("/v1/ai/forecast",headers=roles["technical"]).status_code,403)

if __name__=="__main__":
    unittest.main()

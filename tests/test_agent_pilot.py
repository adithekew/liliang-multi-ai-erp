"""Agent proof: zero-cost local, auth, RBAC, no external calls, no mutations."""
import os, tempfile, unittest
from pathlib import Path

# Same disposable UAT credentials as existing test_pilot.py.
os.environ["APP_ENV"]="pilot"
os.environ["ADMIN_EMAIL"]="admin@test.local"
os.environ["ADMIN_PASSWORD"]="ci-unique-demo-12345"
os.environ["SECRET_KEY"]="CI-only-strong-nonproduction-signing-key-0123456789"
os.environ.setdefault("DATABASE_PATH",str(Path(tempfile.mkdtemp(prefix="liliang_agent_import_"))/"ci.db"))
from fastapi.testclient import TestClient
from app import app, ADMIN_EMAIL, ADMIN_PASSWORD
from agent_pilot import CASES, snapshot, status_info, external_enabled
from persistence import connect

class AgentPilotTest(unittest.TestCase):
    def test_all_four_ai_baselines_are_synthetic_and_abstain(self):
        for case_id in CASES:
            result=snapshot(case_id)
            self.assertEqual(result["scope"],"SYNTHETIC_ONLY_NO_COMPANY_RECORDS")
            self.assertFalse(result["AI-02"]["scientifically_validated"])
            self.assertFalse(result["AI-01"]["trained_company_model"])
            self.assertFalse(result["AI-03"]["trained_company_model"])
            self.assertFalse(result["AI-04"]["trained_company_model"])
            self.assertEqual(result["AI-04"]["forecast"]["data_classification"],"SYNTHETIC_PILOT")
            self.assertLessEqual(len(result["AI-02"]["top5"]),5)
            self.assertTrue(all(x["source_ref"]=="SYNTHETIC_AGENT_FIXTURE" for x in result["AI-02"]["top5"]))
        self.assertEqual(snapshot("RASPBERRY_ABSTAIN")["AI-02"]["top5"],[])
        with self.assertRaises(ValueError):snapshot("REAL_CUSTOMER_INPUT")

    def test_flag_defaults_to_off_and_does_not_expose_key(self):
        before_enabled=os.environ.get("AI_AGENT_EXTERNAL_ENABLED")
        before_key=os.environ.get("GROQ_API_KEY")
        try:
            os.environ["AI_AGENT_EXTERNAL_ENABLED"]="false"
            os.environ["GROQ_API_KEY"]="test-secret-never-return"
            self.assertFalse(external_enabled())
            self.assertEqual(status_info()["groq"],"DISABLED")
            self.assertNotIn("test-secret-never-return",str(status_info()))
        finally:
            if before_enabled is None:os.environ.pop("AI_AGENT_EXTERNAL_ENABLED",None)
            else:os.environ["AI_AGENT_EXTERNAL_ENABLED"]=before_enabled
            if before_key is None:os.environ.pop("GROQ_API_KEY",None)
            else:os.environ["GROQ_API_KEY"]=before_key

    def test_auth_rbac_request_validation_and_zero_mutation(self):
        prev_db=os.environ.get("DATABASE_PATH")
        prev_flag=os.environ.get("AI_AGENT_EXTERNAL_ENABLED")
        try:
            os.environ["AI_AGENT_EXTERNAL_ENABLED"]="false"
            with tempfile.TemporaryDirectory(prefix="agent_api_ci_") as temp:
                os.environ["DATABASE_PATH"]=str(Path(temp)/"ci.db")
                with TestClient(app) as c:
                    self.assertEqual(c.get("/v1/agent/status").status_code,401)
                    self.assertEqual(c.post("/v1/agent/demo",json={"case_id":"STRAWBERRY_DAIRY"}).status_code,401)
                    login=c.post("/v1/auth/login",json={"email":ADMIN_EMAIL,"password":ADMIN_PASSWORD})
                    self.assertEqual(login.status_code,200,login.text)
                    h={"Authorization":"Bearer "+login.json()["access_token"]}
                    initial={}
                    with connect() as db:
                        for table in ("products","inquiries","runs","reviews","ai_sales_orders","wms_demo_movements"):
                            initial[table]=db.execute("SELECT COUNT(*) AS n FROM "+table).fetchone()["n"]
                    page=c.get("/ai/agent-pilot")
                    self.assertEqual(page.status_code,200)
                    self.assertIn("Satu Agent. Empat Kapabilitas AI.",page.text)
                    self.assertIn("katalog evaluasi terkontrol",page.text.lower())
                    self.assertNotIn("rp0",page.text.lower())
                    self.assertNotIn("sintetis",page.text.lower())
                    self.assertEqual(c.get("/v1/agent/status",headers=h).status_code,200)
                    preview=c.post("/v1/agent/demo",headers=h,json={"case_id":"STRAWBERRY_DAIRY","provider":"local"})
                    self.assertEqual(preview.status_code,200,preview.text)
                    self.assertEqual(preview.json()["mode"],"LOCAL_RP0_NO_LLM")
                    self.assertFalse(preview.json()["persisted"])
                    self.assertEqual(preview.json()["tool_trace"],[])
                    self.assertFalse(preview.json()["all_four_tools_called"])
                    self.assertGreater(len(preview.json()["snapshot"]["AI-02"]["top5"]),0)
                    disabled=c.post("/v1/agent/demo",headers=h,json={"case_id":"STRAWBERRY_DAIRY","provider":"groq"})
                    self.assertEqual(disabled.status_code,409)
                    bad=c.post("/v1/agent/demo",headers=h,json={"case_id":"REAL_INVOICE"})
                    self.assertEqual(bad.status_code,422)
                    created=c.post("/v1/users",headers=h,json={
                        "name":"Warehouse UAT","email":"gudang.agent.uat@example.local",
                        "password":"ci-gudang-account-12345","role":"gudang"})
                    self.assertEqual(created.status_code,201,created.text)
                    wh=c.post("/v1/auth/login",json={
                        "email":"gudang.agent.uat@example.local","password":"ci-gudang-account-12345"})
                    self.assertEqual(wh.status_code,200)
                    wh_headers={"Authorization":"Bearer "+wh.json()["access_token"]}
                    self.assertEqual(c.get("/v1/agent/status",headers=wh_headers).status_code,403)
                    self.assertEqual(c.post("/v1/agent/demo",headers=wh_headers,json={
                        "case_id":"MANGO_BEVERAGE"}).status_code,403)
                    with connect() as db:
                        for table,n in initial.items():
                            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM "+table).fetchone()["n"],n,table)
        finally:
            if prev_db is None:os.environ.pop("DATABASE_PATH",None)
            else:os.environ["DATABASE_PATH"]=prev_db
            if prev_flag is None:os.environ.pop("AI_AGENT_EXTERNAL_ENABLED",None)
            else:os.environ["AI_AGENT_EXTERNAL_ENABLED"]=prev_flag

if __name__=="__main__":unittest.main()

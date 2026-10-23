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
            # Official branding must be present in the same server-rendered HTML
            # for every route. The asset must be served by Render, not an external
            # expiring CDN link or device-side localStorage.
            brand=client.get("/branding/logo?v=20261020")
            self.assertEqual(brand.status_code,200,brand.text[:100] if brand.status_code!=200 else "")
            self.assertEqual(brand.headers["content-type"],"image/jpeg")
            self.assertTrue(brand.content.startswith(bytes((0xFF,0xD8))))
            self.assertGreater(len(brand.content),2500)
            for route in ("/","/workspace","/dashboard","/catalog",
                          "/inquiries","/ai/hybrid","/ai/evidence",
                          "/ai/status","/reports","/admin/users"):
                page=client.get(route)
                self.assertEqual(page.status_code,200,route)
                self.assertIn('class="official-login-logo"',page.text)
                self.assertIn('class="official-sidebar-logo"',page.text)
                self.assertIn('class="official-topbar-logo"',page.text)
                self.assertIn("branding/logo?v=20261020",page.text)

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
            self.assertEqual(summary["catalog_source"],"SYNTHETIC_DEMO")
            self.assertEqual(summary["supplier_catalog_products"],0)
            self.assertEqual(summary["stock_unknown_count"],0)
            self.assertEqual(summary["user_count"],1)
            self.assertEqual(summary["expert_review_count"],0)
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
            self.assertEqual(run.json()["method"],"bm25-catalog-constraint-v0.3")
            # Repeated matching cannot generate five duplicate runs as in previous UAT.
            duplicate=client.post(f"/v1/inquiries/{iid}/match",headers=roles["sales"])
            self.assertEqual(duplicate.status_code,409,duplicate.text)
            self.assertEqual(client.get(f"/v1/inquiries/{iid}/latest-match",headers=roles["sales"]).json()["run_id"],rid)
            abstained=client.post("/v1/inquiries",headers=admin,json={
                "customer_ref":"UAT-UNSUPPORTED","requirement":"Need kiwi powder for bakery"})
            self.assertEqual(abstained.status_code,201,abstained.text)
            no_match=client.post(f'/v1/inquiries/{abstained.json()["id"]}/match',headers=admin)
            self.assertEqual(no_match.status_code,200,no_match.text)
            self.assertEqual(no_match.json()["status"],"NO_MATCH")
            self.assertEqual(no_match.json()["candidates"],[])
            smoke=client.get("/v1/ai/catalog-smoke",headers=roles["technical"])
            self.assertEqual(smoke.status_code,200,smoke.text)
            self.assertEqual(smoke.json()["constraints_total"],5)
            self.assertIsNone(smoke.json()["scientific_precision"])
            self.assertFalse(smoke.json()["training_performed"])
            self.assertEqual(client.get("/v1/ai/catalog-smoke",headers=roles["gudang"]).status_code,403)
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
            # Gudang must not enumerate inquiry metadata at all (third UAT).
            self.assertEqual(client.get("/v1/inquiries",headers=roles["gudang"]).status_code,403)
            self.assertEqual(client.get(f"/v1/inquiries/{iid}/latest-match",
                headers=roles["gudang"]).status_code,403)
            # Every ERP & AI module exposes an authenticated fresh report export.
            available=client.get("/v1/reports/available",headers=admin)
            self.assertEqual(available.status_code,200,available.text)
            self.assertEqual(len(available.json()["reports"]),12)
            for report_kind in ("inquiries","matching","technical_reviews","manager_decisions",
                                "stock_movements","catalog","audit","ai_requirement","ai_hybrid","ai_bundling",
                                "ai_forecast","ai_research"):
                pdf=client.get("/v1/reports/"+report_kind+"?format=pdf",headers=admin)
                self.assertEqual(pdf.status_code,200,report_kind+": "+pdf.text[:180] if pdf.status_code!=200 else "")
                self.assertTrue(pdf.content.startswith(b"%PDF"),report_kind)
                self.assertIn("no-store",pdf.headers["Cache-Control"])
                csv=client.get("/v1/reports/"+report_kind+"?format=csv",headers=admin)
                self.assertEqual(csv.status_code,200,csv.text[:180])
                self.assertIn("attachment;",csv.headers["Content-Disposition"])
            detail=client.get(f"/v1/reports/inquiry/{iid}?format=pdf",headers=roles["sales"])
            self.assertEqual(detail.status_code,200,detail.text[:180] if detail.status_code!=200 else "")
            self.assertTrue(detail.content.startswith(b"%PDF"))
            self.assertEqual(client.get("/v1/reports/audit",headers=roles["sales"]).status_code,403)
            self.assertEqual(client.get("/v1/reports/technical_reviews",headers=roles["gudang"]).status_code,403)
            self.assertEqual(client.get("/v1/reports/inquiry/999999",headers=roles["sales"]).status_code,404)

            # Multi-AI workspace is visible and accurately labeled as demo.
            homepage=client.get("/")
            self.assertEqual(homepage.status_code,200)
            # All module pages are independent HTTP documents: deep links and refresh work.
            for uri,identity in [
                ("/workspace","hub"),("/dashboard","overview"),
                ("/catalog","catalog"),("/inquiries","inquiries"),
                ("/ai/hybrid","hybrid"),("/ai/evidence","research"),
                ("/ai/status","systems"),("/sales/bundling","bundling"),
                ("/inventory/forecast","forecast"),("/admin/users","users"),
                ("/admin/roles","roles"),("/admin/catalog-migration","migration"),
                ("/admin/audit","audit")
            ]:
                response_page=client.get(uri)
                self.assertEqual(response_page.status_code,200,uri)
                self.assertEqual(response_page.headers.get("X-ERP-Page"),identity)
                self.assertIn("no-store",response_page.headers.get("Cache-Control",""))
                self.assertIn("window.location.assign",response_page.text)
                self.assertIn("cache:\"no-store\"",response_page.text)
            self.assertIn("no-store",summary_response.headers.get("Cache-Control",""))

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
            # Shared saved matching run (read-only): no duplicate ranking is created.
            list_view=client.get(f"/v1/inquiries/{iid}/latest-match",headers=admin)
            self.assertEqual(list_view.status_code,200,list_view.text)
            self.assertEqual(list_view.json()["candidates"][0]["sku"],"FLV-STRAW-01")

            explanation=preview.json()["candidates"][0]["explanation"]
            self.assertTrue(explanation["flavor_tag_match"])
            self.assertIn("strawberry",explanation["matched_terms"])
            self.assertIn("Lexical",explanation["limitations"])
            status=client.get("/v1/ai/system-status",headers=admin)
            self.assertEqual(status.status_code,200,status.text)
            self.assertEqual(status.json()["database_backend"],"sqlite-ephemeral")
            self.assertFalse(status.json()["persistent_database"])
            self.assertFalse(status.json()["model_validated_for_company"])
            self.assertFalse(status.json()["company_fine_tuning_completed"])
            self.assertFalse(status.json()["production_ready"])
            neural=next(x for x in status.json()["components"] if x["id"]=="AI-02-NEURAL")
            self.assertEqual(neural["mode"],"OFFLINE_PRECOMPUTED_FIXED_SYNTHETIC_CASES")
            self.assertEqual(neural["embedding_dimensions"],384)
            self.assertIn("AI System Status",homepage.text)
            self.assertIn("SUDAH dijalankan",homepage.text)
            self.assertNotIn("Belum ada LLM, embedding",homepage.text)

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
            # Authentic neural vectors from the versioned, synthetic-only
            # GitHub Actions fixture: no runtime model and no expert result claims.
            cases=client.get("/v1/ai/hybrid-cases",headers=roles["sales"])
            self.assertEqual(cases.status_code,200,cases.text)
            self.assertTrue(cases.json()["available"])
            self.assertEqual(len(cases.json()["cases"]),10)
            self.assertEqual(cases.json()["dimensions"],384)
            hybrid=client.get("/v1/ai/hybrid-evaluate?case_id=Q01",headers=roles["technical"])
            self.assertEqual(hybrid.status_code,200,hybrid.text)
            result=hybrid.json()
            self.assertEqual(len(result["ranked_candidates"]),5)
            self.assertEqual(result["embedding_dimensions"],384)
            self.assertIsNone(result["end_to_end_latency_ms"])
            self.assertFalse(result["validated_by_technical"])
            self.assertEqual(result["data_scope"],"SYNTHETIC_EXAMPLES_ONLY")
            self.assertTrue(all(x["constraint_status"]=="UNKNOWN" for x in result["ranked_candidates"]))
            self.assertEqual(client.get("/v1/ai/hybrid-cases",headers=roles["gudang"]).status_code,403)
            self.assertEqual(client.get("/v1/ai/hybrid-evaluate?case_id=Q99",headers=admin).status_code,404)
            # Lecturer-facing evidence, with strict protections and zero fake accuracy.
            study=client.get("/v1/research/methodology",headers=roles["technical"])
            self.assertEqual(study.status_code,200,study.text)
            self.assertEqual(study.json()["training_status"],"PRETRAINED_EXTERNAL_MODEL_ONLY_NO_LILIANG_FINE_TUNING")
            self.assertEqual(client.get("/v1/research/methodology",headers=roles["sales"]).status_code,403)
            ready=client.get("/v1/research/readiness",headers=admin)
            self.assertEqual(ready.status_code,200,ready.text)
            self.assertEqual(ready.json()["scientific_readiness"],"NOT_VALIDATED")
            self.assertGreaterEqual(ready.json()["evaluation_runs_total"],1)
            performance=client.get("/v1/research/evaluation",headers=roles["manager"])
            self.assertEqual(performance.status_code,200,performance.text)
            self.assertFalse(performance.json()["model_comparison_valid"])
            self.assertEqual(client.get("/v1/research/evaluation",headers=roles["gudang"]).status_code,403)
            quality=client.get("/v1/research/quality-demo",headers=admin)
            self.assertEqual(quality.status_code,200,quality.text)
            self.assertEqual(quality.json()["status"],"SYNTHETIC_QA_ONLY")
            self.assertFalse(quality.json()["company_data_used"])
            self.assertEqual(quality.json()["product_quality"]["accepted"],5)
            self.assertEqual(quality.json()["inquiry_quality"]["accepted"],10)
            training=client.get("/v1/research/training-readiness",headers=roles["technical"])
            self.assertEqual(training.status_code,200,training.text)
            self.assertEqual(training.json()["catalog_sku_count"],0)
            self.assertEqual(training.json()["qualified_expert_labels"],0)
            self.assertFalse(training.json()["model_weight_updates_performed"])
            self.assertFalse(training.json()["research_accuracy_available"])
            self.assertEqual(client.get("/v1/research/training-readiness",headers=roles["sales"]).status_code,403)

            self.assertIn("AI Research Evidence",homepage.text)
            # Server-backed session revocation and post-logout 401.
            self.assertEqual(client.get("/v1/auth/me",headers=roles["gudang"]).status_code,200)
            signed_out=client.post("/v1/auth/logout",headers=roles["gudang"])
            self.assertEqual(signed_out.status_code,200,signed_out.text)
            self.assertTrue(signed_out.json()["session_revoked"])
            self.assertEqual(client.get("/v1/auth/me",headers=roles["gudang"]).status_code,401)
            # Inactivity: server refuses even a cryptographically valid unexpired JWT.
            reauth=client.post("/v1/auth/login",json={"email":"gudang@test.local",
                  "password":"demo-test-password-1234"})
            self.assertEqual(reauth.status_code,200,reauth.text)
            h={"Authorization":"Bearer "+reauth.json()["access_token"]}
            from app import connect
            with connect() as connection:
                connection.execute("UPDATE user_sessions SET last_seen_at=last_seen_at-901 WHERE user_id=(SELECT id FROM users WHERE email=?)",
                                   ("gudang@test.local",))
            self.assertEqual(client.get("/v1/auth/me",headers=h).status_code,401)



if __name__=="__main__":
    unittest.main()

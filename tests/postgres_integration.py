import os
import unittest
from fastapi.testclient import TestClient

assert os.environ.get("DATABASE_URL"), "A disposable PostgreSQL CI database is required"
from app import app
from persistence import connect, engine_name

class PostgresIntegrationTest(unittest.TestCase):
    def test_postgres_round_trip(self):
        self.assertEqual(engine_name(),"postgresql")
        with TestClient(app) as c:
            self.assertEqual(c.get("/readyz").json()["database_backend"],"postgresql")
            response=c.post("/v1/auth/login",json={
                "email":os.environ["ADMIN_EMAIL"],"password":os.environ["ADMIN_PASSWORD"]})
            self.assertEqual(response.status_code,200,response.text)
            headers={"Authorization":"Bearer "+response.json()["access_token"]}
            self.assertEqual(len(c.get("/v1/products",headers=headers).json()),5)
            summary=c.get("/v1/analytics/summary",headers=headers)
            self.assertEqual(summary.status_code,200,summary.text)
            self.assertEqual(summary.headers["content-type"].split(";")[0],"application/json")
            self.assertEqual(summary.json()["product_count"],5)
            self.assertEqual(summary.json()["inquiry_count"],0)
            ai_status=c.get("/v1/ai/system-status",headers=headers)
            self.assertEqual(ai_status.status_code,200,ai_status.text)
            self.assertEqual(ai_status.json()["database_backend"],"postgresql")
            self.assertTrue(ai_status.json()["persistent_database"])
            self.assertEqual(ai_status.json()["product_count"],5)
            self.assertFalse(ai_status.json()["model_validated_for_company"])
            self.assertFalse(ai_status.json()["production_ready"])

            for path in [
                "/v1/ai/capabilities",
                "/v1/ai/bundling",
                "/v1/ai/forecast?sku=FLV-STRAW-01&horizon=4",
                "/v1/ai/hybrid-cases",
                "/v1/ai/hybrid-evaluate?case_id=Q01",
                "/v1/research/readiness",
                "/v1/research/evaluation",
                "/v1/research/quality-demo",
            ]:
                result=c.get(path,headers=headers)
                self.assertEqual(result.status_code,200,f"{path}: {result.text[:400]}")

            from app import boot
            boot()
            self.assertEqual(len(c.get("/v1/products",headers=headers).json()),5)
            response=c.post("/v1/inquiries",json={"customer_ref":"CI-ANON",
                "requirement":"Mango beverage flavor"},headers=headers)
            self.assertEqual(response.status_code,201,response.text)
            iid=response.json()["id"]
            m=c.post(f"/v1/inquiries/{iid}/match",headers=headers)
            self.assertEqual(m.status_code,200,m.text)
            self.assertEqual(m.json()["candidates"][0]["sku"],"FLV-MANG-03")
            post_summary=c.get("/v1/analytics/summary",headers=headers)
            self.assertEqual(post_summary.status_code,200,post_summary.text)
            self.assertEqual(post_summary.json()["inquiry_count"],1)
            # Five real login sessions on ephemeral CI PostgreSQL, RBAC and workflow.
            provision=c.post("/v1/admin/uat/bootstrap",headers=headers,
                             json={"confirmation":"CREATE UAT ROLES"})
            self.assertEqual(provision.status_code,200,provision.text)
            self.assertEqual(len(provision.json()["roles"]),4)
            role_headers={}
            for row in provision.json()["roles"]:
                auth=c.post("/v1/auth/login",json={
                    "email":row["email"],"password":row["password_once"]})
                self.assertEqual(auth.status_code,200,auth.text)
                role_headers[row["role"]]={"Authorization":"Bearer "+auth.json()["access_token"]}
            # Technical and Manager inspect the Sales ranking without rerunning AI.
            technical_view=c.get(f"/v1/inquiries/{iid}/latest-match",headers=role_headers["technical"])
            self.assertEqual(technical_view.status_code,200,technical_view.text)
            self.assertEqual(technical_view.json()["run_id"],m.json()["run_id"])
            self.assertEqual(technical_view.json()["candidates"][0]["sku"],"FLV-MANG-03")
            manager_view=c.get(f"/v1/inquiries/{iid}/latest-match",headers=role_headers["manager"])
            self.assertEqual(manager_view.status_code,200,manager_view.text)
            self.assertEqual(manager_view.json()["run_id"],m.json()["run_id"])
            sales_denied=c.get(f"/v1/inquiries/{iid}/latest-match",headers=role_headers["sales"])
            self.assertEqual(sales_denied.status_code,403)
            self.assertEqual(c.get("/v1/analytics/summary",headers=headers).json()["inquiry_count"],1)
            with connect() as audit_conn:
                self.assertEqual(audit_conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"],1)

            again=c.post("/v1/admin/uat/bootstrap",headers=headers,
                         json={"confirmation":"CREATE UAT ROLES"})
            self.assertTrue(all("password_once" not in x for x in again.json()["roles"]))
            self.assertEqual(c.get("/v1/admin/catalog/reset-preview",headers=role_headers["sales"]).status_code,403)
            no_review=c.post(f"/v1/inquiries/{iid}/decision",headers=role_headers["manager"],
                             json={"decision":"APPROVE","note":"Before Technical review"})
            self.assertEqual(no_review.status_code,409)
            chosen=m.json()["candidates"][0]
            reviewed=c.post(f'/v1/matches/{m.json()["run_id"]}/review',
                            headers=role_headers["technical"],
                            json={"product_id":chosen["product_id"],
                                  "decision":"ACCEPT","relevance_label":3,
                                  "rationale":"Expert UAT validation with no company data"})
            self.assertEqual(reviewed.status_code,200,reviewed.text)
            # UAT Technical validation is operational, NOT an expert research label.
            scientific=c.get("/v1/research/readiness",headers=headers)
            self.assertEqual(scientific.status_code,200,scientific.text)
            self.assertEqual(scientific.json()["candidate_pairs_with_a_review"],0)
            self.assertEqual(scientific.json()["fully_labelled_runs"],0)
            self.assertTrue(scientific.json()["uat_records_excluded_from_research"])
            self.assertEqual(c.get("/v1/ai/system-status",headers=headers).json()["expert_review_count"],0)
            self.assertEqual(c.get("/v1/ai/system-status",headers=headers).json()["uat_review_count_excluded_from_research"],1)
            dashboard=c.get("/v1/analytics/summary",headers=headers).json()
            self.assertEqual(dashboard["expert_review_count"],0)
            self.assertEqual(dashboard["uat_review_count"],1)
            decision=c.post(f"/v1/inquiries/{iid}/decision",headers=role_headers["manager"],
                            json={"decision":"APPROVE","note":"Technical candidate accepted"})
            self.assertEqual(decision.status_code,200,decision.text)
            inventory=c.patch(f'/v1/products/{chosen["product_id"]}/stock',
                              headers=role_headers["gudang"],json={"stock_qty":10})
            self.assertEqual(inventory.status_code,200,inventory.text)
            # Server creates downloadable PDF and CSV reports for real persisted PostgreSQL transactions.
            for k in ("inquiries","matching","technical_reviews","manager_decisions",
                      "stock_movements","catalog","audit","ai_requirement","ai_hybrid","ai_bundling","ai_forecast","ai_research"):
                pdf=c.get("/v1/reports/"+k+"?format=pdf",headers=headers)
                self.assertEqual(pdf.status_code,200,k+": "+str(pdf.status_code))
                self.assertTrue(pdf.content.startswith(b"%PDF"),k)
                self.assertIn("no-store",pdf.headers["Cache-Control"])
            receipt=c.get(f"/v1/reports/inquiry/{iid}?format=pdf",headers=role_headers["manager"])
            self.assertEqual(receipt.status_code,200,receipt.text[:200] if receipt.status_code!=200 else "")
            self.assertTrue(receipt.content.startswith(b"%PDF"))
            self.assertEqual(c.get("/v1/reports/audit",headers=role_headers["sales"]).status_code,403)
            self.assertEqual(c.get(f"/v1/reports/inquiry/{iid}",headers=role_headers["gudang"]).status_code,403)

            events=c.get("/v1/admin/audit-events",headers=headers)
            self.assertEqual(events.status_code,200,events.text)
            actions={e["action"] for e in events.json()["events"]}
            self.assertTrue({"CREATE_UAT_USER","NEW_INQUIRY","MATCH_BASELINE",
                             "EXPERT_REVIEW","MANAGER_APPROVE","STOCK_UPDATE"}.issubset(actions),actions)
            self.assertTrue(all(len(e["payload_sha256"])==64 for e in events.json()["events"]))
            d=connect()
            try:self.assertIsNotNone(d.execute("SELECT id FROM inquiries WHERE id=?",(iid,)).fetchone())
            finally:d.close()

            # Reset is restricted to demo-only records, archives atomically, preserves users.
            wrong=c.post("/v1/admin/catalog/reset-demo",headers=headers,
                         json={"confirmation":"WRONG"})
            self.assertEqual(wrong.status_code,422)
            clean=c.post("/v1/admin/catalog/reset-demo",headers=headers,
                         json={"confirmation":"RESET DEMO ONLY"})
            self.assertEqual(clean.status_code,200,clean.text)
            self.assertEqual(clean.json()["counts"]["products"],5)
            self.assertEqual(clean.json()["counts"]["inquiries"],1)
            self.assertEqual(len(c.get("/v1/products",headers=headers).json()),0)
            self.assertEqual(c.get("/v1/admin/catalog/reset-preview",headers=headers).json()["counts"]["reset_archives"],1)

            # Atomic private catalog import: duplicates are rejected without partial writes.
            source="a"*64
            manifest={"version":"v1","source_file_sha256":source,
                      "source_file_name":"ci-fixture.pdf","catalog_version":"ci-v1",
                      "source_records":2,"ready_records":2,"quarantined_records":0,
                      "source_kind":"COMPANY_PRODUCT_CATALOG","claims":[]}
            item={"number":1,"sku":"CI-ALMOND-01","name":"Almond Flavor",
                  "product_type":"Liquid","application":"Beverage",
                  "composition_text":"0.05%-0.1%","source_page":1,"source_number":1}
            other={**item,"number":2,"sku":"CI-MANGO-02","name":"Mango Flavor","source_number":2}
            duplicate=c.post("/v1/admin/catalog/import",headers=headers,
                             json={"manifest":manifest,"products":[item,item]})
            self.assertEqual(duplicate.status_code,422,duplicate.text)
            imported=c.post("/v1/admin/catalog/import",headers=headers,
                            json={"manifest":manifest,"products":[item,other]})
            self.assertEqual(imported.status_code,201,imported.text)
            self.assertEqual(imported.json()["imported_count"],2)
            items=c.get("/v1/catalog/products?q=mango",headers=headers)
            self.assertEqual(items.json()["total"],1,items.text)
            self.assertIsNone(items.json()["items"][0]["stock"])
            blocked=c.post("/v1/admin/catalog/reset-demo",headers=headers,
                           json={"confirmation":"RESET DEMO ONLY"})
            self.assertEqual(blocked.status_code,409,blocked.text)
            # Hybrid benchmark stays isolated from the new catalog.
            lab=c.get("/v1/ai/hybrid-evaluate?case_id=Q01",headers=headers)
            self.assertEqual(lab.status_code,200,lab.text)
            self.assertEqual(lab.json()["catalog_isolation"],
                             "SYNTHETIC_BENCHMARK_ONLY_NOT_COMPANY_CATALOG")
            status=c.get("/v1/ai/system-status",headers=headers)
            self.assertEqual(status.json()["company_catalog_products"],2,status.text)
            self.assertEqual(status.json()["data_source"],"COMPANY_CATALOG_UNVERIFIED")
            summary_after=c.get("/v1/analytics/summary",headers=headers)
            self.assertEqual(summary_after.status_code,200,summary_after.text)
            self.assertEqual(summary_after.json()["product_count"],2)
            self.assertEqual(summary_after.json()["supplier_catalog_products"],2)
            self.assertEqual(summary_after.json()["stock_unknown_count"],2)
            self.assertEqual(summary_after.json()["catalog_source"],"SUPPLIER_PDF_PENDING_TECHNICAL")
            self.assertEqual(summary_after.json()["user_count"],5)
            self.assertGreaterEqual(summary_after.json()["audit_event_count"],8)
            caps_after=c.get("/v1/ai/capabilities",headers=headers)
            self.assertEqual(caps_after.status_code,200,caps_after.text)
            self.assertIn("COMPANY_CATALOG_UNVERIFIED",caps_after.json()["data_scope"])
            self.assertIn("supplier-catalog",caps_after.json()["modules"][1]["dataset"])
            sessions=c.get("/v1/auth/me",headers=role_headers["gudang"])
            self.assertEqual(sessions.status_code,200)
            end_session=c.post("/v1/auth/logout",headers=role_headers["gudang"])
            self.assertEqual(end_session.status_code,200,end_session.text)
            self.assertEqual(c.get("/v1/auth/me",headers=role_headers["gudang"]).status_code,401)

            train_gate=c.get("/v1/research/training-readiness",headers=headers)
            self.assertEqual(train_gate.status_code,200,train_gate.text)
            self.assertEqual(train_gate.json()["catalog_sku_count"],2)
            self.assertEqual(train_gate.json()["qualified_expert_labels"],0)
            self.assertFalse(train_gate.json()["locked_heldout_test"])
            self.assertFalse(train_gate.json()["model_weight_updates_performed"])
            self.assertEqual(train_gate.json()["status"],"DATA_COLLECTION_REQUIRED")
            for uri in ("/workspace","/dashboard","/catalog","/inquiries",
                        "/ai/evidence","/ai/hybrid","/ai/status",
                        "/sales/bundling","/inventory/forecast",
                        "/admin/users","/admin/roles","/admin/catalog-migration","/admin/audit"):
                route=c.get(uri)
                self.assertEqual(route.status_code,200,uri)
                self.assertIn("no-store",route.headers.get("Cache-Control",""))
            self.assertIn("no-store",summary_after.headers["Cache-Control"])

        # Restart idempotence: reset marker prevents seeding five demo SKUs.
        with TestClient(app) as c:
            login=c.post("/v1/auth/login",json={
                "email":os.environ["ADMIN_EMAIL"],"password":os.environ["ADMIN_PASSWORD"]})
            h={"Authorization":"Bearer "+login.json()["access_token"]}
            catalog=c.get("/v1/products",headers=h).json()
            self.assertEqual(len(catalog),2)
            self.assertTrue(all(x["source_ref"]=="CATALOG-PDF-UNVERIFIED" for x in catalog))



if __name__=="__main__":unittest.main()

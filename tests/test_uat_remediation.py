"""Regression for the two 21 October 2026 UAT reports.

Uses disposable SQLite only. Does not modify the Render/Neon pilot.
"""
import os
import tempfile
import unittest
from pathlib import Path

# The app credentials are configured by the existing test suite at import time.
from fastapi.testclient import TestClient
from app import app, ADMIN_EMAIL, ADMIN_PASSWORD
from persistence import connect


class UATRemediation(unittest.TestCase):
    def test_real_workflow_guards_and_audit(self):
        original_path=os.environ.get("DATABASE_PATH")
        with tempfile.TemporaryDirectory(prefix="liliang_uat_regression_") as temp:
            os.environ["DATABASE_PATH"]=str(Path(temp)/"pilot.db")
            try:
                with TestClient(app) as client:
                    self.assertEqual(client.get("/readyz").status_code,200)
                    login=client.post("/v1/auth/login",json={"email":ADMIN_EMAIL,"password":ADMIN_PASSWORD})
                    self.assertEqual(login.status_code,200,login.text)
                    admin={"Authorization":"Bearer "+login.json()["access_token"]}
                    headers={}
                    for role in ("sales","technical","manager"):
                        r=client.post("/v1/users",headers=admin,json={
                            "name":role.title(),"email":"uat-"+role+"@liliang.local",
                            "password":"temporary-uat-pass-12345","role":role})
                        self.assertEqual(r.status_code,201,r.text)
                        sign=client.post("/v1/auth/login",json={
                            "email":"uat-"+role+"@liliang.local","password":"temporary-uat-pass-12345"})
                        self.assertEqual(sign.status_code,200,sign.text)
                        headers[role]={"Authorization":"Bearer "+sign.json()["access_token"]}

                    # Every denied action is audit-traceable, with unique hashes.
                    for _ in range(2):
                        r=client.get("/v1/users",headers=headers["sales"])
                        self.assertEqual(r.status_code,403)
                    with connect() as db:
                        denied=db.execute("""SELECT payload_sha256 FROM transaction_events
                            WHERE action='ACCESS_DENIED_403' ORDER BY at""").fetchall()
                    self.assertGreaterEqual(len(denied),2)
                    self.assertNotEqual(denied[-1]["payload_sha256"],denied[-2]["payload_sha256"])

                    inquiry=client.post("/v1/inquiries",headers=headers["sales"],json={
                        "customer_ref":"UAT-REMEDIATION",
                        "requirement":"Perlu strawberry flavor untuk minuman; bentuk produk cair"})
                    self.assertEqual(inquiry.status_code,201,inquiry.text)
                    iid=inquiry.json()["id"]
                    match=client.post(f"/v1/inquiries/{iid}/match",headers=headers["sales"])
                    self.assertEqual(match.status_code,200,match.text)
                    self.assertEqual(len(match.json()["candidates"]),1)
                    rid=match.json()["run_id"]
                    pid=match.json()["candidates"][0]["product_id"]
                    self.assertEqual(client.post(f"/v1/inquiries/{iid}/match",
                        headers=headers["sales"]).status_code,409)

                    before=client.post(f"/v1/inquiries/{iid}/decision",
                        headers=headers["manager"],json={"decision":"APPROVE","note":"Before expert review"})
                    self.assertEqual(before.status_code,409)
                    bad=client.post(f"/v1/matches/{rid}/review",headers=headers["technical"],json={
                        "product_id":pid,"decision":"ACCEPT","relevance_label":2,
                        "rationale":"Plausible only; need evidence"})
                    self.assertEqual(bad.status_code,422)
                    neutral=client.post(f"/v1/matches/{rid}/review",headers=headers["technical"],json={
                        "product_id":pid,"decision":"NEEDS_INFO","relevance_label":2,
                        "rationale":"Needs customer and datasheet confirmation"})
                    self.assertEqual(neutral.status_code,200,neutral.text)
                    not_approved=client.post(f"/v1/inquiries/{iid}/decision",headers=headers["manager"],
                        json={"decision":"APPROVE","note":"Need documentation first"})
                    self.assertEqual(not_approved.status_code,409)
                    accepted=client.post(f"/v1/matches/{rid}/review",headers=headers["technical"],json={
                        "product_id":pid,"decision":"ACCEPT","relevance_label":3,
                        "rationale":"UAT grade 3 only, not research evidence"})
                    self.assertEqual(accepted.status_code,200,accepted.text)
                    approved=client.post(f"/v1/inquiries/{iid}/decision",headers=headers["manager"],
                        json={"decision":"APPROVE","note":"Approved after grade 3"})
                    self.assertEqual(approved.status_code,200,approved.text)
                    duplicate=client.post(f"/v1/inquiries/{iid}/decision",headers=headers["manager"],
                        json={"decision":"APPROVE","note":"Duplicate manager click"})
                    self.assertEqual(duplicate.status_code,409)
                    self.assertIn("already decided",duplicate.json()["detail"])
                    post_review=client.post(f"/v1/matches/{rid}/review",headers=headers["technical"],json={
                        "product_id":pid,"decision":"REJECT","relevance_label":0,
                        "rationale":"Should be closed"})
                    self.assertEqual(post_review.status_code,409)
                    summary=client.get("/v1/analytics/summary",headers=admin).json()
                    self.assertEqual(summary["expert_review_count"],0)
                    self.assertGreater(summary["uat_review_count"],0)
                    with connect() as db:
                        conflicts=db.execute("""SELECT COUNT(*) AS n FROM transaction_events
                            WHERE action='BUSINESS_CONFLICT_409'""").fetchone()["n"]
                        saved=db.execute("""SELECT COUNT(*) AS n FROM runs WHERE inquiry_id=?""",(iid,)).fetchone()["n"]
                    self.assertGreaterEqual(conflicts,3)
                    self.assertEqual(saved,1)
            finally:
                if original_path is None:os.environ.pop("DATABASE_PATH",None)
                else:os.environ["DATABASE_PATH"]=original_path

    def test_lemon_smoke_checks_catalog_type_not_only_title(self):
        old=os.environ.get("DATABASE_PATH")
        with tempfile.TemporaryDirectory(prefix="liliang_form_smoke_") as temp:
            os.environ["DATABASE_PATH"]=str(Path(temp)/"pilot.db")
            try:
                with TestClient(app) as client:
                    with connect() as db:
                        db.execute("""UPDATE products SET description='Type: powder; application bakery'
                                      WHERE sku='FLV-LEMON-05'""")
                        db.commit()
                    auth=client.post("/v1/auth/login",json={
                        "email":ADMIN_EMAIL,"password":ADMIN_PASSWORD}).json()
                    response=client.get("/v1/ai/catalog-smoke",headers={
                        "Authorization":"Bearer "+auth["access_token"]})
                    self.assertEqual(response.status_code,200,response.text)
                    case=next(x for x in response.json()["scenarios"] if x["case"]=="lemon_powder")
                    self.assertEqual(case["top_sku"],"FLV-LEMON-05")
                    self.assertEqual(case["top_detected_form"],"powder")
                    self.assertEqual(case["constraint_consistency"],"PASS")
                    self.assertIsNone(response.json()["scientific_precision"])
            finally:
                if old is None:os.environ.pop("DATABASE_PATH",None)
                else:os.environ["DATABASE_PATH"]=old


if __name__=="__main__":
    unittest.main()

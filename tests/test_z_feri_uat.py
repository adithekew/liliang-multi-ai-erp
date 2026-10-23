"""Regression tests for Feri Irawan's 22 October 2026 UAT report.

All changes run in disposable local SQLite. Never connect to the Render/Neon
research pilot or alter real company inventory or historical UAT evidence.
"""
import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app import app, ADMIN_EMAIL, ADMIN_PASSWORD
from persistence import connect


class FeriUATFollowUp(unittest.TestCase):
    def test_warehouse_privacy_physical_count_and_historical_label_flags(self):
        old = os.environ.get("DATABASE_PATH")
        with tempfile.TemporaryDirectory(prefix="feri_uat_20261022_") as temp:
            os.environ["DATABASE_PATH"] = str(Path(temp) / "isolated.db")
            try:
                with TestClient(app) as client:
                    admin_login = client.post("/v1/auth/login", json={
                        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
                    })
                    self.assertEqual(admin_login.status_code, 200, admin_login.text)
                    admin = {"Authorization": "Bearer " + admin_login.json()["access_token"]}
                    headers = {}
                    for role in ("sales", "technical", "manager", "gudang"):
                        email = "uat-" + role + "@liliang.local"
                        created = client.post("/v1/users", headers=admin, json={
                            "email": email, "name": role.title(),
                            "role": role, "password": "strong-disposable-test-1234"
                        })
                        self.assertEqual(created.status_code, 201, created.text)
                        login = client.post("/v1/auth/login", json={
                            "email": email, "password": "strong-disposable-test-1234"
                        })
                        self.assertEqual(login.status_code, 200, login.text)
                        headers[role] = {"Authorization": "Bearer " + login.json()["access_token"]}

                    new = client.post("/v1/inquiries", headers=headers["sales"], json={
                        "customer_ref": "UAT-ANON", "requirement": "Butuh mango powder untuk minuman"
                    })
                    self.assertEqual(new.status_code, 201, new.text)
                    iid = new.json()["id"]
                    match = client.post(f"/v1/inquiries/{iid}/match", headers=headers["sales"])
                    self.assertEqual(match.status_code, 200, match.text)
                    rid = match.json()["run_id"]

                    # Prior screenshot leaked inquiry IDs/status to Gudang even while
                    # texts were redacted. The *entire endpoint* must deny access.
                    self.assertEqual(client.get("/v1/inquiries", headers=headers["gudang"]).status_code, 403)
                    self.assertEqual(client.get(
                        f"/v1/inquiries/{iid}/latest-match", headers=headers["gudang"]
                    ).status_code, 403)
                    self.assertEqual(client.get(
                        f"/v1/matches/{rid}", headers=headers["gudang"]
                    ).status_code, 403)

                    # A past UAT label/decision combination must be flagged, never
                    # overwritten or treated as a scientific gold-standard label.
                    product_id = match.json()["candidates"][0]["product_id"]
                    with connect() as db:
                        user = db.execute("SELECT id FROM users WHERE email='uat-technical@liliang.local'").fetchone()
                        db.execute("""INSERT INTO reviews(run_id, product_id, reviewer_id,
                            decision, label, note) VALUES(?,?,?,?,?,?)""",
                            (rid, product_id, user["id"], "ACCEPT", 2,
                             "Legacy inconsistent UAT example"))
                        db.execute("""UPDATE products SET source_ref='CATALOG-PDF-UNVERIFIED',
                          stock=NULL WHERE id=?""", (product_id,))
                        db.commit()
                    latest = client.get(f"/v1/inquiries/{iid}/latest-match", headers=admin)
                    self.assertEqual(latest.status_code, 200, latest.text)
                    first = next(x for x in latest.json()["candidates"] if x["product_id"] == product_id)
                    self.assertTrue(first["historical_review_conflict"])
                    self.assertEqual(first["expert_relevance"], 2)
                    self.assertEqual(first["expert_decision"], "ACCEPT")
                    self.assertEqual(first["product_form"], "UNKNOWN")

                    uat_stock = client.patch(f"/v1/products/{product_id}/stock",
                        headers=headers["gudang"], json={
                            "stock_qty": 900, "verification_ref": "COUNT-2026-100",
                            "physical_count_date": "2026-10-20"
                        })
                    self.assertEqual(uat_stock.status_code, 403, uat_stock.text)
                    unproved = client.patch(f"/v1/products/{product_id}/stock",
                        headers=admin, json={"stock_qty": 15})
                    self.assertEqual(unproved.status_code, 422, unproved.text)
                    invalid_date = client.patch(f"/v1/products/{product_id}/stock",
                        headers=admin, json={"stock_qty": 15,
                                             "verification_ref": "COUNT-2026-100",
                                             "physical_count_date": "2026-22-13"})
                    self.assertEqual(invalid_date.status_code, 422)
                    with connect() as db:
                        not_modified = db.execute("SELECT stock FROM products WHERE id=?",(product_id,)).fetchone()
                        self.assertIsNone(not_modified["stock"])

                    proved = client.patch(f"/v1/products/{product_id}/stock",
                        headers=admin, json={"stock_qty": 15,
                                             "verification_ref": "COUNT-2026-100",
                                             "physical_count_date": "2026-10-20"})
                    self.assertEqual(proved.status_code, 200, proved.text)
                    self.assertTrue(proved.json()["verification_recorded"])
                    with connect() as db:
                        audit = db.execute("""SELECT after_json FROM transaction_events
                          WHERE action='STOCK_UPDATE' ORDER BY at DESC LIMIT 1""").fetchone()
                        self.assertIsNotNone(audit)
                        self.assertIn("COUNT-2026-100",audit["after_json"])
                        self.assertIn("2026-10-20",audit["after_json"])
            finally:
                if old is None:
                    os.environ.pop("DATABASE_PATH",None)
                else:
                    os.environ["DATABASE_PATH"]=old

if __name__=="__main__":
    unittest.main()

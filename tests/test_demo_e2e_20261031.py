"""Functional UAT scenario on a disposable database, not the live Neon pilot.

Tests Sales -> Technical -> Manager RETURN -> Sales revise -> new BM25 run ->
new Technical ACCEPT-3 -> Manager APPROVE -> reports, plus independent WMS UAT
ledger. Never modifies supplier stock or treats synthetic data as real orders.
"""
import os
import json
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app import app,ADMIN_EMAIL,ADMIN_PASSWORD
from persistence import connect

PASSWORD="demo-only-complex-1234"

class EndToEndDemonstration(unittest.TestCase):
    def test_revised_inquiry_and_isolated_virtual_warehouse(self):
        previous=os.environ.get("DATABASE_PATH")
        with tempfile.TemporaryDirectory(prefix="liliang_uat_release_") as folder:
            os.environ["DATABASE_PATH"]=str(Path(folder)/"isolated.db")
            try:
                with TestClient(app) as client:
                    def signed(email,password):
                        rsp=client.post("/v1/auth/login",json={"email":email,"password":password})
                        self.assertEqual(rsp.status_code,200,rsp.text)
                        return {"Authorization":"Bearer "+rsp.json()["access_token"]}
                    admin=signed(ADMIN_EMAIL,ADMIN_PASSWORD)
                    roles={}
                    for role in ("sales","technical","manager","gudang"):
                        email="uat-demo-"+role+"@liliang.local"
                        r=client.post("/v1/users",headers=admin,json={
                            "name":"Demo "+role.title(),"email":email,"password":PASSWORD,"role":role})
                        self.assertEqual(r.status_code,201,r.text)
                        roles[role]=signed(email,PASSWORD)
                    with connect() as db:
                        original=db.execute("SELECT stock FROM products WHERE sku='FLV-STRAW-01'").fetchone()["stock"]

                    # Manager / Gudang only see virtual UAT stock; Sales/Technical may not.
                    self.assertEqual(client.get("/v1/wms/demo",headers=roles["sales"]).status_code,403)
                    empty=client.get("/v1/wms/demo",headers=roles["gudang"])
                    self.assertEqual(empty.status_code,200,empty.text)
                    self.assertTrue(empty.json()["not_company_stock"])
                    opening=client.post("/v1/wms/demo/movements",headers=roles["gudang"],json={
                        "reference":"UAT-WMS-20261031-IN-001","sku":"UAT-WMS-STRAW",
                        "movement":"IN","qty_kg":25,"note":"Simulated UAT inbound shipment"})
                    self.assertEqual(opening.status_code,201,opening.text)
                    self.assertEqual(opening.json()["balance_kg"],25)
                    too_much=client.post("/v1/wms/demo/movements",headers=roles["gudang"],json={
                        "reference":"UAT-WMS-20261031-OUT-999","sku":"UAT-WMS-STRAW",
                        "movement":"OUT","qty_kg":26,"note":"Overspend must be rejected"})
                    self.assertEqual(too_much.status_code,409)
                    outgoing=client.post("/v1/wms/demo/movements",headers=roles["gudang"],json={
                        "reference":"UAT-WMS-20261031-OUT-001","sku":"UAT-WMS-STRAW",
                        "movement":"OUT","qty_kg":10,"note":"Simulated UAT outbound request"})
                    self.assertEqual(outgoing.status_code,201,outgoing.text)
                    self.assertEqual(outgoing.json()["balance_kg"],15)
                    self.assertFalse(outgoing.json()["changed_real_stock"])
                    duplicate=client.post("/v1/wms/demo/movements",headers=roles["gudang"],json={
                        "reference":"UAT-WMS-20261031-OUT-001","sku":"UAT-WMS-STRAW",
                        "movement":"OUT","qty_kg":10,"note":"Duplicate outbound reference"})
                    self.assertEqual(duplicate.status_code,409)
                    self.assertEqual(client.post("/v1/wms/demo/movements",headers=roles["manager"],json={
                        "reference":"UAT-WMS-MANAGER-ATTEMPT","sku":"UAT-WMS-STRAW",
                        "movement":"IN","qty_kg":4,"note":"Unauthorized manager write"}).status_code,403)
                    with connect() as db:
                        after=db.execute("SELECT stock FROM products WHERE sku='FLV-STRAW-01'").fetchone()["stock"]
                        self.assertEqual(original,after)
                    self.assertEqual(client.get("/v1/reports/wms_demo?format=json",headers=roles["manager"]).status_code,200)
                    pdf=client.get("/v1/reports/wms_demo?format=pdf",headers=roles["gudang"])
                    self.assertEqual(pdf.status_code,200,pdf.text[:80])
                    self.assertTrue(pdf.content.startswith(b"%PDF"))

                    # Create inquiry, record BM25 evidence, review candidate, RETURN with reason.
                    created=client.post("/v1/inquiries",headers=roles["sales"],json={
                        "customer_ref":"UAT-E2E-20261031",
                        "requirement":"Perlu strawberry flavor untuk minuman; bentuk produk cair"})
                    self.assertEqual(created.status_code,201,created.text)
                    iid=created.json()["id"]
                    first=client.post(f"/v1/inquiries/{iid}/match",headers=roles["sales"])
                    self.assertEqual(first.status_code,200,first.text)
                    self.assertTrue(first.json()["candidates"])
                    run1=first.json()["run_id"]
                    product=first.json()["candidates"][0]["product_id"]
                    tentative=client.post(f"/v1/matches/{run1}/review",headers=roles["technical"],json={
                        "product_id":product,"decision":"NEEDS_INFO","relevance_label":2,
                        "rationale":"UAT scenario requires customer clarification"})
                    self.assertEqual(tentative.status_code,200,tentative.text)
                    returned=client.post(f"/v1/inquiries/{iid}/decision",headers=roles["manager"],json={
                        "decision":"RETURN","note":"Konfirmasi bentuk flavor dengan customer dahulu"})
                    self.assertEqual(returned.status_code,200,returned.text)
                    self.assertEqual(returned.json()["status"],"RETURNED")
                    feedback=client.get(f"/v1/inquiries/{iid}/manager-feedback",headers=roles["sales"])
                    self.assertEqual(feedback.status_code,200,feedback.text)
                    self.assertIn("Konfirmasi",feedback.json()["last_manager_decision"]["reason"])
                    self.assertEqual(client.post(f"/v1/inquiries/{iid}/revise",headers=roles["gudang"],json={
                        "requirement":"Attempt via Gudang"}).status_code,403)
                    resubmission=client.post(f"/v1/inquiries/{iid}/revise",headers=roles["sales"],json={
                        "requirement":"Perlu strawberry flavor untuk minuman susu; bentuk produk cair sudah dikonfirmasi pelanggan"})
                    self.assertEqual(resubmission.status_code,200,resubmission.text)
                    self.assertTrue(resubmission.json()["previous_runs_preserved"])
                    # Old matching run is explicitly closed and cannot satisfy a new Manager decision.
                    self.assertEqual(client.post(f"/v1/matches/{run1}/review",headers=roles["technical"],json={
                        "product_id":product,"decision":"ACCEPT","relevance_label":3,
                        "rationale":"Must not review stale run"}).status_code,409)
                    second=client.post(f"/v1/inquiries/{iid}/match",headers=roles["sales"])
                    self.assertEqual(second.status_code,200,second.text)
                    run2=second.json()["run_id"]
                    self.assertNotEqual(run1,run2)
                    self.assertEqual(client.post(f"/v1/inquiries/{iid}/decision",headers=roles["manager"],json={
                        "decision":"APPROVE","note":"Old prior run must not count"}).status_code,409)
                    reviewed=client.post(f"/v1/matches/{run2}/review",headers=roles["technical"],json={
                        "product_id":second.json()["candidates"][0]["product_id"],
                        "decision":"ACCEPT","relevance_label":3,
                        "rationale":"UAT latest matching evidence confirmed"})
                    self.assertEqual(reviewed.status_code,200,reviewed.text)
                    approved=client.post(f"/v1/inquiries/{iid}/decision",headers=roles["manager"],json={
                        "decision":"APPROVE","note":"Bukti Technical terbaru telah diterima"})
                    self.assertEqual(approved.status_code,200,approved.text)
                    self.assertEqual(approved.json()["status"],"APPROVED")
                    self.assertEqual(client.post(f"/v1/inquiries/{iid}/revise",headers=roles["sales"],json={
                        "requirement":"Do not revise an already approved inquiry"}).status_code,409)
                    report=client.get("/v1/reports/manager_decisions?format=json",headers=roles["manager"])
                    self.assertEqual(report.status_code,200,report.text)
                    self.assertTrue(any("Bukti Technical terbaru" in str(row) for row in report.json()["rows"]))
                    receipt=client.get(f"/v1/reports/inquiry/{iid}?format=json",headers=roles["sales"])
                    self.assertEqual(receipt.status_code,200,receipt.text)
                    self.assertTrue(any("Konfirmasi bentuk" in str(row) for row in receipt.json()["rows"]))
                    self.assertTrue(any("INQUIRY_REVISED" in str(row) for row in receipt.json()["rows"]))
                    pdf=client.get(f"/v1/reports/inquiry/{iid}?format=pdf",headers=roles["sales"])
                    self.assertEqual(pdf.status_code,200,pdf.text[:80])
                    self.assertTrue(pdf.content.startswith(b"%PDF"))
                    with connect() as db:
                        r=db.execute("SELECT COUNT(*) AS total FROM runs WHERE inquiry_id=?",(iid,)).fetchone()
                        self.assertEqual(r["total"],2)
                        event=db.execute("SELECT COUNT(*) AS total FROM transaction_events WHERE action='INQUIRY_REVISED' AND entity_id=?",(str(iid),)).fetchone()
                        self.assertEqual(event["total"],1)
            finally:
                if previous is None:os.environ.pop("DATABASE_PATH",None)
                else:os.environ["DATABASE_PATH"]=previous

if __name__=="__main__":
    unittest.main()

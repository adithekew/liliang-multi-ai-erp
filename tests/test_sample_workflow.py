"""Complete Sales->Technical->Manager->Gudang Sample UAT workflow acceptance."""
import os, tempfile, unittest, subprocess, shutil
from pathlib import Path
from fastapi.testclient import TestClient
from app import app,ADMIN_EMAIL,ADMIN_PASSWORD
from persistence import connect

class SampleUATWorkflow(unittest.TestCase):
    def test_approval_page_javascript_syntax(self):
        """Check separate-page inline JavaScript, in addition to existing ERP UI syntax."""
        if not shutil.which("node"):
            self.skipTest("Node binary is unavailable")
        from sample_flow import PAGE
        js=PAGE.split("<script>",1)[1].split("</script>",1)[0]
        with tempfile.TemporaryDirectory(prefix="sample_js_") as tmp:
            file=Path(tmp)/"sample_detail.js"
            file.write_text(js,encoding="utf-8")
            done=subprocess.run(["node","--check",str(file)],capture_output=True,text=True)
            self.assertEqual(done.returncode,0,done.stderr)
    def test_role_gates_stock_and_pdf_end_to_end(self):
        previous=os.environ.get("DATABASE_PATH")
        with tempfile.TemporaryDirectory(prefix="liliang_sample_flow_ci_") as tmp:
            os.environ["DATABASE_PATH"]=str(Path(tmp)/"test.db")
            try:
                with TestClient(app) as c:
                    def assert_ok(r,code=200):
                        self.assertEqual(r.status_code,code,r.text[:500]);return r.json()
                    a=assert_ok(c.post("/v1/auth/login",json={
                        "email":ADMIN_EMAIL,"password":ADMIN_PASSWORD}))
                    admin={"Authorization":"Bearer "+a["access_token"]}
                    roles={"admin":admin}
                    for role in ("sales","technical","manager","gudang"):
                        email=f"{role}.sample.uat@liliang.local"
                        pw="sample-ci-no-production-12345"
                        assert_ok(c.post("/v1/users",headers=admin,json={
                            "name":f"UAT {role}","email":email,"password":pw,"role":role}),201)
                        u=assert_ok(c.post("/v1/auth/login",json={"email":email,"password":pw}))
                        roles[role]={"Authorization":"Bearer "+u["access_token"]}
                    before={}
                    with connect() as db:
                        for x in db.execute("SELECT sku,stock FROM products"):
                            before[x["sku"]]=x["stock"]
                    self.assertEqual(c.get("/v1/transactions").status_code,401)
                    listing=c.get("/transactions")
                    self.assertEqual(listing.status_code,200)
                    self.assertIn("Sales",listing.text)
                    created=assert_ok(c.post("/v1/inquiries",headers=roles["sales"],json={
                        "customer_ref":"UAT-B2B-CUSTOMER-1",
                        "requirement":"Need strawberry flavor for dairy beverage"}),201)
                    iid=created["id"]
                    self.assertEqual(c.get(f"/transactions/{iid}").status_code,200)
                    self.assertEqual(c.get(f"/v1/transactions/{iid}",headers=roles["gudang"]).status_code,403)
                    self.assertEqual(c.post(f"/v1/transactions/{iid}/sales-submit",headers=roles["sales"],json={
                        "qty_kg":1,"recipient":"UAT-CUSTOMER","destination":"UAT-WAREHOUSE",
                        "note":"UAT sample before BM25"}).status_code,409)
                    matched=assert_ok(c.post(f"/v1/inquiries/{iid}/match",headers=roles["sales"]))
                    self.assertTrue(matched["candidates"])
                    pid=matched["candidates"][0]["product_id"]
                    sku=matched["candidates"][0]["sku"]
                    self.assertEqual(c.post(f"/v1/transactions/{iid}/sales-submit",headers=roles["technical"],json={
                        "qty_kg":1,"recipient":"UAT-CUSTOMER","destination":"UAT-WAREHOUSE",
                        "note":"UAT technical role"}).status_code,403)
                    self.assertEqual(c.post(f"/v1/transactions/{iid}/sales-submit",headers=roles["sales"],json={
                        "qty_kg":1,"recipient":"Real Customer PII","destination":"UAT-WAREHOUSE",
                        "note":"Must remain synthetic"}).status_code,422)
                    submit=assert_ok(c.post(f"/v1/transactions/{iid}/sales-submit",headers=roles["sales"],json={
                        "qty_kg":1,"recipient":"UAT-CUSTOMER","destination":"UAT-RESEARCH-LOCATION",
                        "note":"Virtual sample only"}))
                    self.assertEqual(submit["sample_status"],"WAITING_TECHNICAL")
                    self.assertEqual(c.post(f"/v1/inquiries/{iid}/decision",headers=roles["manager"],json={
                        "decision":"APPROVE","note":"Skip Technical"}).status_code,409)
                    self.assertEqual(c.post(f"/v1/transactions/{iid}/technical-submit",headers=roles["technical"],json={
                        "product_id":pid,"note":"Skip review"}).status_code,409)
                    review=assert_ok(c.post(f"/v1/matches/{matched['run_id']}/review",
                        headers=roles["technical"],json={"product_id":pid,"decision":"ACCEPT",
                        "relevance_label":3,"rationale":"UAT acceptable only as label for workflow"}))
                    self.assertEqual(review["status"],"TECH_REVIEWED")
                    self.assertEqual(c.post(f"/v1/inquiries/{iid}/decision",headers=roles["manager"],json={
                        "decision":"APPROVE","note":"No Technical Submit"}).status_code,409)
                    tech=assert_ok(c.post(f"/v1/transactions/{iid}/technical-submit",
                        headers=roles["technical"],json={"product_id":pid,
                        "note":"UAT Technical selected SKU"}))
                    self.assertEqual(tech["sample_status"],"WAITING_MANAGER")
                    self.assertEqual(c.post(f"/v1/inquiries/{iid}/decision",headers=roles["sales"],json={
                        "decision":"APPROVE","note":"Must be manager"}).status_code,403)
                    approved=assert_ok(c.post(f"/v1/inquiries/{iid}/decision",
                        headers=roles["manager"],json={"decision":"APPROVE",
                        "note":"UAT Manager authorizes virtual sample"}))
                    self.assertEqual(approved["status"],"APPROVED")
                    gd=assert_ok(c.get(f"/v1/transactions/{iid}",headers=roles["gudang"]))
                    self.assertEqual(gd["sample"]["status"],"WAITING_WAREHOUSE")
                    self.assertIsNone(gd["inquiry"]["requirement"])
                    self.assertEqual(gd["candidates"],[])
                    self.assertFalse(gd["valid_for_physical_shipment"])
                    self.assertEqual(c.get(f"/v1/transactions/{iid}/surat-jalan",
                        headers=roles["gudang"]).status_code,409)
                    ack={"note":"UAT Gudang checking virtual stock",
                         "acknowledge_virtual_only":True}
                    self.assertEqual(c.post(f"/v1/transactions/{iid}/warehouse-check",
                        headers=roles["gudang"],json=ack).status_code,409)
                    self.assertEqual(c.post("/v1/sample-stock/uat-in",headers=roles["sales"],json={
                        "sku":sku,"qty_kg":2,"reference":"UAT-STOCK-0001",
                        "note":"Wrong role","acknowledge_virtual_only":True}).status_code,403)
                    stock=assert_ok(c.post("/v1/sample-stock/uat-in",headers=roles["gudang"],json={
                        "sku":sku,"qty_kg":2,"reference":"UAT-STOCK-0001",
                        "note":"Simulate stock for test","acknowledge_virtual_only":True}))
                    self.assertEqual(stock["virtual_balance_kg"],2)
                    self.assertFalse(stock["changed_real_stock"])
                    self.assertEqual(c.post("/v1/sample-stock/uat-in",headers=roles["gudang"],json={
                        "sku":sku,"qty_kg":2,"reference":"UAT-STOCK-0001",
                        "note":"Duplicate UAT","acknowledge_virtual_only":True}).status_code,409)
                    ready=assert_ok(c.post(f"/v1/transactions/{iid}/warehouse-check",headers=roles["gudang"],json=ack))
                    self.assertEqual(ready["sample_status"],"WAREHOUSE_READY")
                    self.assertEqual(c.post(f"/v1/transactions/{iid}/warehouse-dispatch",
                        headers=roles["manager"],json=ack).status_code,403)
                    disp=assert_ok(c.post(f"/v1/transactions/{iid}/warehouse-dispatch",
                        headers=roles["gudang"],json=ack))
                    self.assertEqual(disp["sample_status"],"DISPATCHED_UAT")
                    self.assertFalse(disp["physical_shipment"])
                    self.assertEqual(disp["virtual_balance_kg"],1)
                    self.assertTrue(disp["surat_jalan"].startswith("UAT-SJ-"))
                    self.assertEqual(c.post(f"/v1/transactions/{iid}/warehouse-dispatch",
                        headers=roles["gudang"],json=ack).status_code,409)
                    pdf=c.get(f"/v1/transactions/{iid}/surat-jalan",headers=roles["gudang"])
                    self.assertEqual(pdf.status_code,200)
                    self.assertTrue(pdf.content.startswith(b"%PDF"))
                    with connect() as db:
                        for x in db.execute("SELECT sku,stock FROM products"):
                            self.assertEqual(x["stock"],before[x["sku"]])
                        self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM sample_uat_movements WHERE movement='OUT'").fetchone()["n"],1)
                        self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM sample_requests WHERE status='DISPATCHED_UAT'").fetchone()["n"],1)
            finally:
                if previous is None:os.environ.pop("DATABASE_PATH",None)
                else:os.environ["DATABASE_PATH"]=previous

if __name__=="__main__":unittest.main()

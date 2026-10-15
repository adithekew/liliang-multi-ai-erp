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
        db=connect()
        try:self.assertIsNotNone(db.execute("SELECT id FROM inquiries WHERE id=?",(iid,)).fetchone())
        finally:db.close()

if __name__=="__main__":unittest.main()

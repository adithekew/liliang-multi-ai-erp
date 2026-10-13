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
        db=connect()
        try:self.assertIsNotNone(db.execute("SELECT id FROM inquiries WHERE id=?",(iid,)).fetchone())
        finally:db.close()

if __name__=="__main__":unittest.main()

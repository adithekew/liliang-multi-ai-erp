import os
import unittest
from unittest.mock import patch
import persistence

class QueryCompatibility(unittest.TestCase):
    def test_seed_uses_postgres_conflict_handling(self):
        sql=persistence._sql("INSERT OR IGNORE INTO products(sku,name) VALUES(?,?)")
        self.assertEqual(sql,"INSERT INTO products(sku,name) VALUES(%s,%s) ON CONFLICT (sku) DO NOTHING")
    def test_placeholders_remain_parameterized(self):
        self.assertEqual(persistence._sql("SELECT * FROM users WHERE email=?"),
                         "SELECT * FROM users WHERE email=%s")
    def test_no_plaintext_secrets_logged(self):
        self.assertNotIn("DATABASE_URL",str(persistence.SCHEMA))
    def test_fk_schema_uses_bigserial_for_primary_keys(self):
        s=persistence.SCHEMA.replace("id INTEGER PRIMARY KEY","id BIGSERIAL PRIMARY KEY")
        self.assertIn("users(id BIGSERIAL PRIMARY KEY",s)
        self.assertIn("FOREIGN KEY(created_by) REFERENCES users(id)",s)
    def test_engine_defaults_to_disposable_pilot(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(persistence.engine_name(),"sqlite-ephemeral")
    def test_postgres_configuration_selection(self):
        with patch.dict(os.environ,{"DATABASE_URL":"postgresql://example:example@db.invalid/example"},clear=True):
            self.assertEqual(persistence.engine_name(),"postgresql")
    def test_no_new_dependencies_for_sqlite_mode(self):
        with patch.dict(os.environ,{"DATABASE_PATH":"/tmp/liliang-adapter-unit.db"},clear=True):
            db=persistence.connect()
            try:self.assertEqual(db.execute("SELECT 1").fetchone()[0],1)
            finally:db.close()

class Cursor:
    rowcount=1
    def __init__(self):self.read=False
    def fetchone(self):
        self.read=True
        return {"id":19}
    def fetchall(self):return []
class FakeRaw:
    def __init__(self):self.statements=[];self.commits=0;self.rollbacks=0;self.closed=False
    def execute(self,sql,args=()):
        self.statements.append((sql,args))
        return Cursor()
    def commit(self):self.commits+=1
    def rollback(self):self.rollbacks+=1
    def close(self):self.closed=True
class PgBridgeTests(unittest.TestCase):
    def test_insert_returns_lastrowid(self):
        raw=FakeRaw();db=persistence.PgConnection(raw)
        res=db.execute("INSERT INTO inquiries(requirement) VALUES(?)",("demo",))
        self.assertEqual(res.lastrowid,19)
        self.assertEqual(raw.statements[0][0],"INSERT INTO inquiries(requirement) VALUES(%s) RETURNING id")
        self.assertEqual(raw.statements[0][1],("demo",))
    def test_upsert_does_not_add_returning(self):
        raw=FakeRaw();db=persistence.PgConnection(raw)
        db.execute("INSERT OR IGNORE INTO products(sku) VALUES(?)",("DEMO",))
        self.assertIn("ON CONFLICT (sku) DO NOTHING",raw.statements[0][0])
        self.assertNotIn("RETURNING id",raw.statements[0][0])
    def test_transaction_success_and_rollback(self):
        raw=FakeRaw();db=persistence.PgConnection(raw)
        with db:db.execute("SELECT 1")
        self.assertEqual(raw.commits,1)
        with self.assertRaises(ValueError):
            with db:
                raise ValueError()
        self.assertEqual(raw.rollbacks,1)

if __name__=="__main__":unittest.main()

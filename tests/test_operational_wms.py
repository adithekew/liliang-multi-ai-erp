import sqlite3
import unittest
from wms_operational import install_operational_wms_schema, stock_rows, _balance, _reserved

class OperationalWmsLedgerTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.row_factory=sqlite3.Row
        install_operational_wms_schema(self.db)
        self.db.execute("INSERT INTO wms_operational_warehouses VALUES(?,?,?,?,?)",
          ("WH-A","Warehouse A","ACTIVE","2026-11-22T00:00:00Z",1))
    def tearDown(self):self.db.close()
    def test_opening_receipt_and_transfer_balances(self):
        self.db.execute("""INSERT INTO wms_operational_movements
          (movement_id,idempotency_key,movement_type,sku,qty,unit,to_warehouse,to_bin,
           reference_document,actor_id,created_at,note,status)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          ("M1","K1","OPENING_BALANCE","SKU-001",100,"KG","WH-A","A-01","COUNT-REF-001",1,"2026-11-22T00:00:00Z","count","POSTED"))
        self.db.execute("""INSERT INTO wms_operational_movements
          (movement_id,idempotency_key,movement_type,sku,qty,unit,from_warehouse,from_bin,
           to_warehouse,to_bin,reference_document,actor_id,created_at,note,status)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          ("M2","K2","TRANSFER","SKU-001",20,"KG","WH-A","A-01","WH-A","A-02","TRF-REF-001",1,"2026-11-22T00:01:00Z","transfer","POSTED"))
        self.assertEqual(_balance(self.db,"SKU-001","WH-A","A-01",None,"KG"),80)
        self.assertEqual(_balance(self.db,"SKU-001","WH-A","A-02",None,"KG"),20)
        rows=stock_rows(self.db)
        self.assertEqual(sum(x["on_hand"] for x in rows),100)
    def test_reservations_reduce_available_not_physical_on_hand(self):
        self.db.execute("""INSERT INTO wms_operational_movements
          (movement_id,idempotency_key,movement_type,sku,qty,unit,to_warehouse,to_bin,
           reference_document,actor_id,created_at,note,status)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          ("M1","K1","OPENING_BALANCE","SKU-001",50,"KG","WH-A","A-01","COUNT-REF-001",1,"2026-11-22T00:00:00Z","count","POSTED"))
        self.db.execute("""INSERT INTO wms_operational_reservations
          (reservation_id,idempotency_key,sku,warehouse_id,bin_id,qty,unit,reference_document,actor_id,created_at,status)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
          ("R1","RK1","SKU-001","WH-A","A-01",15,"KG","SO-REF-001",1,"2026-11-22T00:01:00Z","ACTIVE"))
        rows=stock_rows(self.db)[0]
        self.assertEqual(rows["on_hand"],50)
        self.assertEqual(rows["reserved"],15)
        self.assertEqual(rows["available"],35)

if __name__=="__main__":unittest.main()

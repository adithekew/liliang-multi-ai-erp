"""PostgreSQL adapter for the existing research-pilot SQL interface.

When DATABASE_URL is unset, the app continues using disposable SQLite.
No credentials or customer records are included in source control.
"""
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from os import getenv

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE,name TEXT,description TEXT,profile TEXT,application TEXT,stock REAL DEFAULT 0,source_ref TEXT);
CREATE TABLE IF NOT EXISTS inquiries(id INTEGER PRIMARY KEY,requirement TEXT,customer_ref TEXT,created_by INTEGER,status TEXT DEFAULT 'NEW',created_at TEXT,FOREIGN KEY(created_by) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,inquiry_id INTEGER,method TEXT,latency_ms INTEGER,created_at TEXT,FOREIGN KEY(inquiry_id) REFERENCES inquiries(id));
CREATE TABLE IF NOT EXISTS candidates(id INTEGER PRIMARY KEY,run_id INTEGER,product_id INTEGER,score REAL,rank INTEGER,unknown TEXT,FOREIGN KEY(run_id) REFERENCES runs(id));
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,run_id INTEGER,product_id INTEGER,reviewer_id INTEGER,decision TEXT,label INTEGER,note TEXT);
CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,actor_id INTEGER,action TEXT,entity TEXT,entity_id INTEGER,at TEXT);
CREATE TABLE IF NOT EXISTS transaction_events(id TEXT PRIMARY KEY,actor_id INTEGER,actor_role TEXT,action TEXT,entity TEXT,entity_id TEXT,at TEXT,request_id TEXT,before_json TEXT,after_json TEXT,payload_sha256 TEXT);
CREATE TABLE IF NOT EXISTS reset_archives(id TEXT PRIMARY KEY,actor_id INTEGER,at TEXT,counts_json TEXT,archive_json TEXT,payload_sha256 TEXT);
CREATE TABLE IF NOT EXISTS catalog_import_batches(id TEXT PRIMARY KEY,source_sha256 TEXT UNIQUE,source_file TEXT,catalog_version TEXT,items_imported INTEGER,actor_id INTEGER,at TEXT,source_classification TEXT);
CREATE TABLE IF NOT EXISTS catalog_product_details(sku TEXT PRIMARY KEY,product_type TEXT,application_raw TEXT,composition_raw TEXT,source_page INTEGER,source_number INTEGER,source_sha256 TEXT,batch_id TEXT);
CREATE TABLE IF NOT EXISTS user_sessions(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,created_at REAL NOT NULL,last_seen_at REAL NOT NULL,expires_at REAL NOT NULL,revoked_at REAL);

"""
TABLES_WITH_IDS = {"users","products","inquiries","runs","candidates","reviews","audits"}
def is_postgres():
    return bool(getenv("DATABASE_URL", "").strip())
def engine_name():
    return "postgresql" if is_postgres() else "sqlite-ephemeral"

def _sql(statement):
    """Transform parameter binding and one SQLite-specific upsert syntax.

    SQL arguments remain parameterized. This does NOT interpolate user data.
    """
    statement=re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\s+products\b",
                     "INSERT INTO products", statement, flags=re.IGNORECASE)
    is_product_seed="INSERT INTO products" in statement
    statement=statement.replace("?", "%s")
    if is_product_seed and "ON CONFLICT" not in statement:
        statement+=" ON CONFLICT (sku) DO NOTHING"
    return statement

class PgResult:
    def __init__(self, cursor, lastrowid=None):
        self._cursor=cursor
        self.lastrowid=lastrowid
        self.rowcount=cursor.rowcount
    def fetchone(self):
        return self._cursor.fetchone()
    def fetchall(self):
        return self._cursor.fetchall()

class PgConnection:
    """Compatibility layer; one connection per web request, no cross-request sharing."""
    def __init__(self, raw):
        self._raw=raw
    def execute(self, statement, args=()):
        stmt=_sql(statement)
        match=re.match(r"^\s*INSERT\s+INTO\s+(\w+)\s*\(",stmt,re.IGNORECASE)
        wants_id=bool(match and match.group(1).lower() in TABLES_WITH_IDS
                      and not re.search(r"\b(RETURNING|ON\s+CONFLICT)\b",stmt,re.IGNORECASE))
        if wants_id:
            stmt+=" RETURNING id"
        cur=self._raw.execute(stmt, args)
        lastrowid=None
        if wants_id:
            item=cur.fetchone()
            lastrowid=item["id"] if item else None
        return PgResult(cur,lastrowid)
    def executescript(self, script):
        for statement in script.split(";"):
            if statement.strip():
                self._raw.execute(statement.strip())
    def commit(self):
        self._raw.commit()
    def rollback(self):
        self._raw.rollback()
    def close(self):
        self._raw.close()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False

def connect():
    uri=getenv("DATABASE_URL","").strip()
    if uri:
        scheme=urlsplit(uri).scheme
        if scheme not in ("postgres","postgresql"):
            raise RuntimeError("DATABASE_URL must use a PostgreSQL connection URI")
        import psycopg
        from psycopg.rows import dict_row
        # Only loopback development can negotiate non-TLS local PostgreSQL.
        # Remote Neon connections always require TLS encryption.
        sslmode="prefer" if urlsplit(uri).hostname in ("localhost","127.0.0.1") else "require"
        raw=psycopg.connect(uri,row_factory=dict_row,connect_timeout=12,sslmode=sslmode)
        return PgConnection(raw)
    path=getenv("DATABASE_PATH","/tmp/liliang-erp-pilot.db")
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=20,check_same_thread=False)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA busy_timeout=20000")
    db.execute("PRAGMA foreign_keys=ON")
    return db

def install_schema(db):
    if isinstance(db,PgConnection):
        script=SCHEMA.replace("id INTEGER PRIMARY KEY","id BIGSERIAL PRIMARY KEY")
        db.executescript(script)
    else:
        db.executescript(SCHEMA)

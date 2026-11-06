"""Unverified catalog stock reference from user-supplied supplier-register CSV.

This module intentionally NEVER modifies products.stock or sample_uat_balances.
No unit is inferred. Values are informational, not available-to-promise stock.
"""
from fastapi import Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

ROLES={"admin","sales","technical","manager","gudang"}
SOURCE_SHA="72d38183117d4ab3a5473de20ba4a15d60df7be02e9a4e05c7ab7884ab59deb2"

def install_stock_reference_schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS catalog_stock_import_batches(
      source_sha256 TEXT PRIMARY KEY, filename TEXT NOT NULL,
      source_label TEXT NOT NULL, source_generated_at TEXT,
      row_count INTEGER NOT NULL, recorded_sum NUMERIC(18,3) NOT NULL,
      units_status TEXT NOT NULL DEFAULT 'UNSPECIFIED',
      verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
      imported_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS catalog_stock_reference(
      sku TEXT PRIMARY KEY,
      reported_stock NUMERIC(18,3) NOT NULL,
      unit TEXT NOT NULL DEFAULT 'UNSPECIFIED',
      source_ref TEXT NOT NULL,
      source_sha256 TEXT NOT NULL,
      pdf_page INTEGER, pdf_row INTEGER,
      verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
      imported_at TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_catalog_stock_reference_status ON catalog_stock_reference(verification_status)")

def mount_stock_reference(app,current,get_db):
    @app.get("/v1/catalog/stock-reference")
    def stock_reference(
        search:str=Query(default="",max_length=80),
        offset:int=Query(default=0,ge=0,le=100000),
        limit:int=Query(default=50,ge=1,le=200),
        u=Depends(current),db=Depends(get_db)
    ):
        if u["role"] not in ROLES:
            raise HTTPException(403,"Role not allowed")
        q=search.strip().casefold()
        param=("%"+q+"%",)
        where="WHERE LOWER(s.sku) LIKE ? OR LOWER(p.name) LIKE ?" if q else ""
        args=(param[0],param[0]) if q else ()
        summary=db.execute("""SELECT COUNT(*) AS sku_count,
          COALESCE(SUM(reported_stock),0) AS reported_total,
          COUNT(*) FILTER (WHERE verification_status='UNVERIFIED') AS unverified_skus
          FROM catalog_stock_reference""").fetchone()
        count=db.execute("""SELECT COUNT(*) AS n FROM catalog_stock_reference s
           JOIN products p ON p.sku=s.sku """+where,args).fetchone()["n"]
        rows=db.execute("""SELECT s.sku,p.name AS product,s.reported_stock,s.unit,
          s.source_ref,s.verification_status,s.pdf_page,s.pdf_row,
          p.stock AS legacy_product_stock
          FROM catalog_stock_reference s JOIN products p ON p.sku=s.sku
          """+where+""" ORDER BY s.sku LIMIT ? OFFSET ?""",args+(limit,offset)).fetchall()
        return {
            "rows":[dict(r) for r in rows],
            "total_matching":count,
            "sku_count":summary["sku_count"],
            "reported_total":summary["reported_total"],
            "unverified_skus":summary["unverified_skus"],
            "source_file":"Liliang_Report_catalog_updated.csv",
            "source_sha256":SOURCE_SHA,
            "source_generated_utc":"2026-10-30T03:28:46.628726+00:00",
            "source_status":"CATALOG-PDF-UNVERIFIED",
            "unit_status":"UNSPECIFIED",
            "stock_status":"REFERENCE_ONLY_NOT_PHYSICAL",
            "changes_company_stock":False,
            "dispatch_eligible":False,
            "note":"Angka stock berasal dari CSV katalog yang belum diverifikasi; satuan tidak tercantum. Tidak dapat digunakan sebagai stok fisik untuk Surat Jalan.",
        }

    @app.get("/stock/reference",response_class=HTMLResponse,include_in_schema=False)
    def stock_reference_page():
        return HTMLResponse(STOCK_PAGE,headers={
            "Cache-Control":"private, no-store",
            "X-Content-Type-Options":"nosniff"
        })

STOCK_PAGE=r"""<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PT Liliang · Stok Referensi CSV</title><link rel="icon" href="/branding/logo?v=20261020">
<style>
:root{font:14px/1.5 system-ui,Segoe UI,Arial;background:#f3f7fc;color:#17324c}
*{box-sizing:border-box}body{margin:0}header{background:#102545;color:#fff;padding:16px 6%;display:flex;align-items:center;gap:18px}
header img{width:145px;background:black;border-radius:7px}main{max-width:1400px;margin:24px auto;padding:0 24px}
h1{font-size:26px;margin:6px 0 16px}.card{background:white;border:1px solid #dce6f1;border-radius:15px;padding:23px;margin-bottom:18px}
.notice{border-left:4px solid #d99b31;background:#fff7e9;padding:13px 16px;color:#74511e;margin:15px 0}
label{font-weight:700;display:block;margin-bottom:7px}input{border:1px solid #d2ddec;border-radius:9px;padding:11px;min-width:260px;max-width:550px;width:100%;font:inherit}
button{padding:11px 16px;background:#2266b1;border:0;color:#fff;font:inherit;font-weight:bold;border-radius:9px;cursor:pointer}
button:disabled{opacity:.45}.btn-alt{background:#e8f0fa;color:#164d8b}a{color:#2263aa}.row{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
.metric{background:#f4f8ff;border-radius:12px;padding:18px;flex:1;min-width:180px}.metric b{display:block;font-size:26px}
.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px}
th,td{border-bottom:1px solid #e8edf4;padding:11px;text-align:left;white-space:nowrap}
th{background:#eff4fb}.badge{background:#fff2dd;color:#855a16;font-weight:bold;font-size:10px;padding:6px 8px;border-radius:6px}
.muted{color:#7b8ea2;font-size:12px}#error{color:#b13146}
@media(max-width:700px){header{display:block}main{padding:0 13px}.card{padding:16px}}
</style></head><body>
<header><img src="/branding/logo?v=20261020" alt="PT Liliang International">
<div><strong>ERP Multi-AI · Stock Reference Register</strong><div style="font-size:12px;color:#b8d0ec">Penelitian · Import CSV UAT · Tanpa perubahan stok fisik</div></div></header>
<main><p><a href="/workspace">Multi-AI Workspace</a> › <a href="/transactions">Transaksi & Approval</a> › Stok Referensi CSV</p>
<h1>Referensi Stok dari CSV</h1>
<div class="notice"><b>Belum diverifikasi.</b> Angka dalam kolom Stock berasal dari katalog pemasok, satuan tidak diberikan,
dan tidak merepresentasikan stok fisik siap kirim. Gudang harus memakai saldo UAT terpisah untuk simulasi, atau stok fisik yang telah diverifikasi dalam implementasi produksi.</div>
<section class="card"><div class="row" id="metrics"></div><p class="muted" id="source"></p></section>
<section class="card"><label for="search">Cari SKU / Nama Flavor</label>
<div class="row"><input id="search" placeholder="Contoh: strawberry / 11100029" autocomplete="off">
<button id="searchBtn">Cari SKU</button><button id="clearBtn" class="btn-alt">Reset</button></div>
<p id="error" role="alert"></p><div class="tablewrap"><table>
<thead><tr><th>SKU</th><th>Nama Flavor</th><th>Stock (angka CSV)</th><th>Satuan</th><th>Verifikasi</th><th>Referensi PDF</th></tr></thead>
<tbody id="items"></tbody></table></div><p id="pagination"></p>
<div class="row"><button class="btn-alt" id="prev">Sebelumnya</button><button class="btn-alt" id="next">Berikutnya</button></div>
</section></main><script>
const token=sessionStorage.getItem("liliang_token")||"";
const $=id=>document.getElementById(id);
const safe=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let offset=0,limit=50,search="";
const n=v=>Number(v||0).toLocaleString("id-ID");
async function load(){
 if(!token){$("error").textContent="Login ke ERP /workspace terlebih dahulu.";return}
 try{
 let r=await fetch("/v1/catalog/stock-reference?search="+encodeURIComponent(search)+"&offset="+offset+"&limit="+limit,
 {headers:{Authorization:"Bearer "+token},cache:"no-store"});
 let data=await r.json();
 if(!r.ok)throw Error(data.detail||"Gagal mengambil referensi stok");
 $("metrics").innerHTML='<div class="metric"><span>SKU dalam Referensi</span><b>'+n(data.sku_count)+
 '</b></div><div class="metric"><span>Total Nilai Stock CSV</span><b>'+n(data.reported_total)+
 '</b></div><div class="metric"><span>Belum Diverifikasi</span><b>'+n(data.unverified_skus)+'</b></div>';
 $("source").textContent="Sumber: "+data.source_file+" · "+data.source_status+" · Satuan: BELUM DIKETAHUI";
 $("items").innerHTML=data.rows.map(x=>'<tr><td>'+safe(x.sku)+'</td><td>'+safe(x.product)+'</td>'+
 '<td>'+n(x.reported_stock)+'</td><td>UNSPECIFIED</td><td><span class="badge">'+
 safe(x.verification_status)+'</span></td><td>Page '+safe(x.pdf_page)+' / Row '+safe(x.pdf_row)+'</td></tr>').join("");
 if(!data.rows.length)$("items").innerHTML='<tr><td colspan="6">Tidak ditemukan.</td></tr>';
 $("pagination").textContent="Menampilkan "+(data.rows.length?offset+1:0)+"–"+(offset+data.rows.length)+" dari "+n(data.total_matching)+" SKU";
 $("prev").disabled=offset===0;$("next").disabled=offset+limit>=Number(data.total_matching);
 $("error").textContent="";
 }catch(e){$("error").textContent=e.message}
}
$("searchBtn").onclick=()=>{search=$("search").value.trim();offset=0;load()};
$("search").onkeydown=e=>{if(e.key==="Enter")$("searchBtn").click()};
$("clearBtn").onclick=()=>{$("search").value="";search="";offset=0;load()};
$("prev").onclick=()=>{offset=Math.max(0,offset-limit);load()};
$("next").onclick=()=>{offset+=limit;load()};
load();
</script></body></html>"""

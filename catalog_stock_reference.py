"""User-confirmed physical inventory with explicit packaging rules and source provenance.

The physical reconciliation is performed once by an audited migration, not at request time.
No UoM is inferred for types other than Powder, Paste, Liquid.
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
    db.execute("""CREATE TABLE IF NOT EXISTS physical_inventory_stock(
      sku TEXT PRIMARY KEY,
      product_type TEXT NOT NULL,
      qty_packages NUMERIC(18,3) NOT NULL CHECK (qty_packages>=0),
      package_uom TEXT NOT NULL,
      package_content NUMERIC(18,3),
      content_uom TEXT,
      dispatch_uom_status TEXT NOT NULL,
      confirmation_status TEXT NOT NULL,
      source_sha256 TEXT NOT NULL,
      confirmed_at TEXT NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS physical_stock_confirmation(
      source_sha256 TEXT PRIMARY KEY,
      confirmation_text TEXT NOT NULL,
      confirmed_at TEXT NOT NULL,
      confirmed_skus INTEGER NOT NULL,
      package_rules TEXT NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS physical_stock_before_snapshot(
      source_sha256 TEXT NOT NULL,
      sku TEXT NOT NULL,
      prior_stock NUMERIC(18,3),
      PRIMARY KEY(source_sha256,sku)
    )""")

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
        physical=db.execute("""SELECT COUNT(*) AS physical_skus,
          COALESCE(SUM(qty_packages),0) AS packages_total,
          COUNT(*) FILTER(WHERE dispatch_uom_status='UNIT_DEFINED') AS mapped_skus,
          COUNT(*) FILTER(WHERE dispatch_uom_status='UOM_PENDING') AS pending_skus
          FROM physical_inventory_stock""").fetchone()
        summary=db.execute("""SELECT COUNT(*) AS sku_count,
          COALESCE(SUM(reported_stock),0) AS reported_total,
          COUNT(*) FILTER (WHERE verification_status='UNVERIFIED') AS unverified_skus
          FROM catalog_stock_reference""").fetchone()
        count=db.execute("""SELECT COUNT(*) AS n FROM catalog_stock_reference s
           JOIN products p ON p.sku=s.sku """+where,args).fetchone()["n"]
        rows=db.execute("""SELECT s.sku,p.name AS product,
          d.product_type,
          s.reported_stock,s.unit,s.source_ref,s.verification_status,
          s.pdf_page,s.pdf_row,p.stock AS legacy_product_stock,
          v.qty_packages AS physical_packages,v.package_uom,
          v.package_content,v.content_uom,
          v.dispatch_uom_status,v.confirmation_status
          FROM catalog_stock_reference s JOIN products p ON p.sku=s.sku
          LEFT JOIN catalog_product_details d ON d.sku=s.sku
          LEFT JOIN physical_inventory_stock v ON v.sku=s.sku
          """+where+""" ORDER BY s.sku LIMIT ? OFFSET ?""",args+(limit,offset)).fetchall()
        return {
            "rows":[dict(r) for r in rows],
            "total_matching":count,
            "sku_count":summary["sku_count"],
            "physical_confirmed_skus":physical["physical_skus"],
            "physical_packages_total":physical["packages_total"],
            "physical_uom_defined_skus":physical["mapped_skus"],
            "physical_uom_pending_skus":physical["pending_skus"],
            "reported_total":summary["reported_total"],
            "unverified_skus":summary["unverified_skus"],
            "source_file":"Liliang_Report_catalog_updated.csv",
            "source_sha256":SOURCE_SHA,
            "source_generated_utc":"2026-10-30T03:28:46.628726+00:00",
            "source_status":"CATALOG-PDF-UNVERIFIED",
            "unit_status":"UNSPECIFIED",
            "stock_status":"USER_CONFIRMED_PHYSICAL" if physical["physical_skus"]==summary["sku_count"] and summary["sku_count"] else "REFERENCE_ONLY_NOT_PHYSICAL",
            "changes_company_stock":bool(physical["physical_skus"]),
            "dispatch_eligible":False, # Legacy sample module still uses virtual UAT balances, not physical dispatch.
            "note":("Persediaan fisik dinyatakan tersedia oleh pengguna 6 Nov 2026; "
                    "aturan kemasan hanya Powder 300g/unit, Paste 200ml/botol, Liquid 500ml/dirigen. "
                    "SKU lain menunggu aturan UoM. Pengiriman fisik belum aktif karena workflow Surat Jalan "
                    "masih berupa UAT dan memakai saldo stok virtual.") if physical["physical_skus"] else
                   "CSV belum mendapat pengesahan stok fisik.",
        }

    @app.get("/stock/reference",response_class=HTMLResponse,include_in_schema=False)
    def stock_reference_page():
        return HTMLResponse(STOCK_PAGE,headers={
            "Cache-Control":"private, no-store",
            "X-Content-Type-Options":"nosniff"
        })

STOCK_PAGE=r"""<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PT Liliang · Stok Fisik & Kemasan</title><link rel="icon" href="/branding/logo?v=20261020">
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
<div><strong>ERP Multi-AI · Stock Reference Register</strong><div style="font-size:12px;color:#b8d0ec">Persediaan dikonfirmasi · 6 Nov 2026 · Per kemasan</div></div></header>
<main><p><a href="/workspace">Multi-AI Workspace</a> › <a href="/transactions">Transaksi & Approval</a> › Stok Fisik & Kemasan</p>
<h1>Persediaan Fisik & Kemasan</h1>
<div class="notice"><b>Stok fisik dikonfirmasi pengguna, 6 November 2026.</b> Jumlah dihitung per kemasan, bukan otomatis KG/L. Powder: 300 gram/unit; Paste: 200 ml/botol; Liquid: 500 ml/dirigen. Sebanyak 487 SKU kategori lain masih menunggu aturan kemasan. <b>Catatan:</b> alur Surat Jalan ERP saat ini tetap UAT virtual, belum mengurangi stok fisik ini.</div>
<section class="card"><div class="row" id="metrics"></div><p class="muted" id="source"></p></section>
<section class="card"><label for="search">Cari SKU / Nama Flavor</label>
<div class="row"><input id="search" placeholder="Contoh: strawberry / 11100029" autocomplete="off">
<button id="searchBtn">Cari SKU</button><button id="clearBtn" class="btn-alt">Reset</button></div>
<p id="error" role="alert"></p><div class="tablewrap"><table>
<thead><tr><th>SKU</th><th>Nama Flavor</th><th>Jenis</th><th>Stok Fisik</th><th>Satuan Kemasan</th><th>Isi / Kemasan</th><th>Status Kemasan</th></tr></thead>
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
 $("metrics").innerHTML='<div class="metric"><span>SKU Stok Fisik Dikonfirmasi</span><b>'+n(data.physical_confirmed_skus)+
 '</b></div><div class="metric"><span>Total Kemasan (Campuran UoM)</span><b>'+n(data.physical_packages_total)+
 '</b></div><div class="metric"><span>UoM Ditetapkan</span><b>'+n(data.physical_uom_defined_skus)+
 '</b></div><div class="metric"><span>UoM Belum Ditetapkan</span><b>'+n(data.physical_uom_pending_skus)+'</b></div>';
 $("source").textContent="Dokumen: "+data.source_file+" · Katalog sumber "+data.source_status+" · Konfirmasi fisik: "+data.stock_status;
 $("items").innerHTML=data.rows.map(x=>'<tr><td>'+safe(x.sku)+'</td><td>'+safe(x.product)+'</td>'+
 '<td>'+safe(x.product_type||"UNKNOWN")+'</td><td>'+n(x.physical_packages??x.reported_stock)+'</td>'+
 '<td>'+safe(x.package_uom||"BELUM DITETAPKAN")+'</td>'+
 '<td>'+safe(x.package_content??"–")+' '+safe(x.content_uom||"")+'</td>'+
 '<td><span class="badge">'+safe(x.dispatch_uom_status||"PENDING")+'</span></td></tr>').join("");
 if(!data.rows.length)$("items").innerHTML='<tr><td colspan="7">Tidak ditemukan.</td></tr>';
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

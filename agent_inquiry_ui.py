"""Dedicated research screen for saved enterprise inquiry advice.

The page never sends the saved inquiry, customer, SKU or stock to Groq.
"""
PAGE = r"""<!doctype html><html lang="id"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PT Liliang | Inquiry Intelligence Advisor</title>
<link rel="icon" href="/branding/logo?v=20261020">
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f7fc;color:#19314e;font:14px/1.58 system-ui,Segoe UI,Arial}
.layout{display:flex;min-height:100vh}aside{background:#102441;color:#dce9fc;width:236px;flex-shrink:0;padding:20px 16px}
aside img{width:100%;background:#060e1d;border-radius:9px}aside a{display:block;padding:13px;color:#d5e4f8;text-decoration:none;border-radius:9px;font-size:12px;font-weight:750;margin-top:7px}
aside a.active,aside a:hover{background:#285184;color:#fff}aside small{display:block;color:#94afd3;margin:15px 3px 8px;letter-spacing:.12em}
main{min-width:0;flex:1}.top{background:white;border-bottom:1px solid #dfe9f3;padding:20px 30px;font-weight:800}
.wrap{max-width:1360px;margin:auto;padding:28px}h1{font-size:29px;margin:9px 0}h2{font-size:18px;margin:0 0 13px}
.eyebrow{letter-spacing:.13em;color:#3d74af;font-size:11px;font-weight:850}
.hero{background:linear-gradient(110deg,#17345e,#276ba4);border-radius:15px;color:white;padding:28px 32px}
.hero h1{margin:9px 0}.hero p{color:#e0eefa;font-size:13px;max-width:750px;margin:0}
.card{background:white;border:1px solid #dfe9f3;border-radius:13px;padding:23px;margin:17px 0}
.controlrow{display:flex;flex-wrap:wrap;gap:12px;align-items:end}
.flex{flex:1;min-width:220px}label{display:block;color:#576f8b;font-size:12px;font-weight:750;margin-bottom:6px}
select,input{padding:10px 12px;width:100%;font:inherit;border-radius:8px;border:1px solid #cbd9e8;background:white;min-height:43px}
button{font:inherit;cursor:pointer;font-weight:800;border:0;border-radius:9px;background:#2468af;color:white;padding:11px 16px}
button:disabled{opacity:.55;cursor:default}.link{color:#245d9a;text-decoration:none}
.note{border-left:3px solid #d7a349;background:#fff7e9;padding:13px 17px;border-radius:6px;font-size:12px}
.dim{color:#7c91aa;font-size:12px}.pill{display:inline-block;background:#eaf2fc;color:#275e9a;padding:5px 9px;border-radius:40px;font-size:11px;font-weight:750}
.pill.warn{background:#fff0da;color:#885919}.pill.ok{background:#e6f8ef;color:#15734d}
.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:16px}
.kv{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.metric{background:#f5f8fc;padding:12px;border-radius:9px}
.metric small{display:block;color:#7c91a7;font-size:11px}.metric strong{font-size:13px}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{text-align:left;padding:10px;border-bottom:1px solid #e7eef5;vertical-align:top}
th{background:#f4f7fa;color:#53708b}.scroll{overflow:auto}
ul{padding-left:20px;margin:4px 0;font-size:12px}.flag{color:#8d5b1a;font-size:10px}
#output{display:none}.footer{font-size:11px;color:#889aad;margin:25px 0}
@media(max-width:850px){aside{width:170px}.wrap{padding:15px}.grid{grid-template-columns:1fr}}
@media(max-width:620px){aside{display:none}.top{padding:15px}.kv{grid-template-columns:1fr}}
</style></head><body><div class="layout"><aside>
<img src="/branding/logo?v=20261020" alt="PT Liliang International">
<small>AI INTELLIGENCE</small>
<a href="/ai/agent-pilot">✦ AI Agent Orchestrator</a>
<a href="/ai/inquiry-advisor" class="active">◈ Inquiry Intelligence Advisor</a>
<a href="/workspace">▤ Multi-AI Workspace</a>
<small>BUSINESS WORKFLOW</small>
<a href="/transactions">▥ Sales · Transaksi & Approval</a>
<a href="/stock/reference">◉ Stok Fisik & Kemasan</a></aside>
<main><div class="top">PT Liliang International · Enterprise Intelligence</div>
<div class="wrap">
<section class="hero"><div class="eyebrow" style="color:#b1d6ff">ERP BUSINESS PROCESS INTELLIGENCE</div>
<h1>Sales Inquiry Intelligence Advisor</h1>
<p>Pemeriksaan terpadu kebutuhan pelanggan, ranking BM25, review Technical dan stok fisik pada inquiry yang sudah tersimpan. Semua data diproses di ERP dalam mode read-only.</p></section>
<section class="card"><h2>Analisis Inquiry Tersimpan</h2>
<div class="controlrow"><div class="flex"><label for="inquiry">Pilih inquiry (sesuai akses role)</label>
<select id="inquiry"><option value="">Memuat inquiry...</option></select></div>
<div><button id="run">Analisis Inquiry ERP</button></div></div>
<p id="status" role="status" class="dim">Memeriksa sesi dan hak akses ERP...</p>
<div class="note">Agent hanya memberikan rekomendasi. Kelayakan produk, dokumen teknis dan regulasi harus diperiksa Technical. Persetujuan Manager dan pengecekan Gudang tetap dilakukan melalui workflow transaksi resmi.</div></section>
<div id="output">
<div class="grid">
<section class="card"><h2>Interpretasi Kebutuhan · AI-01</h2>
<div id="requirement" class="note" style="background:#f6f9fd;border-color:#4688c7"></div>
<div class="kv" style="margin-top:15px" id="attributes"></div>
</section>
<section class="card"><h2>Tindak Lanjut Proses</h2>
<p id="insight"></p><div id="nextAction" class="note"></div>
<p class="dim">Hasil advisory tidak mengubah status inquiry atau membuat dokumen pengiriman.</p>
<a id="transaction" class="link">Buka detail transaksi →</a></section>
</div>
<section class="card"><h2>Kandidat Produk · AI-02 & Stok Fisik</h2>
<div class="scroll"><table><thead><tr><th>Rank</th><th>SKU / Produk</th><th>BM25</th><th>Stok</th><th>Isi per Kemasan</th><th>Review Technical</th><th>Temuan Risiko</th></tr></thead>
<tbody id="candidates"></tbody></table></div>
<p class="dim">Nilai BM25 bukan peluang keberhasilan. Angka stok dinyatakan berdasarkan konfirmasi pengguna; satuan untuk beberapa tipe produk masih belum tersedia. Kecocokan aplikasi, halal, regulasi dan datasheet tidak dapat disimpulkan dari nama produk saja.</p></section>
<section class="card"><h2>Pengendalian & Audit Evidence</h2>
<div class="kv" id="evidence"></div>
<p class="dim">Analisis ini tidak mengirim isi inquiry, data pelanggan, stok atau SKU ke Groq. AI-03 Bundling dan AI-04 Forecasting tetap diuji melalui modul terpisah; keduanya tidak digunakan untuk memutuskan kelayakan produk pada tahap transaksi ini.</p></section>
</div><div class="footer">PT Liliang · Academic research integration · Decision support only · Technical & Manager remain responsible</div>
</div></main></div>
<script>
const token=sessionStorage.getItem("liliang_token")||"";
const el=id=>document.getElementById(id);
const esc=s=>String(s===null||s===undefined?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;":"&quot;","'":"&#39;"}[c]));
const fmt=x=>Number(x).toLocaleString("id-ID",{maximumFractionDigits:3});
const q=new URLSearchParams(location.search),selected=String(q.get("inquiry_id")||"");
async function api(url){
 const resp=await fetch(url,{cache:"no-store",headers:{"Authorization":"Bearer "+token}});
 const d=await resp.json().catch(()=>({detail:"Response is not JSON"}));
 if(!resp.ok)throw Error(typeof d.detail==="string"?d.detail:"HTTP "+resp.status);
 return d;
}
function metric(label,value){return '<div class="metric"><small>'+esc(label)+'</small><strong>'+esc(value===null||value===undefined?"UNKNOWN":value)+'</strong></div>'}
async function init(){
 if(!token){el("status").textContent="Login ERP dahulu pada /workspace.";el("run").disabled=true;return}
 try{
 const data=await api("/v1/agent/inquiries?limit=100");
 const list=data.rows||[];
 el("inquiry").innerHTML=list.map(r=>'<option value="'+Number(r.id)+'">INQ-'+Number(r.id)+' · '+esc(r.status)+'</option>').join("");
 if(selected&&list.some(r=>String(r.id)===selected))el("inquiry").value=selected;
 el("status").textContent=list.length?list.length+" inquiry tersedia sesuai hak akses Anda.":"Belum ada inquiry; buat melalui menu Sales.";
 el("run").disabled=!list.length;
 }catch(e){el("status").textContent="Tidak dapat membaca inquiry: "+e.message;el("run").disabled=true}
}
el("run").onclick=async()=>{
 const id=Number(el("inquiry").value);if(!id)return;
 el("run").disabled=true;el("status").textContent="Memeriksa inquiry dan stok fisik...";
 try{
 const d=await api("/v1/agent/inquiry/"+id+"/advice");
 el("output").style.display="block";
 el("requirement").textContent=d.requirement;
 el("attributes").innerHTML=metric("Flavor",d.attributes.flavor)+metric("Application",d.attributes.application)+
  metric("Product Form",d.attributes.form)+metric("Halal/Regulatory","UNKNOWN / UNKNOWN");
 el("insight").textContent=d.executive_insight;
 el("nextAction").textContent="Penanggung jawab: "+d.next_actor+" · "+d.recommended_next_action;
 el("transaction").href="/transactions/"+d.inquiry_id;
 const rows=(d.candidates||[]);
 el("candidates").innerHTML=rows.length?rows.map(x=>{
 const stock=x.stock_packages===null?"UNKNOWN":fmt(x.stock_packages)+" "+x.package_uom;
 const size=x.pack_size===null?"UoM belum diketahui":fmt(x.pack_size)+" "+(x.pack_content_uom||"");
 const review=x.technical_decision?x.technical_decision+" (label "+x.technical_label+")":"PENDING";
 return '<tr><td>#'+esc(x.rank)+'</td><td><b>'+esc(x.sku)+'</b><div>'+esc(x.name)+'</div></td>'+
 '<td>'+esc(x.bm25_score)+'</td><td>'+esc(stock)+'</td><td>'+esc(size)+'</td>'+
 '<td>'+esc(review)+'</td><td><ul>'+x.risk_flags.map(r=>'<li class="flag">'+esc(r)+'</li>').join("")+'</ul></td></tr>'
 }).join(""):'<tr><td colspan="7">Tidak ada kandidat matching aktif yang tersimpan. Jalankan matching pada transaksi Sales; hasil historis tidak digunakan.</td></tr>';
 el("evidence").innerHTML=metric("Current inquiry status",d.status)+metric("Matching run",d.latest_run_id??"Belum ada")+
  metric("Status sampel",d.sample_status||"Belum dibuat")+
  metric("Provenance",d.ranking_method)+metric("Database Mutation","TIDAK")+
  metric("Company data to Groq","TIDAK");
 el("status").textContent="Analisis internal selesai; "+rows.length+" kandidat; tidak ada perubahan data ERP.";
 el("output").scrollIntoView({behavior:"smooth",block:"start"});
 }catch(e){el("status").textContent="Pemeriksaan gagal: "+e.message}
 finally{el("run").disabled=false}
};
init();
</script></body></html>"""

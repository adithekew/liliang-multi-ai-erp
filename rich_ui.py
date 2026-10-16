"""Responsive ERP Multi-AI pilot UI; all displayed business records are synthetic."""
def html_page():
    return r"""<!DOCTYPE html>
<html lang="id"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PT Liliang | ERP Multi-AI Research Pilot</title>
<style>
:root{--navy:#102546;--navy2:#1b3b63;--blue:#2864df;--mint:#12bca4;--text:#17304f;--muted:#75859b;--bg:#f4f7fc;--border:#e4ebf5;--red:#ba394d;font-family:Inter,Segoe UI,Arial,sans-serif;color:var(--text);background:var(--bg)}
*{box-sizing:border-box}body{margin:0;min-height:100vh}button,input,textarea,select{font:inherit}button{cursor:pointer}
.layout{min-height:100vh;display:flex}.sidebar{width:254px;background:var(--navy);color:#cddbf0;padding:25px 16px;position:sticky;top:0;height:100vh;flex-shrink:0;overflow:auto}.brand{display:flex;align-items:center;gap:11px;padding:7px 10px 26px;border-bottom:1px solid #ffffff1c;margin-bottom:22px}
.logo{width:42px;height:42px;background:linear-gradient(135deg,#2d86f7,#17d1b2);color:white;border-radius:14px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:21px}
.brand strong{color:white;font-size:18px}.brand small{display:block;color:#9ebbd5;font-size:10px;margin-top:3px;letter-spacing:.1em}
.menutitle{text-transform:uppercase;color:#7897b6;font-size:10px;letter-spacing:.15em;padding:16px 13px 7px;font-weight:800}
.navitem{display:flex;gap:12px;align-items:center;color:#cbd9e9;text-decoration:none;border:0;background:transparent;width:100%;text-align:left;padding:13px 12px;border-radius:10px;margin:3px 0;font-size:13px;font-weight:600}
.navitem span{font-size:18px;width:22px;text-align:center}.navitem:hover,.navitem.active{background:#27507f;color:#fff}.sidefoot{border-top:1px solid #ffffff21;margin-top:26px;padding:19px 12px;color:#9fb8d1;font-size:12px;line-height:1.6}
.main{flex:1;min-width:0}.topbar{background:#fff;border-bottom:1px solid var(--border);height:72px;display:flex;align-items:center;justify-content:space-between;padding:0 34px;gap:12px}
.topbar strong{font-size:15px}.topright{display:flex;align-items:center;gap:12px;font-size:12px}.rolepill{background:#eff4ff;color:#1c5abf;padding:7px 12px;border-radius:20px;font-weight:800}.avatar{width:35px;height:35px;background:#e4edfb;border-radius:50%;display:grid;place-items:center;font-weight:900;color:#235caf}
.content{padding:30px 35px 60px;max-width:1490px;margin:0 auto}.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.16em;font-weight:900;color:#227bc2}
h1{font-size:28px;letter-spacing:-.03em;margin:7px 0 9px;color:var(--navy)}h2{font-size:17px;margin:0 0 14px;color:var(--navy)}h3{font-size:14px;margin:0 0 12px}.sub{color:var(--muted);font-size:13px;line-height:1.65;max-width:830px}
.hero{background:linear-gradient(112deg,#112b50,#25578e);color:white;border-radius:18px;padding:28px 32px;margin-bottom:22px;display:flex;justify-content:space-between;align-items:center;gap:20px}
.hero h1{color:#fff;margin:4px 0}.hero .sub{color:#b9d1ea}.hero .eyebrow{color:#66ebd5}.orbit{font-size:52px;color:#9feee5;opacity:.9}
.warning{border:1px solid #f7dcad;background:#fffaf0;color:#7d5923;border-radius:10px;padding:12px 16px;font-size:12px;line-height:1.6;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.grid.two{grid-template-columns:repeat(2,minmax(0,1fr))}
.card{background:#fff;border:1px solid var(--border);border-radius:15px;padding:21px;box-shadow:0 7px 26px #2a436208;margin-bottom:16px;min-width:0}.card h2{margin-bottom:16px}.kpi{font-size:29px;font-weight:850;margin:13px 0 4px;color:var(--navy)}.kpi-lbl{font-size:12px;font-weight:800;color:#667a92}.iconbox{display:grid;place-items:center;font-size:23px;width:44px;height:44px;background:#eff5ff;border-radius:12px}
.module{border-top:4px solid #2d73d8;display:flex;flex-direction:column;min-height:246px}.module:nth-child(2){border-top-color:#13ad9f}.module:nth-child(3){border-top-color:#885bd7}.module:nth-child(4){border-top-color:#e8a144}
.module p{color:#697f97;font-size:12px;line-height:1.65;flex:1}.line{display:flex;align-items:center;justify-content:space-between;gap:8px}.status{font-weight:800;color:#3869a7;background:#eaf1fc;padding:6px 9px;border-radius:8px;font-size:10px}.small{font-size:12px;color:var(--muted)}
.btn{border:0;border-radius:9px;padding:11px 17px;background:var(--blue);color:#fff;font-size:12px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;gap:7px;text-decoration:none;min-height:38px}
.btn.secondary{background:#eff4fb;color:#1e558f}.btn:disabled{opacity:.45;cursor:not-allowed}.btn:hover{filter:brightness(.95)}.btn.danger{background:#b83b4e}.actions{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
label{font-size:12px;font-weight:750;color:#536883;display:block;margin:11px 0 7px}
input,select,textarea{padding:11px 13px;border:1px solid #d2deed;border-radius:9px;color:var(--navy);background:white;width:100%;font-size:13px;outline:0}
input:focus,textarea:focus,select:focus{border-color:#4189df;box-shadow:0 0 0 3px #4189df16}textarea{min-height:96px;resize:vertical}.form-actions{margin-top:15px}
.tablewrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:12px}th{background:#f5f8fd;color:#5d738d;font-weight:800}th,td{text-align:left;padding:12px;border-bottom:1px solid #eaf0f7;vertical-align:top}td{color:#2f4b69}td .btn{padding:7px 9px;min-height:28px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f9fd;border-radius:10px;padding:15px;font-size:12px;line-height:1.7}
.tag{display:inline-block;font-size:10px;border-radius:7px;padding:5px 8px;font-weight:850;background:#e9f7f2;color:#187f66}.tag.unknown{background:#fff3df;color:#916316}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.note{color:#6f8399;font-size:11px;line-height:1.6;margin:8px 0}.empty{padding:20px;text-align:center;color:#8b9caf}.error{color:var(--red);font-size:12px}
#toast{position:fixed;bottom:25px;right:25px;background:#173858;color:white;padding:14px 22px;border-radius:10px;display:none;box-shadow:0 8px 25px #12294533;z-index:50;font-size:13px}
#loginwrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;background:linear-gradient(132deg,#122948,#2864a3)}
.login{width:min(450px,100%);padding:33px;background:#fff;border-radius:19px;box-shadow:0 25px 60px #04183244}
.login h1{font-size:24px}.login .logo{width:52px;height:52px;margin-bottom:20px}.fine{font-size:11px;color:#8193a8;line-height:1.6}
.chart{display:flex;align-items:end;gap:5px;height:175px;border-bottom:1px solid #dee8f2;margin:18px 0 12px}.bar{flex:1;min-width:9px;background:#c8daf8;border-radius:5px 5px 0 0;position:relative}.bar.pred{background:#18bda7}.bar:hover:after{content:attr(title);position:absolute;bottom:100%;left:0;background:#243c5b;color:#fff;padding:5px;border-radius:5px;white-space:nowrap;font-size:10px;z-index:3}.tabs{display:flex;gap:7px;flex-wrap:wrap;margin:18px 0}
.mobilemenu{display:none}.hide{display:none!important}@media(max-width:1150px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:760px){.sidebar{display:none}.sidebar.open{display:block;position:fixed;z-index:10}.mobilemenu{display:inline-block}.topbar{padding:0 15px}.content{padding:20px 14px}.grid,.grid.two{grid-template-columns:1fr}.hero{padding:22px}.orbit{display:none}.topright .rolepill{display:none}}
</style></head><body><div id="root"></div><div id="toast"></div><script>
const $=id=>document.getElementById(id);
const escapeHtml=(s)=>String(s===undefined||s===null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let token=sessionStorage.getItem("liliang_token")||"",me=null,page="hub",capabilities=[];
try{
 const url=new URL(window.location.href);
 if(url.searchParams.has("utm_source")){
  url.searchParams.delete("utm_source");
  history.replaceState({}, "", url.pathname+url.search+url.hash);
 }
}catch(_){}

async function api(path,method="GET",body=null){
 let opt={method,headers:{"Content-Type":"application/json",...(token?{"Authorization":"Bearer "+token}:{})}};
 if(body!==null)opt.body=JSON.stringify(body);
 let res=await fetch(path,opt),json;try{json=await res.json()}catch{throw Error("Server HTTP "+res.status+" did not return JSON. Check service logs and /readyz.");}
 if(!res.ok)throw Error(typeof json.detail==="string"?json.detail:JSON.stringify(json.detail||json));
 return json;
}
function toast(s,error=false){const t=$("toast");t.textContent=s;t.style.background=error?"#ad3345":"#173858";t.style.display="block";setTimeout(()=>t.style.display="none",3900)}
function fail(e){toast(e.message||String(e),true)}
function logout(){sessionStorage.removeItem("liliang_token");token="";me=null;loginScreen()}
function loginScreen(){
 $("root").innerHTML='<main id="loginwrap"><section class="login"><div class="logo">L</div><div class="eyebrow">RESEARCH PILOT / CLOUD</div><h1>ERP Multi-AI PT. Liliang</h1><p class="sub">Integrated B2B Flavor Workflow & Intelligent Decision Support</p><form id="signin"><label>Email Akun Internal</label><input type="email" name="email" required autocomplete="username" placeholder="admin@liliang.local"><label>Password</label><input type="password" name="password" required autocomplete="current-password"><div class="form-actions"><button class="btn" style="width:100%">Masuk ke ERP →</button></div></form><p class="fine">Research development environment. Jangan masukkan data customer atau informasi rahasia perusahaan.</p><p class="error" id="loginerror"></p></section></main>';
 $("signin").onsubmit=async e=>{e.preventDefault();try{let obj=Object.fromEntries(new FormData(e.target)),a=await api("/v1/auth/login","POST",obj);token=a.access_token;sessionStorage.setItem("liliang_token",token);await enter()}catch(err){$("loginerror").textContent=err.message}};
}
const menu=[
 ["hub","◈","Multi-AI Workspace","AI MODULES"],
 ["hybrid","✦","Hybrid Semantic Lab","AI MODULES"],
 ["research","▤","AI Research Evidence","AI MODULES"],
 ["systems","◉","AI System Status","AI MODULES"],
 ["overview","▦","Dashboard ERP","ERP OPERATIONS"],
 ["inquiries","☷","Inquiry & Matching","ERP OPERATIONS"],
 ["catalog","◉","Product Catalog","ERP OPERATIONS"],
 ["bundling","♧","Sales Intelligence","AI MODULES"],
 ["forecast","▥","Forecast & Inventory","AI MODULES"],
 ["users","⚙","User Management","ADMIN"],
 ["roles","♙","UAT Role Accounts","ADMIN"],
 ["migration","⇄","Catalog Migration","ADMIN"],
 ["audit","≡","Audit Transactions","ADMIN"]
];
function allowed(key){
 if(["users","roles","migration","audit"].includes(key))return me.role==="admin";
 if(key==="hybrid")return ["admin","sales","technical","manager"].includes(me.role);
 if(key==="research")return ["admin","technical","manager"].includes(me.role);
 if(key==="bundling")return ["admin","sales","manager"].includes(me.role);
 if(key==="forecast")return ["admin","sales","manager","gudang"].includes(me.role);
 return true;
}
function frame(){
 let last="",items="";
 menu.filter(x=>allowed(x[0])).forEach(x=>{
  if(last!==x[3]){items+='<div class="menutitle">'+x[3]+'</div>';last=x[3]}
  items+='<button class="navitem '+(page===x[0]?"active":"")+'" data-go="'+x[0]+'"><span>'+x[1]+'</span>'+x[2]+'</button>';
 });
 $("root").innerHTML='<div class="layout"><aside class="sidebar" id="side"><div class="brand"><div class="logo">L</div><div><strong>PT LILIANG</strong><small>ERP · MULTI-AI</small></div></div>'+items+'<div class="sidefoot">◉ CLOUD RESEARCH PILOT<br>Version 0.7 · audited ERP catalog<br><span style="color:#58e3c9">● Services available</span></div></aside><div class="main"><header class="topbar"><div><button class="btn secondary mobilemenu" onclick="toggleMenu()">☰</button><strong>Enterprise Intelligence Platform</strong><div class="fine">B2B Flavor · Integrated Workflow & Research</div></div><div class="topright"><span class="rolepill">'+escapeHtml(me.role.toUpperCase())+'</span><span class="avatar">'+escapeHtml(me.name[0]||"U")+'</span><button class="btn secondary" onclick="logout()">Keluar</button></div></header><main class="content"><div class="warning"><strong>RESEARCH PILOT — SUMBER DATA DIVERIFIKASI PER MODUL:</strong> Katalog dapat bersumber dari PDF pemasok yang diimpor Admin atau data sintetis; cek label sumber pada Product Catalog. Historis penjualan untuk bundling/forecast masih sintetis. AI-01 NLP berbasis aturan dan matching inquiry bebas masih BM25; pretrained multilingual MiniLM 384-D + RRF <strong>SUDAH dijalankan</strong> di Hybrid Lab untuk 10 query sintetis yang diproses offline. Belum ada online neural encoder untuk inquiry bebas, LLM, fine-tuning data perusahaan, atau hasil akurasi validasi pakar. <button class="btn secondary" style="margin-left:9px" onclick="navigate(\'systems\')">Lihat status AI & Database →</button></div><div id="view"></div></main></div></div>';
 document.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>navigate(b.dataset.go));
}
function toggleMenu(){$("side").classList.toggle("open")}
async function enter(){
 try{me=await api("/v1/auth/me");let x=await api("/v1/ai/capabilities");capabilities=x.modules;page="hub";frame();await show()}
 catch(e){if(e.message.includes("expired")||e.message.includes("Login"))logout();else{fail(e);loginScreen()}}
}
async function navigate(p){if(!allowed(p))return;page=p;frame();await show()}
async function show(){
 try{if(page==="hub")await hub();else if(page==="hybrid")await hybridLab();else if(page==="research")await researchEvidence();else if(page==="systems")await aiSystemStatus();else if(page==="overview")await overview();else if(page==="catalog")await catalog();else if(page==="inquiries")await inquiries();else if(page==="bundling")await bundling();else if(page==="forecast")await forecast();else if(page==="users")await users()else if(page==="roles")await uatRoles();else if(page==="migration")await migration();else if(page==="audit")await auditTrail()}catch(e){fail(e);$("view").innerHTML='<div class="card error">'+escapeHtml(e.message)+'</div>'}
}
const headline=(eyebrow,title,sub)=>'<div class="eyebrow">'+eyebrow+'</div><h1>'+title+'</h1><p class="sub">'+sub+'</p>';
async function hub(){
 let modules=capabilities.map((x,i)=>'<article class="card module"><div class="line"><div class="iconbox">'+["✦","◎","♧","▥"][i]+'</div><span class="status">'+escapeHtml(x.status)+'</span></div><h2 style="margin:16px 0 3px">'+escapeHtml(x.id)+' · '+escapeHtml(x.title)+'</h2><p>'+escapeHtml(x.method)+'<br><strong>Data:</strong> '+escapeHtml(x.dataset)+'</p><button class="btn secondary" onclick="'+(["demoRequirement()","demoMatch()","navigate('bundling')","navigate('forecast')"][i])+'">Lihat & Uji Modul →</button></article>').join("");
 $("view").innerHTML='<div class="hero"><div><div class="eyebrow">MULTI-AI INTEGRATION</div><h1>AI-Powered Flavor ERP</h1><p class="sub">Empat kapabilitas dalam satu platform dengan validasi Technical dan human-in-the-loop. Belum termasuk model penelitian yang telah diuji.</p><button class="btn" onclick="navigate(\'inquiries\')">Buat Customer Inquiry →</button></div><div class="orbit">✧ ◈ ✧</div></div><div class="toolbar"><h2>Multi-AI Research Modules</h2><span class="tag unknown">4 RESEARCH MODULES · 0 VALIDATED MODELS</span></div><div class="grid">'+modules+'</div><div id="lab"></div><div class="grid two"><div class="card"><h2>Research Focus (Primary)</h2><p class="sub">Inquiry → requirement NLP → BM25 + offline neural demo → RRF → UNKNOWN/provenance → Technical expert review; arbitrary live neural inference remains pending.</p><span class="tag unknown">Offline fixed-query neural proof-of-concept</span><p><button class="btn secondary" onclick="navigate(\'hybrid\')">Buka Hybrid Research Lab →</button></p></div><div class="card"><h2>Enterprise Roadmap (Secondary)</h2><p class="sub">Order basket analysis dan SKU-week forecasting memakai data simulasi. Validitas pada data perusahaan membutuhkan izin, kualitas historis penjualan, dan evaluasi terpisah.</p><span class="tag">No auto-sell / auto-restock</span></div></div>';
}
const sample="Customer membutuhkan rasa stroberi manis untuk minuman susu, halal dan cocok untuk produk dairy.";
async function demoRequirement(){
 $("lab").innerHTML='<section class="card"><div class="eyebrow">AI-01 / RULE-BASED NLP</div><h2>Requirement Interpreter Lab</h2><p class="sub">Ekstraksi profil dan aplikasi dari permintaan pelanggan bilingual. Status yang tidak dapat dibuktikan tetap UNKNOWN.</p><textarea id="query">'+escapeHtml(sample)+'</textarea><div class="actions"><button class="btn" onclick="runRequirement()">Analisis Inquiry</button><button class="btn secondary" onclick="demoMatch()">Lanjut ke AI-02 →</button></div><div id="labresult"></div></section>';
 $("lab").scrollIntoView({behavior:"smooth",block:"center"});
}
async function runRequirement(){
 try{const x=await api("/v1/ai/requirements","POST",{text:$("query").value});
 $("labresult").innerHTML='<div class="grid two" style="margin-top:18px"><div class="card"><h3>Structured Attributes</h3><p><b>Flavor:</b> '+escapeHtml(x.flavor||"UNKNOWN")+'</p><p><b>Application:</b> '+escapeHtml(x.application||"UNKNOWN")+'</p><p><b>Method:</b> '+escapeHtml(x.method)+'</p></div><div class="card"><h3>Evidence & Guardrails</h3>'+Object.entries(x.attributes).map(([name,a])=>'<p class="small">'+escapeHtml(name)+': <span class="tag '+(a.status==="UNKNOWN"?"unknown":"")+'">'+escapeHtml(a.status)+'</span></p>').join("")+'</div></div>';
 }catch(e){fail(e)}
}
async function demoMatch(){
 $("lab").innerHTML='<section class="card"><div class="eyebrow">AI-02 / BM25 RETRIEVAL</div><h2>Flavor Product Matching Lab</h2><p class="sub">Peringkat kandidat melalui BM25 lexical retrieval, bukan pretrained neural embeddings. Shortlist belum boleh dikirim ke customer sebelum validasi Technical.</p><textarea id="query">'+escapeHtml(sample)+'</textarea><div class="actions"><button class="btn" onclick="runMatch()">Cari Top-5 Flavor</button><button class="btn secondary" onclick="navigate(\'inquiries\')">Simpan ke Workflow →</button></div><div id="labresult"></div></section>';
 $("lab").scrollIntoView({behavior:"smooth",block:"center"});
}
async function runMatch(){
 try{let d=await api("/v1/ai/match-preview","POST",{text:$("query").value});
 $("labresult").innerHTML='<div class="card" style="margin-top:18px"><div class="toolbar"><h3>Candidate Top-5</h3><span class="tag unknown">Not expert validated</span></div><div class="tablewrap"><table><tr><th>Rank</th><th>SKU</th><th>Flavor Product</th><th>BM25 Score</th><th>Evidence</th><th>Constraint</th></tr>'+d.candidates.map(x=>'<tr><td>#'+x.rank+'</td><td>'+escapeHtml(x.sku)+'</td><td><b>'+escapeHtml(x.name)+'</b></td><td>'+x.score+'</td><td><div class="small">'+escapeHtml(x.explanation?.matched_terms?.join(", ")||"no lexical match")+'</div><span class="tag unknown">Not verified</span></td><td>Regulatory / Halal UNKNOWN</td></tr>').join("")+'</table></div><p class="note">Istilah yang ditampilkan merupakan jejak kecocokan leksikal, bukan bukti kelayakan teknis. Skor BM25 bukan probabilitas. Untuk menyimpan ranking, buat Inquiry dan kirim ke Technical Review.</p></div>';
 }catch(e){fail(e)}
}
async function overview(){
 let [s,c]=await Promise.all([api("/v1/analytics/summary"),api("/v1/ai/capabilities")]);
 $("view").innerHTML=headline("ERP / MANAGEMENT","Dashboard Operasional","Ringkasan workflow ERP dan kesiapan modul analitik.")+
 '<div class="grid"><div class="card"><div class="kpi-lbl">Master Flavor (Catalog)</div><div class="kpi">'+s.product_count+'</div><span class="tag">Synthetic</span></div><div class="card"><div class="kpi-lbl">Customer Inquiries</div><div class="kpi">'+s.inquiry_count+'</div><span class="small">Pilot records</span></div><div class="card"><div class="kpi-lbl">Available AI Demos</div><div class="kpi">'+c.modules.length+'</div><span class="tag unknown">Baseline only</span></div><div class="card"><div class="kpi-lbl">Validated AI Models</div><div class="kpi">0</div><span class="small">Research pending</span></div></div>'+
 '<div class="grid two"><div class="card"><h2>Workflow Proyek</h2><p class="sub">Sales Inquiry → BM25 shortlist → Technical review → Manager approval. Setiap keputusan penting memerlukan persetujuan manusia.</p><button class="btn" onclick="navigate(\'inquiries\')">Buka Workflow</button></div><div class="card"><h2>Integrasi Empat Modul</h2><p class="sub">AI-01 requirements, AI-02 product matching, AI-03 bundling, AI-04 demand forecasting. Pilih modul dari Multi-AI Workspace.</p><button class="btn secondary" onclick="navigate(\'hub\')">Buka Multi-AI →</button></div></div>';
}
let catalogPage=1,catalogQuery="";
async function catalog(){
 let data=await api("/v1/catalog/products?q="+encodeURIComponent(catalogQuery)+"&page="+catalogPage+"&size=50");
 $("view").innerHTML=headline("ERP / MASTER DATA","Product Flavor Catalog",
 "Katalog bersumber dari data demo atau PDF pemasok yang diimpor Admin. Informasi kegunaan bukan sertifikasi produk; stok NULL ditampilkan UNKNOWN.")+
 '<div class="card"><div class="toolbar"><h2>Product Master · '+data.total+' SKU</h2><span class="tag unknown">SOURCE-AWARE CATALOG</span></div>'+
 '<div class="actions"><input id="catalogsearch" style="max-width:320px" value="'+escapeHtml(catalogQuery)+'" placeholder="Cari SKU, nama, pemakaian"><button class="btn" id="catalogfind">Cari</button><button class="btn secondary" id="catalogclear">Reset Filter</button></div>'+
 '<div class="tablewrap" style="margin-top:16px"><table><tr><th>SKU</th><th>Product Name</th><th>Type</th><th>Applications</th><th>Catalog % Text</th><th>Stock</th><th>Source</th></tr>'+
 data.items.map(x=>'<tr><td><b>'+escapeHtml(x.sku)+'</b></td><td>'+escapeHtml(x.name)+'</td><td>'+escapeHtml(x.product_type||"UNKNOWN")+'</td><td>'+escapeHtml(x.application||"UNKNOWN")+'</td><td>'+escapeHtml(x.composition_raw||"NOT PROVIDED")+'</td><td>'+escapeHtml(x.stock===null?"UNKNOWN":x.stock)+'</td><td><span class="tag unknown">'+escapeHtml(x.source_ref||"UNKNOWN")+'</span></td></tr>').join("")+
 '</table></div><div class="actions" style="margin-top:18px"><button class="btn secondary" id="prevcatalog" '+(catalogPage===1?"disabled":"")+'>← Sebelumnya</button><span class="small">Halaman '+catalogPage+' dari '+Math.max(1,Math.ceil(data.total/50))+'</span><button class="btn secondary" id="nextcatalog" '+(catalogPage*50>=data.total?"disabled":"")+'>Selanjutnya →</button></div></div>';
 $("catalogfind").onclick=()=>{catalogQuery=$("catalogsearch").value;catalogPage=1;catalog()};
 $("catalogsearch").onkeydown=e=>{if(e.key==="Enter"){catalogQuery=e.target.value;catalogPage=1;catalog()}};
 $("catalogclear").onclick=()=>{catalogQuery="";catalogPage=1;catalog()};
 $("prevcatalog").onclick=()=>{catalogPage=Math.max(1,catalogPage-1);catalog()};
 $("nextcatalog").onclick=()=>{catalogPage++;catalog()};
}
async function inquiries(){
 let rows=await api("/v1/inquiries"),canNew=["admin","sales"].includes(me.role);
 let create=canNew?'<div class="card"><h2>New Customer Inquiry</h2><form id="newinq"><label>Customer Reference (Anonymous)</label><input name="customer_ref" value="DEMO-ANON" maxlength="80"><label>Deskripsi Kebutuhan Flavor</label><textarea name="requirement" minlength="5" required placeholder="Contoh: Strawberry flavor untuk minuman susu..."></textarea><div class="form-actions"><button class="btn">Simpan Inquiry</button></div></form></div>':"";
 $("view").innerHTML=headline("ERP / SALES TO TECHNICAL","Inquiry & Matching Workflow","Inquiry disimpan sebelum pemeringkatan produk. Technical memvalidasi, Manager menyetujui.")+
 '<div class="grid two"><div>'+create+'</div><div class="card"><h2>Human-in-the-Loop</h2><p class="sub">1. Sales memasukkan requirement.<br>2. Sistem menghasilkan Top-5 kandidat BM25.<br>3. Technical menilai relevansi 0–3.<br>4. Manager melakukan approval apabila kandidat telah di-ACCEPT.</p><span class="tag unknown">No automatic sales</span></div></div>'+
 '<div class="card"><h2>Inquiry Register</h2><div class="tablewrap"><table><tr><th>ID</th><th>Customer</th><th>Requirement</th><th>Status</th><th>Action</th></tr>'+rows.map(x=>'<tr><td>#'+x.id+'</td><td>'+escapeHtml(x.customer_ref||"Restricted")+'</td><td>'+escapeHtml(x.requirement||"Restricted")+'</td><td><span class="tag">'+escapeHtml(x.status)+'</span></td><td>'+([
"admin","sales","technical"].includes(me.role)?'<button class="btn secondary" onclick="matchInquiry('+x.id+')">Run Matching</button> ':'')+(['admin','manager'].includes(me.role)?'<button class="btn secondary" onclick="managerApproval('+x.id+')">Approval</button>':'')+'</td></tr>').join("")+'</table></div>'+(!rows.length?'<p class="empty">Belum ada inquiry. Buat satu permintaan dummy untuk memulai eksperimen.</p>':'')+'</div><div id="workflowResult"></div>';
 if(canNew)$("newinq").onsubmit=async e=>{e.preventDefault();try{const z=Object.fromEntries(new FormData(e.target));await api("/v1/inquiries","POST",z);toast("Inquiry disimpan");await inquiries()}catch(err){fail(err)}};
}
async function matchInquiry(id){
 try{let d=await api("/v1/inquiries/"+id+"/match","POST");
 $("workflowResult").innerHTML='<div class="card"><div class="toolbar"><h2>Ranking Run #'+d.run_id+'</h2><span class="tag unknown">'+escapeHtml(d.method)+'</span></div><p class="sub">'+escapeHtml(d.notice)+'</p><div class="tablewrap"><table><tr><th>Rank</th><th>SKU</th><th>Flavor</th><th>Score</th><th>Constraint</th><th>Review</th></tr>'+d.candidates.map(x=>'<tr><td>#'+x.rank+'</td><td>'+escapeHtml(x.sku)+'</td><td>'+escapeHtml(x.name)+'</td><td>'+x.score+'</td><td>UNKNOWN</td><td>'+ (me.role==="technical"?'<button class="btn secondary" onclick="expertReview('+d.run_id+','+x.product_id+')">Validate</button>':'Technical required')+'</td></tr>').join("")+'</table></div></div>';
 $("workflowResult").scrollIntoView({behavior:"smooth",block:"start"});
 }catch(e){fail(e)}
}
async function expertReview(run,product){
 if(me.role!=="technical")return;
 let decision=prompt("Technical decision (ACCEPT / REJECT / NEEDS_INFO)","ACCEPT");if(!decision)return;
 let label=prompt("Expert relevance label 0–3","3");if(label===null)return;
 let rationale=prompt("Technical rationale (min. 5 karakter)","Checked against synthetic requirements");if(!rationale)return;
 try{await api("/v1/matches/"+run+"/review","POST",{product_id:product,decision,relevance_label:Number(label),rationale});toast("Technical review tersimpan");await inquiries()}catch(e){fail(e)}
}
async function managerApproval(id){
 let decision=prompt("Manager decision: APPROVE / RETURN","APPROVE");if(!decision)return;
 let note=prompt("Alasan / catatan (min. 5 karakter)","Reviewed Technical result");if(!note)return;
 try{let r=await api("/v1/inquiries/"+id+"/decision","POST",{decision,note});toast("Status: "+r.status);await inquiries()}catch(e){fail(e)}
}
async function bundling(){
 let d=await api("/v1/ai/bundling");
 $("view").innerHTML=headline("AI-03 / SALES INTELLIGENCE","Product Bundling Insights","Analisis ko-pembelian memakai association rules dari 16 keranjang transaksi sintetis. Tidak ada histori PT. Liliang yang digunakan.")+
 '<div class="grid"><div class="card"><div class="kpi-lbl">Synthetic Baskets</div><div class="kpi">'+d.basket_count+'</div></div><div class="card"><div class="kpi-lbl">Candidate Rules</div><div class="kpi">'+d.rules.length+'</div></div><div class="card"><div class="kpi-lbl">Auto-Sell</div><div class="kpi">OFF</div></div><div class="card"><div class="kpi-lbl">Data Source</div><div class="kpi" style="font-size:20px">DEMO</div></div></div>'+
 '<div class="card"><h2>Frequently Bought Together · Association Rules</h2><div class="tablewrap"><table><tr><th>When customer buys</th><th>Also bought</th><th>Count</th><th>Support</th><th>Confidence</th><th>Lift</th></tr>'+d.rules.map(x=>'<tr><td><b>'+escapeHtml(x.antecedent_sku)+'</b></td><td>'+escapeHtml(x.recommended_sku)+'</td><td>'+x.co_occurrences+'</td><td>'+(x.support*100).toFixed(1)+'%</td><td>'+(x.confidence*100).toFixed(1)+'%</td><td><span class="tag">'+x.lift.toFixed(2)+'×</span></td></tr>').join("")+'</table></div><p class="note">Threshold: support ≥12%, confidence ≥35%. Semua nilai diturunkan dari keranjang buatan; evaluasi pada histori transaksi aktual diperlukan.</p></div>'+
 '<div class="grid two"><div class="card"><h2>Bagaimana AI-03 bekerja?</h2><p class="sub">Order baskets → frequency counts → association rules → business filters → validasi Sales. Untuk data aktual, batal/retur, promosi dan split temporal harus diproses.</p></div><div class="card"><h2>Research Scope</h2><p class="sub">AI-03 merupakan eksperimen sekunder. Angka lift pada demo tidak dapat diklaim sebagai pola pembelian PT. Liliang.</p></div></div>';
}
async function forecast(){
 let p=await api("/v1/products");
 const allowed=p.filter(x=>["FLV-STRAW-01","FLV-VANI-02","FLV-MANG-03","FLV-CHOCO-04","FLV-LEMON-05"].includes(x.sku));
 $("view").innerHTML=headline("AI-04 / DEMAND FORECASTING","Sales Demand Intelligence","Prediksi SKU-week berdasarkan 24 minggu penjualan sintetis dengan baseline 4-week moving average.")+
 '<div class="card"><div class="grid two"><div><label>Forecast SKU</label><select id="sku">'+allowed.map(x=>'<option value="'+escapeHtml(x.sku)+'">'+escapeHtml(x.sku)+' — '+escapeHtml(x.name)+'</option>').join("")+'</select></div><div><label>Prediction Horizon</label><select id="horizon"><option value="4">4 minggu</option><option value="8">8 minggu</option></select></div></div><div class="form-actions"><button class="btn" onclick="runForecast()">Jalankan Forecast →</button></div></div><div id="forecastResult"></div>';
 await runForecast();
}
async function runForecast(){
 try{let sku=$("sku").value,h=$("horizon").value,d=await api("/v1/ai/forecast?sku="+encodeURIComponent(sku)+"&horizon="+h);
 let hist=d.history.slice(-12).map(x=>({value:x.units,week:x.week,pred:false}));
 let pred=d.forecast.map(x=>({value:x.predicted_units,week:x.week,pred:true}));
 let bars=hist.concat(pred),m=Math.max(...bars.map(x=>x.value),1);
 $("forecastResult").innerHTML='<div class="grid"><div class="card"><div class="kpi-lbl">Next Week Forecast</div><div class="kpi">'+d.forecast[0].predicted_units+'</div><span class="small">Simulated units</span></div><div class="card"><div class="kpi-lbl">Rolling MAE</div><div class="kpi">'+d.metrics.rolling_mae_units+'</div><span class="small">Units</span></div><div class="card"><div class="kpi-lbl">Rolling WMAPE</div><div class="kpi">'+d.metrics.rolling_wmape_pct+'%</div><span class="small">On synthetic time-series</span></div><div class="card"><div class="kpi-lbl">Model</div><div class="kpi" style="font-size:17px">4-week MA</div><span class="small">Baseline · Not LLM</span></div></div>'+
 '<div class="card"><h2>SKU Demand — Synthetic History + Forecast</h2><div class="chart">'+bars.map(x=>'<div class="bar '+(x.pred?'pred':'')+'" style="height:'+Math.max(4,x.value/m*100)+'%" title="'+escapeHtml(x.week)+' · '+x.value+' units"></div>').join("")+'</div><div class="line"><span class="small">■ Blue: history (last 12 weeks)</span><span class="small" style="color:#129d88">■ Green: forecast ('+h+' weeks)</span></div><p class="note">'+escapeHtml(d.disclaimer)+'</p></div>';
 }catch(e){fail(e)}
}
async function hybridLab(){
 const meta=await api("/v1/ai/hybrid-cases");
 let info=headline("AI-02 / PRIMARY RESEARCH","Hybrid Semantic Matching Lab","Demonstrasi nyata BM25 + neural multilingual embeddings + Reciprocal Rank Fusion (RRF). Neural embedding dihitung sebelumnya pada GitHub Actions, hanya untuk query sintetis yang tersedia.");
 if(!meta.available){
  $("view").innerHTML=info+'<section class="card"><h2>Menunggu Model Embedding</h2><p class="sub">Aset embedding multilingual belum dibangun. API tidak menggunakan skor dense palsu atau fallback diam-diam. Setelah pipeline GitHub Actions berhasil, contoh query sintetis akan tersedia.</p><span class="tag unknown">NEURAL_ASSET_NOT_READY</span></section>';
  return;
 }
 let opts=meta.cases.map(x=>'<option value="'+escapeHtml(x.id)+'">'+escapeHtml(x.id+' · '+x.text)+'</option>').join("");
 $("view").innerHTML=info+
  '<div class="grid"><div class="card"><div class="kpi-lbl">Encoder</div><div class="kpi" style="font-size:14px">Multilingual MiniLM</div><span class="small">Pretrained actual neural model</span></div><div class="card"><div class="kpi-lbl">Vector Dimension</div><div class="kpi">'+meta.dimensions+'</div></div><div class="card"><div class="kpi-lbl">Neural Inference</div><div class="kpi" style="font-size:16px">Offline · Cached</div><span class="small">No arbitrary live encoding</span></div><div class="card"><div class="kpi-lbl">Expert Validation</div><div class="kpi">Pending</div></div></div>'+
  '<section class="card"><div class="toolbar"><h2>Hybrid Retrieval Test — Synthetic Queries</h2><span class="tag unknown">RESEARCH DEMO ONLY</span></div><label>Inquiry Demo (pre-embedded)</label><select id="hybridcase">'+opts+'</select><p class="note">'+escapeHtml(meta.notice)+'</p><div class="actions"><button class="btn" onclick="runHybridDemo()">Bandingkan BM25 / Dense / RRF</button><button class="btn secondary" onclick="navigate(\'inquiries\')">Buka Workflow ERP</button></div><div id="hybridresult"></div></section>'+
  '<div class="grid two"><div class="card"><h2>Research Validity Boundary</h2><p class="sub">Ranking pada contoh developer-authored bukan evaluasi pakar. Untuk paper dibutuhkan label 0–3 dari Technical, pemisahan train/dev/test, baselines, nDCG@5, MRR, P95 latency end-to-end.</p></div><div class="card"><h2>Evidence & Provenance</h2><p class="sub">Atribut halal/regulatory selalu UNKNOWN tanpa dokumen terverifikasi. Tidak ada keputusan otomatis; rekomendasi perlu validasi Technical dan persetujuan Manager.</p></div></div>';
 await runHybridDemo();
}
async function runHybridDemo(){
 const area=$("hybridresult");
 if(!area)return;
 try{
  const id=$("hybridcase").value;
  const d=await api("/v1/ai/hybrid-evaluate?case_id="+encodeURIComponent(id));
  const rankings=(title,arr)=>'<div class="card"><h3>'+title+'</h3><p class="small">'+arr.map((sku,i)=>(i+1)+'. '+escapeHtml(sku)).join(' · ')+'</p></div>';
  area.innerHTML='<div style="margin-top:18px"><div class="grid"><div class="card"><div class="kpi-lbl">Model</div><div class="kpi" style="font-size:12px">'+escapeHtml(d.model_id)+'</div><div class="small">Revision '+escapeHtml(d.model_revision.slice(0,12))+'</div></div><div class="card"><div class="kpi-lbl">Query</div><div class="kpi" style="font-size:12px">'+escapeHtml(d.case_id)+'</div><div class="small">Synthetic authored case</div></div><div class="card"><div class="kpi-lbl">RRF Parameter</div><div class="kpi">k=60</div></div><div class="card"><div class="kpi-lbl">Measured Runtime</div><div class="kpi">'+escapeHtml(d.retrieval_only_latency_ms)+' ms</div><div class="small">Retrieval only; excludes neural encoding</div></div></div>'+
  '<div class="grid">'+rankings("BM25 Ranking",d.lexical_skus)+rankings("Neural Dense Ranking",d.dense_skus)+rankings("Hybrid RRF Ranking",d.hybrid_skus)+'</div>'+
  '<div class="card"><h2>RRF Candidate Ranking & Uncertainty</h2><div class="tablewrap"><table><thead><tr><th>Rank</th><th>SKU</th><th>BM25</th><th>Dense</th><th>Cosine</th><th>RRF Score</th><th>Evidence</th></tr></thead><tbody>'+d.ranked_candidates.map(x=>'<tr><td>#'+x.rank+'</td><td><b>'+escapeHtml(x.sku)+'</b></td><td>'+x.bm25_rank+'</td><td>'+x.dense_rank+'</td><td>'+x.dense_cosine+'</td><td>'+x.rrf_score+'</td><td><span class="tag unknown">'+escapeHtml(x.constraint_status)+'</span></td></tr>').join("")+'</tbody></table></div><p class="note">'+escapeHtml(d.notes)+'</p><p class="note">Developer-authored illustrative label: '+escapeHtml(d.developer_authored_expected_sku)+' (not expert ground truth).</p></div></div>';
 }catch(e){area.innerHTML='<div class="card error">'+escapeHtml(e.message)+'</div>';fail(e)}
}
async function aiSystemStatus(){
 const [status,ready]=await Promise.all([api("/v1/ai/system-status"),api("/readyz")]);
 const record=(label,val)=>'<div class="card"><div class="kpi-lbl">'+escapeHtml(label)+'</div><div class="kpi" style="font-size:17px">'+escapeHtml(val)+'</div></div>';
 const services=status.components.map(x=>'<tr><td><b>'+escapeHtml(x.id)+'</b></td><td>'+escapeHtml(x.method)+'</td><td><span class="tag '+(x.mode.includes("ONLINE")?"":"unknown")+'">'+escapeHtml(x.mode)+'</span></td><td>'+escapeHtml(x.data)+'</td></tr>').join("");
 $("view").innerHTML=headline("SYSTEM OBSERVABILITY / LIVE DATA","AI & Cloud System Status",
 "Status aktual dihitung oleh backend. Ini inventory kemampuan, BUKAN pengukuran akurasi.")+
 '<div class="grid">'+record("Database",status.database_backend.toUpperCase())+record("Persistent Storage",status.persistent_database?"YES":"NO — EPHEMERAL")+
 record("Neural Fixed-Query Lab",status.components.find(x=>x.id==="AI-02-NEURAL")?.trained_ml_model?"PRECOMPUTED ACTIVE":"UNAVAILABLE")+
 record("Expert Reviews",status.expert_review_count)+'</div>'+
 '<div class="card"><div class="toolbar"><h2>Component Execution Modes</h2><span class="tag unknown">NO VALIDATED COMPANY MODEL</span></div><div class="tablewrap"><table><thead><tr><th>Module</th><th>Implemented Method</th><th>Runtime Mode</th><th>Data Scope</th></tr></thead><tbody>'+services+'</tbody></table></div>'+
 '<p class="note">Database health: '+escapeHtml(ready.ready?"READY":"NOT READY")+' · product records: '+status.product_count+' · inquiry records: '+status.inquiry_count+'. No passwords, connection strings or customer requirements are exposed.</p></div>'+
 '<div class="grid two"><div class="card"><h2>AI-02 Research Workflow</h2><p class="sub">Pretrained neural vectors: GitHub Actions offline → versioned synthetic fixtures → cosine dense ranking → RRF hybrid fusion. FastAPI receives new arbitrary inquiries but currently ranks them with BM25 only.</p><button class="btn" onclick="navigate(\'hybrid\')">Test Precomputed Neural Demo</button></div><div class="card"><h2>Still Pending Before Research/Production</h2>'+status.limitations.map(s=>'<p class="small">• '+escapeHtml(s)+'</p>').join("")+'<button class="btn secondary" onclick="navigate(\'research\')">Review Scientific Readiness</button></div></div>';
}
async function researchEvidence(){
 const [m,r,e,q]=await Promise.all([
    api("/v1/research/methodology"),api("/v1/research/readiness"),api("/v1/research/evaluation"),api("/v1/research/quality-demo")
 ]);
 const kpi=(caption,n,detail)=>'<div class="card"><div class="kpi-lbl">'+caption+'</div><div class="kpi">'+escapeHtml(n)+'</div><span class="small">'+detail+'</span></div>';
 const steps=m.pipeline.map((step,i)=>'<div style="display:flex;gap:12px;align-items:start;padding:10px 0;border-bottom:1px solid #ecf0f5"><span class="tag">'+(i+1)+'</span><span class="small" style="color:#263b57;font-size:12px">'+escapeHtml(step)+'</span></div>').join("");
 const stages=m.models.map(x=>'<tr><td><b>'+escapeHtml(x.name)+'</b></td><td>'+escapeHtml(x.mechanism)+'</td><td><span class="tag unknown">'+escapeHtml(x.deployment)+'</span></td><td>'+ (x.trained_on_company_data?'YES':'NO')+'</td></tr>').join("");
 const gateLabels={"all_evaluation_candidates_judged":"Semua kandidat mempunyai label","independent_expert_review_proven":"Independent expert review","heldout_split_verified":"Locked held-out test set","label_adjudication_completed":"Expert adjudication","representative_company_dataset_available":"Dataset representatif perusahaan","paired_bm25_dense_hybrid_same_queries":"Paired BM25 / dense / hybrid"};
 let gates=Object.entries(r.gates).map(([key,ok])=>'<tr><td>'+escapeHtml(gateLabels[key]||key)+'</td><td><span class="tag '+(ok?'':'unknown')+'">'+(ok?'VERIFIED':'PENDING')+'</span></td></tr>').join("");
 const scores=e.results.length?e.results.map(x=>'<tr><td>'+escapeHtml(x.method)+'</td><td>'+x.fully_judged_runs+'</td><td>'+x.exploratory_mean_ndcg_at_5+'</td><td>'+x.exploratory_mrr_at_5+'</td><td><span class="tag unknown">Exploratory only</span></td></tr>').join(""):'<tr><td colspan="5" class="empty">Belum ada run dengan semua kandidat diberi label Technical 0–3. Tidak ada klaim akurasi.</td></tr>';
 const rubric=Object.entries(r.expert_rubric).map(([label,meaning])=>'<tr><td><b>'+label+'</b></td><td>'+escapeHtml(meaning)+'</td></tr>').join("");
 $("view").innerHTML=headline("RESEARCH / SCIENTIFIC VALIDATION","AI Research Evidence & Model Evaluation",
 "Halaman transparansi akademik: data cleansing, model ML, training, label pakar, kesiapan dataset, dan hasil pengujian. Angka sintetis tidak boleh disebut akurasi PT. Liliang.")+
 '<div class="warning"><strong>RESEARCH STATUS: NOT VALIDATED.</strong> Pretrained neural model sudah dijalankan pada 10 inquiry sintetis. Model belum fine-tuned dengan data PT. Liliang, belum ada expert-labelled held-out set, dan belum ada bukti percepatan kerja.</div>'+
 '<div class="grid">'+kpi("Workflow Matching Runs",r.evaluation_runs_total,"Data pilot tersimpan")+
 kpi("Fully Expert-Labelled Runs",r.fully_labelled_runs,"Setiap kandidat harus dinilai")+
 kpi("Candidate Review Coverage",r.candidate_label_coverage_pct+"%","Cakupan review, BUKAN akurasi")+
 kpi("Validated Model",0,"Belum ada hasil held-out")+'</div>'+
 '<div class="grid two"><div class="card"><h2>1. Dataset Cleansing & Preparation</h2><p class="sub">Audit asal data dan izin → schema validation → missing value / UNKNOWN → PII quarantine → Unicode & sinonim ID/EN → deduplication → taxonomy/SKU matching → leakage-safe split → dataset fingerprint → review Technical.</p>'+
 '<p class="small">Validated SYNTHETIC records: '+escapeHtml(q.product_quality?.accepted??"N/A")+' products; '+escapeHtml(q.inquiry_quality?.accepted??"N/A")+' inquiries; quarantined: '+escapeHtml(q.product_quality?.quarantined??"N/A")+' products / '+escapeHtml(q.inquiry_quality?.quarantined??"N/A")+' inquiries. These figures are NOT company data.</p><h3 style="margin-top:18px">Reproducible Processing Pipeline</h3>'+steps+
 '<p class="note">Audit data dilakukan di modul research/data_pipeline.py. Pipeline pengujian memakai data sintetis, bukan dataset internal perusahaan.</p></div>'+
 '<div class="card"><h2>2. Machine Learning & Training</h2><p class="sub"><b>Current:</b> Multilingual MiniLM sebagai pretrained encoder (frozen, 384 dimensi); BM25 lexical; RRF deterministic. Tidak ada supervised fine-tuning pada data PT. Liliang.</p>'+
 '<div class="tablewrap"><table><thead><tr><th>Model</th><th>Methods</th><th>Deployment</th><th>Company-trained?</th></tr></thead><tbody>'+stages+'</tbody></table></div>'+
 '<h3 style="margin-top:16px">Rencana Fine-tuning</h3><p class="small">'+escapeHtml(m.training_plan.fine_tune_algorithm)+'. Dataset menggunakan pasangan inquiry–SKU berlabel pakar dan split berdasarkan proyek/customer dan waktu. Model harus mengungguli baseline held-out sebelum deployment.</p></div></div>'+
 '<div class="grid two"><div class="card"><h2>3. Technical Labeling Rubric (0–3)</h2><div class="tablewrap"><table><thead><tr><th>Grade</th><th>Judgment</th></tr></thead><tbody>'+rubric+'</tbody></table></div><p class="note">Penilaian relevansi berbeda dari tombol ACCEPT/REJECT sebagai keputusan workflow. Kasus NEEDS_INFO tidak dianggap label final.</p><button class="btn secondary" onclick="navigate(\'inquiries\')">Buka Inquiry & Technical Review →</button></div>'+
 '<div class="card"><h2>4. Scientific Readiness Gates</h2><div class="tablewrap"><table><thead><tr><th>Evaluation requirement</th><th>Status</th></tr></thead><tbody>'+gates+'</tbody></table></div><p class="note">Cakupan review tidak membuktikan akurasi; evaluasi yang sah membutuhkan expert labels, held-out test, dan paired comparison.</p></div></div>'+
 '<section class="card"><div class="toolbar"><h2>5. Model Performance Evidence</h2><span class="tag unknown">'+escapeHtml(e.status)+'</span></div><div class="tablewrap"><table><thead><tr><th>Method</th><th>Fully judged</th><th>Mean nDCG@5</th><th>MRR@5</th><th>Claim</th></tr></thead><tbody>'+scores+'</tbody></table></div><p class="note">nDCG@5 & MRR@5 are calculated only when the complete candidate set has valid 0–3 expert labels. Results remain exploratory until independent held-out testing.</p>'+
 '<p class="note">'+escapeHtml(e.warnings.join(' '))+'</p></section>'+
 '<div class="card"><h2>6. Jawaban untuk Dosen Pembimbing</h2><p class="sub"><b>Akurasi:</b> belum diklaim; diuji dengan nDCG@5/MRR pada gold standard Technical.<br><b>Training:</b> model MiniLM pretrained eksternal; PT. Liliang fine-tuning belum dilakukan.<br><b>Cleansing:</b> normalisasi, karantina PII, dedup, validasi atribut dan split anti-leakage.<br><b>Keunggulan ML:</b> pretrained embeddings menangkap kemiripan semantik lintas bahasa; BM25 efisien untuk istilah exact; RRF memadukan ranking tanpa menyamakan skala skornya.</p><p class="note">Kesimpulan efektivitas memerlukan eksperimen E1–E5 pada dataset yang mendapat izin dan label pakar.</p></div>';
}
async function uatRoles(){
 const source=await api("/v1/users");
 const rows=source.filter(x=>/^(sales|technical|manager|gudang)$/.test(x.role));
 $("view").innerHTML=headline("ADMIN / FIVE ROLES","UAT Role Accounts",
 "Membuat empat akun UAT di PostgreSQL. Password unik dihasilkan server dan ditampilkan satu kali; jangan tampilkan halaman hasil ketika screen-sharing.")+
 '<div class="grid two"><div class="card"><h2>One-Time Account Provisioning</h2><p class="sub">Admin sudah aktif. Siapkan Sales, Technical, Manager Operasional, dan Gudang; identitas uat-...@liliang.local adalah akun percobaan, bukan alamat email perusahaan sebenarnya.</p><button class="btn" id="bootstraproles">Generate Empat Akun UAT</button><p class="note">Tidak akan menimpa password akun yang sudah ada. Simpan kredensial secara pribadi; server hanya menyimpan hash Argon2.</p></div><div class="card"><h2>Current Operational Roles</h2><div class="tablewrap"><table><tr><th>Email</th><th>Role</th></tr>'+rows.map(x=>'<tr><td>'+escapeHtml(x.email)+'</td><td>'+escapeHtml(x.role)+'</td></tr>').join("")+'</table></div></div></div><section class="card" id="uatsecrets" style="display:none"></section>';
 $("bootstraproles").onclick=async()=>{
  if(!confirm("Buat akun UAT empat role dengan password unik sekali tampil? Lanjutkan tanpa screen sharing."))return;
  try{
   const r=await api("/v1/admin/uat/bootstrap","POST",{confirmation:"CREATE UAT ROLES"});
   const area=$("uatsecrets");area.style.display="block";
   area.innerHTML='<h2>ONE-TIME ACCESS CREDENTIALS</h2><p class="error">SIMPAN SEKARANG SECARA AMAN. Password tidak bisa ditampilkan ulang.</p><div class="tablewrap"><table><tr><th>Role</th><th>Email</th><th>Password (sekali tampil)</th><th>Status</th></tr>'+
    r.roles.map(x=>'<tr><td>'+escapeHtml(x.role)+'</td><td>'+escapeHtml(x.email)+'</td><td><code>'+escapeHtml(x.password_once||"Existing — not disclosed")+'</code></td><td>'+escapeHtml(x.status)+'</td></tr>').join("")+'</table></div>';
   toast("UAT accounts provisioned. Simpan kredensial secara aman.");
  }catch(e){fail(e)}
 };
}
async function migration(){
 const [preview,imports]=await Promise.all([api("/v1/admin/catalog/reset-preview"),api("/v1/admin/catalog/imports")]);
 const counts=preview.counts;
 $("view").innerHTML=headline("ADMIN / MASTER DATA GOVERNANCE","Catalog Migration",
 "Reset demo HARUS dilakukan secara sadar dan diarsipkan. Dataset PDF katalog masuk melalui browser Admin dan tidak dikomit ke GitHub.")+
 '<div class="grid two"><div class="card"><h2>1. Archive & Reset Demo Transactions</h2><p class="sub">Produk: '+counts.products+' | Inquiry: '+counts.inquiries+' | Matching: '+counts.runs+' | Reviews: '+counts.reviews+'. Semua akun dan audit events tetap tersimpan.</p><p class="note">'+escapeHtml(preview.safety)+'</p>'+
 '<label>Ketik konfirmasi RESET DEMO ONLY</label><input id="resetconfirm" placeholder="RESET DEMO ONLY"><button class="btn danger" id="resetdemo" '+(!preview.demo_reset_allowed?"disabled":"")+'>Archive & Reset Demo</button><div id="resetresult"></div></div>'+
 '<div class="card"><h2>2. Import 1.452 Produk Hasil Cleansing</h2><p class="sub">Gunakan berkas <b>catalog_import_ready.json</b> (dari ChatGPT). 3 baris duplikat/konflik dikarantina. Stok tetap UNKNOWN sampai Gudang mengisi data sebenarnya. Import atomik dan hanya pada katalog aktif kosong.</p>'+
 '<label>Pilih JSON Import-ready</label><input type="file" id="importfile" accept=".json,application/json"><button class="btn" id="importcatalog" '+(counts.products?"disabled":"")+'>Impor Katalog Private ke Neon</button><div id="importresult"></div></div></div>'+
 '<div class="card"><h2>Catalog Import History</h2><p class="sub">'+imports.imports.length+' batch tercatat. PDF bukan data stok atau penjualan riil.</p><div class="tablewrap"><table><tr><th>Imported</th><th>Count</th><th>Source</th><th>Validation</th></tr>'+imports.imports.map(x=>'<tr><td>'+escapeHtml(x.at)+'</td><td>'+x.items_imported+'</td><td>'+escapeHtml(x.source_file)+'</td><td>'+escapeHtml(x.source_classification)+'</td></tr>').join("")+'</table></div></div>';
 $("resetdemo").onclick=async()=>{
  if($("resetconfirm").value!=="RESET DEMO ONLY"){toast("Konfirmasi tidak cocok",true);return}
  if(!confirm("LAST CONFIRMATION: Arsipkan lalu bersihkan produk dan seluruh inquiry/matching demo saat ini? Akun dan audit log TIDAK dihapus."))return;
  try{const r=await api("/v1/admin/catalog/reset-demo","POST",{confirmation:"RESET DEMO ONLY"});
      toast("Archived demo reset completed");await migration()}
  catch(e){fail(e)}
 };
 $("importcatalog").onclick=async()=>{
  const file=$("importfile").files[0];
  if(!file){toast("Pilih JSON hasil cleansing dulu",true);return}
  try{
   const payload=JSON.parse(await file.text());
   if(!payload.manifest||!Array.isArray(payload.products))throw Error("Invalid import manifest or products");
   if(!confirm("Impor "+payload.products.length+" SKU dari "+payload.manifest.source_file_name+" ke Neon? Data tetap memerlukan verifikasi Technical."))return;
   $("importcatalog").disabled=true;$("importresult").textContent="Import berjalan, jangan tutup tab...";
   const r=await api("/v1/admin/catalog/import","POST",payload);
   toast("Imported "+r.imported_count+" catalog records");await migration();
  }catch(e){fail(e);$("importresult").textContent=e.message;$("importcatalog").disabled=false}
 };
}
async function auditTrail(){
 const [x,old]=await Promise.all([api("/v1/admin/audit-events?limit=200"),api("/v1/admin/catalog/imports")]);
 $("view").innerHTML=headline("ADMIN / FORENSIC AUDIT","Transaction Audit Trace",
 "Jejak permanen tindakan penting. Actor, role, operasi, entity, timestamp dan SHA-256 direkam dalam transaksi database yang sama.")+
 '<div class="card"><div class="toolbar"><h2>Latest '+x.events.length+' Transaction Events</h2><span class="tag">APPEND ONLY</span></div>'+
 '<div class="tablewrap"><table><tr><th>UTC Time</th><th>Actor ID / Role</th><th>Action</th><th>Entity</th><th>Trace ID</th></tr>'+
 x.events.map(y=>'<tr><td>'+escapeHtml(y.at)+'</td><td>#'+escapeHtml(y.actor_id)+' / '+escapeHtml(y.actor_role)+'</td><td><b>'+escapeHtml(y.action)+'</b></td><td>'+escapeHtml(y.entity)+' #'+escapeHtml(y.entity_id)+'</td><td><code>'+escapeHtml(y.id.slice(0,13))+'...</code></td></tr>').join("")+'</table></div>'+
 '<p class="note">Password, inquiry free-text dan isi katalog sengaja tidak disalin ke audit event. Sebagian transaksi lama masih tersimpan dalam tabel audit legacy.</p></div>';
}
async function users(){
 let users=await api("/v1/users");
 $("view").innerHTML=headline("ADMIN / ACCESS CONTROL","User Management","Kelola akun internal lima role. Data bisa persisten setelah Neon dihubungkan dan diverifikasi.")+
 '<div class="grid two"><div class="card"><h2>Buat Akun Internal</h2><form id="newuser" autocomplete="off"><label>Nama</label><input name="name" minlength="2" autocomplete="off" required><label>Email</label><input name="email" type="email" autocomplete="off" required><label>Password (minimal 12 karakter)</label><input name="password" type="password" autocomplete="new-password" minlength="12" required><label>Role</label><select name="role"><option value="sales">Sales</option><option value="technical">Technical</option><option value="manager">Manager Operasional</option><option value="gudang">Gudang</option><option value="admin">Admin</option></select><div class="form-actions"><button class="btn">Buat User</button></div></form></div><div class="card"><h2>Registered Users</h2><div class="tablewrap"><table><tr><th>Name</th><th>Email</th><th>Role</th></tr>'+users.map(x=>'<tr><td>'+escapeHtml(x.name)+'</td><td>'+escapeHtml(x.email)+'</td><td><span class="tag">'+escapeHtml(x.role)+'</span></td></tr>').join("")+'</table></div></div></div>';
 $("newuser").onsubmit=async e=>{e.preventDefault();try{let data=Object.fromEntries(new FormData(e.target));await api("/v1/users","POST",data);toast("Akun baru dibuat");await users()}catch(e){fail(e)}};
}
if(token)enter();else loginScreen();
</script></body></html>"""

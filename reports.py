"""Private, RBAC-enforced ERP and AI report exports. No unvalidated KPI claims.

Reports are generated from Neon or deterministic synthetic research baselines, not
device cache or localStorage. PDF/CSV files have no-store response headers.
"""
import csv
import io
import json
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from fastapi import Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, KeepTogether

CATALOG={
 "inquiries":("Inquiry Register",("admin","sales","technical","manager")),
 "matching":("BM25 Matching Runs",("admin","sales","technical","manager")),
 "technical_reviews":("Technical Review Decisions",("admin","technical","manager")),
 "manager_decisions":("Manager Approval and Return Log",("admin","manager")),
 "stock_movements":("Gudang Stock Movement Audit",("admin","gudang","manager")),
 "catalog":("Product Catalog Register",("admin","sales","technical","manager","gudang")),
 "audit":("Transaction Audit Trail",("admin",)),
 "ai_bundling":("AI-03 Product Bundling - Synthetic Baseline",("admin","sales","manager")),
 "ai_forecast":("AI-04 Demand Forecast - Synthetic Baseline",("admin","sales","manager","gudang")),
 "ai_research":("AI-02 Research Evidence Readiness",("admin","technical","manager"))
}
HEADERS={
 "inquiries":["ID","Customer Reference","Requirement","Status","Created At","Created By"],
 "matching":["Run ID","Inquiry ID","Method","Latency (ms)","Candidate Count","Created At"],
 "technical_reviews":["Review ID","Run ID","Inquiry ID","SKU","Relevance (0-3)","Decision","Reviewer ID","Rationale"],
 "manager_decisions":["Time","Actor ID","Inquiry ID","Action","Previous Status","New Status"],
 "stock_movements":["Time","Actor ID","Product ID","SKU","Previous Qty","Updated Qty"],
 "catalog":["SKU","Product","Type","Applications","Stock","Source","PDF Page","PDF Row"],
 "audit":["UTC Timestamp","Actor ID","Actor Role","Action","Entity","Entity ID","Trace ID"],
 "ai_bundling":["SKU A","SKU B","Basket Count","Support","Confidence","Lift"],
 "ai_forecast":["Week","Historical","Forecast","SKU"],
 "ai_research":["Metric","Value"]
}
NO_STORE={"Cache-Control":"private, no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache"}

def scalar(v):
    if v is None:return "UNKNOWN"
    if isinstance(v,bool):return "YES" if v else "NO"
    if isinstance(v,(dict,list)):return json.dumps(v,ensure_ascii=False,sort_keys=True)
    return str(v)

def json_fields(text):
    try:return json.loads(text or "{}")
    except (ValueError,TypeError):return {}

def report_rows(kind,user,db,limit=500):
    role=user["role"]
    if kind not in CATALOG:raise HTTPException(404,"Unknown report")
    if role not in CATALOG[kind][1]:raise HTTPException(403,"Report role access denied")
    source="ACTUAL_ERP"
    if kind=="inquiries":
        sql="""SELECT id,customer_ref,requirement,status,created_at,created_by
               FROM inquiries"""
        args=()
        if role=="sales":sql+=" WHERE created_by=?";args=(user["id"],)
        rows=db.execute(sql+" ORDER BY id DESC LIMIT ?",args+(limit,)).fetchall()
        values=[[r["id"],r["customer_ref"],r["requirement"],r["status"],r["created_at"],r["created_by"]] for r in rows]
    elif kind=="matching":
        sql="""SELECT r.id,r.inquiry_id,r.method,r.latency_ms,
                 (SELECT COUNT(*) FROM candidates c WHERE c.run_id=r.id) AS n,r.created_at
                 FROM runs r JOIN inquiries i ON i.id=r.inquiry_id"""
        args=()
        if role=="sales":sql+=" WHERE i.created_by=?";args=(user["id"],)
        rows=db.execute(sql+" ORDER BY r.id DESC LIMIT ?",args+(limit,)).fetchall()
        values=[[r["id"],r["inquiry_id"],r["method"],r["latency_ms"],r["n"],r["created_at"]] for r in rows]
    elif kind=="technical_reviews":
        rows=db.execute("""SELECT v.id,v.run_id,r.inquiry_id,p.sku,v.label,v.decision,v.reviewer_id,v.note
                           FROM reviews v JOIN runs r ON r.id=v.run_id JOIN products p ON p.id=v.product_id
                           ORDER BY v.id DESC LIMIT ?""",(limit,)).fetchall()
        values=[[r["id"],r["run_id"],r["inquiry_id"],r["sku"],r["label"],r["decision"],r["reviewer_id"],r["note"]] for r in rows]
    elif kind=="manager_decisions":
        rows=db.execute("""SELECT at,actor_id,entity_id,action,before_json,after_json
                           FROM transaction_events WHERE action IN ('MANAGER_APPROVE','MANAGER_RETURN')
                           ORDER BY at DESC LIMIT ?""",(limit,)).fetchall()
        values=[[r["at"],r["actor_id"],r["entity_id"],r["action"],json_fields(r["before_json"]).get("status"),json_fields(r["after_json"]).get("status")] for r in rows]
    elif kind=="stock_movements":
        rows=db.execute("""SELECT e.at,e.actor_id,e.entity_id,p.sku,e.before_json,e.after_json
                           FROM transaction_events e LEFT JOIN products p ON CAST(e.entity_id AS TEXT)=CAST(p.id AS TEXT)
                           WHERE e.action='STOCK_UPDATE' ORDER BY e.at DESC LIMIT ?""",(limit,)).fetchall()
        values=[[r["at"],r["actor_id"],r["entity_id"],r["sku"],json_fields(r["before_json"]).get("stock"),json_fields(r["after_json"]).get("stock")] for r in rows]
    elif kind=="catalog":
        rows=db.execute("""SELECT p.sku,p.name,d.product_type,p.application,p.stock,p.source_ref,d.source_page,d.source_number
                           FROM products p LEFT JOIN catalog_product_details d ON d.sku=p.sku
                           ORDER BY p.sku LIMIT ?""",(limit,)).fetchall()
        values=[[r["sku"],r["name"],r["product_type"],r["application"],r["stock"],r["source_ref"],r["source_page"],r["source_number"]] for r in rows]
        source="SUPPLIER_CATALOG_PDF_UNVERIFIED"
    elif kind=="audit":
        rows=db.execute("""SELECT at,actor_id,actor_role,action,entity,entity_id,id
                           FROM transaction_events ORDER BY at DESC LIMIT ?""",(limit,)).fetchall()
        values=[[r["at"],r["actor_id"],r["actor_role"],r["action"],r["entity"],r["entity_id"],r["id"]] for r in rows]
    elif kind=="ai_bundling":
        from multi_ai import bundling_rules
        rules=bundling_rules()
        values=[[x.get(k) for k in ("antecedent_sku","recommended_sku","co_occurrences","support","confidence","lift")] for x in rules[:limit]]
        source="SYNTHETIC_ORDER_BASKETS_NOT_COMPANY_SALES"
    elif kind=="ai_forecast":
        from multi_ai import forecast_baseline
        data=forecast_baseline("FLV-STRAW-01",4)
        # This report is intentionally limited to a fixed synthetic SKU.
        values=[]
        for x in data.get("history",[]):values.append([x["week"],x["units"],None,"FLV-STRAW-01"])
        for x in data.get("forecast",[]):values.append([x["week"],None,x["predicted_units"],"FLV-STRAW-01"])
        values=values[:limit];source="SYNTHETIC_DEMAND_NOT_COMPANY_SALES"
    else:
        from research.evidence import readiness, methodology
        data=readiness(db)
        methods=methodology()
        values=[["Research status",data.get("scientific_readiness")],
                ["Qualified research runs",data.get("fully_labelled_runs")],
                ["Candidate review coverage",str(data.get("candidate_label_coverage_pct"))+"% (NOT accuracy)"],
                ["Method",methods.get("training_status")],
                ["Company fine-tuned model","NO"],
                ["Held-out test verified","NO"],
                ["UAT records excluded","YES"]]
        source="RESEARCH_STATUS_ONLY_NOT_VALIDATED"
    return {"type":kind,"title":CATALOG[kind][0],"source":source,"generated_at":datetime.now(timezone.utc).isoformat(),
            "columns":HEADERS[kind],"rows":values,"count":len(values),
            "disclaimer":"Research pilot. PDF supplier catalogue remains unverified; AI03/AI04 synthetic and AI02 has no company fine-tuning or validated accuracy."}

def _safe_paragraph(v,style):
    return Paragraph(escape(scalar(v)).replace("\n","<br/>"),style)

def render_pdf(report):
    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=landscape(A4),rightMargin=14*mm,leftMargin=14*mm,
                          topMargin=16*mm,bottomMargin=16*mm,title=report["title"],
                          author="PT. Li Liang ERP Multi-AI Research Pilot")
    styles=getSampleStyleSheet()
    title_style=ParagraphStyle("ReportTitle",parent=styles["Heading1"],fontName="Helvetica-Bold",
                               fontSize=16,leading=21,textColor=colors.HexColor("#18365c"),spaceAfter=10)
    small=ParagraphStyle("ReportSmall",parent=styles["Normal"],fontSize=7.1,leading=10,textColor=colors.HexColor("#283d54"))
    heading=ParagraphStyle("ColumnHeader",parent=small,fontName="Helvetica-Bold",textColor=colors.white)
    normal=ParagraphStyle("CellText",parent=small,fontSize=6.8,leading=9)
    doc_title=report["title"]
    story=[_safe_paragraph(doc_title,title_style),
           _safe_paragraph("ERP MULTI-AI | RESEARCH PILOT | Source: "+report["source"],small),
           _safe_paragraph("Generated UTC: "+report["generated_at"]+" | Rows: "+str(report["count"]),small),
           Spacer(1,9)]
    header=[_safe_paragraph(c,heading) for c in report["columns"]]
    data=[header]+[[_safe_paragraph(v,normal) for v in row] for row in report["rows"]]
    if len(data)==1:data.append([_safe_paragraph("Belum ada transaksi / no records.",normal)]+[""]*(len(header)-1))
    table=LongTable(data,repeatRows=1,hAlign="LEFT",colWidths=[(269*mm)/len(header)]*len(header))
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#18365c")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#eef3f9")]),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("GRID",(0,0),(-1,-1),.25,colors.HexColor("#d8e2ed")),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(table)
    story.extend([Spacer(1,10),_safe_paragraph(report["disclaimer"],small)])
    def decorate(canvas,doc):
        canvas.saveState()
        canvas.setFont("Helvetica",8);canvas.setFillColor(colors.HexColor("#506781"))
        canvas.drawString(14*mm,10*mm,"PT. Li Liang ERP | Internal research pilot")
        canvas.drawRightString(283*mm,10*mm,"Page "+str(doc.page))
        canvas.restoreState()
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
    return buffer.getvalue()

def inquiry_receipt(user,db,iid):
    if user["role"]=="gudang":raise HTTPException(403,"Warehouse cannot export customer inquiries")
    q=db.execute("""SELECT i.id,i.customer_ref,i.requirement,i.status,i.created_at,i.created_by,u.name
                    FROM inquiries i JOIN users u ON u.id=i.created_by WHERE i.id=?""",(iid,)).fetchone()
    if not q:raise HTTPException(404,"Inquiry not found")
    if user["role"]=="sales" and user["id"]!=q["created_by"]:raise HTTPException(403,"Not your inquiry")
    runs=db.execute("SELECT id,method,latency_ms,created_at FROM runs WHERE inquiry_id=? ORDER BY id",(iid,)).fetchall()
    rows=[["Inquiry ID",q["id"]],["Customer Reference",q["customer_ref"]],
          ["Requirement",q["requirement"]],["Status",q["status"]],
          ["Created At",q["created_at"]],["Created By",q["name"]]]
    for r in runs:
        rows.append(["Matching Run",str(r["id"])+" | "+r["method"]+" | "+str(r["latency_ms"])+"ms"])
        candidates=db.execute("""SELECT c.rank,p.sku,p.name,c.score FROM candidates c
                                 JOIN products p ON p.id=c.product_id WHERE c.run_id=? ORDER BY c.rank""",(r["id"],)).fetchall()
        for c in candidates:
            rows.append(["Candidate "+str(c["rank"]),str(c["sku"])+" | "+str(c["name"])+" | BM25 score "+str(c["score"])])
        reviews=db.execute("""SELECT p.sku,v.label,v.decision,v.note,v.reviewer_id FROM reviews v
                              JOIN products p ON p.id=v.product_id WHERE v.run_id=? ORDER BY v.id""",(r["id"],)).fetchall()
        for v in reviews:
            rows.append(["Technical Review",str(v["sku"])+" | "+v["decision"]+" | label "+str(v["label"])+" | reviewer #"+str(v["reviewer_id"])+" | "+v["note"]])
    for e in db.execute("""SELECT at,action,actor_id FROM transaction_events
                           WHERE entity='inquiry' AND entity_id=? AND action IN ('MANAGER_APPROVE','MANAGER_RETURN')
                           ORDER BY at""",(str(iid),)).fetchall():
        rows.append(["Manager Decision",str(e["action"])+" at "+str(e["at"])+" by user #"+str(e["actor_id"])])
    return {"type":"inquiry_receipt","title":"Inquiry #"+str(iid)+" - Transaction Report",
            "source":"LIVE_ERP_TRANSACTION","generated_at":datetime.now(timezone.utc).isoformat(),
            "columns":["Field","Recorded Detail"],"rows":rows,"count":len(rows),
            "disclaimer":"BM25 score is uncalibrated. Technical review/Manager approval are separate business decisions, not scientific accuracy measurements."}

def export(report,fmt,filename):
    if fmt=="json":return JSONResponse(report,headers=NO_STORE)
    if fmt=="csv":
        buf=io.StringIO();w=csv.writer(buf)
        w.writerow(["Title",report["title"]]);w.writerow(["Source",report["source"]])
        w.writerow(["Generated UTC",report["generated_at"]]);w.writerow([])
        w.writerow(report["columns"])
        for row in report["rows"]:w.writerow([scalar(x) for x in row])
        return Response(buf.getvalue().encode("utf-8-sig"),media_type="text/csv; charset=utf-8",headers={**NO_STORE,"Content-Disposition":'attachment; filename="'+filename+'.csv"'})
    content=render_pdf(report)
    return Response(content,media_type="application/pdf",headers={**NO_STORE,"Content-Disposition":'attachment; filename="'+filename+'.pdf"'})

def mount_reports(app,current,get_db):
    @app.get("/v1/reports/available")
    def available(user=Depends(current)):
        return {"reports":[{"id":key,"title":title} for key,(title,roles) in CATALOG.items() if user["role"] in roles],
                "individual_inquiry_print":user["role"] in ("admin","sales","technical","manager"),
                "notice":"PDF and CSV download directly from server; data is refreshed from Neon. UAT review is not scientific accuracy."}
    @app.get("/v1/reports/inquiry/{iid}")
    def print_inquiry(iid:int,format:str=Query(default="pdf",pattern="^(json|csv|pdf)$"),
                      user=Depends(current),db=Depends(get_db)):
        report=inquiry_receipt(user,db,iid)
        return export(report,format,"Liliang_Inquiry_"+str(iid))
    @app.get("/v1/reports/{kind}")
    def print_report(kind:str,format:str=Query(default="pdf",pattern="^(json|csv|pdf)$"),
                     limit:int=Query(default=500,ge=1,le=2000),
                     user=Depends(current),db=Depends(get_db)):
        report=report_rows(kind,user,db,limit)
        return export(report,format,"Liliang_Report_"+kind)

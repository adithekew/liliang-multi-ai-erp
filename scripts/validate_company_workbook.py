"""Offline validation of the PT Liliang ERP Multi-AI data workbook.

The report contains counts, hashes, gates and row references only. It does not
copy inquiry text, customer identifiers, order values or supplier descriptions.
Run in an approved private environment; keep workbook/report outside Git.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from collections import defaultdict,Counter
from datetime import date,datetime,timedelta
from pathlib import Path
from openpyxl import load_workbook

REQUIRED={
"01_SUPPLIER_CATALOG":{"supplier_id","supplier_name","supplier_sku","product_name_official","source_record_date","technical_verification_status"},
"02_TECHNICAL_EVIDENCE":{"evidence_id","supplier_id","supplier_sku","evidence_type","field_supported","verbatim_value","private_storage_uri","review_status"},
"03_CUSTOMER_INQUIRIES":{"inquiry_id","inquiry_date","language","inquiry_text_anonymized","processing_authorization_ref","data_split"},
"04_AI01_GOLD_LABELS":{"inquiry_id","annotator_id","intent_label","label_version"},
"05_AI02_RELEVANCE_LABELS":{"inquiry_id","internal_sku","reviewer_id","relevance_grade_0_3","technical_decision","review_rationale","adjudication_status","label_set_version"},
"06_SALES_ORDERS":{"order_ref","order_date","order_status","source_document_ref","finance_reconciliation_ref","source_classification","finance_verifier_id","verified_at"},
"07_SALES_ORDER_LINES":{"order_ref","line_ref","internal_sku","quantity","unit","line_status"},
"08_DEMAND_WEEKLY":{"internal_sku","week_start","week_end","gross_sales_kg","return_kg","net_demand_kg","missing_data_flag","source_document_ref","finance_reconciliation_ref","finance_verifier_id","verified_at","unit_definition_version"},
"09_WAREHOUSE_LOCATIONS":{"warehouse_id","warehouse_name","location_status"},
"10_STOCK_OPENING":{"snapshot_id","as_of_datetime","warehouse_id","internal_sku","quantity","unit","uom_mapping_status","count_method","reconciliation_status","source_record_ref"},
"11_STOCK_MOVEMENTS":{"movement_id","movement_datetime","movement_type","internal_sku","quantity","unit","reference_document","idempotency_key","movement_status"},
"12_MODEL_RUNS":{"run_id","module","task_type","algorithm_name","model_version","code_commit","dataset_version","run_status","approval_status"},
"13_AI_TEST_RESULTS":{"test_id","run_id","module","test_case_id","test_category","expected_result","actual_result","pass_fail","reviewer_role"},
"14_AGENT_EVALUATION":{"case_id","suite_version","user_role","expected_tool","actual_tool","tool_call_correct","groundedness_score_1_5","policy_compliant","unauthorized_action_attempted","outcome"}
}
PII=[re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",re.I),
     re.compile(r"(?<!\w)(?:\+62|62|08)[\s.-]?\d[\d\s.-]{7,13}\d(?!\w)")]

def _sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def _rows(ws):
    values=list(ws.iter_rows(values_only=True))
    if not values:return [],set()
    headers=[str(x).strip() if x is not None else "" for x in values[0]]
    return [dict(zip(headers,row)) for row in values[1:] if any(x is not None and str(x).strip() for x in row)],set(headers)

def _date(value):
    if isinstance(value,datetime):return value.date()
    if isinstance(value,date):return value
    return date.fromisoformat(str(value)[:10])

def validate(path):
    p=Path(path).expanduser().resolve()
    if not p.is_file():raise ValueError("Workbook not found")
    if any((x/".git").exists() for x in (p,*p.parents)):
        raise ValueError("Company workbook must be outside any Git checkout")
    wb=load_workbook(p,read_only=True,data_only=True)
    errors=[];warnings=[];counts={};data={}
    for sheet,required in REQUIRED.items():
        if sheet not in wb.sheetnames:
            errors.append({"sheet":sheet,"issue":"MISSING_SHEET"});continue
        rows,headers=_rows(wb[sheet]);data[sheet]=rows;counts[sheet]=len(rows)
        missing=sorted(required-headers)
        if missing:errors.append({"sheet":sheet,"issue":"MISSING_COLUMNS","columns":missing})
    if errors and any(x["issue"] in ("MISSING_SHEET","MISSING_COLUMNS") for x in errors):
        return {"status":"SCHEMA_INVALID","workbook_sha256":_sha(p),"counts":counts,"errors":errors,"warnings":warnings}
    supplier=data["01_SUPPLIER_CATALOG"];evidence=data["02_TECHNICAL_EVIDENCE"]
    inquiries=data["03_CUSTOMER_INQUIRIES"];ai01=data["04_AI01_GOLD_LABELS"];ai02=data["05_AI02_RELEVANCE_LABELS"]
    orders=data["06_SALES_ORDERS"];lines=data["07_SALES_ORDER_LINES"];weekly=data["08_DEMAND_WEEKLY"]
    opening=data["10_STOCK_OPENING"];moves=data["11_STOCK_MOVEMENTS"];runs=data["12_MODEL_RUNS"]
    results=data["13_AI_TEST_RESULTS"];agent=data["14_AGENT_EVALUATION"]

    supplier_keys=set();supplier_skus=set()
    for i,r in enumerate(supplier,2):
        key=(str(r.get("supplier_id") or "").strip(),str(r.get("supplier_sku") or "").strip())
        if not all(key) or key in supplier_keys:errors.append({"sheet":"01_SUPPLIER_CATALOG","row":i,"issue":"MISSING_OR_DUPLICATE_SUPPLIER_KEY"})
        supplier_keys.add(key)
        sku=str(r.get("internal_sku") or "").strip().upper()
        if sku:supplier_skus.add(sku)
    evidence_ids={str(r.get("evidence_id") or "").strip() for r in evidence if r.get("evidence_id")}
    verified_supplier=0
    for i,r in enumerate(supplier,2):
        if str(r.get("technical_verification_status") or "").upper()=="VERIFIED":
            verified_supplier+=1
            refs=[str(r.get(k) or "").strip() for k in ("tds_evidence_id","coa_evidence_id","sds_evidence_id")]
            if not any(x and x in evidence_ids for x in refs):
                errors.append({"sheet":"01_SUPPLIER_CATALOG","row":i,"issue":"VERIFIED_WITHOUT_LINKED_EVIDENCE"})
    inquiry_by_id={}
    split_by_group=defaultdict(set)
    for i,r in enumerate(inquiries,2):
        iid=str(r.get("inquiry_id") or "").strip()
        if not iid or iid in inquiry_by_id:errors.append({"sheet":"03_CUSTOMER_INQUIRIES","row":i,"issue":"MISSING_OR_DUPLICATE_INQUIRY_ID"})
        inquiry_by_id[iid]=r
        text=str(r.get("inquiry_text_anonymized") or "")
        if any(rx.search(text) for rx in PII):errors.append({"sheet":"03_CUSTOMER_INQUIRIES","row":i,"issue":"POTENTIAL_PII_REQUIRES_MANUAL_REVIEW"})
        if not str(r.get("processing_authorization_ref") or "").strip():errors.append({"sheet":"03_CUSTOMER_INQUIRIES","row":i,"issue":"MISSING_PROCESSING_AUTHORIZATION"})
        group=str(r.get("duplicate_group_id") or iid)
        split_by_group[group].add(str(r.get("data_split") or "UNASSIGNED").upper())
    for group,splits in split_by_group.items():
        if len(splits)>1:errors.append({"sheet":"03_CUSTOMER_INQUIRIES","issue":"DUPLICATE_GROUP_CROSSES_SPLITS"})
    ai01_coverage=sum(1 for r in ai01 if str(r.get("inquiry_id") or "") in inquiry_by_id)
    pair_reviewers=defaultdict(set);pair_status=defaultdict(set)
    for i,r in enumerate(ai02,2):
        iid=str(r.get("inquiry_id") or "")
        sku=str(r.get("internal_sku") or "").upper()
        raw_grade = r.get("relevance_grade_0_3")
        decision = str(r.get("technical_decision") or "").strip().upper()
        unjudged = raw_grade in (None, "") and decision == "UNKNOWN"
        graded = type(raw_grade) in (int, float, str) and raw_grade in (0, 1, 2, 3, "0", "1", "2", "3")
        reviewer = str(r.get("reviewer_id") or "").strip()
        if iid not in inquiry_by_id:errors.append({"sheet":"05_AI02_RELEVANCE_LABELS","row":i,"issue":"UNKNOWN_INQUIRY_ID"})
        if not graded and not unjudged:errors.append({"sheet":"05_AI02_RELEVANCE_LABELS","row":i,"issue":"INVALID_RELEVANCE_GRADE"})
        if not reviewer:errors.append({"sheet":"05_AI02_RELEVANCE_LABELS","row":i,"issue":"MISSING_REVIEWER_ID"})
        if not str(r.get("review_rationale") or "").strip():errors.append({"sheet":"05_AI02_RELEVANCE_LABELS","row":i,"issue":"MISSING_REVIEW_RATIONALE"})
        if graded and reviewer and decision != "UNKNOWN" and iid in inquiry_by_id and sku:
            key = (iid, sku, r.get("label_set_version"), r.get("review_round"))
            pair_reviewers[key].add(reviewer)
            pair_status[key].add(str(r.get("adjudication_status") or "").upper())
    adjudicated_pairs=len({k[:2] for k in pair_reviewers if len(pair_reviewers[k])>=2 and pair_status[k]&{"AGREED","ADJUDICATED"}})
    # Finance orders: attested/proxy/synthetic are not silently promoted to verified facts.
    order_by_ref={}
    finance_orders=set()
    for i,r in enumerate(orders,2):
        ref=str(r.get("order_ref") or "")
        if not ref or ref in order_by_ref:errors.append({"sheet":"06_SALES_ORDERS","row":i,"issue":"MISSING_OR_DUPLICATE_ORDER_REF"})
        order_by_ref[ref]=r
        if str(r.get("source_classification") or "").upper()=="FINANCE_VERIFIED":
            finance_orders.add(ref)
        else:warnings.append({"sheet":"06_SALES_ORDERS","row":i,"issue":"NOT_FINANCE_VERIFIED_NOT_ELIGIBLE_FOR_COMPANY_EVALUATION"})
    valid_lines=0;kg_by_sku=defaultdict(dict)
    for i,r in enumerate(lines,2):
        ref=str(r.get("order_ref") or "");sku=str(r.get("internal_sku") or "").upper()
        if ref not in order_by_ref:errors.append({"sheet":"07_SALES_ORDER_LINES","row":i,"issue":"UNKNOWN_ORDER_REF"})
        try:q=float(r.get("quantity") or 0)
        except (TypeError,ValueError):q=0
        if q<=0:errors.append({"sheet":"07_SALES_ORDER_LINES","row":i,"issue":"INVALID_QUANTITY"})
        if sku and supplier_skus and sku not in supplier_skus: warnings.append({"sheet":"07_SALES_ORDER_LINES","row":i,"issue":"SKU_NOT_MAPPED_TO_SUPPLIER_CATALOG"})
        if ref in finance_orders and str(r.get("line_status") or "").upper() in ("CONFIRMED","PARTIAL"):
            valid_lines+=1
    for i,r in enumerate(weekly,2):
        sku=str(r.get("internal_sku") or "").upper()
        try:d=_date(r.get("week_start"))
        except Exception:errors.append({"sheet":"08_DEMAND_WEEKLY","row":i,"issue":"INVALID_WEEK_START"});continue
        if d.weekday()!=0:errors.append({"sheet":"08_DEMAND_WEEKLY","row":i,"issue":"WEEK_START_NOT_MONDAY"})
        if str(r.get("missing_data_flag") or "").upper()!="NONE":continue
        try:q=float(r.get("net_demand_kg"))
        except (TypeError,ValueError):q=-1
        if q<0:errors.append({"sheet":"08_DEMAND_WEEKLY","row":i,"issue":"INVALID_NET_DEMAND"})
        if sku in kg_by_sku and d in kg_by_sku[sku]:errors.append({"sheet":"08_DEMAND_WEEKLY","row":i,"issue":"DUPLICATE_SKU_WEEK"})
        kg_by_sku[sku][d]=q
    forecast_ready=[]
    for sku,points in kg_by_sku.items():
        dates=sorted(points)
        if len(dates)>=24 and all(dates[j]-dates[j-1]==timedelta(weeks=1) for j in range(1,len(dates))):
            forecast_ready.append(sku)
    wms_opening_ready=sum(1 for r in opening if str(r.get("uom_mapping_status") or "").upper()=="VERIFIED"
                          and str(r.get("count_method") or "").upper()=="PHYSICAL_COUNT"
                          and str(r.get("reconciliation_status") or "").upper() in ("RECONCILED","APPROVED"))
    movement_ids=[str(r.get("movement_id") or "") for r in moves if r.get("movement_id")]
    idem=[str(r.get("idempotency_key") or "") for r in moves if r.get("idempotency_key")]
    if len(movement_ids)!=len(set(movement_ids)):errors.append({"sheet":"11_STOCK_MOVEMENTS","issue":"DUPLICATE_MOVEMENT_ID"})
    if len(idem)!=len(set(idem)):errors.append({"sheet":"11_STOCK_MOVEMENTS","issue":"DUPLICATE_IDEMPOTENCY_KEY"})
    model_runs={str(r.get("run_id") or "") for r in runs if r.get("run_id")}
    orphan_results=sum(1 for r in results if str(r.get("run_id") or "") not in model_runs)
    if orphan_results:errors.append({"sheet":"13_AI_TEST_RESULTS","issue":"RESULT_REFERENCES_UNKNOWN_RUN","count":orphan_results})
    agent_cases=sum(1 for r in agent if str(r.get("outcome") or "").upper() in ("PASS","FAIL","BLOCKED"))
    eligible_orders=sum(1 for ref,r in order_by_ref.items() if ref in finance_orders and str(r.get("order_status") or "").upper() in ("CONFIRMED","FULFILLED"))
    report={
      "status":"VALIDATION_REPORT_READY_WITH_GATES" if not errors else "VALIDATION_ERRORS_FOUND",
      "workbook_sha256":_sha(p),"counts":counts,
      "readiness":{
        "supplier_catalog_rows":len(supplier),"supplier_rows_marked_verified":verified_supplier,
        "technical_evidence_rows":len(evidence),"authorized_inquiries":len(inquiry_by_id),
        "ai01_label_rows":ai01_coverage,"ai02_relevance_rows":len(ai02),"ai02_pairs_dual_reviewed_and_adjudicated":adjudicated_pairs,
        "finance_verified_orders":eligible_orders,"finance_verified_order_lines":valid_lines,
        "ai03_minimum_10_orders_met":eligible_orders>=10,
        "ai04_skus_with_24_contiguous_complete_weeks":len(forecast_ready),"ai04_ready_skus":sorted(forecast_ready),
        "wms_physical_count_rows_reconciled_uom_verified":wms_opening_ready,
        "model_runs_manifested":len(runs),"ai_test_result_rows":len(results),"agent_test_cases":agent_cases
      },
      "errors":errors,"warnings":warnings,
      "hard_gates":{
        "supplier_technical_verification":"Only rows with valid linked current evidence can be promoted after human review.",
        "ai01":"Needs approved inquiry corpus and adjudicated gold intent/entity labels.",
        "ai02":"Needs authorized inquiries, complete relevance judgments for test candidates, independent dual review, frozen split and paired BM25/dense/RRF evaluation.",
        "ai03":"Only Finance-verified true order/invoice baskets qualify; >=10 is exploratory readiness, not scientific sufficiency.",
        "ai04":"Needs >=24 contiguous complete KG weeks per SKU and rolling-origin comparison against baselines.",
        "wms":"Needs current physical count, verified UoM, reconciled locations, lot/expiry rules and UAT approval.",
        "agent":"Needs held-out tool selection, grounding, role-policy and unauthorized-action evaluation."
      },
      "scientific_validation_complete":False,"production_release_authorized":False,
      "note":"Schema/data-readiness checks do not certify document authenticity, data rights, model accuracy or production readiness."
    }
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--workbook",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    out=Path(a.output).expanduser().resolve()
    if any((x/".git").exists() for x in (out,*out.parents)):raise ValueError("Report must be outside Git checkout")
    report=validate(a.workbook);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"workbook_sha256":report["workbook_sha256"],
      "readiness":report["readiness"],"error_count":len(report["errors"]),
      "warning_count":len(report["warnings"]),"scientific_validation_complete":False},ensure_ascii=False))
if __name__=="__main__":main()

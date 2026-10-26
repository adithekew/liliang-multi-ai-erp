"""Private-source readiness audit for PT Liliang's extracted 2025 sales.

Use only on an authorized LOCAL copy of the supplied files. Emits counts,
SHA256s, and gates; never emits customer names, SKU values, or raw sales totals.
A source document is not independently reconciled SO/invoice evidence.
"""
import argparse,csv,hashlib,json
from collections import Counter
from pathlib import Path

def load_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as stream:
        rows=list(csv.DictReader(stream))
    return rows

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def evaluate(item_file,line_file,monthly_file,basket_file):
    items=load_csv(item_file)
    lines=load_csv(line_file)
    monthly=load_csv(monthly_file)
    baskets=load_csv(basket_file)
    # Fail closed on unrecognized schema; no creating order IDs or dates from
    # arbitrary paragraphs and no treating 2025-06 payment-due as a sale.
    schemas=[
       (items,{"basis","month_label","extract_decision","date_granularity"}),
       (lines,{"line_id","month_label","basket_validated_order_id","date_granularity","manual_sku_review_needed"}),
       (monthly,{"month_label","sku_compare_key","sku_review_needed","date_granularity"}),
       (baskets,{"basket_proxy_id","confirmed_invoice_id","transaction_date_available","valid_for_association_rule_ground_truth"})]
    for rows,required in schemas:
        if not rows or not required.issubset(rows[0]):
            raise ValueError("Missing columns or empty source: "+",".join(sorted(required)))
    sale=[r for r in items if r["basis"]=="SALES_LIST"]
    due=[r for r in items if r["basis"]=="PAYMENT_DUE_LIST"]
    other=len(items)-len(sale)-len(due)
    deid_dates=Counter(r["date_granularity"] for r in lines)
    months=sorted({r["month_label"] for r in monthly})
    review=sum(r["sku_review_needed"]=="YES" for r in monthly)
    proxy=sum(r["valid_for_association_rule_ground_truth"]=="YES" for r in baskets)
    invoices=sum(r["confirmed_invoice_id"]!="NO" and bool(r["confirmed_invoice_id"]) for r in baskets)
    daily=sum(r["transaction_date_available"]=="YES" for r in baskets)
    # In case a later source passes these gates, still do not automatically
    # approve the study. Require documentary and independent expert sign-off.
    no_true_invoice=(invoices==0 or proxy==0)
    no_true_dates=daily==0 or not any(d=="DAY_VERIFIED" for d in deid_dates)
    report={
      "status":"PRELIMINARY_COMPANY_SOURCE_NOT_VERIFIED",
      "input_checksums_sha256":{
        "item_lines":sha(item_file),"deidentified_lines":sha(line_file),
        "monthly_observations":sha(monthly_file),"basket_proxies":sha(basket_file)},
      "counts":{
        "all_item_rows":len(items),"sales_list_rows":len(sale),
        "payment_due_rows":len(due),"other_rows":other,
        "deidentified_sales_lines":len(lines),"monthly_sku_rows":len(monthly),
        "unique_sku_keys_in_monthly":len({r["sku_compare_key"] for r in monthly}),
        "month_count":len(months),"monthly_rows_require_sku_review":review,
        "basket_proxy_groups":len(baskets),"verified_order_baskets":proxy,
        "invoice_ids_present":invoices,"transaction_dates_present":daily
      },
      "coverage":{"observed_months":months,
                  "june_2025_appears_as_sales_month":"2025-06" in months,
                  "date_granularity_summary":dict(deid_dates)},
      "gates":{
         "AI01_INQUIRY_LABEL_TRAINING":"BLOCKED_NEED_APPROVED_INQUIRIES_AND_GOLD_LABELS",
         "AI02_SUPERVISED_MINILM":"BLOCKED_NEED_INDEPENDENT_TECHNICAL_LABELS_0_TO_3",
         "AI03_REAL_BASKET_ASSOCIATIONS":"BLOCKED_NO_VERIFIED_SALES_ORDER_OR_INVOICE" if no_true_invoice else "REQUIRES_MANUAL_FINANCE_SIGNOFF",
         "AI04_WEEKLY_DEMAND_TRAINING":"BLOCKED_NO_TRANSACTION_DATES_AND_JUNE_RECONCILIATION" if no_true_dates else "REQUIRES_FINANCE_DATE_AND_UNIT_SIGNOFF",
         "WMS_REAL_STOCK":"BLOCKED_STOCK_OPNAME_PENDING"
      },
      "rules":[
         "A list bullet / customer grouping is not an order or invoice.",
         "Payment-due June 2025 is not confirmed June sales.",
         "Missing monthly sales do not equal zero demand.",
         "Sale list values may reflect orders, shipments or invoiced quantities; Finance must reconcile.",
         "No new company dataset is committed to public GitHub or automatically deployed."
      ],
      "ready_for_company_model_training":False,
      "independent_finance_validation":False,
      "independent_technical_label_validation":False
    }
    return report

def main():
    p=argparse.ArgumentParser()
    for arg in ["items","lines","monthly","baskets","out"]:
        p.add_argument("--"+arg,required=True)
    a=p.parse_args()
    out=Path(a.out).resolve()
    result=evaluate(a.items,a.lines,a.monthly,a.baskets)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"counts":result["counts"],
                       "ready_for_company_model_training":False}))

if __name__=="__main__":main()

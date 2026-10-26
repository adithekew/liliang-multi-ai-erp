"""Offline, exploratory pooled monthly model on unverified 2025 sales-list data.

June excluded. No invented weekly dates or zeros. Requires six explicitly
observed, unflagged months July–December, with last month held out by time.
Model is NOT validated by Finance and cannot be deployed to /v1/ai/forecast-company.
"""
import csv,json,hashlib,math, argparse
from collections import defaultdict
from pathlib import Path

MONTHS=[f"2025-{m:02d}" for m in range(7,13)]

def _ridge(X,y,penalty=2):
    d=3
    a=[[sum(x[i]*x[j] for x in X)+(penalty if i==j and i>0 else 0)
        for j in range(d)] for i in range(d)]
    b=[sum(x[i]*v for x,v in zip(X,y)) for i in range(d)]
    for k in range(d):
        pivot=max(range(k,d),key=lambda i:abs(a[i][k]))
        if abs(a[pivot][k])<1e-9:raise ValueError("Insufficient independent training data")
        a[k],a[pivot]=a[pivot],a[k];b[k],b[pivot]=b[pivot],b[k]
        z=a[k][k]
        for j in range(k,d):a[k][j]/=z
        b[k]/=z
        for i in range(d):
            if i==k:continue
            z=a[i][k]
            for j in range(k,d):a[i][j]-=z*a[k][j]
            b[i]-=z*b[k]
    return b

def experiment(records):
    series=defaultdict(dict)
    for r in records:
        if r["month_label"]=="2025-06" or r["sku_review_needed"]!="NO":
            continue
        if r["month_label"] not in MONTHS:continue
        q=float(r["quantity_kg"])
        if not math.isfinite(q) or q<0:continue
        key=r["sku_compare_key"]
        if not key or r["month_label"] in series[key]:
            raise ValueError("Missing SKU or duplicate SKU-month")
        series[key][r["month_label"]]=q
    complete={sku:[v[m] for m in MONTHS] for sku,v in series.items()
             if all(m in v for m in MONTHS)}
    if len(complete)<5:raise ValueError("Not enough SKU with 6 complete Jul–Dec months")
    X=[];y=[]
    for vals in complete.values():
        scale=max(1,sum(vals[:2])/2)  # no future-data leakage in normalization
        for i in (2,3):  # train target Sep/Oct only
            X.append([1,vals[i-1]/scale,vals[i-2]/scale])
            y.append(vals[i]/scale)
    weights=_ridge(X,y)
    errors=[];baseline=[]
    for vals in complete.values():
        scale=max(1,sum(vals[:2])/2)
        pred=max(0,scale*sum(w*x for w,x in zip(weights,
                [1,vals[4]/scale,vals[3]/scale])))
        errors.append(abs(vals[5]-pred))
        baseline.append(abs(vals[5]-(vals[4]+vals[3])/2))
    mae=sum(errors)/len(errors)
    naive_mae=sum(baseline)/len(baseline)
    return {"status":"PRELIMINARY_UNVERIFIED_MONTHLY_EXPERIMENT",
      "excluded_month":"2025-06","training_period":"2025-09..2025-10",
      "holdout_month":"2025-12","training_examples":len(X),
      "tested_skus":len(complete),"trained_algorithm":"POOLED_RIDGE_WITH_2_MONTH_LAGS",
      "weights":[round(x,8) for x in weights],
      "model_mae_kg":round(mae,4),"moving_average_2_mae_kg":round(naive_mae,4),
      "model_better_than_baseline":mae<naive_mae,
      "finance_validated":False,"scientifically_validated":False,
      "deployed_to_erp":False,"stock_used":False,
      "limitations":["Small sample; single-month chronological holdout",
       "Monthly sales-list not reconciled against invoice/returns",
       "No evidence of zero sales for missing months; missing SKU-month excluded",
       "Model must not automatically replace live AI-04 baseline"]}

def run(source,output):
    with open(source,encoding="utf-8-sig",newline="") as f:
        r=experiment(list(csv.DictReader(f)))
    out=Path(output).expanduser().resolve()
    if any((p/".git").exists() for p in (out.parent,*out.parent.parents)):
        raise ValueError("Never save private training metadata to public repository")
    out.parent.mkdir(parents=True,exist_ok=True)
    r["source_sha256"]=hashlib.sha256(Path(source).read_bytes()).hexdigest()
    out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    return r

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--monthly",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();result=run(a.monthly,a.out)
    print(json.dumps({"status":result["status"],"tested_skus":result["tested_skus"],
      "model_better_than_baseline":result["model_better_than_baseline"]}))

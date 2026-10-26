"""OFFLINE demand-model training only on independently reconciled weekly kg data.

Train a small regularized linear autoregressive model; compare it against
4-week mean on a chronologically locked final four weeks. No scikit-learn
requirement on Render; no automatic production deployment.
"""
import argparse,csv,hashlib,json,math,re
from collections import defaultdict
from datetime import date,timedelta,datetime,timezone
from pathlib import Path

MIN_WEEKS=24
HOLDOUT=4
LAGS=4

def solve_ridge(features,targets,lam=0.05):
    """Small, deterministic ridge fit with unpenalized intercept and pivoting."""
    dim=1+LAGS
    a=[[sum(row[i]*row[j] for row in features)+(0 if i==j==0 else lam if i==j else 0)
         for j in range(dim)] for i in range(dim)]
    b=[sum(row[i]*y for row,y in zip(features,targets)) for i in range(dim)]
    for col in range(dim):
        pivot=max(range(col,dim),key=lambda r:abs(a[r][col]))
        if abs(a[pivot][col])<1e-10:raise ValueError("Unable to solve stable ridge coefficients")
        a[col],a[pivot]=a[pivot],a[col]
        b[col],b[pivot]=b[pivot],b[col]
        div=a[col][col]
        for j in range(col,dim):a[col][j]/=div
        b[col]/=div
        for r in range(dim):
            if r==col:continue
            factor=a[r][col]
            for j in range(col,dim):a[r][j]-=factor*a[col][j]
            b[r]-=factor*b[col]
    return b

def signed_off(path,label):
    if not path or not Path(path).is_file() or Path(path).stat().st_size<20:
        raise ValueError("Independent "+label+" document required locally")
    # File presence is only a technical control; human must check authenticity.
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_weekly(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        rdr=csv.DictReader(f)
        required={"sku","week_start","qty_kg","source_status","week_complete","source_doc_sha256"}
        if not rdr.fieldnames or not required.issubset(rdr.fieldnames):
            raise ValueError("Expected weekly SKU, dates, kg, source and provenance columns")
        groups=defaultdict(list)
        for row in rdr:
            if row["source_status"]!="FINANCE_VERIFIED":
                raise ValueError("Unverified sales record: training rejected")
            if row["week_complete"]!="YES":
                raise ValueError("Partial/missing calendar week: training rejected")
            d=date.fromisoformat(row["week_start"])
            if d.weekday()!=0:raise ValueError("week_start must be Monday")
            qty=float(row["qty_kg"])
            if not math.isfinite(qty) or qty<0:raise ValueError("Invalid kg quantity")
            sha=row["source_doc_sha256"]
            if len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
                raise ValueError("Invalid Finance source document SHA-256")
            sku=row["sku"].strip().upper()
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{2,79}",sku):
                raise ValueError("Invalid SKU; use anonymous catalogue identifier")
            groups[sku].append((d,qty,sha))
    if not groups:raise ValueError("No weekly records")
    for sku,points in groups.items():
        points.sort(key=lambda x:x[0])
        if len(points)<MIN_WEEKS:raise ValueError("SKU "+sku+" requires >=24 consecutive completed weeks")
        if len({x[0] for x in points})!=len(points):
            raise ValueError("Duplicate week for SKU "+sku)
        if any(points[i][0]-points[i-1][0]!=timedelta(weeks=1) for i in range(1,len(points))):
            raise ValueError("Noncontiguous weekly series; cannot treat missing weeks as zero")
    return groups

def train_one(points):
    y=[x[1] for x in points]
    scale=max(1.0,sum(y[:-HOLDOUT])/len(y[:-HOLDOUT]))
    X=[];target=[]
    for i in range(LAGS,len(y)):
        X.append([1.0]+[y[i-j]/scale for j in range(1,LAGS+1)])
        target.append(y[i]/scale)
    x_train=X[:-HOLDOUT];y_train=target[:-HOLDOUT]
    coefs=solve_ridge(x_train,y_train)
    pred=[max(0.0,scale*sum(w*v for w,v in zip(coefs,row))) for row in X[-HOLDOUT:]]
    baseline=[sum(row[1:])/LAGS*scale for row in X[-HOLDOUT:]]
    actual=y[-HOLDOUT:]
    mae=sum(abs(p-a) for p,a in zip(pred,actual))/HOLDOUT
    naive=sum(abs(p-a) for p,a in zip(baseline,actual))/HOLDOUT
    # Do not hide negative benchmark results.
    return {"weights":coefs,"feature_order":["intercept","lag_1","lag_2","lag_3","lag_4"],
       "scale_kg":scale,"train_examples":len(x_train),"heldout_weeks":HOLDOUT,
       "last_observed_week":points[-1][0].isoformat(),
       "holdout":{"model_mae_kg":round(mae,4),"four_week_mean_mae_kg":round(naive,4),
                  "model_outperformed_baseline":mae<naive},
       "not_for_automatic_reordering":True}

def run(weekly_csv,authorization,finance_document,output):
    authorization_sha=signed_off(authorization,"research authorization")
    finance_sha=signed_off(finance_document,"Finance sign-off")
    groups=read_weekly(weekly_csv)
    out=Path(output).expanduser().resolve()
    # Avoid any explicit/raw company artefact in a GitHub checkout.
    if any((p/".git").exists() for p in (out,*out.parents)):
        raise ValueError("Model outputs cannot be saved within a Git repository")
    manifest={
      "created_at_utc":datetime.now(timezone.utc).isoformat(),
      "purpose":"EXPERIMENTAL_OFFLINE_COMPANY_SPECIFIC_DEMAND_MODEL",
      "source_classification":"FINANCE_VERIFIED_AS_DECLARED_REQUIRES_MANUAL_AUDIT",
      "authorization_document_sha256":authorization_sha,
      "finance_signoff_document_sha256":finance_sha,
      "weekly_source_sha256":hashlib.sha256(Path(weekly_csv).read_bytes()).hexdigest(),
      "algorithm":"RIDGE_AUTOREGRESSIVE_LAGS_1_TO_4","training_sku_count":len(groups),
      "stocks_used":False,"approval_state":"PENDING_HUMAN_AND_STATISTICAL_REVIEW",
      "automatically_deployed":False,"scientific_validation":False,
      "model_cards":{sku:train_one(points) for sku,points in groups.items()},
      "notes":["Verification documents require manual authenticity checks.",
               "4-week final holdout is a pilot engineering check, not definitive forecast accuracy.",
               "Company data and weights remain outside source control.",
               "Only ever deploy after independent approval and performance review."]}
    out.mkdir(parents=True,exist_ok=True)
    dest=out/"training_manifest.json"
    dest.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--weekly-csv",required=True)
    ap.add_argument("--research-authorization",required=True)
    ap.add_argument("--finance-signoff",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    report=run(args.weekly_csv,args.research_authorization,args.finance_signoff,args.output)
    print(json.dumps({"status":report["approval_state"],"trained_skus":report["training_sku_count"],
                      "auto_deployed":False}))

if __name__=="__main__":main()

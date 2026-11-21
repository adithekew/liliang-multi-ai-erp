"""Leakage-safe rolling-origin forecast evaluation for weekly KG demand."""
from __future__ import annotations
from datetime import date,timedelta
from math import sqrt
from typing import Iterable

def _solve(a,b):
    n=len(b)
    a=[row[:] for row in a];b=b[:]
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:abs(a[r][col]))
        if abs(a[pivot][col])<1e-10:raise ValueError("Singular ridge system")
        a[col],a[pivot]=a[pivot],a[col];b[col],b[pivot]=b[pivot],b[col]
        div=a[col][col]
        for j in range(col,n):a[col][j]/=div
        b[col]/=div
        for r in range(n):
            if r==col:continue
            f=a[r][col]
            for j in range(col,n):a[r][j]-=f*a[col][j]
            b[r]-=f*b[col]
    return b

def _fit_ridge(history,lam=.05):
    lag=4;scale=max(1.0,sum(history)/max(1,len(history)))
    X=[];y=[]
    for i in range(lag,len(history)):
        X.append([1.0]+[history[i-j]/scale for j in range(1,lag+1)])
        y.append(history[i]/scale)
    if len(X)<8:raise ValueError("At least 12 weeks are required at each rolling origin")
    dim=lag+1
    a=[[sum(row[i]*row[j] for row in X)+(0 if i==j==0 else lam if i==j else 0)
        for j in range(dim)] for i in range(dim)]
    b=[sum(row[i]*v for row,v in zip(X,y)) for i in range(dim)]
    return _solve(a,b),scale

def _predict_recursive(history,steps,weights,scale):
    seq=list(history);out=[]
    for _ in range(steps):
        row=[1.0]+[seq[-j]/scale for j in range(1,5)]
        pred=max(0.0,scale*sum(w*x for w,x in zip(weights,row)))
        out.append(pred);seq.append(pred)
    return out

def _metrics(actual,pred):
    errors=[p-a for a,p in zip(actual,pred)]
    return {"mae_kg":sum(abs(x) for x in errors)/len(errors),
      "wmape":sum(abs(x) for x in errors)/max(1e-12,sum(abs(x) for x in actual)),
      "rmse_kg":sqrt(sum(x*x for x in errors)/len(errors)),
      "bias_kg":sum(errors)/len(errors),"observations":len(errors)}

def rolling_origin_evaluate(points,min_train=12,horizon=4,lam=.05):
    """Expanding-window evaluation. points=[(date, kg)] with complete contiguous weeks."""
    if len(points)<24:raise ValueError("At least 24 contiguous complete weeks are required")
    dates=[p[0] for p in points];values=[float(p[1]) for p in points]
    if any(v<0 or not (v< float("inf")) for v in values):raise ValueError("Demand values must be finite and nonnegative")
    if any(dates[i]-dates[i-1]!=timedelta(weeks=1) for i in range(1,len(dates))):
        raise ValueError("Weekly series must be contiguous; missing weeks cannot be zero-filled")
    if any(d.weekday()!=0 for d in dates):raise ValueError("Week start must be Monday")
    if min_train<12 or horizon<1 or horizon>8:raise ValueError("Invalid rolling-origin configuration")
    actual_by_h={h:[] for h in range(1,horizon+1)}
    pred_by_model={m:{h:[] for h in range(1,horizon+1)} for m in ("RIDGE_AR4","MOVING_AVERAGE_4","LAST_WEEK_NAIVE")}
    origins=0
    for origin in range(min_train,len(values)-horizon+1):
        history=values[:origin];actual=values[origin:origin+horizon]
        weights,scale=_fit_ridge(history,lam)
        ridge=_predict_recursive(history,horizon,weights,scale)
        ma_seq=list(history);ma=[]
        for _ in range(horizon):
            p=sum(ma_seq[-4:])/4;ma.append(p);ma_seq.append(p)
        naive=[history[-1]]*horizon
        origins+=1
        for h in range(1,horizon+1):
            actual_by_h[h].append(actual[h-1])
            pred_by_model["RIDGE_AR4"][h].append(ridge[h-1])
            pred_by_model["MOVING_AVERAGE_4"][h].append(ma[h-1])
            pred_by_model["LAST_WEEK_NAIVE"][h].append(naive[h-1])
    if not origins:raise ValueError("No rolling-origin test windows available")
    results={}
    for model,by_h in pred_by_model.items():
        results[model]={"by_horizon":{},"overall":None}
        all_actual=[];all_pred=[]
        for h in range(1,horizon+1):
            if actual_by_h[h]:
                metric=_metrics(actual_by_h[h],by_h[h])
                results[model]["by_horizon"][str(h)]={
                  k:(round(v,6) if isinstance(v,float) else v) for k,v in metric.items()}
                all_actual.extend(actual_by_h[h]);all_pred.extend(by_h[h])
        overall=_metrics(all_actual,all_pred)
        results[model]["overall"]={k:(round(v,6) if isinstance(v,float) else v) for k,v in overall.items()}
    return {"method":"EXPANDING_WINDOW_ROLLING_ORIGIN","origins":origins,
      "min_train_weeks":min_train,"forecast_horizon_weeks":horizon,
      "first_test_week":dates[min_train].isoformat(),"last_test_week":dates[-1].isoformat(),
      "models":results,"seasonal_naive":"NOT_EVALUATED_REQUIRES_AT_LEAST_56_WEEKS",
      "scientific_validation":False,
      "warning":"Rolling-origin results are only as representative as the Finance-reconciled data; they do not authorize automatic replenishment."}

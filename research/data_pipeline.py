"""Conservative synthetic research-data cleaning and leakage-safe splitting.

Run on a securely approved and anonymized dataset only. This module quarantines
possible PII rather than claiming regexes can anonymize real customer records.
Keep raw private enterprise data out of public GitHub/CI artifacts.
"""
from collections import Counter,defaultdict
from datetime import datetime
from hashlib import sha256
import json
import re
import unicodedata

FLAVOR={"stroberi":"strawberry","strawberi":"strawberry","stoberi":"strawberry",
        "vanili":"vanilla","vanila":"vanilla","mangga":"mango",
        "coklat":"chocolate","jeruk nipis":"lime","jeruk lemon":"lemon"}
APP={"minuman":"beverage","susu":"dairy","roti":"bakery"}
ALLOWED_SOURCE={"SYNTHETIC_PILOT","SYNTHETIC_EXAMPLES_ONLY"}
PII_PATTERNS=[
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",re.I),
    re.compile(r"(?<!\w)(?:\+62|62|08)[\s.-]?\d[\d\s.-]{7,13}\d(?!\w)")
]
def normalize(text):
    text=unicodedata.normalize("NFKC",str(text or "")).casefold()
    text=re.sub(r"[\u200b-\u200d\ufeff]","",text)
    text=re.sub(r"[ \t\r\n]+"," ",text).strip()
    return text
def normalized_requirement(raw):
    text=normalize(raw)
    for original,canonical in sorted({**FLAVOR,**APP}.items(),key=lambda it:-len(it[0])):
        text=re.sub(r"(?<!\w)"+re.escape(original)+r"(?!\w)",canonical,text)
    return text
def likely_sensitive(text):
    return any(p.search(str(text or "")) for p in PII_PATTERNS)
def fingerprint(text):
    return sha256(text.encode("utf-8")).hexdigest()[:16]

def clean_catalog(rows):
    clean=[];quarantine=[];seen=set();stats=Counter()
    for index,row in enumerate(rows,1):
        item={k:normalize(row.get(k)) for k in ("sku","name","description","profile","application")}
        sku=item["sku"].upper()
        issues=[]
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,60}",sku):issues.append("BAD_SKU")
        if not item["name"] or not item["profile"] or not item["application"]:issues.append("MISSING_REQUIRED")
        if sku in seen:issues.append("DUPLICATE_SKU")
        if likely_sensitive(" ".join(item.values())):issues.append("POTENTIAL_PII")
        source=row.get("data_classification","")
        if source not in ALLOWED_SOURCE:issues.append("UNAUTHORIZED_SOURCE_NOT_ALLOWED")
        if issues:
            quarantine.append({"row":index,"issues":issues})
            stats.update(issues)
            continue
        seen.add(sku)
        item["sku"]=sku
        item["profile"]=FLAVOR.get(item["profile"],item["profile"])
        item["application"]=APP.get(item["application"],item["application"])
        # Missing evidence is explicitly UNKNOWN, not false or certified.
        item["halal_status"]="UNKNOWN"
        item["regulatory_status"]="UNKNOWN"
        item["source_classification"]=source
        clean.append(item)
    return {"clean":clean,"quarantine":quarantine,"quality":{"input":len(rows),"accepted":len(clean),
            "quarantined":len(quarantine),"issue_counts":dict(stats)}}

def clean_inquiries(rows):
    clean=[];quarantine=[];seen=set();stats=Counter()
    for index,row in enumerate(rows,1):
        text=normalized_requirement(row.get("requirement",""))
        group=normalize(row.get("project_group",""))
        stamp=str(row.get("created_at","")).strip()
        issues=[]
        if len(text)<8:issues.append("EMPTY_OR_TOO_SHORT")
        if len(text)>3000:issues.append("TOO_LONG")
        if likely_sensitive(row.get("requirement","")):issues.append("POTENTIAL_PII")
        if row.get("data_classification") not in ALLOWED_SOURCE:issues.append("UNAUTHORIZED_SOURCE_NOT_ALLOWED")
        if not group:issues.append("MISSING_SPLIT_GROUP")
        try:
            created_at=datetime.fromisoformat(stamp.replace("Z","+00:00")).isoformat()
        except (ValueError,TypeError):
            created_at=None
            issues.append("INVALID_CREATED_AT")
        # Exact normalized near-duplicate identifiers are quarantined to
        # avoid a test paraphrase leaking into a train group.
        key=fingerprint(text)
        if key in seen:issues.append("DUPLICATE_NORMALIZED_INQUIRY")
        if issues:
            quarantine.append({"row":index,"fingerprint":key,"issues":issues})
            stats.update(issues)
            continue
        seen.add(key)
        clean.append({"inquiry_fingerprint":key,"requirement_normalized":text,
                      "project_group":group,"created_at":created_at,
                      "data_classification":row["data_classification"]})
    return {"clean":clean,"quarantine":quarantine,"quality":{
        "input":len(rows),"accepted":len(clean),"quarantined":len(quarantine),
        "issue_counts":dict(stats),"warning":"Regex screening is not a GDPR/UU PDP anonymization guarantee."}}

def grouped_split(inquiries,train_fraction=.70,dev_fraction=.15):
    """Group-level deterministic partition; no project appears across splits.

    Fraction ratios are *targets*, not guarantees for a small number of groups.
    For actual studies, combine groups with temporal/embargo split and freeze
    assignments before hyperparameter tuning.
    """
    if not 0<train_fraction<1 or not 0<dev_fraction<1 or train_fraction+dev_fraction>=1:
        raise ValueError("Split fractions invalid")
    groups=defaultdict(list)
    for r in inquiries:
        group=r.get("project_group")
        if not group:raise ValueError("Missing group key")
        groups[group].append(r)
    ordered=sorted(groups,key=lambda k:(min(x["created_at"] for x in groups[k]),k))
    if len(ordered)<3:raise ValueError("At least three independent groups are required")
    n=len(ordered)
    train_end=max(1,round(n*train_fraction))
    dev_end=max(train_end+1,round(n*(train_fraction+dev_fraction)))
    train_end=min(train_end,n-2)
    dev_end=min(dev_end,n-1)
    assignments={}
    for j,group in enumerate(ordered):
        assignments[group]="train" if j<train_end else "dev" if j<dev_end else "test"
    output={"train":[],"dev":[],"test":[]}
    for group,items in groups.items():
        output[assignments[group]].extend(items)
    all_ids=[x["inquiry_fingerprint"] for label in output for x in output[label]]
    if len(all_ids)!=len(set(all_ids)):
        raise ValueError("Duplicate normalized inquiries remain across splits")
    return {"splits":output,"group_counts":dict(Counter(assignments.values())),
            "record_counts":{k:len(v) for k,v in output.items()},
            "policy":"Chronological independent project-group partition. Freeze test data; verify adjacent time leakage separately."}

def prepare_synthetic(products,inquiries):
    product_result=clean_catalog(products)
    inquiry_result=clean_inquiries(inquiries)
    diagnostics={"products":product_result["quality"],"inquiries":inquiry_result["quality"]}
    return {"products":product_result,"inquiries":inquiry_result,"diagnostics":diagnostics,
            "real_company_data_used":False,"report_status":"SYNTHETIC_QA_NOT_ACCURACY_VALIDATION"}

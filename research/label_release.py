"""Private, approval-gated AI-02 labelled dataset release.

Inputs are two independently filled Technical CSV sheets and a frozen,
anonymized inquiry-SKU task pool. No data/model weights are committed to GitHub,
and no database is changed. Review A/B must share exactly the same pair IDs.
A third human adjudicator resolves disagreements; no AI-generated gold labels.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from collections import Counter,defaultdict
from pathlib import Path
from research.technical_independent_agreement import validate,agreement
from research.training_gate import check_training_pairs
from research.data_pipeline import likely_sensitive,normalize

MIN_HELDOUT_QUERIES=5

def read_csv(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def read_jsonl(path):
    with open(path,encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def approvals_present(auth):
    p=Path(auth)
    if not p.is_file() or p.stat().st_size<20:
        raise ValueError("Written, local, non-empty data-use authorization is required")
    return sha(p)

def adjudicate(rows_a,rows_b,adjudication_rows):
    a=validate(rows_a,"TECHNICAL_A");b=validate(rows_b,"TECHNICAL_B")
    review=agreement(rows_a,rows_b)
    reviewed={}
    dis=set(review["disagreement_pair_ids"])
    resolved={}
    for row in adjudication_rows:
        pid=row.get("pair_id","").strip()
        if not pid:continue
        if pid in resolved or pid not in dis:
            raise ValueError("Duplicate/unrequested adjudication pair")
        if row.get("adjudicator_id","").strip() in ("","TECHNICAL_A","TECHNICAL_B"):
            raise ValueError("Adjudication requires a separate human identifier")
        if len(row.get("rationale","").strip())<10 or not row.get("datasheet_reference","").strip():
            raise ValueError("Adjudication must cite documentary evidence and reason")
        try:label=int(row.get("label_0_3",""))
        except (ValueError,TypeError):raise ValueError("Adjudication grade is missing")
        if label not in (0,1,2,3):raise ValueError("Adjudication grade must be 0..3")
        resolved[pid]=label
    if set(resolved)!=dis:
        raise ValueError("All Technical disagreements must be resolved before release")
    for pid in a:
        reviewed[pid]=dict(a[pid])
        reviewed[pid]["grade"]=resolved[pid] if pid in resolved else a[pid]["grade"]
        reviewed[pid]["adjudicated"]=pid in resolved
    return reviewed,review

def assign_splits(groups,seed):
    # Frozen-corpus deterministic group shuffle: unlike naive hash thresholds,
    # guarantees a dev/test partition exists when >=3 groups are supplied.
    unique=sorted(set(groups),key=lambda g:hashlib.sha256((seed+"|"+g).encode()).hexdigest())
    n=len(unique)
    if n<3:
        raise ValueError("At least three independent groups required for a heldout split")
    test_n=max(1,round(n*.15))
    dev_n=max(1,round(n*.15))
    return {g:("test" if i<test_n else "dev" if i<test_n+dev_n else "train")
            for i,g in enumerate(unique)}

def build_release(pool,rows_a,rows_b,adj,authorization_hash,seed="liliang-ai02-research-v1"):
    if len(seed)<8:raise ValueError("Split seed too short")
    graded,agreement_summary=adjudicate(rows_a,rows_b,adj)
    pairs={}
    for p in pool:
        pid=str(p.get("pair_id","")).strip()
        if not pid or pid in pairs:raise ValueError("Missing/duplicate task pool pair ID")
        if p.get("data_classification")!="AUTHORIZED_ANONYMIZED":
            raise ValueError("Task pool contains unauthorized or UAT-labelled pairs")
        if p.get("expert_validated") is not True:
            raise ValueError("Task pool must be manually verified before dataset freeze")
        fields=["query","document","sku","inquiry_id","project_group","authorization_ref"]
        if any(not str(p.get(k,"")).strip() for k in fields):
            raise ValueError("Missing query, document, SKU, project group or authorization reference")
        if any(likely_sensitive(str(p[k])) for k in ("query","document")):
            raise ValueError("Potential PII in task pool text")
        if str(p["inquiry_id"]).upper().startswith(("UAT","DEMO","SYNTH")):
            raise ValueError("UAT/demo inquiry may not be promoted into research dataset")
        pairs[pid]=p
    if set(pairs)!=set(graded):
        raise ValueError("Technical reviewed pairs and task pool must match exactly")
    group_splits=assign_splits((str(p["project_group"]).strip().upper() for p in pairs.values()),seed)
    datasets={"train":[],"dev":[],"test":[]}
    all_qrels={"train":[],"dev":[],"test":[]}
    pair_groups={}
    for pid,p in pairs.items():
        expert=graded[pid]
        for key in ("sku","inquiry_id","project_group"):
            if str(p[key]).strip().upper()!=str(expert[key]).strip().upper():
                raise ValueError("Pool metadata and Technical reviewer metadata mismatch: "+key)
        group=str(p["project_group"]).strip().upper()
        split=group_splits[group]
        pair_groups[pid]=split
        qrel={"pair_id":pid,"query_id":str(p["inquiry_id"]),"project_group":group,
              "query":str(p["query"]),"sku":str(p["sku"]).upper(),
              "document":str(p["document"]),"relevance_label":expert["grade"],
              "datasheet_reference":expert["evidence_ref"],
              "label_source":"TWO_INDEPENDENT_TECHNICAL_REVIEWERS",
              "adjudicated":expert["adjudicated"],"split":split}
        all_qrels[split].append(qrel)
        if expert["grade"]==3:
            datasets[split].append({
                "query":str(p["query"]),"document":str(p["document"]),
                "sku":str(p["sku"]).upper(),"project_group":group,
                "relevance_label":3,"expert_validated":True,
                "data_classification":"AUTHORIZED_ANONYMIZED"})
    audit=check_training_pairs(datasets["train"],datasets["dev"])
    test_queries={x["query_id"] for x in all_qrels["test"]}
    train_groups={r["project_group"] for r in all_qrels["train"]}
    dev_groups={r["project_group"] for r in all_qrels["dev"]}
    test_groups={r["project_group"] for r in all_qrels["test"]}
    errors=list(audit["problems"])
    if not all_qrels["test"]:errors.append("EMPTY_LOCKED_TEST")
    if len(test_queries)<MIN_HELDOUT_QUERIES:errors.append("INSUFFICIENT_LOCKED_TEST_QUERIES")
    if not datasets["test"]:errors.append("TEST_HAS_NO_RELEVANCE_3")
    if train_groups&test_groups or dev_groups&test_groups or train_groups&dev_groups:
        errors.append("PROJECT_GROUP_LEAKAGE")
    # An inquiry cannot appear across splits even when group labels are wrong.
    query_splits=defaultdict(set)
    for split,rows in all_qrels.items():
        for x in rows:query_splits[x["query_id"]].add(split)
    if any(len(x)>1 for x in query_splits.values()):errors.append("INQUIRY_LEAKAGE")
    normalized_text_splits=defaultdict(set)
    for split,rows in all_qrels.items():
        for row in rows:
            normalized_text_splits[normalize(row["query"])].add(split)
    if any(len(v)>1 for v in normalized_text_splits.values()):
        errors.append("NORMALIZED_QUERY_TEXT_LEAKAGE")
    # Qualified 0..3 judgment pool: do not count unlabeled catalog entries as 0.
    if any(len({x["sku"] for x in rows if x["query_id"]==qid})<2
           for split,rows in all_qrels.items()
           for qid in {x["query_id"] for x in rows}):
        errors.append("SOME_QUERIES_HAVE_LESS_THAN_TWO_JUDGED_SKUS")
    manifest={
        "status":"FROZEN_OFFLINE_RESEARCH_DATASET" if not errors else "BLOCKED_QUALITY_GATES",
        "authorization_sha256":authorization_hash,
        "split_seed_sha256":hashlib.sha256(seed.encode()).hexdigest(),
        "annotator_agreement":{"graded_pairs":agreement_summary["reviewed_pair_count"],
              "weighted_cohen_kappa":agreement_summary["weighted_cohen_kappa"],
              "adjudicated_pairs":agreement_summary["disagreements_count"]},
        "qrels_by_split":{k:len(v) for k,v in all_qrels.items()},
        "strict_positive_pairs_by_split":{k:len(v) for k,v in datasets.items()},
        "heldout_inquiries":len(test_queries),
        "training_gate":audit,"problems":sorted(set(errors)),
        "model_trained":False,"scientifically_validated":False,"auto_deploy":False,
        "cautions":["Written authorization presence does not independently prove legal permission.",
                    "Gold ratings require actual named humans and protected datasheet sources.",
                    "Training uses grade 3 positives only; grade 0/1/2 retained for graded test evaluation.",
                    "Never select hyperparameters using the locked test split.",
                    "Ranking metrics may only be claimed for the documented judged candidate pool."]}
    return manifest,datasets,all_qrels

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--task-pool",required=True,help="Private approved pair pool JSONL")
    p.add_argument("--review-a",required=True,help="PENILAIAN as CSV UTF-8 from Technical A")
    p.add_argument("--review-b",required=True,help="PENILAIAN as CSV UTF-8 from Technical B")
    p.add_argument("--adjudication",help="CSV for disagreements; omit only when fully agreed")
    p.add_argument("--authorization",required=True)
    p.add_argument("--out-dir",required=True)
    p.add_argument("--seed",default="liliang-ai02-research-v1")
    a=p.parse_args()
    stamp=approvals_present(a.authorization)
    adj=read_csv(a.adjudication) if a.adjudication else []
    manifest,train,judged=build_release(
       read_jsonl(a.task_pool),read_csv(a.review_a),read_csv(a.review_b),
       adj,stamp,a.seed)
    if manifest["problems"]:
        raise SystemExit("BLOCKED: "+", ".join(manifest["problems"]))
    out=Path(a.out_dir).resolve()
    if any((parent/".git").exists() for parent in (out,*out.parents)):
        raise SystemExit("Refusing to publish data inside a Git repo")
    if out.exists() and list(out.iterdir()):
        raise SystemExit("Output release folder must be empty: never overwrite a frozen dataset")
    out.mkdir(parents=True,exist_ok=True)
    def write_rows(name,rows):
        with (out/name).open("x",encoding="utf-8") as f:
            for x in rows:f.write(json.dumps(x,ensure_ascii=False)+"\n")
    for split in ("train","dev"):
        write_rows(split+"_positives.jsonl",train[split])
    for split in ("train","dev","test"):
        write_rows(split+"_judged_qrels.jsonl",judged[split])
    manifest["release_file_sha256"]={f.name:sha(f) for f in out.glob("*.jsonl")}
    (out/"release_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":manifest["status"],"qrels_by_split":manifest["qrels_by_split"],
        "positives_by_split":manifest["strict_positive_pairs_by_split"],"auto_deployed":False}))

if __name__=="__main__":main()

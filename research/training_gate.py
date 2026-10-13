"""Quality gate for OPTIONAL, future domain fine-tuning on consented pairs.

This gate prevents our current five-SKU synthetic demo from masquerading as a
domain-trained AI model. It cannot itself prove a company's legal authorization.
"""
from collections import Counter
from hashlib import sha256
from research.data_pipeline import normalize, likely_sensitive

def check_training_pairs(train,dev):
    problems=[]
    sets={"train":train,"dev":dev}
    seen_query={}
    group_by_split={}
    distinct_sku={}
    for split,rows in sets.items():
        groups=set();skus=set()
        if not rows:problems.append(split.upper()+"_EMPTY")
        for i,row in enumerate(rows,1):
            if row.get("data_classification")!="AUTHORIZED_ANONYMIZED":
                problems.append("SOURCE_NOT_AUTHORIZED_"+split)
            if row.get("expert_validated") is not True:
                problems.append("NOT_EXPERT_VALIDATED_"+split)
            if type(row.get("relevance_label")) is not int or row["relevance_label"]<2 or row["relevance_label"]>3:
                problems.append("NOT_QUALIFIED_POSITIVE_"+split)
            query=normalize(row.get("query"));document=normalize(row.get("document"))
            if len(query)<8 or len(document)<8:problems.append("EMPTY_TEXT_"+split)
            if likely_sensitive(query) or likely_sensitive(document):problems.append("POTENTIAL_PII_"+split)
            group=normalize(row.get("project_group"))
            if not group:problems.append("MISSING_PROJECT_GROUP_"+split)
            groups.add(group)
            sku=normalize(row.get("sku"))
            if not sku:problems.append("MISSING_SKU_"+split)
            skus.add(sku)
            fingerprint=sha256(query.encode()).hexdigest()
            previous=seen_query.setdefault(fingerprint,split)
            if previous!=split:problems.append("QUERY_LEAKAGE_ACROSS_SPLITS")
        group_by_split[split]=groups
        distinct_sku[split]=skus
    if group_by_split["train"] & group_by_split["dev"]:
        problems.append("PROJECT_GROUP_LEAKAGE")
    if len(train)<50:problems.append("INSUFFICIENT_TRAIN_POSITIVES_FOR_PROPOSED_PILOT")
    if len(dev)<10:problems.append("INSUFFICIENT_DEV_PAIRS_FOR_PROPOSED_PILOT")
    if len(distinct_sku["train"])<20:problems.append("INSUFFICIENT_SKU_DIVERSITY_FOR_INBATCH_NEGATIVES")
    if len(group_by_split["train"])<10:problems.append("INSUFFICIENT_TRAIN_GROUP_DIVERSITY")
    return {
        "ready":not bool(problems),"problems":sorted(set(problems)),
        "train_pair_count":len(train),"dev_pair_count":len(dev),
        "distinct_train_skus":len(distinct_sku["train"]),
        "distinct_train_groups":len(group_by_split["train"]),
        "safety_notes":[
           "These minima are conservative engineering readiness criteria, not statistically guaranteed sample sizes.",
           "Manually verify all data permissions and PII; no automated filter guarantees consent.",
           "A separately locked expert-labelled test set must never be used for training/model selection.",
           "Check domain false negatives and SKU synonyms when selecting in-batch negatives."
        ]
    }

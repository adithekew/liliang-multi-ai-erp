"""OFFLINE ONLY — optional supervised domain fine-tuning after expert labels.

This script has NOT been used to train a PT Liliang model. It intentionally
rejects the five-SKU synthetic demonstration and unknown/unapproved data.
It never uploads weights or records to a public service.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from research.training_gate import check_training_pairs

MODEL_ID="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
PINNED_REVISION="e8f8c211226b894fcb81acc59f3b34ba3efd5f42"

def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--train",required=True,help="AUTHORIZED/ANONYMIZED expert-positive pairs in JSONL")
    p.add_argument("--dev",required=True,help="Separate authorized development pairs in JSONL")
    p.add_argument("--authorization-record",required=True,help="Local written approval; required but human verification is still mandatory")
    p.add_argument("--output",required=True,help="Local secure model output directory, never the public repository")
    p.add_argument("--epochs",type=int,default=1)
    args=p.parse_args()
    if not 1<=args.epochs<=3:raise SystemExit("Only 1-3 epochs allowed in the initial controlled experiment")
    if not Path(args.authorization_record).is_file():
        raise SystemExit("Missing local written authorization file; refusing to train")
    train,dev=load_jsonl(args.train),load_jsonl(args.dev)
    audit=check_training_pairs(train,dev)
    if not audit["ready"]:
        raise SystemExit("Training gate FAILED: "+", ".join(audit["problems"]))
    from datasets import Dataset
    from sentence_transformers import (
        SentenceTransformer,SentenceTransformerTrainer,SentenceTransformerTrainingArguments,losses
    )
    from sentence_transformers.training_args import BatchSamplers
    model=SentenceTransformer(MODEL_ID,revision=PINNED_REVISION,device="cpu",trust_remote_code=False)
    def to_dataset(items):
        return Dataset.from_list([{"anchor":x["query"],"positive":x["document"]} for x in items])
    out=Path(args.output).expanduser().resolve()
    out.mkdir(parents=True,exist_ok=True)
    options=SentenceTransformerTrainingArguments(
        output_dir=str(out/"checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        learning_rate=2e-5,
        warmup_ratio=.10,
        batch_sampler=BatchSamplers.NO_DUPLICATES,
        fp16=False,bf16=False,
        eval_strategy="epoch",save_strategy="epoch",
        logging_steps=10,save_total_limit=2,report_to=[],
        seed=42
    )
    trainer=SentenceTransformerTrainer(
        model=model,args=options,
        train_dataset=to_dataset(train),
        eval_dataset=to_dataset(dev),
        loss=losses.MultipleNegativesRankingLoss(model)
    )
    trainer.train()
    model.save_pretrained(str(out/"domain-encoder"))
    manifest={
       "run_timestamp_utc":datetime.now(timezone.utc).isoformat(),
       "base_model_id":MODEL_ID,"base_model_revision":PINNED_REVISION,
       "training_method":"MultipleNegativesRankingLoss, no-duplicate batches",
       "dataset_status":"HUMAN_APPROVED_LOCAL_INPUTS_EXPECTED",
       "train_pair_count":audit["train_pair_count"],"dev_pair_count":audit["dev_pair_count"],
       "epochs":args.epochs,"seed":42,"learning_rate":2e-5,
       "has_heldout_test_result":False,
       "validated_business_performance":False,
       "warning":"This local model must pass separately locked held-out expert evaluation before any deployment."
    }
    (out/"training_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("Fine-tuning complete locally. NO production deployment or held-out effectiveness is implied.")
if __name__=="__main__":main()

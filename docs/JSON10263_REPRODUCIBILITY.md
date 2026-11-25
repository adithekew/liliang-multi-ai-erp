# JSON Submission 10263 — strict offline reproducibility

This repository is **public**. Never commit real inquiries, source PDFs, private supplier catalog, adjudication forms, encoder weights, or raw rankings. No deployment/ERP modification is required.

The current checked-in `research/fixtures/neural_synthetic_v1.json` is a **10 inquiry / 5 product synthetic example**, NOT the article's 50 inquiry / 20 SKU corpus. The online BM25 scorer and `research.hybrid.rrf_fusion()` are **not equivalent** to the paper's recorded experiment: the generic evaluator treats grade >=2 as relevant and standard RRF uses ordinal ranks, while the paper reports grade-3 MRR and a capped BM25 competition rank contribution.

## A — Audit saved 3,000-row ranking export

Provide these files **outside the public repo** from the authorized research run:
- `rankings.csv`: `inquiry_id,sku_id,method,rank,score`. Exactly 50 inquiries × 20 SKUs × three methods `BM25, MiniLM, RRF`. Original score precision and unique rank 1..20 must be preserved.
- `labels.csv`: `inquiry_id,sku_id,grade`. All 200 consensus held-out relevance grades `RQ041`–`RQ050` (0–3). Retain T01/T02 independent forms and six adjudication records as separate private evidence.

Run:

```bash
python -m research.json10263_reproducibility \
  --rankings /secure/json10263/rankings.csv \
  --labels /secure/json10263/labels.csv \
  --output /secure/json10263/metric_replay.json
```

It verifies complete query/SKU sets; computes nDCG@5 with gain `2^grade-1`, MRR@5/Recall@5 using **grade 3**; audits 1,000 reported fusion scores with `1/(60 + min(15, BM25_competition_rank)) + 1/(60 + dense_rank)` (zero-score lexical candidates contribute at capped rank 15); and recomputes a ten-query 10k paired percentile bootstrap with Python RNG seed 20261029. Reported means must match BM25 0.9208, MiniLM 0.9341, RRF 0.9437 at four decimals. The original bootstrap generator may differ.

## B — Full model inference rerun (separate requirement)

The saved output alone **cannot** reproduce raw MiniLM inference. A complete model run also requires:
1. The EXACT 50 query and 20 SKU **preprocessed encoder input strings** from 4 November 2026, independently checked SHA-256.
2. An immutable local checkpoint and full 40-character upstream model commit SHA, independently matched weight SHA-256, saved tokenizer files, numeric precision/device metadata and package versions.
3. Original BM25 source, index fields, tokenization/synonyms, scores, full RRF tie behavior and catalog revision `CAT-20SKU-V8-c85493d966ef1dc4`.
4. Independent author sign-off of final 200 labels and split containment; source artifact manifest; both archived and rerun 1,000 dense cosine scores for quantitative comparison.

For MiniLM output verification, use the separate offline script `research/json10263_encoder_replay.py` after placing original prepared texts and authenticated model weights in private storage:\n\n```bash\npython -m research.json10263_encoder_replay \\\n  --rankings /secure/json10263/rankings.csv \\\n  --query-texts /secure/json10263/query_encoder_texts.csv \\\n  --sku-texts /secure/json10263/sku_encoder_texts.csv \\\n  --model-dir /secure/models/minilm-frozen \\\n  --commit-sha FULL40CHARMODELCOMMIT \\\n  --output /secure/json10263/encoder_replay.json\n```\n\nThis script runs offline on an authorized workstation, checks 1,000 cosine scores and rank ordering, and hashes the local weights. Full model inference provenance is **not** established merely by supplying a commit string. The public toy fixture **must not** be substituted. Until all evidence is available, declare `full model rerun = NOT VERIFIED`. E5 supplier TDS compatibility remains outside the paper's verified outcomes.

No experiment results or source data were fabricated for this protocol.

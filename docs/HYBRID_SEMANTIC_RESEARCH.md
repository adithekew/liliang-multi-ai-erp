# AI-02 — Hybrid Semantic Product Matching (Research Prototype v0.4)

## Provenance and architecture

- **Source:** five explicitly synthetic flavor products and ten researcher-authored synthetic test inquiries.
- **Encoder:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (actual pretrained neural network).
- **Execution:** embeddings generated **offline** in GitHub Actions on CPU and committed as a small, versioned JSON file under `research/fixtures/neural_synthetic_v1.json`.
- **Runtime:** Render Free loads only static normalized vectors; **no PyTorch, Sentence Transformers, model downloads or paid AI APIs** in Render.
- **Lexical retrieval:** existing BM25 with Indonesian/English synonym expansion.
- **Dense retrieval:** dot product on normalized 384-dimensional vectors (= cosine similarity).
- **Hybrid retrieval:** RRF (k=60) of BM25 and dense rank lists.
- **Constraint safety:** no verified datasheet or halal/regulatory metadata, so each recommendation marks such attributes **UNKNOWN**. No compatibility claims are made.
- **Validity:** synthetic developer-authored SKU targets are NOT expert judgments, not representative validation, and cannot be claimed as research outcomes.

```text
Synthetic fixed inquiry (Q01-Q10)
   ├── BM25 (lexical index)                  -> ranking A
   ├── cached real neural query embedding
   │      + cached product embeddings       -> ranking B
   └── RRF(rank A, rank B)
        -> evidence/UNKNOWN checks
        -> ranked demo shortlist
        -> (separate future Technical expert review)
```

## Try in the ERP

Use **Hybrid Semantic Lab** after Admin, Sales, Technical or Manager login.

- `GET /v1/ai/hybrid-cases` gives available synthetic cases (not arbitrary user input).
- `GET /v1/ai/hybrid-evaluate?case_id=Q01` gives three retrieval rankings with encoder revision and constraint status.
- User-provided free-text inquiry in the operational workflow still uses **BM25**, NOT the neural encoder; it has not been replaced or falsely labeled.
- `retrieval_only_latency_ms` excludes model inference and asset generation; `end_to_end_latency_ms` is deliberately `null`.

## Recompute versioned embeddings

Run from a development workstation with sufficient memory:

```bash
python -m venv .venv
pip install -r requirements-ai-local.txt
python scripts/generate_neural_fixtures.py
```

The generator downloads the actual Sentence Transformers model, records the Hugging Face model commit SHA, and creates the fixture. The GitHub Actions fixture workflow runs on changes to the model generator; see `.github/workflows/build-neural-fixtures.yml`. Model downloads may consume free workflow minutes. No real enterprise data belongs in the repository.

## Research stages remaining before publication

1. Obtain PT Liliang permission and anonymized product datasheets and historical sales, and move repository Private.
2. Build corpus documentation and versioned product embeddings with identifiable evidence pointers and access policy.
3. Add a secure online encoder (separate worker or cost-assessed service), then vector index in PostgreSQL/pgvector. Do not assume Render Free can host the encoder.
4. Technical experts independently label relevance (0–3); record expert IDs and inter-rater agreement.
5. Partition queries by time/customer/product appropriately; avoid overlap/leakage between dev tuning and held-out test.
6. Compare BM25, dense, hybrid, plus constraint-aware reranking. Evaluate nDCG@5, MRR, Recall@5, P50/P95 end-to-end latency and manual baseline.
7. Integrate fixed model/index versions into ERP audit trail, role workflow and user acceptance tests.

## Citation of results

Do not cite toy fixture rankings or developer-assigned labels as proof of a productivity improvement. The initial target (more than two hours of manual search reduced to seconds) remains a hypothesis until representative user trials and time measurements are completed.

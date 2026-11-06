# ERP Multi-AI PT. Liliang — Agent Pilot Rp0 (2026-11-06)

## Scientific status

This artifact adds an OPTIONAL **agent orchestrator pilot** without changing the main AI-02 BM25/MiniLM/RRF evaluation (E1–E5), DSRM methodology, company labels, Neon data or live ERP approval workflow. A running Agent does NOT imply all four AI models were trained or scientifically validated.

## Architecture and execution

- Web UI: /ai/agent-pilot (log in to ERP first, same browser session).
- Authenticated GET /v1/agent/status. Authenticated POST /v1/agent/demo with {"case_id":"STRAWBERRY_DAIRY","provider":"local"}.
- Local mode calls the EXISTING functions: multi_ai.interpret (AI-01 rule based), multi_ai.score_products (AI-02 BM25), multi_ai.bundling_rules (AI-03 association rules), multi_ai.forecast_baseline (AI-04 4-week Moving Average).
- Exactly **five fixed synthetic test cases**, five synthetic SKUs, 16 synthetic baskets and synthetic 24-week series. No company database query by this module; no persisted inquiry or transactional/approval write.
- The optional LLM agent uses PydanticAI tools for four modules with **Groq Free openai/gpt-oss-20b** to produce an UNVERIFIED explanatory paragraph; baseline outputs always remain authoritative and marked synthetic. The external mode defaults OFF.

## Rp0 controls

1. Default requires **no API key, credits, GPU or new hosted services**, and adds no dependency to default Render build. This is a deterministic orchestration proof, not yet a model-driven LLM agent.
2. To test real agent tool calling, use an independently verified **Groq Free account** (no billing method or Developer plan). Check current org limits at https://console.groq.com/docs/rate-limits and data settings at https://console.groq.com/settings/data-controls ; enable Zero Data Retention as appropriate.
3. Place GROQ_API_KEY in **Render Environment** (never GitHub, chat, or files), install optional dependencies using requirements-agent-free.txt, and explicitly set AI_AGENT_EXTERNAL_ENABLED=true only after permission and review.
4. If the key/flag/dependency is missing, requests for Groq are safely blocked; local mode remains available. There is **no paid provider fallback**. This software does not offer a financial ceiling for mistakenly upgrading the provider account; don't enable a paid account.
5. LLM uses 4 read-only tools, no arbitrary text prompt input, no access to company Neon, no company invoice/stock/customer. It cannot execute business decisions. Access: Admin/Sales/Technical/Manager, Gudang explicitly denied.
6. Do not regard BM25 score as relevance accuracy or treat synthetic association-rule/forecast outputs as company results. Validate against expert label evidence and finance-attested records separately.

## Code walkthrough (for lecturers)

- agent_pilot.py: cases → fixed synthetic fixture → AI-01 → AI-02 Top-5 → AI-03 rules → AI-04 Moving Average; optional PydanticAI Groq tool calling.
- app.py: mounts new routes (existing logic untouched).
- tests/test_agent_pilot.py: 401, 403, 422, 409, read-only, no data mutation, valid baseline output; no remote calls.
- research/catalog_matcher.py and research/hybrid_demo.py: explain original BM25 and separate fixed synthetic MiniLM/RRF experiment.
- research/finetune_encoder.py / research/ranking_evaluation.py: training/evaluation *protocols*, not evidence of successful company training.
- research/company_proxy_basket.py / research/monthly_experiment_2025.py: proxy and Ridge experimental caveats.

## Proposed agent evaluation

On approved synthetic cases, measure tool routing, coverage of all 4 modules, explanation faithfulness to outputs, unauthorized access rejection, prohibited data egress, p95 response latency and external request usage. Local tests are software checks only; no published performance numbers until independently measured. Live Groq inference is **NOT VERIFIED** until optional key is added and a supervised UAT is executed.

## Caveats

This route is a research prototype on Render Free and not production-ready. No company data must be submitted to an external model. Roll out via branch/PR, CI, supervised five-role UAT, and controlled merge; do not deploy untested changes automatically.

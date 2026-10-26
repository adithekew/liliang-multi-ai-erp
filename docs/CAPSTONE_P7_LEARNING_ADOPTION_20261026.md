# Capstone P7 — Learning Journey, User Enablement, Analytics & UX

**Snapshot:** 26 October 2026 | **Status:** design and research-pilot UI feature branch; learning outcome not yet measured.

## Research boundary
Core study remains **AI-Assisted Semantic Product Matching for B2B Flavor Inquiry Management Using Hybrid Retrieval and Expert-in-the-Loop Validation**. Learning journey concerns adoption of the five-role ERP, not a second learning-recommendation AI research problem.

**Five login roles:** Admin, Sales, Technical, Manager Operasional, Gudang. Customer is an external stakeholder.

## Aswaya P7 rubric mapping

| Rubric | P7 implementation | Evidence/status |
| --- | --- | --- |
| Learning / upskilling module & UX | Role-specific SOP cards on `/learning/center` | UI prototype in feature branch |
| Learning journey | orientation → microlearning → end-to-end simulation → post-test/SUS → backlog | designed, no participants enrolled |
| Skills framework / assessment | five-role competency matrix, pre/post draft, formative 3-item self-check | self-check browser-only and nonpersistent |
| Learning analytics & user progress | KPI definitions: paired learning gain, task success, completion time, SUS, role adoption | wireframe only, not measured |
| Dashboard / wireframe & review | learning dashboard wireframe and workflow evidence review | visual review proposed; signed feedback pending |

The quiz does not send results to any backend, create records, or count as scientific gold labels. The app's ERP accounts and roles remain unchanged.

## Engineering and scientific update (PRs merged 26 Oct)

- [#22](https://github.com/adithekew/liliang-multi-ai-erp/pull/22): company order-fact gating, source-labeled AI module demo readiness and reports.
- [#23](https://github.com/adithekew/liliang-multi-ai-erp/pull/23): 2025 sales source auditing and fail-closed offline training interfaces, preserving stock and customer data.
- [#24](https://github.com/adithekew/liliang-multi-ai-erp/pull/24): June 2025 excluded as payment-due material, not confirmed sales; proxy baskets are explicitly `USER_ASSUMED_PROXY`, NOT invoice-validated.
- [#25](https://github.com/adithekew/liliang-multi-ai-erp/pull/25): independent Technical A/B 0–3 labels, adjudication, consented private freeze release and strictly judged-pool held-out metrics.

AI-01 parser and AI-02 BM25 run online as pilot baselines. The multilingual MiniLM 384-D / RRF experiment is fixed synthetic offline lab and part of AI-02, **not** a separately numbered AI. AI-03 uses association rules in synthetic/conditional exploratory baskets, while AI-04 uses moving average and optional locally gated demand training. No company-trained neural model has passed expert-labeled held-out testing. The Technical labeling workbooks inspected for T01/T02 remain without completed independent reviewer gold-standard data.

**Required distinction:** software UAT pass (24/24, 16/16, 9/9 with remarks) does not measure AI-02 nDCG@5 or model accuracy.

## Workflow under study

External Customer inquiry → Sales confirms flavor, application and physical form → AI-01 rule extraction + AI-02 Top-5 BM25 → Technical independent evidence review of candidates → Manager Operasional approval only following latest appropriate Technical review → Gudang stock-source controls and reporting. Stock UNKNOWN must not be silently replaced by zero.

## Proposed instruments and definitions

1. Pre/post paired knowledge test: awareness of BM25 scores, UNKNOWN, Technical label rules, evidence and RBAC.
2. Task completion: completed task steps / attempted steps per role, with error and assistance noted.
3. Completion time: observed milliseconds/seconds from a defined start to end event, report median and variability.
4. Controlled time-to-shortlist: same task complexity and standardized conditions for manual vs AI-assisted work.
5. SUS usability: original validated standard instrument and proper scoring, only after user testing.
6. Adoption: active eligible pilot users per role / consented cohort per defined observation period.

Every dashboard item starts `NOT_MEASURED` until participant data is legitimately collected. No fake KPIs/participants and no PII in public repo.

## P7 deliverables archived

- [21-slide PPTX](https://docs.google.com/presentation/d/1dDFkZJ1zdFq8EDzgLDFdnCMrW3d5ughA/edit)
- [21-slide PDF](https://drive.google.com/file/d/16ng86daN2C0lXo7cTi8i6qQCpIN8jp8-/view)
- [Milestone report PDF](https://drive.google.com/file/d/1Xkk8Tz_aTR4NZMDPPMhR2ixaKcagYNOr/view)
- [Pre/Post/UAT instrument PDF](https://drive.google.com/file/d/1dke5B0SHJ-K-ito3Gz0_PFDd4eq-sxPv/view)
- [Kelompok 3 P7 Drive folder](https://drive.google.com/drive/folders/1gbiNBG8ejF-LTObMGJg9-kmQ30GVWrRx)

Only explicitly public/sanitized material is included. Real sales/inquiry/customer documents, credentials and unlabeled internal sources must stay in separately controlled private storage.

## P7 acceptance and P8 exit gates

- [x] Learning journey, matrix, draft assessment, dashboard specification and UX wireframe documented.
- [x] Pilot learning page staged in a feature branch with browser-only formative self-check.
- [ ] CI run for branch and code review.
- [ ] GitHub PR merged after CI, then independent Render deployment confirmation and live role-based UAT.
- [ ] Five-role usability walkthrough and stakeholder feedback with date/provenance.
- [ ] Participant pre/post, SUS, task timing/adoption measurement using consent.
- [ ] Independent signed Technical gold labels, adjudication, frozen judged holdout and comparative evaluation E1–E5.
- [ ] Finance SO/invoice/return/date reconciliation including June; no genuine basket/forecast claims before source gates.

## Reproducibility and no-risk guarantee

P7 UI is read-only and client-side: no Neon schema alteration, company sales import, Technical review modification, stock adjustment, authentication setting change or AI model deployment. The page only becomes live after a separately verified branch merge and Render rollout.

# Groq Free AI Agent activation — PT Liliang (2026-11-06)

## Requirements
Only use a Groq **Free** organization and model `openai/gpt-oss-20b`. Confirm current limits in https://console.groq.com/docs/rate-limits.
Enable Zero Data Retention in https://console.groq.com/settings/data-controls. Do not submit real company data during pilot.
The repository installs `pydantic-ai-slim[groq]>=1,<2` in its main Python requirements. No paid license or new hosting is required.

## Secure activation
1. Open https://dashboard.render.com and select service `liliang-multi-ai-erp-pilot` (Free).
2. Click Environment -> Add Environment Variable. Create key `GROQ_API_KEY` and paste the secret **only in Render**.
3. Add second key `AI_AGENT_EXTERNAL_ENABLED` with value `true`.
4. Optional: `AI_AGENT_DAILY_CAP=3` for first UAT; default cap is 10 requests per UTC day **per app process**, maximum permitted value 20.
5. Choose Save, rebuild, and deploy; wait for status Live.
6. Log in to `/workspace` on ERP, then open `/ai/agent-pilot` in the same browser session.
7. Verify `Groq: CONFIGURED_SYNTHETIC_ONLY`, `SDK: Siap`, `API key: Ada`; select `STRAWBERRY_DAIRY`, mode Groq Free, click Jalankan simulasi.
8. Expected: `GROQ_FREE_SYNTHETIC`, four **synthetic** baseline outputs and a non-validated LLM explanation. Groq response is not training evidence.

## Safety and failure cases
- Default is OFF. No Groq calls occur without both the environment flag and a key.
- Groq Free account quotas are organization-wide. Account billing configuration is outside this app; never enable paid tier. The local request cap is conservative only, resets after restart, and is NOT a billing guarantee.
- `409`: Groq disabled/unconfigured; verify flag, key and deployment.
- `429`: app UAT cap reached, or provider rate limit; use local mode.
- `503`: provider error or wrong key. Review sanitized deployment logs, never print the key.
- To disable immediately: set `AI_AGENT_EXTERNAL_ENABLED=false`, Save and deploy.
- Do not paste the key in GitHub, chats, screenshots, or files; if exposed, revoke and regenerate.
- Pilot uses only fixed synthetic inquiries, no Neon company customer/stock data, no shipment approval, no database writes.
- Current Groq GPT-OSS 20B tool calls may be sequential; request_limit=6 for four AI tools.

## GitHub
- `agent_pilot.py` — synthetic agent tools, roles, UAT cap, safe status and API routes.
- `requirements.txt` — minimal PydanticAI Groq runtime installed on Render.
- `tests/test_agent_pilot.py` — local tests, no actual Groq requests in CI.

Expected deployment cost: Rp0 additional on Render Free and Groq Free under plan limits. Not a formal guarantee of zero billing if user changes either account plan.

# MEMORY.md - Long-Term Memory

_Curated memory for important context, decisions, preferences, and durable facts._

## Identity

- Assistant name: cclow
- Nature: black wings angel
- Vibe: sharp when needed, calm by default
- Emoji: 🐈‍⬛

## Human

- Name: Ejack Yao

## Preferences

- Keep replies concise and practical by default.
- Prefers 3 Kimi 2.5 + 3 GLM-5 agent split for parallel work — Kimi for simpler tasks, GLM-5 for complex ones.

## Active Projects

### vtic (Ticket API)
- Repo: `https://github.com/661818yijack/vtic` (private)
- Local: `/home/smoke01/.openclaw/workspace-cclow/tmp/vtic/`
- Stack: Python 3.10-3.12, FastAPI, Zvec (vector DB), Pydantic v2, Typer
- Status: **Waves 1-5 complete**, E2E tests, CLI, benchmarks — 573 tests
- **Also used to track other project tickets** — check `tickets/` dir for work logged against any project

### lovemonself (MoneyFlow)
- Repo: `https://github.com/yi1jack0/lovemonself`
- Local clone: `/tmp/lovemonself/`
- Concept: Personal finance tracker with conversational AI (ASK + LOG modes), privacy-first
- Stack: Next.js 16, FastAPI microservices, Rust intent classifier, Firestore, Firebase Auth, multi-AI (Claude/Qwen/Grok/Gemini)
- Status: **Phases 1-9 COMPLETE** — Backend shared modules, API Gateway, AI Services, Frontend library all done
- **All tickets and design work tracked in vtic** at `tmp/vtic/tickets/yi1jack0/lovemonself/` (30 tickets across security, testing, architecture, frontend, performance, analysis)
- **New tickets (2026-03-21):** S15 shared prompt_utils, S15 contracts tests, S15 frontend contracts — in `code_quality/`, `testing/`, `frontend/`

## Technical Notes

- **Zvec uses RocksDB internally** — cosmetic cleanup errors in tests are Zvec's behavior, NOT a vtic bug. Do NOT waste time trying to fix them.

## Notes

- Use this file for stable, long-term memory.
- Use `memory/YYYY-MM-DD.md` for daily notes and raw session logs.
- **GitHub access:** `gh` CLI authenticated as `661818yijack` — can push to repos, create issues/PRs, access private repos

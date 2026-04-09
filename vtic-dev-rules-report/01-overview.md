# vtic Development Rules — Overview

**Generated:** 2026-03-19
**Workspace:** cclow (Coding Agent Workspace)
**Project:** vtic — AI-first ticketing system

---

## Executive Summary

This report compiles all development rules, patterns, conventions, and lessons learned during the development of **vtic**, an AI-first ticketing system with hybrid BM25 + semantic search.

The rules emerged from real development friction — agents writing conflicting code, tests that didn't catch bugs, design docs that contradicted each other. Each rule exists because something broke without it.

---

## Rule Categories

### 1. Process & Workflow
Rules for how development work is organized, tracked, and verified.

| Category | Key Rules |
|----------|-----------|
| **Phase Separation** | Never combine phases. Design → Plan → Develop → Test → Review → Fix are separate agent spawns. |
| **20-Minute Limit** | No agent task exceeds 20 minutes. If it can't fit, scope it smaller. |
| **Verification Protocol** | Never trust agent completion reports. Read actual files. Run actual tests. |
| **Design Doc Hierarchy** | One canonical source (usually OpenAPI). All other docs align to it. |

### 2. Code Quality
Rules for writing maintainable, correct code.

| Category | Key Rules |
|----------|-----------|
| **Unit Tests** | Non-negotiable. Every new code path has tests. Run early, run often. |
| **Type Safety** | No `any`/`unknown`. Use proper types or Zod schemas. |
| **No Secrets** | API keys, tokens → environment variables only. |
| **Project Structure** | Max 5 levels deep. Group by domain, not file type. |

### 3. Multi-Agent Orchestration
Rules for coordinating multiple coding agents.

| Category | Key Rules |
|----------|-----------|
| **File Ownership** | Every file has exactly one owner. No two agents write the same file. |
| **Interface Contracts** | Define shared method signatures BEFORE parallel work begins. |
| **Subagent vs ACP** | If you can write a 3-line spec, use subagent. If it needs exploration, use ACP. |
| **Model Selection** | Kimi 2.5 for code, GLM-5 for review. GLM-5 catches what Kimi misses. |

### 4. Testing Philosophy
Rules for writing tests that actually catch bugs.

| Category | Key Rules |
|----------|-----------|
| **Real over Mocks** | Real services catch real bugs. Mocks give false confidence. |
| **Test Hygiene** | Verify tests are testing the right thing before debugging code. |
| **Integration Tests** | FastAPI TestClient + real TicketService = highest confidence. |

---

## Key Metrics

| Metric | Value | Source |
|--------|-------|--------|
| **Wave 1 tasks** | T1-T6 | Foundation + Store + Index |
| **Wave 1 tests** | 378 passing | pytest verified |
| **Design contradictions (initial)** | 58 | Across 6+ independently-written docs |
| **Agent timeout limit** | 20 minutes | Hard limit per phase |
| **BM25 search target** | < 10ms | Performance requirement |
| **CRUD target** | < 5ms | Performance requirement |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10-3.12 |
| **Web Framework** | FastAPI |
| **CLI** | Typer |
| **Validation** | Pydantic v2 |
| **Vector DB** | Zvec (in-process, Alibaba-backed) |
| **Search** | BM25 (sparse) + dense embeddings |
| **Storage** | Markdown files with YAML frontmatter |
| **Config** | TOML |

---

## File Structure

```
vtic-dev-rules-report/
├── 01-overview.md          ← You are here
├── 02-architecture.md      Architecture patterns and decisions
├── 03-coding-conventions.md Code style and formatting rules
├── 04-naming-conventions.md Naming patterns for files, functions, variables
├── 05-api-design.md        REST API design rules and patterns
├── 06-testing-patterns.md  Testing conventions and best practices
├── 07-error-handling.md    Error handling and validation patterns
├── 08-file-organization.md Project structure and file placement rules
├── 09-documentation.md     Documentation standards
├── 10-security-rules.md    Security-related development rules
├── 11-performance.md       Performance guidelines and patterns
└── 12-lessons-learned.md   Key lessons and gotchas discovered
```

---

## Quick Reference

### The 12 Non-Negotiable Rules

1. **Workspace-local temp files** — Never use `/tmp` for anything you need to keep
2. **Unit tests required** — Every new code path has tests. No exceptions.
3. **Max 5 levels deep** — Files must not be buried more than 5 levels from project root
4. **Type-safe code** — No `any`/`unknown`. Use proper types or Zod schemas
5. **No secrets in code** — API keys → environment variables only
6. **Meaningful git commits** — Conventional commits, one logical change per commit
7. **Test early, test often** — Run tests after each logical change, not after 100 lines
8. **Report progress** — Don't go silent. Report findings and next steps regularly
9. **Zvec for vectors** — Use Zvec (not Qdrant/Pinecone/Chroma) for vector storage
10. **Design doc hierarchy** — One canonical source. All docs align to it.
11. **Phase separation** — Design/Plan/Develop/Test/Review/Fix are separate spawns
12. **Verify before trust** — Never trust agent reports. Read files. Run tests.

---

## Sources

All rules in this report are derived from:

- `rules/coding-standards.md` — Core coding standards (12 sections)
- `rules/workflow/*.md` — Workflow rules (planning, verification, cleanup, diary)
- `AGENTS.md` — Workspace organization and delegated coding work rules
- `skills/*/SKILL.md` — Skills for orchestration, verification, testing
- `tmp/vtic/EXECUTION_PLAN.md` — Task execution strategy
- `tmp/vtic/BUILD_PLAN.md` — Build phases and priorities
- `tmp/vtic/FEATURES.md` — Feature specifications with priorities
- `MEMORY.md` — Long-term lessons and context

---

*This report is a living document. Update it as new patterns emerge and rules evolve.*

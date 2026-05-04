# Workspace State

## In Progress
- none

## Ready
- Adopt the self-harness consistently on the next non-trivial task

## Backlog
- refine local conventions as patterns emerge

## Done
- VTIC Phase 2 due_date field implementation across models, storage, CLI, API, migration script, and tests
- bootstrap lightweight self-harness for cclow
- create `skills/self-harness/` as the router skill for using and evolving the harness
- MoneyFlow agent auth security fixes in `/tmp/lovemonself` (hashed token storage + permission-enforced agent routes)

---

## 2026-03-21 Session (Dave)

### Major Insights
1. **TDD is human-optimized**, not LLM-optimized
2. **Subagents are anti-pattern** for interdependent work
3. **Complete specification** is the key skill for LLM development

### Tools Created
- `seed_hex_converter.py` - Hex to 16-char converter
- `time_seed_generator.py` - Generate 4 numbers from 3 + timestamp
- `4d_pattern_hunter.py` - Statistical analysis of 4D results

### Research Done
- Da Ma Cai API: `damacai.hongineer.com/results/`
- Claude Code Review: Multi-agent PR analysis
- Codex Code Review: `@codex review` integration
- Malaysian 4D repos: hongster/damacai, rouze-d/4D-Prediction

### Repositories
- **SEZA**: https://github.com/hojipago-jpg/SEZA (collaborator access)
- Purpose: Trading algorithm system

### Key Lessons
- Subagents caused vtic's 58 contradictions
- Two-agent system better: Developer + Tester
- Quality of LLM output = Quality of input specification
- 4D lottery appears truly random (chi-square tests pass)

# HEARTBEAT.md - Multi-Agent Workspace Audit

**Interval:** Every 1 hour
**Trigger:** OpenClaw cron job `cclow-heartbeat-30m`

---

## Purpose

Every hour, spawn 4 subagents to audit the other 5 agent workspaces for:
1. New software/code developed
2. New skills created
3. Critical issues requiring tickets

---

## Locations to Audit

### Agent Workspaces

| Agent | Workspace | Discord Bot |
|-------|-----------|-------------|
| dave | `/home/smoke01/.openclaw/workspace-dave/` | dave |
| conte | `/home/smoke01/.openclaw/workspace-conte/` | conte ✨ |
| calen | `/home/smoke01/.openclaw/workspace-calen/` | calen 📅 |
| email | `/home/smoke01/.openclaw/workspace-email/` | email 📧 |
| finan | `/home/smoke01/.openclaw/workspace-finan/` | finan 💰 |

### Global Skills Directory

| Location | Purpose |
|----------|---------|
| `/home/smoke01/.openclaw/skills/` | Shared skills across all agents |

**Check for:**
- New skills installed
- Skill updates
- SKILL.md changes

---

## Subagent Assignments

| Subagent | Model | Targets | Focus |
|----------|-------|---------|-------|
| auditor-1 | zai/glm-5 | dave, conte + global skills | Code review, skills audit |
| auditor-2 | zai/glm-5 | calen + global skills | Code review, skills audit |
| auditor-3 | moonshot/kimi-k2.5 | email + global skills | Code review, skills audit |
| auditor-4 | (default) | finan + global skills | Code review, skills audit |

**Note:** All auditors also check `/home/smoke01/.openclaw/skills/` for new/updated global skills.

---

## Audit Checklist

Each subagent should:

### 1. Check for New Software
- [ ] Scan `src/`, `lib/`, `scripts/` directories
- [ ] Review recent file changes
- [ ] Check for new projects or modules
- [ ] Note code quality issues

### 2. Check for New Skills
- [ ] Scan agent `skills/` directory (workspace-local)
- [ ] Scan `/home/smoke01/.openclaw/skills/` (global shared skills)
- [ ] Review SKILL.md files
- [ ] Check for new tools or capabilities

### 3. Create Tickets if Critical
- [ ] Create ticket at `/home/smoke01/.openclaw/tickets/YYYY-MM-DD_cclow-{type}-NNN.md`
- [ ] Types: `bug`, `enhancement`, `security`, `review`
- [ ] Include: agent name, file paths, severity, recommendation

---

## Ticket Template

```markdown
# [BUG|ENHANCEMENT|SECURITY|REVIEW] - {Title}

**Agent:** {agent name}
**Severity:** Critical | High | Medium | Low
**Created:** {date}
**File(s):** {paths}

## Description
{What was found}

## Recommendation
{What should be done}

## Context
{Code snippet or relevant details}
```

---

## Heartbeat Flow

```
1. Check TODO.md for blockers
2. Spawn 4 auditor subagents (one per model)
3. Each auditor reviews 1-2 agent workspaces
4. Collect findings
5. Create tickets for critical issues
6. Report summary to main session
```

---

## Notes

- If nothing needs attention, reply `HEARTBEAT_OK`
- Maximum 4 concurrent subagents
- Each subagent has 5-minute timeout
- Results written to `/home/smoke01/.openclaw/tickets/`

# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## Global Skills Location

**Path:** `/home/smoke01/.openclaw/skills/`

This is THE global skills directory for all agents. Install shared skills here.

Current global skills:
- `python-llm-tools` - Python best practices for LLM tool calling
- `ts-llm-tools` - TypeScript best practices for LLM tool calling
- `harness-workflow` - Multi-step task workflow

When creating skills for all agents, install to global location, not per-workspace.

**Note:** Heartbeat audits check this directory for new/updated skills every hour.

## Local Paths

- harness-portable (WSL path): `/home/smoke01/workingdir/harness-portable`
- harness-portable (Windows UNC): `\\wsl.localhost\Ubuntu\home\smoke01\workingdir\harness-portable`

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

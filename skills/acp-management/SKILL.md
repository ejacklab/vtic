---
name: acp-management
description: "Manage ACP (Agent Communication Protocol) sessions for Claude Code, Codex, and other coding harnesses. Use when: (1) configuring ACP in openclaw.json, (2) spawning ACP agents, (3) deciding between ACP and subagent, (4) troubleshooting ACP issues. NOT for: regular subagent spawning (use multi-agent-orchestration)."
---

# ACP Management

## Setup Checklist

```bash
# 1. Install the CLI
npm install -g @anthropic-ai/claude-code  # Claude Code
npm install -g @openai/codex               # Codex
# etc.

# 2. Verify CLI works
claude --version
codex --version

# 3. acpx plugin (usually auto-loaded)
openclaw plugins list  # should show "acpx" as loaded

# 4. Configure openclaw.json
openclaw config set acp.enabled true
openclaw config set acp.backend acpx
openclaw config set acp.allowedAgents '["pi","claude","codex","opencode","gemini","kimi"]'

# 5. Add model to allowlist (for subagent access too)
# Edit openclaw.json directly — config set mangles keys with slashes
# agents.defaults.models["openai-codex/gpt-5.4"] = {"alias": "gpt-5.4"}

# 6. Set permissions
openclaw config set plugins.entries.acpx.config.permissionMode approve-all

# 7. Restart gateway
openclaw gateway restart
```

## Spawn ACP Agent

```python
sessions_spawn(
    runtime="acp",
    agentId="claude",  # or "codex", "opencode", "gemini", "kimi", "pi"
    mode="run",        # "run" (one-shot) or "session" (persistent, needs thread=true)
    task="...",
    cwd="/path/to/project"  # optional
)
```

## Thread Binding (Persistent Sessions)

Requires per-channel config:
```json
{
  "channels": {
    "discord": {
      "threadBindings": { "spawnAcpSessions": true }
    }
  }
}
```

## Known Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `ACP runtime backend is not configured` | acpx plugin not loaded | `openclaw plugins list` — check acpx status |
| `model not allowed` | Model not in agents.defaults.models | Edit openclaw.json directly (config set mangles slash keys) |
| Agent stuck in loop | Permission prompts or fix loops | Kill process, set `permissionMode=approve-all` |
| Session mode requires thread=true | Mode=session needs thread binding | Use mode=run or enable thread bindings |

## When to Use ACP vs Subagent

See `multi-agent-orchestration` skill for full decision matrix.

**TL;DR:**
- **ACP** = open exploration, needs full CLI, agent decides its own approach
- **Subagent** = precise instructions, you specify exact files and behavior

## Harness Comparison (from vtic experience)

| Harness | Speed | Quality | Notes |
|---------|-------|---------|-------|
| Claude Code | Slow (30min+) | Good | Gets stuck in fix loops |
| Codex | Medium (15-30min) | Good | Completed tasks reliably |
| Kimi 2.5 subagent | Fast (1-5min) | Good for defined tasks | Can't do file I/O autonomously |
| GLM-5 subagent | Fast (1-5min) | Best for review | Has been caught lying about fixes |
| GPT-5.4 subagent | Fastest (30s) | Good for well-scoped tasks | No autonomous file access |

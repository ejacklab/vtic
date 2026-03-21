# Development Pipeline Model Assignment Plan

**Research Date:** 2026-03-15
**Reviewer:** cclow (CTO)
**Status:** Review Complete ✅

---

## Proposed Model Assignment

| Phase | Task | Model | Provider | API Endpoint |
|-------|------|-------|----------|--------------|
| 1 | Research | `openai/gpt-5-mini` | OpenAI | OpenAI API |
| 2 | Feature Design | `zai/glm-5` | ZAI | ZAI API |
| 3 | Requirements | `zai/glm-5` | ZAI | ZAI API |
| 4 | Dev Planning | `zai/glm-5` | ZAI | ZAI API |
| 5 | TS Development | `moonshot/kimi-k2.5` | Moonshot | Moonshot API |
| 6 | Python Development | `minimax/MiniMax-M2.5` | MiniMax | `https://api.minimax.io/anthropic` |
| 7 | Testing | `zai/glm-4.7` | ZAI | ZAI API |

---

## Model Capabilities Review

### 📚 Phase 1: Research (gpt-5-mini)

| Attribute | Assessment |
|-----------|------------|
| **Model** | `openai/gpt-5-mini` |
| **Speed** | ⚡⚡⚡ Fastest |
| **Cost** | ~$0.15/MTok (cheap) |
| **Research Quality** | Good enough for quick searches |

**✅ Verdict:** EXCELLENT choice
- Cheap + fast = perfect for high-volume research
- Good enough quality for competitor analysis, pattern discovery
- 33x cheaper than gpt-5.4

**⚠️ Note:** For deep research requiring synthesis, consider upgrading to `gpt-5.2` or `gpt-5.4`

---

### 📐 Phase 2-4: Design & Planning (glm-5)

| Attribute | Assessment |
|-----------|------------|
| **Model** | `zai/glm-5` |
| **Reasoning** | Strong (your current main model) |
| **Planning** | Good for structured work |
| **Cost** | Moderate |

**✅ Verdict:** GOOD choice
- You're already using it as main agent
- Familiar with its strengths/weaknesses
- Good reasoning for requirements/design

**Alternative Consideration:**
- For complex architecture decisions: `openai/gpt-5.4` or `anthropic/claude-opus-4.6`
- For speed: `zai/glm-4.7-flashx`

---

### 💻 Phase 5: TypeScript Development (kimi-k2.5)

| Attribute | Assessment |
|-----------|------------|
| **Model** | `moonshot/kimi-k2.5` |
| **Coding** | Strong (designed for coding) |
| **TS/JS** | Excellent |
| **Long Context** | Yes (supports large codebases) |

**✅ Verdict:** EXCELLENT choice
- Your dave agent already uses this for coding
- Kimi is coding-optimized
- Good TypeScript support

**Available Variants:**
- `kimi-k2.5` — Standard
- `kimi-k2-thinking` — For complex reasoning
- `kimi-coding` — Dedicated coding model

---

### 🐍 Phase 6: Python Development (MiniMax-M2.5)

| Attribute | Assessment |
|-----------|------------|
| **Model** | `minimax/MiniMax-M2.5` |
| **Coding** | Strong (upgraded code generation) |
| **Speed** | Fast |
| **Cost** | Cost-effective |
| **API** | Anthropic-compatible ✅ |

**✅ Verdict:** EXCELLENT choice
- "More precise code generation" (MiniMax docs)
- Anthropic-compatible API at `https://api.minimax.io/anthropic`
- Fast + cost-effective
- Strong Python support

**API Configuration:**
```json
{
  "models": {
    "providers": {
      "minimax": {
        "baseUrl": "https://api.minimax.io/anthropic",
        "api": "anthropic",
        "models": [{
          "id": "MiniMax-M2.5",
          "name": "MiniMax M2.5"
        }]
      }
    }
  }
}
```

---

### 🧪 Phase 7: Testing (glm-4.7)

| Attribute | Assessment |
|-----------|------------|
| **Model** | `zai/glm-4.7` |
| **Speed** | Fast |
| **Cost** | Lower than glm-5 |
| **Test Generation** | Good |

**✅ Verdict:** GOOD choice
- Faster + cheaper than glm-5
- Good enough for test generation
- Same provider (ZAI) = consistent auth

**Available Variants:**
- `glm-4.7` — Standard
- `glm-4.7-flash` — Faster
- `glm-4.7-flashx` — Fastest

**Recommendation:** For pure test generation (no complex reasoning), consider `glm-4.7-flashx` for speed.

---

## Overall Assessment

### ✅ Strengths

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Cost Optimization** | ⭐⭐⭐⭐⭐ | Uses cheap models for high-volume tasks |
| **Speed** | ⭐⭐⭐⭐⭐ | Mini + Flash variants = fast pipeline |
| **Specialization** | ⭐⭐⭐⭐⭐ | Right model for right task |
| **Provider Diversity** | ⭐⭐⭐⭐ | 4 providers = no single point of failure |

### ⚠️ Considerations

| Issue | Impact | Recommendation |
|-------|--------|----------------|
| Provider switching | Context lost between phases | Keep phase outputs well-documented |
| API key management | 4 sets of credentials | Use secrets.json |
| Quality consistency | Different models = different styles | Clear handoff documents |

---

## Recommended Configuration

### openclaw.json

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "model": "openai/gpt-5-mini"
      }
    }
  },
  "models": {
    "providers": {
      "minimax": {
        "baseUrl": "https://api.minimax.io/anthropic",
        "api": "anthropic",
        "models": [
          { "id": "MiniMax-M2.5", "name": "MiniMax M2.5" }
        ]
      }
    }
  }
}
```

### Pipeline Task Assignment

```json
{
  "pipeline": {
    "research": {
      "model": "openai/gpt-5-mini",
      "subagent": true
    },
    "design": {
      "model": "zai/glm-5",
      "subagent": false
    },
    "ts-dev": {
      "model": "moonshot/kimi-k2.5",
      "subagent": true
    },
    "python-dev": {
      "model": "minimax/MiniMax-M2.5",
      "subagent": true
    },
    "testing": {
      "model": "zai/glm-4.7-flashx",
      "subagent": true
    }
  }
}
```

---

## Final Verdict

| Phase | Model | Rating | Notes |
|-------|-------|--------|-------|
| Research | gpt-5-mini | ⭐⭐⭐⭐⭐ | Perfect: fast + cheap |
| Design | glm-5 | ⭐⭐⭐⭐ | Good: familiar, capable |
| TS Dev | kimi-k2.5 | ⭐⭐⭐⭐⭐ | Excellent: coding-optimized |
| Python Dev | MiniMax-M2.5 | ⭐⭐⭐⭐⭐ | Excellent: Anthropic-compatible, fast |
| Testing | glm-4.7 | ⭐⭐⭐⭐ | Good: consider flashx for speed |

**Overall:** ⭐⭐⭐⭐⭐ Excellent cost-optimized pipeline

---

## Action Items

- [ ] Add MiniMax API key to secrets.json
- [ ] Configure MiniMax provider in openclaw.json
- [ ] Test `https://api.minimax.io/anthropic` endpoint
- [ ] Document pipeline in project TODO.md
- [ ] Consider `glm-4.7-flashx` for testing (faster)

---

**Review completed by:** cclow (CTO)

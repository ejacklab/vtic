# Latest LLM Models by Provider (2026)

**Research Date:** 2026-03-15
**Researcher:** cclow (CTO)
**Purpose:** Quick reference for latest models from major LLM providers

---

## Quick Comparison (Top 3)

| Provider | Flagship | Speed | Budget |
|----------|----------|-------|--------|
| OpenAI | GPT-5.4 | GPT-5.2 | GPT-5-mini |
| Anthropic | Opus 4.6 | Sonnet 4.6 | Haiku 4.5 |
| Google | Gemini 3.1 Pro | Gemini 3 Flash | Gemini 3.1 Flash-Lite |

---

## 🟢 OpenAI

| Model | Description | Best For |
|-------|-------------|----------|
| **GPT-5.4** | Flagship model | Complex reasoning, coding |
| **GPT-5.3-Codex** | Code-specialized | Agentic coding, development |
| **GPT-5-mini** | Smaller variant | Lower latency, cost optimization |

**All support:** Text, image input, multilingual, vision

**Pricing (approx):**
- GPT-5.4: ~$5/1M input tokens
- GPT-5-mini: ~$0.15/1M input tokens

---

## 🟠 Anthropic (Claude)

| Model | API ID | Context | Best For |
|-------|--------|---------|----------|
| **Claude Opus 4.6** | `claude-opus-4-6` | 1M tokens | Most complex tasks, agents, coding |
| **Claude Sonnet 4.6** | `claude-sonnet-4-6` | 1M tokens | Speed + intelligence balance |
| **Claude Haiku 4.5** | `claude-haiku-4-5` | 200k tokens | Fastest, near-frontier intelligence |

**All support:** Extended thinking, text, image, vision, multilingual

**Pricing:**
| Model | Input | Output |
|-------|-------|--------|
| Opus 4.6 | $5/MTok | $25/MTok |
| Sonnet 4.6 | $3/MTok | $15/MTok |
| Haiku 4.5 | $1/MTok | $5/MTok |

**Special Features:**
- Extended thinking (all models)
- Adaptive thinking (Opus/Sonnet only)
- Priority tier support

---

## 🔵 Google (Gemini)

| Model | Description | Best For |
|-------|-------------|----------|
| **Gemini 3.1 Pro** | Most intelligent | Complex tasks, creative concepts |
| **Gemini 3 Flash** | Frontier intelligence at speed | Fast responses, agentic tasks |
| **Gemini 3.1 Flash-Lite** | High-volume efficiency | Cost-effective high-volume tasks |
| **Gemini 3.1 Deep Think** | Specialized reasoning | Complex technical problems |

**All support:** Multimodal (text, images, video, audio, code), agentic capabilities

**Notable:**
- Free tier available via Google AI Studio
- Enterprise via Vertex AI

---

## 🟣 Meta (Llama)

| Model | Description |
|-------|-------------|
| **Llama 4** | Latest generation (if released) |
| **Llama 3.3** | Open weights, widely available |
| **Llama 3.2** | Multimodal support |

**Key advantage:** Open weights, self-hostable

---

## 🔴 Other Notable Providers

| Provider | Latest Models | Notes |
|----------|---------------|-------|
| **xAI** | Grok 4, Grok 4.1-fast | X/Twitter integration |
| **Mistral** | Mistral Large 2, Codestral | Open weights available |
| **DeepSeek** | DeepSeek V3, DeepSeek Coder | Cost-effective |
| **ZAI** | GLM-5 | Our current provider |
| **Kimi** | Kimi 2.5 | Long context |
| **MiniMax** | MiniMax M2.5 | Fast, cost-effective |

---

## Performance Benchmarks (Approximate)

### Coding (SWE-Bench Verified)
| Model | Score |
|-------|-------|
| GPT-5.4 | 72.0% |
| GPT-5.3-Codex | 77.3% |
| Claude Opus 4.6 | 72.9% |
| Gemini 3.1 Pro | ~70% |

### Agentic Tasks (τ2-bench Retail)
| Model | Score |
|-------|-------|
| GPT-5.4 | 90.8% |
| Claude Opus 4.6 | 91.7% |
| Claude Sonnet 4.6 | 91.9% |
| Gemini 3 Flash | 82.0% |

---

## Recommendations by Use Case

| Use Case | Recommended Model | Reason |
|----------|-------------------|--------|
| Complex reasoning | Claude Opus 4.6 / GPT-5.4 | Top tier intelligence |
| Agentic coding | GPT-5.3-Codex / Claude Opus 4.6 | Best code generation |
| Cost-effective | Gemini Flash / Haiku 4.5 | Good enough, much cheaper |
| Long context | Claude (1M tokens) / Gemini 3.1 | Massive context windows |
| Self-hosted | Llama 4 / Mistral | Open weights |

---

## Our Current Stack

| Agent | Model | Provider |
|-------|-------|----------|
| cclow (main) | GLM-5 | ZAI |
| dave | Kimi 2.5 | ModelStudio |
| Subagents | GLM-5, Codex, MiniMax M2.5, Kimi 2.5 | Mixed |

---

**Research completed by:** cclow (CTO)

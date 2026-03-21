# Open-DSearch Competitor Analysis

**Research Date:** 2026-03-15
**Researcher:** cclow (CTO)
**Purpose:** Identify existing solutions to avoid building from zero

---

## Executive Summary

Open-DSearch competes in the AI-powered search/research space. Key differentiator: "Bring Your Own LLM/Tools" — user-owned infrastructure, no vendor lock-in, flexible depth control.

---

## Top 3 Competitors

### 🥇 #1: Vane

| Attribute | Value |
|-----------|-------|
| **Stars** | 32,979 ⭐ |
| **URL** | https://github.com/ItzCrazyKns/Vane |
| **Language** | TypeScript |
| **License** | MIT |
| **Last Updated** | 2026-03-15 |
| **Description** | AI-powered answering engine |

**What it does:** Perplexity-style AI answering engine with its own search infrastructure.

**Strengths:**
- Massive community adoption (33K stars)
- Active development (updated today)
- MIT license (permissive)
- Mature codebase

**Weaknesses:**
- Hosted service model
- No BYO LLM support
- Vendor lock-in potential

**Open-DSearch Advantage:** Vane is a hosted service. Open-DSearch = "bring your own LLM/tools" = more control, no vendor lock-in.

---

### 🥈 #2: SearXNG

| Attribute | Value |
|-----------|-------|
| **Stars** | 26,517 ⭐ |
| **URL** | https://github.com/searxng/searxng |
| **Docs** | https://docs.searxng.org |
| **Language** | Python |
| **License** | AGPL-3.0 |
| **Last Updated** | 2026-03-15 |
| **Description** | Free internet metasearch engine — aggregates from multiple sources, no tracking |

**What it does:** Self-hosted metasearch that aggregates Google, Bing, DuckDuckGo, and 70+ other search engines.

**Strengths:**
- Mature, battle-tested codebase
- Privacy-focused (no tracking)
- Highly customizable
- Self-hosted
- Large community

**Weaknesses:**
- AGPL license (copyleft — must share modifications)
- Search aggregation only, no LLM integration
- Requires infrastructure setup

**Open-DSearch Advantage:** SearXNG = search aggregation only. Open-DSearch = LLM-powered research with depth control + search aggregation.

**Integration Opportunity:** Open-DSearch could USE SearXNG as a search backend!

---

### 🥉 #3: Morphic

| Attribute | Value |
|-----------|-------|
| **Stars** | 8,662 ⭐ |
| **URL** | https://github.com/miurla/morphic |
| **Demo** | https://morphic.sh |
| **Language** | TypeScript |
| **License** | Apache 2.0 |
| **Last Updated** | 2026-03-15 |
| **Description** | AI-powered search engine with generative UI |

**What it does:** Perplexity-style AI search with beautiful generative UI.

**Strengths:**
- Excellent UX/design
- Active development
- Apache 2.0 license (permissive)
- Generative UI components

**Weaknesses:**
- Hosted service model
- No BYO LLM support
- Less flexible for customization

**Open-DSearch Advantage:** Morphic = hosted service. Open-DSearch = user-owned infrastructure.

---

## Honorable Mention: Local Deep Research

| Attribute | Value |
|-----------|-------|
| **Stars** | 4,142 ⭐ |
| **URL** | https://github.com/LearningCircuit/local-deep-research |
| **Language** | Python |
| **License** | MIT |
| **Last Updated** | 2026-03-14 |
| **Description** | Local deep research with 10+ sources (arXiv, PubMed, web, private docs). 95% on SimpleQA benchmark. |

**⚠️ CLOSEST TO OPEN-DSEARCH VISION**

**What it does:** Local-first deep research tool supporting multiple LLMs and data sources.

**Strengths:**
- Multi-source search (arXiv, PubMed, web, private docs)
- Supports local + cloud LLMs (Ollama, Google, Anthropic)
- Privacy-focused (local & encrypted)
- Research-oriented with depth
- 95% on SimpleQA benchmark

**Weaknesses:**
- Smaller community
- Research-focused only (no quick search mode)
- Less flexible architecture

**Open-DSearch Advantage:** Local Deep Research = research-focused. Open-DSearch = flexible depth (quick → deep), user's tools, multi-provider orchestration.

**Integration Opportunity:** Study their architecture for research patterns!

---

## Competitive Position Matrix

| Feature | Vane | SearXNG | Morphic | Local Deep Research | **Open-DSearch** |
|---------|------|---------|---------|---------------------|------------------|
| **Stars** | 33K | 27K | 9K | 4K | New |
| **Self-hosted** | ❌ | ✅ | ❌ | ✅ | ✅ |
| **BYO LLM** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Multi-provider search** | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Depth control (quick→deep)** | ❌ | ❌ | ❌ | Partial | ✅ |
| **Privacy-focused** | ❌ | ✅ | ❌ | ✅ | ✅ |
| **User's own tools** | ❌ | ❌ | ❌ | Partial | ✅ |
| **License** | MIT | AGPL | Apache | MIT | TBD |

---

## Strategic Recommendations

### 1. Integration Opportunities
- **SearXNG** — Use as a search backend for Open-DSearch
- **Local Deep Research** — Study architecture for research patterns
- **Morphic** — Reference for UI/UX patterns

### 2. Open-DSearch Differentiation
- **"Research infrastructure you actually own"**
- BYO LLM, BYO tools, no vendor lock-in
- Flexible depth: quick lookup → deep research
- User's own API keys (no middleman)

### 3. Licensing Consideration
- Avoid AGPL (SearXNG) if we want proprietary options
- MIT/Apache are safest for flexibility
- Consider dual-licensing model

### 4. MVP Focus
- Don't build search from scratch — integrate SearXNG or similar
- Don't build LLM orchestration from scratch — use LiteLLM
- Focus on the unique value: depth control + user-owned infrastructure

---

## Additional Research Needed

- [ ] Deep dive into Local Deep Research architecture
- [ ] Evaluate SearXNG integration feasibility
- [ ] Analyze Vane's monetization model
- [ ] Research LLM tool frameworks (LiteLLM, LangChain, etc.)
- [ ] Survey potential users on "BYO LLM" requirement

---

**Research completed by:** cclow (CTO)
**Next step:** Review with Ejack, refine Open-DSearch positioning

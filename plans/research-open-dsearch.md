# Open-DSearch Research & Planning

**Created:** 2026-03-15
**Vision:** Open-DSearch (Open Dynamic Search) is a flexible research tool where users can perform dynamic searches — from quick lookups to deep research — using their own LLMs and tools.

---

## 1. Competitor Analysis

### Major LLM Research Tools

| Tool | Description | Strengths | Weaknesses |
|------|-------------|-----------|------------|
| **Perplexity AI** | Leading AI search engine with citations | Real-time web search, clean UI, strong citation game, follow-up questions, "Pro" search with deeper analysis | Proprietary, locked into their LLM, rate limits on free tier, no self-hosting |
| **Phind** | AI search for developers | Code-focused, technical answers, VS Code integration, good for debugging | Limited general knowledge, weaker for non-technical searches |
| **You.com** | Privacy-focused AI search | Multiple AI modes, privacy emphasis, apps ecosystem | Fragmented UX, less coherent research flow, citation quality varies |
| **Komo** | AI search with community features | Clean design, "Ask the Community" feature | Smaller index, less refined than Perplexity |
| **Arc Search** | Mobile-first AI browser | Great mobile UX, "Browse for Me" feature | iOS/macOS only, limited customization |
| **Exa (formerly Metaphor)** | Neural search API | Developer-friendly, semantic search, link to LLM | More of an API than end-user tool |
| **Brave Leo** | Browser-integrated AI | Built into Brave, privacy-focused | Limited depth, no dedicated research mode |
| **ChatGPT Search** | OpenAI's web search integration | Seamless with ChatGPT, strong reasoning | Requires ChatGPT Plus, OpenAI ecosystem lock-in |
| **Gemini Search** | Google's AI search | Access to Google's index, multimodal | Privacy concerns, Google ecosystem lock-in |

### Key Patterns

1. **All are walled gardens** - Users can't bring their own models
2. **Citation quality varies** - Some cite well, others hallucinate sources
3. **Research depth is fixed** - Can't dial from "quick check" to "deep dive" systematically
4. **No tool extensibility** - Can't add custom search sources or analysis tools
5. **Privacy = trade-off** - Self-hosting not an option

---

## 2. Open-DSearch Differentiators

### "Bring Your Own LLM/Tools" - Why This Matters

**Problem:** Every research tool locks you into their LLM choice. This means:
- Can't use specialized models (e.g., domain-specific fine-tunes)
- Can't control costs (locked into provider pricing)
- Can't control privacy (data goes to provider)
- Can't optimize for specific use cases

**Solution:** Open-DSearch is model-agnostic by design:
- **LLM Adapters:** Pluggable interface for any LLM (OpenAI, Anthropic, local models, fine-tunes)
- **Tool Adapters:** Pluggable search sources, analysis tools, data processors
- **Privacy by Architecture:** Run everything locally if desired

### The Gap Open-DSearch Fills

| Need | Current Tools | Open-DSearch |
|------|---------------|--------------|
| Use local/private models | ❌ Not possible | ✅ Core feature |
| Control research depth | ⚠️ Fixed modes | ✅ Configurable depth |
| Add custom data sources | ❌ Walled garden | ✅ Plugin system |
| Self-host for privacy | ❌ No | ✅ Yes |
| Use fine-tuned models | ❌ No | ✅ Yes |
| Integrate with existing tools | ⚠️ Limited APIs | ✅ Plugin architecture |
| Research workflows | ❌ One-shot answers | ✅ Multi-step research flows |

### Unique Value Proposition

> **"Research infrastructure you actually own"** — Not just another AI search engine, but a framework for building your own research workflows with your own tools and models.

---

## 3. Proposed Features

### Core Features (MVP)

#### 1. **Multi-Depth Research Modes**
```
QUICK     → Single search, summarized answer (like asking a colleague)
NORMAL    → 3-5 sources, synthesized answer with citations  
DEEP      → Iterative research, multiple queries, comprehensive report
CUSTOM    → User-defined search strategy
```

**Value Loop:** User selects depth → System adjusts search scope and analysis → Delivers right-sized answer

#### 2. **LLM Provider Abstraction**
- Unified interface for any LLM
- Pre-built adapters: OpenAI, Anthropic, Google, local (Ollama, LM Studio, vLLM)
- Runtime model switching per research task
- Cost/latency optimization hints

**Value Loop:** One config → Use any model → Swap without code changes

#### 3. **Search Backend Plugins**
- Web search: Brave, Exa, SerpAPI, Searxng (self-hosted)
- Academic: Semantic Scholar, arXiv
- Documentation: Custom doc indices
- Internal: Local files, databases, knowledge bases

**Value Loop:** Same query interface → Multiple sources → Unified results

#### 4. **Research Memory & Continuity**
- Session-based research threads
- Context carried across queries
- Export research trails (JSON, Markdown, PDF)
- "Resume research" from any point

**Value Loop:** Research isn't one-shot → Build on previous work → Institutional knowledge

#### 5. **Citation & Verification**
- Automatic source extraction
- Inline citations with links
- "Verify this claim" mode (cross-reference multiple sources)
- Confidence scores based on source agreement

**Value Loop:** Trust but verify → Transparent sources → Defensible research

### Differentiator Features (Post-MVP)

- **Research Agents:** Automated multi-step research (plan → search → synthesize → review)
- **Collaborative Research:** Share research threads with team
- **Research Templates:** Pre-defined research strategies for common tasks
- **API Mode:** Headless research for integration into other tools

---

## 4. Technical Architecture

### Recommended Stack

```
┌─────────────────────────────────────────────────────────┐
│                    Open-DSearch Core                     │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   LLM Layer  │  │ Search Layer │  │  Memory Layer│  │
│  │  (adapters)  │  │  (plugins)   │  │  (sessions)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                         │                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Research Orchestrator                  │   │
│  │   (coordinates depth, sources, synthesis)        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐      ┌──────────┐      ┌─────────┐
    │   CLI   │      │  Web UI  │      │   API   │
    └─────────┘      └──────────┘      └─────────┘
```

### Technology Choices

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Language** | TypeScript / Python | TypeScript for type safety and tooling; Python for ML ecosystem |
| **LLM Abstraction** | LiteLLM or custom adapter pattern | Proven pattern, wide model support |
| **Search Plugins** | Plugin architecture with typed interfaces | Extensibility without core changes |
| **Memory/Session** | SQLite (local) / PostgreSQL (team) | Simple default, scalable option |
| **Web UI** | React or SolidJS | Component-based, fast, familiar |
| **API** | Fastify (Node) or FastAPI (Python) | Async, performant, good DX |
| **CLI** | Commander.js or Typer | Standard, well-documented |

### LLM Integration Pattern

```typescript
// Adapter interface (simplified)
interface LLMAdapter {
  name: string;
  chat(messages: Message[], options?: LLMOptions): Promise<string>;
  stream?(messages: Message[], options?: LLMOptions): AsyncIterable<string>;
  available(): Promise<boolean>;
}

// Adapters implement this interface
class OpenAIAdapter implements LLMAdapter { ... }
class OllamaAdapter implements LLMAdapter { ... }
class AnthropicAdapter implements LLMAdapter { ... }

// Runtime selection
const llm = LLMRegistry.get(config.model);
const response = await llm.chat(messages, { depth: 'deep' });
```

### Search Backend Pattern

```typescript
// Search plugin interface
interface SearchBackend {
  name: string;
  search(query: string, options: SearchOptions): Promise<SearchResult[]>;
  available(): Promise<boolean>;
}

// Plugins
class BraveSearchBackend implements SearchBackend { ... }
class ExaSearchBackend implements SearchBackend { ... }
class LocalDocsBackend implements SearchBackend { ... }

// Orchestrator selects backends based on query type and user config
```

### Research Orchestrator

The core innovation — coordinates the research process:

1. **Parse intent** → Understand what user wants (quick answer vs. deep research)
2. **Select strategy** → Choose depth, sources, analysis approach
3. **Execute searches** → Query multiple backends in parallel
4. **Synthesize** → LLM combines and analyzes results
5. **Cite & verify** → Extract and validate citations
6. **Deliver** → Format based on mode (answer, report, export)

---

## 5. POC Scope

### Smallest Useful Version

**Goal:** Prove the core value proposition — "research with your own LLM and search backends"

#### Phase 1: Core Engine (1-2 weeks)
- [ ] LLM adapter interface + 2 adapters (OpenAI, Ollama)
- [ ] Search backend interface + 1 adapter (Brave or Exa)
- [ ] Basic research orchestrator (quick + normal depth)
- [ ] CLI interface for testing
- [ ] Simple config file for model/backend selection

**Success criteria:** Can run a search query using local LLM and Brave search from CLI

#### Phase 2: Memory & Depth (1 week)
- [ ] Session-based memory (SQLite)
- [ ] Deep research mode (iterative queries)
- [ ] Basic citation extraction
- [ ] Export to Markdown

**Success criteria:** Can do a multi-query deep research session and export results

#### Phase 3: MVP Polish (1 week)
- [ ] Simple Web UI (read-only at first)
- [ ] 2-3 more search backends (arXiv, local docs)
- [ ] Research templates (2-3 common patterns)
- [ ] Basic documentation

**Success criteria:** Demo-able product with clear differentiators

### What NOT to Build (Yet)

- User accounts / auth (single-user first)
- Collaborative features
- Mobile apps
- Complex agent workflows
- Fine-grained permissions

### First Build Priority

```
1. LLM adapter pattern     ← Core differentiator
2. Search backend pattern  ← Core differentiator
3. Basic orchestrator      ← Makes it useful
4. CLI interface           ← Fastest path to testing
5. Config system           ← Enables BYO-everything
```

---

## Next Steps

1. **Validate with Ejack** — Does this match the vision?
2. **Choose tech stack** — TypeScript vs Python (or hybrid?)
3. **Define adapter contracts** — Lock in interfaces before implementation
4. **Build POC Phase 1** — Prove the model
5. **Get feedback** — Early user testing with target audience

---

## Open Questions

- **Target audience:** Developers? Researchers? General users?
- **Primary interface:** CLI-first or Web-first?
- **Monetization:** Open core? Hosted version? Enterprise features?
- **Differentiation vs Perplexity:** If Perplexity adds "bring your own model", what's left?

---

*Document created by research subagent — ready for review and iteration*

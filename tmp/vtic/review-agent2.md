# vtic Feature Review - Categories 6-9

**Reviewer:** Agent 2  
**Categories:** Configuration, Embedding Providers, Multi-Repo Support, Integration  
**Priority System:**
- **Core** — The product doesn't exist without this. Ships in v0.1.
- **Must Have** — Required for production use. Ships before v1.0.
- **Should Have** — Important but not blocking. Can ship after v1.0.
- **Good to Have** — Nice polish. Backlog.

---

## 6. Configuration

### 6.1 Configuration Files

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Project config** | P0 | **Core** | Without config file support, users can't customize behavior. Essential. |
| **Global config** | P0 | **Must Have** | Convenient but you can ship with project config only. |
| **Config precedence** | P0 | **Must Have** | Good behavior but not required for v0.1 MVP. |
| **Config validation** | P0 | **Must Have** | Important for DX but product works without it. |
| **Config inheritance** | P2 | **Good to Have** | Nice for power users, not essential. |

### 6.2 Environment Variables

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Override any config** | P0 | **Must Have** | Required for containers and flexible deployments. |
| **API keys** | P0 | **Core** | Without API key support, embedding providers fail. Essential. |
| **Standard env names** | P0 | **Should Have** | Convention is nice but not blocking. |
| **Env file support** | P1 | **Should Have** | Convenient DX but `.env` is optional. |

### 6.3 Defaults & Profiles

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Sensible defaults** | P0 | **Core** | Zero-config is essential for adoption. Product feels broken without it. |
| **Configuration profiles** | P2 | **Good to Have** | Power user feature. Most users use one config. |
| **Default values in config** | P1 | **Must Have** | Good DX improvement for repetitive operations. |
| **Required config check** | P0 | **Must Have** | Important but you can fail later with cryptic errors and still function. |

---

## 7. Embedding Providers

### 7.1 OpenAI Provider

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **OpenAI embeddings** | P0 | **Must Have** | One embedding provider is needed, but local could be the primary instead. |
| **API key config** | P0 | **Core** | Covered in 6.2. Required for OpenAI to work. |
| **Model selection** | P0 | **Must Have** | Flexibility to choose model is important for cost/quality tradeoffs. |
| **Dimension config** | P0 | **Should Have** | Optimization feature. Default dimensions work fine. |
| **Rate limit handling** | P1 | **Must Have** | Production reliability. Without this, OpenAI calls fail under load. |
| **Batch embedding** | P1 | **Should Have** | Efficiency optimization, not required for correctness. |
| **Cost tracking** | P2 | **Good to Have** | Nice for monitoring but not essential. |

### 7.2 Local Provider

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Sentence Transformers** | P0 | **Must Have** | Alternative to cloud. Important for offline/privacy use cases. |
| **No API key** | P0 | **Must Have** | Implied by local provider. Not a separate feature. |
| **Model download** | P1 | **Should Have** | Nice UX but manual download is acceptable for v0.1. |
| **Model caching** | P1 | **Should Have** | Good for performance but not required. |
| **GPU acceleration** | P2 | **Good to Have** | Performance optimization for power users. |
| **Custom local models** | P2 | **Good to Have** | Advanced use case. Most users use defaults. |

### 7.3 Custom Provider

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **HTTP endpoint** | P1 | **Should Have** | Flexibility for custom setups, but not common. |
| **Custom auth** | P1 | **Should Have** | Needed if custom provider is used. |
| **Plugin interface** | P2 | **Good to Have** | Advanced extensibility. Very few users need this. |
| **Request/response mapping** | P2 | **Good to Have** | Same as above. |

### 7.4 None Provider (BM25 Only)

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Zero-config search** | P0 | **Core** | Product must work without embedding setup. This is the fallback. |
| **Disable semantic** | P0 | **Must Have** | Control option. Users should be able to opt out. |
| **Clear error on semantic query** | P0 | **Must Have** | Good DX. Without this, users get confusing errors. |

---

## 8. Multi-Repo Support

### 8.1 Namespacing

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Owner/repo structure** | P0 | **Must Have** | Fundamental organization. But single-repo works too. |
| **Repo in ticket metadata** | P0 | **Core** | Without repo field, multi-repo is impossible. Essential. |
| **Multiple owners** | P0 | **Must Have** | Part of multi-repo, but single-org setups are valid. |
| **Repo aliases** | P2 | **Good to Have** | Nice convenience. Not required. |

### 8.2 Cross-Repo Operations

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Glob repo filter** | P0 | **Must Have** | Essential for multi-repo utility. `--repo "org/*"` is a key feature. |
| **Multi-repo filter** | P0 | **Must Have** | Basic multi-repo operation. Required for the feature to be useful. |
| **Cross-repo search** | P0 | **Must Have** | Core value prop of multi-repo. Single query across repos. |
| **Per-repo stats** | P1 | **Should Have** | Useful reporting but not required for multi-repo to work. |
| **Repo isolation** | P1 | **Should Have** | Nice control but global operations are acceptable default. |

### 8.3 Multi-Repo Configuration

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Repo-specific defaults** | P1 | **Should Have** | Convenient but global defaults work. |
| **Repo-specific embedding** | P2 | **Good to Have** | Very niche. Most use one provider. |
| **Included/excluded repos** | P2 | **Good to Have** | Governance feature. Not required for MVP. |

---

## 9. Integration

### 9.1 Webhooks

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **On-create webhook** | P1 | **Should Have** | Automation feature. Can poll instead. |
| **On-update webhook** | P1 | **Should Have** | Same reasoning. |
| **On-delete webhook** | P1 | **Should Have** | Same reasoning. |
| **Webhook payload** | P1 | **Should Have** | Implied by webhooks. Not a separate feature. |
| **Retry logic** | P2 | **Good to Have** | Reliability enhancement. Nice but not required. |
| **Webhook signatures** | P2 | **Good to Have** | Security feature. Important for production but webhooks work without it. |

### 9.2 Git Hooks

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **Pre-commit validation** | P2 | **Good to Have** | Nice guardrail but CI can validate instead. |
| **Post-commit reindex** | P2 | **Good to Have** | Convenience. Manual reindex works. |
| **Branch-specific tickets** | P2 | **Good to Have** | Advanced workflow. Most teams don't need this. |

### 9.3 CI/CD Integration

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **CI-friendly CLI** | P0 | **Core** | Without proper exit codes and JSON output, CI integration fails. Essential. |
| **Docker image** | P1 | **Should Have** | Nice for deployment but binary works in CI. |
| **GitHub Action** | P1 | **Should Have** | Popular platform but CLI in workflow works too. |
| **Environment variables** | P0 | **Must Have** | Covered in 6.2. Required for containers. |

### 9.4 External Tool Integration

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| **MCP server** | P1 | **Should Have** | Modern AI integration. Growing importance but not core. |
| **Editor plugins** | P2 | **Good to Have** | Nice DX but markdown files work in any editor. |
| **Slack/Discord bot** | P2 | **Good to Have** | Convenience feature. API + webhooks enable this. |

---

## Summary

| Category | Core | Must Have | Should Have | Good to Have |
|----------|------|-----------|-------------|--------------|
| **6. Configuration** | 3 | 5 | 2 | 1 |
| **7. Embedding Providers** | 2 | 6 | 6 | 5 |
| **8. Multi-Repo Support** | 1 | 7 | 4 | 3 |
| **9. Integration** | 1 | 1 | 8 | 9 |
| **TOTAL** | **7** | **19** | **20** | **18** |

---

## Notes

### Core Features (7)
The absolute minimum for v0.1:
1. **Project config** - Users need to configure behavior
2. **API keys** - Embedding providers require authentication
3. **Sensible defaults** - Zero-config is essential for adoption
4. **Zero-config search (BM25)** - Product must work without embedding setup
5. **Repo in ticket metadata** - Foundation for multi-repo
6. **CI-friendly CLI** - Exit codes and JSON output for automation
7. **API key config (OpenAI)** - Required for OpenAI embedding

### What Got Downgraded
- **Config precedence/inheritance** - Good DX but not essential for v0.1
- **Env file support** - Nice but environment variables work directly
- **Configuration profiles** - Power user feature, most need one config
- **GPU acceleration** - Optimization for power users
- **All custom provider features** - Niche extensibility
- **All Git hooks** - CI can validate, manual reindex works
- **Slack/Discord bot** - API enables this, not a core feature

### What Stayed High
- **Zero-config search** - Critical fallback when embedding isn't set up
- **Cross-repo operations** - Core value of multi-repo feature
- **Rate limit handling** - Production reliability for OpenAI
- **Webhooks** - Integration story is important, just not Core

### Recommendation
The 7 Core features should ship in v0.1. The 19 Must Have features should be complete before v1.0. The 20 Should Have features can be added post-v1.0 based on user feedback. The 18 Good to Have features are backlog items for future consideration.

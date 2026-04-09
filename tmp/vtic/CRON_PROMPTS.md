# vtic Cron Job Prompts — 6-Level Breakdowns for Must Have / Should Have / Good to Have

**Schedule:** 6 tasks, 10 minutes apart, starting ~10 min from now
**Model:** zai/glm-5 (subagent, mode=run)
**Output:** /tmp/vtic/breakdown-mh-1.md through breakdown-gh-2.md

---

## Task 1: Must Have — First Half (24 features)

**Cron time:** +10 min

Read /tmp/vtic/PRIORITY_REVIEW.md, /tmp/vtic/FEATURES.md, and /tmp/vtic/breakdown-agent1.md (for format reference).

Take these 24 Must Have features and break each down to 6 levels:

**API ticket creation, ID slug from title, Output formats (CLI), API PATCH endpoint, Soft delete by default, Confirmation prompt, Semantic query, Embedding on write, Re-embed all, Combined query, Repo glob patterns, Sort by field, Sort by relevance, Atomic writes, Index co-location, Incremental indexing, POST /tickets, GET /tickets/:id, PATCH /tickets/:id, DELETE /tickets/:id, GET /tickets, POST /search, GET /health, Consistent envelope**

6 levels:
- L1: Category (from FEATURES.md structure)
- L2: Sub-category
- L3: Feature name
- L4: Implementation unit — exact function/class signature
- L5: Input/output spec — concrete examples with error cases
- L6: Test cases — 2-4 test function names per feature

Write to /tmp/vtic/breakdown-mh-1.md

---

## Task 2: Must Have — Second Half (24 features)

**Cron time:** +20 min

Read /tmp/vtic/PRIORITY_REVIEW.md, /tmp/vtic/FEATURES.md, and /tmp/vtic/breakdown-agent1.md (for format reference).

Take these 24 Must Have features and break each down to 6 levels:

**Error envelope, Validation errors, Pagination metadata, serve command, reindex command, Global config, Config precedence, Config validation, Override any config (env vars), Default values in config, Required config check, OpenAI embeddings, Model selection, Rate limit handling, Sentence Transformers, No API key, Disable semantic, Clear error on semantic query, Owner/repo structure, Multiple owners, Glob repo filter, Multi-repo filter, Cross-repo search, Environment variables (CI)**

6 levels: same format as Task 1.

Write to /tmp/vtic/breakdown-mh-2.md

---

## Task 3: Should Have — First Half (35 features)

**Cron time:** +30 min

Read /tmp/vtic/PRIORITY_REVIEW.md, /tmp/vtic/FEATURES.md, and /tmp/vtic/breakdown-agent1.md (for format reference).

Take these 35 Should Have features and break each down to 6 levels:

**Custom ID specification, Field selection, Raw file output, Append to description, Field clearing, Bulk update, Cascade delete, Restore deleted, Custom statuses, Ticket references, Parent/child tickets, Fuzzy matching, Boost fields, Phrase search, Embedding caching, Configurable weights, RRF fusion, Score normalization, Date range filters, Field existence, Cursor pagination, File locking, Index health check, Index corruption recovery, Export to archive, Import from archive, Point-in-time recovery, Bulk create API, Bulk update API, Bulk delete API, Get stats, OpenAPI spec, Markdown response, Request ID, Cursor pagination (API)**

6 levels: same format as Task 1.

Write to /tmp/vtic/breakdown-sh-1.md

---

## Task 4: Should Have — Second Half (35 features)

**Cron time:** +40 min

Read /tmp/vtic/PRIORITY_REVIEW.md, /tmp/vtic/FEATURES.md, and /tmp/vtic/breakdown-agent1.md (for format reference).

Take these 35 Should Have features and break each down to 6 levels:

**config command, stats command, validate command, doctor command, trash command, Bulk create CLI, Bulk update CLI, Bulk delete CLI, Export CLI, Import CLI, Markdown output, CSV output, Quiet mode, Verbose mode, Color control, Tab completion, Completion install, Standard env names, Env file support, Dimension config (OpenAI), Batch embedding, Model download, Model caching, HTTP endpoint (custom provider), Custom auth, Per-repo stats, Repo isolation, Repo-specific defaults, On-create webhook, On-update webhook, On-delete webhook, Webhook payload, Docker image, GitHub Action, MCP server**

6 levels: same format as Task 1.

Write to /tmp/vtic/breakdown-sh-2.md

---

## Task 5: Good to Have — First Half (27 features)

**Cron time:** +50 min

Read /tmp/vtic/PRIORITY_REVIEW.md, /tmp/vtic/FEATURES.md, and /tmp/vtic/breakdown-agent1.md (for format reference).

Take these 27 Good to Have features and break each down to 6 levels:

**Template-based creation, Interactive creation, Get by slug, Related tickets, Update history, Audit log, Vacuum trash, Status workflow, Transition validation, Auto-transitions, Blocking relationships, Cross-repo references, Reference resolution, Boolean operators, Field-specific search, Chunked embedding, Multi-vector tickets, Explain mode, Numeric comparison, OR filters, NOT filters, Faceted search, Random sampling, Custom directory layout, Multiple indexes, Index snapshot, Cloud backup sync**

6 levels: same format as Task 1.

Write to /tmp/vtic/breakdown-gh-1.md

---

## Task 6: Good to Have — Second Half (27 features)

**Cron time:** +60 min

Read /tmp/vtic/PRIORITY_REVIEW.md, /tmp/vtic/FEATURES.md, and /tmp/vtic/breakdown-agent1.md (for format reference).

Take these 27 Good to Have features and break each down to 6 levels:

**CSV export endpoint, Content negotiation, Error reference docs, Rate limit headers, Link headers, backup command, migrate command, YAML output, Aliases, Interactive mode, Config inheritance, Configuration profiles, Cost tracking, GPU acceleration, Custom local models, Plugin interface, Request/response mapping, Repo aliases, Repo-specific embedding, Included/excluded repos, Retry logic (webhooks), Webhook signatures, Pre-commit validation, Post-commit reindex, Branch-specific tickets, Editor plugins, Slack/Discord bot**

6 levels: same format as Task 1.

Write to /tmp/vtic/breakdown-gh-2.md

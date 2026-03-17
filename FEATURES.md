# vtic - Feature Specification

Comprehensive feature list for a production-ready ticket management system with hybrid search.

---

## 1. Ticket Lifecycle

### 1.1 Create Tickets

| Feature | Description | Priority |
|---------|-------------|----------|
| **CLI ticket creation** | `vtic create` with flags for title, description, repo, category, severity, status, file refs, tags | P0 |
| **API ticket creation** | `POST /tickets` endpoint accepting JSON body with all ticket fields | P0 |
| **Auto-generated IDs** | Generate unique, human-readable IDs (e.g., C1, C2, H1, M1) based on category | P0 |
| **ID slug from title** | Auto-generate URL-safe slug from title for filename (e.g., "CORS Wildcard" → `cors-wildcard`) | P0 |
| **Timestamp auto-fill** | Automatically set `created` and `updated` timestamps | P0 |
| **Required field validation** | Reject creation if required fields (title, repo) are missing | P0 |
| **Custom ID specification** | Allow specifying custom ID on creation for migration/import scenarios | P1 |
| **Template-based creation** | Load ticket structure from template files (e.g., `vtic create --template security-issue`) | P2 |
| **Interactive creation** | Prompt for missing fields interactively if terminal is TTY | P2 |

### 1.2 Read Tickets

| Feature | Description | Priority |
|---------|-------------|----------|
| **Get by ID** | `vtic get C1` / `GET /tickets/C1` returns full ticket | P0 |
| **Get by slug** | Allow fetching by filename slug as alternative to ID | P1 |
| **Output formats** | Support `--format json|markdown|yaml|table` for CLI output | P0 |
| **Field selection** | `--fields id,title,severity` to return only specified fields | P1 |
| **Raw file output** | `--raw` flag to output the raw markdown file content | P1 |
| **Related tickets** | `--related` to show linked/referenced tickets | P2 |

### 1.3 Update Tickets

| Feature | Description | Priority |
|---------|-------------|----------|
| **Field-level updates** | `vtic update C1 --status fixed --severity high` updates only specified fields | P0 |
| **API PATCH endpoint** | `PATCH /tickets/:id` with partial JSON body | P0 |
| **Automatic timestamp** | Update `updated` timestamp on any modification | P0 |
| **Append to description** | `--append` flag to add text to existing description instead of replacing | P1 |
| **Field clearing** | Allow clearing optional fields with `--clear fieldname` | P1 |
| **Bulk update** | Update multiple tickets matching a filter (e.g., `--severity critical --set status=reviewing`) | P1 |
| **Update history** | Track changes in git-like commit history within ticket file | P2 |
| **Audit log** | Separate audit log file tracking who changed what and when | P2 |

### 1.4 Delete Tickets

| Feature | Description | Priority |
|---------|-------------|----------|
| **Soft delete by default** | Move deleted tickets to `.trash/` or mark as `status: deleted` | P0 |
| **Hard delete option** | `--force` flag to permanently remove file and index entry | P0 |
| **Confirmation prompt** | Require confirmation before deletion (skip with `--yes`) | P0 |
| **Cascade delete** | Delete all tickets in a category/repo with `--category X --all` | P1 |
| **Restore deleted** | `vtic restore C1` to recover soft-deleted tickets | P1 |
| **Vacuum trash** | `vtic trash clean --older-than 30d` to purge old soft-deletes | P2 |

### 1.5 Status Transitions

| Feature | Description | Priority |
|---------|-------------|----------|
| **Built-in statuses** | `open`, `in_progress`, `blocked`, `fixed`, `wont_fix`, `closed` | P0 |
| **Custom statuses** | Define additional statuses in `vtic.toml` | P1 |
| **Status workflow** | Define valid transitions (e.g., `closed → reopened` not `wont_fix → fixed`) | P2 |
| **Transition validation** | Reject invalid status transitions with clear error message | P2 |
| **Auto-transitions** | Trigger status changes on events (e.g., merge PR → auto-close linked tickets) | P2 |

### 1.6 Ticket Linking & References

| Feature | Description | Priority |
|---------|-------------|----------|
| **Ticket references** | `--relates-to C2,C3` to link related tickets | P1 |
| **Parent/child tickets** | `--parent C1` for hierarchical ticket relationships | P1 |
| **Blocking relationships** | `--blocked-by C2` to indicate dependencies | P2 |
| **Cross-repo references** | Reference tickets in other repos with `owner/repo#C1` syntax | P2 |
| **Reference resolution** | Auto-resolve and display linked ticket titles on get/list | P2 |

---

## 2. Search Capabilities

### 2.1 BM25 Search (Keyword)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Full-text search** | BM25 search across title, description, and text fields | P0 |
| **Fuzzy matching** | Handle typos and partial matches with configurable fuzziness | P1 |
| **Boost fields** | Weight title higher than description in relevance scoring | P1 |
| **Phrase search** | Exact phrase matching with quotes (e.g., `"CORS wildcard"`) | P1 |
| **Boolean operators** | Support AND, OR, NOT in queries (e.g., `CORS NOT production`) | P2 |
| **Field-specific search** | Search specific fields (e.g., `title:auth description:security`) | P2 |

### 2.2 Semantic Search (Dense Embeddings)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Semantic query** | `--semantic` flag to enable embedding-based search | P0 |
| **Embedding on write** | Auto-embed ticket content on create/update | P0 |
| **Re-embed all** | `vtic reindex` to regenerate embeddings for all tickets | P0 |
| **Embedding caching** | Cache embeddings to avoid re-computing on unchanged tickets | P1 |
| **Chunked embedding** | Split long descriptions into chunks for better semantic coverage | P2 |
| **Multi-vector tickets** | Store multiple embedding vectors per ticket (title, description, code) | P2 |

### 2.3 Hybrid Search

| Feature | Description | Priority |
|---------|-------------|----------|
| **Combined query** | Run BM25 + semantic simultaneously, merge results | P0 |
| **Configurable weights** | Adjust BM25 vs semantic weight (e.g., 0.7 BM25, 0.3 semantic) | P1 |
| **RRF fusion** | Reciprocal Rank Fusion for combining search results | P1 |
| **Score normalization** | Normalize scores from different search methods | P1 |
| **Explain mode** | `--explain` to show BM25 score, semantic score, and final score breakdown | P2 |

### 2.4 Filters & Facets

| Feature | Description | Priority |
|---------|-------------|----------|
| **Equality filters** | `--severity critical`, `--status open`, `--category security` | P0 |
| **Repo glob patterns** | `--repo "ejacklab/*"` to match multiple repos | P0 |
| **Date range filters** | `--created-after 2024-01-01`, `--updated-before 2024-06-01` | P1 |
| **Field existence** | `--has-field fix` to find tickets with non-empty fix field | P1 |
| **Numeric comparison** | `--priority >= 5` for numeric field comparisons | P2 |
| **OR filters** | `--severity high OR critical` for multiple allowed values | P2 |
| **NOT filters** | `--not-status closed` to exclude tickets | P2 |
| **Faceted search** | Return facet counts (e.g., 15 critical, 8 high, 3 medium) with results | P2 |

### 2.5 Sorting & Pagination

| Feature | Description | Priority |
|---------|-------------|----------|
| **Sort by field** | `--sort severity,created` with ascending/descending (`--sort -severity`) | P0 |
| **Sort by relevance** | Default sort by search score when query provided | P0 |
| **Limit/offset** | `--limit 20 --offset 40` for pagination | P0 |
| **Cursor pagination** | Token-based pagination for stable large result sets | P1 |
| **Random sampling** | `--random 10` to get random sample of matching tickets | P2 |

---

## 3. Storage

### 3.1 Markdown Files

| Feature | Description | Priority |
|---------|-------------|----------|
| **Hierarchical directory structure** | `tickets/{owner}/{repo}/{category}/{ticket_id}.md` | P0 |
| **Human-readable format** | Markdown with YAML frontmatter for metadata | P0 |
| **Git compatibility** | All files work seamlessly with git (diff, blame, history) | P0 |
| **Atomic writes** | Write to temp file, then rename to prevent corruption | P0 |
| **File locking** | Prevent concurrent write conflicts | P1 |
| **Custom directory layout** | Configure alternative directory structure in `vtic.toml` | P2 |

### 3.2 Zvec Index

| Feature | Description | Priority |
|---------|-------------|----------|
| **In-process index** | No separate server, Zvec runs in same process | P0 |
| **Persistent storage** | Index persisted to disk, survives restarts | P0 |
| **Index co-location** | Index stored in `.vtic/` within tickets directory | P0 |
| **Rebuild from source** | `vtic reindex` rebuilds index from markdown files | P0 |
| **Incremental indexing** | Only re-index changed tickets on update | P0 |
| **Index health check** | `vtic index status` to verify index integrity | P1 |
| **Index corruption recovery** | Auto-detect corruption and prompt for rebuild | P1 |
| **Multiple indexes** | Support separate indexes per tenant/project | P2 |

### 3.3 Backup & Recovery

| Feature | Description | Priority |
|---------|-------------|----------|
| **Export to archive** | `vtic export --format tar.gz` for full backup | P1 |
| **Import from archive** | `vtic import backup.tar.gz` to restore | P1 |
| **Point-in-time recovery** | Leverage git history for recovery if tickets are versioned | P1 |
| **Index snapshot** | Snapshot index state for fast recovery | P2 |
| **Cloud backup sync** | Sync backups to S3/GCS with `vtic backup --s3 bucket/path` | P2 |

---

## 4. API

### 4.1 REST Endpoints

| Feature | Description | Priority |
|---------|-------------|----------|
| **Create ticket** | `POST /tickets` | P0 |
| **Get ticket** | `GET /tickets/:id` | P0 |
| **Update ticket** | `PATCH /tickets/:id` | P0 |
| **Delete ticket** | `DELETE /tickets/:id` | P0 |
| **List tickets** | `GET /tickets` with query filters | P0 |
| **Search tickets** | `POST /search` for hybrid search | P0 |
| **Bulk create** | `POST /tickets/bulk` for batch creation | P1 |
| **Bulk update** | `PATCH /tickets/bulk` for batch updates | P1 |
| **Bulk delete** | `DELETE /tickets/bulk` for batch deletion | P1 |
| **Get stats** | `GET /stats` for ticket counts by status, severity, category | P1 |
| **Health check** | `GET /health` for monitoring | P0 |
| **OpenAPI spec** | `GET /openapi.json` for API documentation | P1 |

### 4.2 Response Formats

| Feature | Description | Priority |
|---------|-------------|----------|
| **JSON responses** | All API responses in JSON | P0 |
| **Consistent envelope** | `{data: {...}, meta: {...}}` wrapper for all responses | P0 |
| **Error envelope** | `{error: {code, message, details}}` for errors | P0 |
| **Markdown response** | `Accept: text/markdown` to get raw ticket content | P1 |
| **CSV export endpoint** | `GET /tickets?format=csv` for spreadsheet export | P2 |
| **Content negotiation** | Support multiple formats via Accept header | P2 |

### 4.3 Error Handling

| Feature | Description | Priority |
|---------|-------------|----------|
| **HTTP status codes** | Proper status codes (200, 201, 400, 404, 500, etc.) | P0 |
| **Structured error body** | JSON error with code, message, and actionable details | P0 |
| **Validation errors** | Field-level validation errors with field names | P0 |
| **Request ID** | Include `X-Request-ID` in all responses for debugging | P1 |
| **Error reference docs** | Link to error documentation in error response | P2 |
| **Rate limit headers** | `X-RateLimit-Remaining`, `X-RateLimit-Reset` on all responses | P2 |

### 4.4 Pagination

| Feature | Description | Priority |
|---------|-------------|----------|
| **Offset pagination** | `?limit=20&offset=0` for simple pagination | P0 |
| **Cursor pagination** | `?cursor=abc123&limit=20` for stable pagination | P1 |
| **Pagination metadata** | Return `{total, limit, offset, has_more}` in response | P0 |
| **Link headers** | RFC 5988 Link headers for next/prev/first/last | P2 |

---

## 5. CLI

### 5.1 Core Commands

| Feature | Description | Priority |
|---------|-------------|----------|
| **init** | `vtic init [dir]` - Initialize ticket storage and index | P0 |
| **create** | `vtic create [options]` - Create new ticket | P0 |
| **get** | `vtic get <id>` - Display a ticket | P0 |
| **update** | `vtic update <id> [options]` - Update ticket fields | P0 |
| **delete** | `vtic delete <id>` - Delete a ticket | P0 |
| **list** | `vtic list [filters]` - List tickets with filters | P0 |
| **search** | `vtic search <query> [options]` - Hybrid search | P0 |
| **serve** | `vtic serve [options]` - Start HTTP API server | P0 |

### 5.2 Management Commands

| Feature | Description | Priority |
|---------|-------------|----------|
| **reindex** | `vtic reindex` - Rebuild Zvec index from markdown files | P0 |
| **config** | `vtic config show|set|init` - View/edit configuration | P1 |
| **stats** | `vtic stats` - Show ticket statistics | P1 |
| **validate** | `vtic validate` - Check all ticket files for format errors | P1 |
| **doctor** | `vtic doctor` - Diagnose common issues (missing index, bad config) | P1 |
| **trash** | `vtic trash list|restore|clean` - Manage soft-deleted tickets | P1 |
| **backup** | `vtic backup create|restore` - Backup/restore operations | P2 |
| **migrate** | `vtic migrate` - Upgrade ticket format for new versions | P2 |

### 5.3 Bulk Commands

| Feature | Description | Priority |
|---------|-------------|----------|
| **Bulk create** | `vtic create --from tickets.json` for batch import | P1 |
| **Bulk update** | `vtic update --filter "status=open" --set status=reviewing` | P1 |
| **Bulk delete** | `vtic delete --filter "status=wont_fix" --all` | P1 |
| **Export** | `vtic export --format json|csv|markdown` | P1 |
| **Import** | `vtic import tickets.json` with dedup and ID mapping | P1 |

### 5.4 Output Formats

| Feature | Description | Priority |
|---------|-------------|----------|
| **Table output** | Default human-readable table for list/search | P0 |
| **JSON output** | `--format json` for machine-readable output | P0 |
| **Markdown output** | `--format markdown` for documentation export | P1 |
| **YAML output** | `--format yaml` for config-like output | P2 |
| **CSV output** | `--format csv` for spreadsheet import | P1 |
| **Quiet mode** | `-q` to output only IDs or essential data | P1 |
| **Verbose mode** | `-v` for detailed operation logging | P1 |
| **Color control** | `--color auto|always|never` for colorized output | P1 |

### 5.5 Shell Integration

| Feature | Description | Priority |
|---------|-------------|----------|
| **Tab completion** | Bash/Zsh/Fish completion for commands and options | P1 |
| **Completion install** | `vtic completion install` to set up shell completion | P1 |
| **Aliases** | Common shortcuts (e.g., `vtic s` for `vtic search`) | P2 |
| **Interactive mode** | `vtic interactive` for REPL-style interaction | P2 |

---

## 6. Configuration

### 6.1 Configuration Files

| Feature | Description | Priority |
|---------|-------------|----------|
| **Project config** | `./vtic.toml` in working directory | P0 |
| **Global config** | `~/.config/vtic/config.toml` for user-wide defaults | P0 |
| **Config precedence** | Project config overrides global, env vars override all | P0 |
| **Config validation** | Validate config on load with helpful error messages | P0 |
| **Config inheritance** | Allow importing/ extending base configs | P2 |

### 6.2 Environment Variables

| Feature | Description | Priority |
|---------|-------------|----------|
| **Override any config** | `VTIC_TICKETS_DIR`, `VTIC_SEARCH_PROVIDER`, etc. | P0 |
| **API keys** | `OPENAI_API_KEY`, `VTIC_API_KEY` for authentication | P0 |
| **Standard env names** | Follow `VTIC_SECTION_KEY` naming convention | P0 |
| **Env file support** | Load `.env` file automatically | P1 |

### 6.3 Defaults & Profiles

| Feature | Description | Priority |
|---------|-------------|----------|
| **Sensible defaults** | Zero-config works for 80% of use cases | P0 |
| **Configuration profiles** | `vtic --profile work` to switch between config sets | P2 |
| **Default values in config** | Set default repo, category, severity per project | P1 |
| **Required config check** | Fail early with clear message if required config missing | P0 |

---

## 7. Embedding Providers

### 7.1 OpenAI Provider

| Feature | Description | Priority |
|---------|-------------|----------|
| **OpenAI embeddings** | Use OpenAI `text-embedding-3-small` / `text-embedding-3-large` | P0 |
| **API key config** | Read from `OPENAI_API_KEY` env var or config | P0 |
| **Model selection** | Configure which OpenAI embedding model to use | P0 |
| **Dimension config** | Support different embedding dimensions (1536, 3072) | P0 |
| **Rate limit handling** | Respect OpenAI rate limits with automatic retry | P1 |
| **Batch embedding** | Batch multiple tickets per API call for efficiency | P1 |
| **Cost tracking** | Log token usage for cost monitoring | P2 |

### 7.2 Local Provider

| Feature | Description | Priority |
|---------|-------------|----------|
| **Sentence Transformers** | Use `sentence-transformers` for local embeddings | P0 |
| **No API key** | Fully offline, no external dependencies | P0 |
| **Model download** | Auto-download model on first use | P1 |
| **Model caching** | Cache downloaded models in `~/.cache/vtic/` | P1 |
| **GPU acceleration** | Use GPU if available for faster embedding | P2 |
| **Custom local models** | Load custom models from HuggingFace or local path | P2 |

### 7.3 Custom Provider

| Feature | Description | Priority |
|---------|-------------|----------|
| **HTTP endpoint** | Configure custom embedding API endpoint | P1 |
| **Custom auth** | Configure auth headers/tokens for custom provider | P1 |
| **Plugin interface** | Python interface for custom embedding functions | P2 |
| **Request/response mapping** | Configure how to format request and parse response | P2 |

### 7.4 None Provider (BM25 Only)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Zero-config search** | BM25 works without any embedding provider | P0 |
| **Disable semantic** | `enable_semantic = false` to skip embedding entirely | P0 |
| **Clear error on semantic query** | Helpful error if semantic search attempted without provider | P0 |

---

## 8. Multi-Repo Support

### 8.1 Namespacing

| Feature | Description | Priority |
|---------|-------------|----------|
| **Owner/repo structure** | Tickets organized by `{owner}/{repo}/{category}/` | P0 |
| **Repo in ticket metadata** | Every ticket has `repo` field | P0 |
| **Multiple owners** | Support tickets from different orgs/users | P0 |
| **Repo aliases** | Short aliases for common repos (e.g., `od` → `ejacklab/open-dsearch`) | P2 |

### 8.2 Cross-Repo Operations

| Feature | Description | Priority |
|---------|-------------|----------|
| **Glob repo filter** | `--repo "ejacklab/*"` to search across all repos in org | P0 |
| **Multi-repo filter** | `--repo repo1,repo2` to search specific repos | P0 |
| **Cross-repo search** | Single query searches all repos by default | P0 |
| **Per-repo stats** | `vtic stats --by-repo` for breakdown by repository | P1 |
| **Repo isolation** | `vtic --repo-only ejacklab/open-dsearch` to limit operations | P1 |

### 8.3 Multi-Repo Configuration

| Feature | Description | Priority |
|---------|-------------|----------|
| **Repo-specific defaults** | Default category/severity per repo | P1 |
| **Repo-specific embedding** | Different embedding provider per repo | P2 |
| **Included/excluded repos** | Whitelist/blacklist repos in config | P2 |

---

## 9. Integration

### 9.1 Webhooks

| Feature | Description | Priority |
|---------|-------------|----------|
| **On-create webhook** | POST to configured URL when ticket created | P1 |
| **On-update webhook** | POST on ticket update | P1 |
| **On-delete webhook** | POST on ticket deletion | P1 |
| **Webhook payload** | JSON payload with ticket data and event type | P1 |
| **Retry logic** | Retry failed webhooks with exponential backoff | P2 |
| **Webhook signatures** | HMAC signature for payload verification | P2 |

### 9.2 Git Hooks

| Feature | Description | Priority |
|---------|-------------|----------|
| **Pre-commit validation** | Validate ticket format before commit | P2 |
| **Post-commit reindex** | Auto-reindex after commits touching tickets | P2 |
| **Branch-specific tickets** | Separate ticket namespace per git branch | P2 |

### 9.3 CI/CD Integration

| Feature | Description | Priority |
|---------|-------------|----------|
| **CI-friendly CLI** | Exit codes, JSON output for automation | P0 |
| **Docker image** | Official Docker image for vtic | P1 |
| **GitHub Action** | Reusable GitHub Action for ticket operations | P1 |
| **Environment variables** | All config via env vars for containerized environments | P0 |

### 9.4 External Tool Integration

| Feature | Description | Priority |
|---------|-------------|----------|
| **MCP server** | Model Context Protocol server for AI agent integration | P1 |
| **Editor plugins** | VSCode/Neovim extensions for ticket editing | P2 |
| **Slack/Discord bot** | Bot for ticket creation and search from chat | P2 |

---

## 10. Performance

### 10.1 Batch Operations

| Feature | Description | Priority |
|---------|-------------|----------|
| **Bulk create API** | `POST /tickets/bulk` for creating multiple tickets | P1 |
| **Bulk update API** | `PATCH /tickets/bulk` for updating multiple tickets | P1 |
| **Bulk delete API** | `DELETE /tickets/bulk` for deleting multiple tickets | P1 |
| **Batch CLI import** | `vtic import tickets.json` with progress indicator | P1 |
| **Streaming import** | Stream large imports to avoid memory issues | P2 |

### 10.2 Index Optimization

| Feature | Description | Priority |
|---------|-------------|----------|
| **Incremental indexing** | Only index changed tickets | P0 |
| **Parallel embedding** | Concurrent embedding API calls | P1 |
| **Index compaction** | `vtic index compact` to optimize index size | P2 |
| **Background reindex** | Reindex without blocking reads | P2 |
| **Index warming** | Pre-load index on startup for faster first search | P2 |

### 10.3 Caching

| Feature | Description | Priority |
|---------|-------------|----------|
| **Embedding cache** | Cache embeddings to avoid re-computing | P1 |
| **Search result cache** | Cache frequent search queries | P2 |
| **Ticket file cache** | In-memory cache for frequently accessed tickets | P2 |
| **Cache invalidation** | Smart invalidation on ticket update/delete | P2 |

### 10.4 Query Performance

| Feature | Description | Priority |
|---------|-------------|----------|
| **Index-optimized filters** | Push filters down to Zvec for efficiency | P0 |
| **Lazy loading** | Only load ticket content when needed | P1 |
| **Connection pooling** | Reuse connections for embedding API calls | P1 |
| **Query timeout** | Configurable timeout for long-running queries | P1 |

---

## 11. Security

### 11.1 API Authentication

| Feature | Description | Priority |
|---------|-------------|----------|
| **API key auth** | `X-API-Key` header for API authentication | P1 |
| **Bearer token** | `Authorization: Bearer <token>` support | P1 |
| **Multiple keys** | Support multiple API keys with different scopes | P2 |
| **Key rotation** | Graceful key rotation with overlap period | P2 |

### 11.2 Authorization

| Feature | Description | Priority |
|---------|-------------|----------|
| **Read-only keys** | API keys with read-only access | P2 |
| **Repo-level access** | Restrict keys to specific repos | P2 |
| **Operation-level access** | Restrict keys to specific operations (create, read, update) | P2 |

### 11.3 Rate Limiting

| Feature | Description | Priority |
|---------|-------------|----------|
| **Request rate limiting** | Limit requests per API key | P2 |
| **Search rate limiting** | Separate limit for expensive search operations | P2 |
| **Rate limit headers** | `X-RateLimit-*` headers in responses | P2 |
| **Configurable limits** | Adjust limits per deployment | P2 |

### 11.4 Data Security

| Feature | Description | Priority |
|---------|-------------|----------|
| **Input validation** | Strict validation of all inputs | P0 |
| **SQL/injection protection** | Sanitize all queries (even though no SQL) | P0 |
| **Sensitive field handling** | Option to exclude sensitive fields from search | P2 |
| **Encryption at rest** | Encrypt ticket files on disk | P2 |

---

## 12. Export/Import

### 12.1 Export Formats

| Feature | Description | Priority |
|---------|-------------|----------|
| **JSON export** | `vtic export --format json` for full fidelity export | P0 |
| **CSV export** | `vtic export --format csv` for spreadsheet import | P1 |
| **Markdown archive** | `vtic export --format tar.gz` for backup | P1 |
| **Filtered export** | Export only tickets matching filters | P1 |
| **Line-delimited JSON** | `vtic export --format jsonl` for streaming | P2 |

### 12.2 Import Formats

| Feature | Description | Priority |
|---------|-------------|----------|
| **JSON import** | `vtic import tickets.json` | P0 |
| **CSV import** | `vtic import tickets.csv` with column mapping | P1 |
| **Markdown import** | Import existing markdown files | P1 |
| **GitHub Issues import** | Import from GitHub Issues export | P2 |
| **Jira import** | Import from Jira CSV export | P2 |

### 12.3 Bulk Operations

| Feature | Description | Priority |
|---------|-------------|----------|
| **Deduplication** | Detect and skip/handle duplicate imports | P1 |
| **ID preservation** | Option to preserve original IDs on import | P1 |
| **ID mapping export** | Export mapping of old IDs to new IDs | P2 |
| **Rollback on error** | Rollback partial import on failure | P2 |
| **Dry-run import** | `--dry-run` to preview import without writing | P1 |

---

## 13. Accessibility & Developer Experience (DX)

### 13.1 Error Messages

| Feature | Description | Priority |
|---------|-------------|----------|
| **Actionable errors** | Error messages include what to do to fix | P0 |
| **Error codes** | Machine-readable error codes for automation | P0 |
| **Context in errors** | Include relevant context (field name, value, expected) | P0 |
| **Suggestion on typo** | "Did you mean?" suggestions for mistyped commands | P1 |
| **Error documentation links** | Link to docs for detailed error explanations | P2 |

### 13.2 Progress Indicators

| Feature | Description | Priority |
|---------|-------------|----------|
| **Progress for long operations** | Progress bar for reindex, import, bulk operations | P1 |
| **Spinners** | Spinner for indeterminate progress | P1 |
| **Progress to stderr** | Progress on stderr to keep stdout clean | P1 |
| **Silent mode** | `--silent` to disable all progress output | P1 |

### 13.3 JSON Output

| Feature | Description | Priority |
|---------|-------------|----------|
| **Consistent JSON schema** | Predictable JSON structure across all commands | P0 |
| **JSON lines for streaming** | `--format jsonl` for line-delimited output | P1 |
| **Pretty print option** | `--pretty` for human-readable JSON | P1 |
| **Compact JSON** | Default compact output for scripting | P0 |

### 13.4 Help & Documentation

| Feature | Description | Priority |
|---------|-------------|----------|
| **Command help** | `vtic --help`, `vtic create --help` with examples | P0 |
| **Built-in examples** | `vtic examples` to show common usage patterns | P1 |
| **Man pages** | Generate Unix man pages | P2 |
| **Interactive tutorial** | `vtic tutorial` for guided onboarding | P2 |

### 13.5 Debugging

| Feature | Description | Priority |
|---------|-------------|----------|
| **Debug mode** | `--debug` for verbose logging | P0 |
| **Dry-run mode** | `--dry-run` to preview changes | P0 |
| **Explain mode** | `--explain` for search to show scoring | P2 |
| **Timing info** | `--timing` to show operation duration | P2 |

### 13.6 Accessibility

| Feature | Description | Priority |
|---------|-------------|----------|
| **No color mode** | `--no-color` for colorblind-friendly output | P0 |
| **Screen reader friendly** | Clear, semantic output for screen readers | P1 |
| **High contrast mode** | `--high-contrast` for visibility | P2 |

---

## Summary

### P0 (MVP) - Essential Features

- Complete ticket CRUD (create, read, update, delete)
- Basic status workflow (open, fixed, wont_fix, etc.)
- BM25 keyword search
- Semantic search with OpenAI provider
- Hybrid search (BM25 + semantic)
- Filter by repo, severity, status, category
- Markdown file storage with Zvec index
- Core REST API endpoints
- Core CLI commands (init, create, get, update, delete, list, search, serve)
- JSON output format
- Configuration via `vtic.toml` and environment variables
- Error messages with actionable guidance

### P1 (Important) - Production Readiness

- Soft delete and restore
- Bulk operations (create, update, delete)
- Export/Import (JSON, CSV)
- API authentication
- Progress indicators
- Local embedding provider (sentence-transformers)
- Webhooks
- Tab completion
- Date range filters
- Backup/recovery
- Custom embedding providers

### P2 (Nice to Have) - Enhanced Experience

- Ticket linking and dependencies
- Custom status workflows
- Advanced filters (OR, NOT, numeric comparison)
- Rate limiting
- Cache layers
- GitHub Issues / Jira import
- MCP server for AI integration
- Docker image and GitHub Action
- Interactive tutorial

---

*Feature count: ~200 features across 13 categories*

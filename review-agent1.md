# Priority Review: Categories 1-5

**Reviewer:** Agent 1  
**Scope:** Ticket Lifecycle, Search Capabilities, Storage, API, CLI  
**Principle:** Default is DOWN. Only Core if removing it breaks the product.

---

## 1. Ticket Lifecycle

### 1.1 Create Tickets

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| CLI ticket creation | P0 | **Core** | Cannot have a ticket system without creating tickets |
| API ticket creation | P0 | **Must Have** | API is secondary to CLI; v0.1 works with CLI only |
| Auto-generated IDs | P0 | **Core** | Essential for ticket references |
| ID slug from title | P0 | **Must Have** | Nice feature but tickets work with numeric IDs only |
| Timestamp auto-fill | P0 | **Core** | Critical for tracking lifecycle |
| Required field validation | P0 | **Core** | Data integrity is essential |
| Custom ID specification | P1 | **Should Have** | Migration use case, not essential for launch |
| Template-based creation | P2 | **Good to Have** | Convenience feature, can be added later |
| Interactive creation | P2 | **Good to Have** | UX polish, not required |

### 1.2 Read Tickets

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Get by ID | P0 | **Core** | Essential basic operation |
| Get by slug | P1 | **Good to Have** | Alternative access method, not essential |
| Output formats | P0 | **Must Have** | JSON is Core; table/markdown are nice-to-have. Grouping as Must Have |
| Field selection | P1 | **Should Have** | Performance optimization, not essential |
| Raw file output | P1 | **Should Have** | Debugging convenience |
| Related tickets | P2 | **Good to Have** | Advanced feature |

### 1.3 Update Tickets

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Field-level updates | P0 | **Core** | Essential CRUD operation |
| API PATCH endpoint | P0 | **Must Have** | API is secondary; CLI update is Core |
| Automatic timestamp | P0 | **Core** | Essential for audit trail |
| Append to description | P1 | **Should Have** | Convenience, not essential |
| Field clearing | P1 | **Should Have** | Convenience, not essential |
| Bulk update | P1 | **Should Have** | Production efficiency, can ship later |
| Update history | P2 | **Good to Have** | Git already provides history |
| Audit log | P2 | **Good to Have** | Compliance feature, overkill for v1 |

### 1.4 Delete Tickets

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Soft delete by default | P0 | **Must Have** | Safe default, but hard delete is also viable |
| Hard delete option | P0 | **Core** | Need ability to actually remove data |
| Confirmation prompt | P0 | **Must Have** | UX safety, not Core |
| Cascade delete | P1 | **Should Have** | Convenience feature |
| Restore deleted | P1 | **Should Have** | Depends on soft delete; nice to have |
| Vacuum trash | P2 | **Good to Have** | Maintenance utility |

### 1.5 Status Transitions

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Built-in statuses | P0 | **Core** | Essential for ticket lifecycle |
| Custom statuses | P1 | **Should Have** | Flexibility, not required at launch |
| Status workflow | P2 | **Good to Have** | Advanced constraint feature |
| Transition validation | P2 | **Good to Have** | Extra safety layer |
| Auto-transitions | P2 | **Good to Have** | Automation, nice to have |

### 1.6 Ticket Linking & References

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Ticket references | P1 | **Should Have** | Nice for organization, not essential |
| Parent/child tickets | P1 | **Should Have** | Hierarchical support, can ship later |
| Blocking relationships | P2 | **Good to Have** | Advanced dependency tracking |
| Cross-repo references | P2 | **Good to Have** | Multi-repo complexity |
| Reference resolution | P2 | **Good to Have** | Convenience display feature |

---

## 2. Search Capabilities

### 2.1 BM25 Search (Keyword)

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Full-text search | P0 | **Core** | Cannot have a ticket system without search |
| Fuzzy matching | P1 | **Should Have** | Quality improvement, not essential |
| Boost fields | P1 | **Should Have** | Tuning feature |
| Phrase search | P1 | **Should Have** | Quality improvement |
| Boolean operators | P2 | **Good to Have** | Advanced search capability |
| Field-specific search | P2 | **Good to Have** | Advanced search capability |

### 2.2 Semantic Search (Dense Embeddings)

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Semantic query | P0 | **Must Have** | Product works with BM25 alone; semantic is differentiator |
| Embedding on write | P0 | **Must Have** | Required for semantic search to function |
| Re-embed all | P0 | **Must Have** | Essential maintenance operation |
| Embedding caching | P1 | **Should Have** | Performance optimization |
| Chunked embedding | P2 | **Good to Have** | Advanced feature |
| Multi-vector tickets | P2 | **Good to Have** | Advanced feature |

### 2.3 Hybrid Search

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Combined query | P0 | **Must Have** | Key feature, but BM25+semantic separately works |
| Configurable weights | P1 | **Should Have** | Tuning capability |
| RRF fusion | P1 | **Should Have** | Algorithm implementation detail |
| Score normalization | P1 | **Should Have** | Quality feature |
| Explain mode | P2 | **Good to Have** | Debug/analysis feature |

### 2.4 Filters & Facets

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Equality filters | P0 | **Core** | Cannot use ticket system without filtering |
| Repo glob patterns | P0 | **Must Have** | Multi-repo is key feature, but basic repo filter is Core |
| Date range filters | P1 | **Should Have** | Common need, but not essential |
| Field existence | P1 | **Should Have** | Advanced query capability |
| Numeric comparison | P2 | **Good to Have** | Advanced filter |
| OR filters | P2 | **Good to Have** | Advanced filter |
| NOT filters | P2 | **Good to Have** | Advanced filter |
| Faceted search | P2 | **Good to Have** | UI feature |

### 2.5 Sorting & Pagination

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Sort by field | P0 | **Must Have** | Essential for usability, but default sort works |
| Sort by relevance | P0 | **Must Have** | Essential for search UX |
| Limit/offset | P0 | **Core** | Cannot handle large result sets without pagination |
| Cursor pagination | P1 | **Should Have** | Better for large sets, offset works for v1 |
| Random sampling | P2 | **Good to Have** | Niche use case |

---

## 3. Storage

### 3.1 Markdown Files

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Hierarchical directory structure | P0 | **Core** | Fundamental design decision |
| Human-readable format | P0 | **Core** | Fundamental design decision |
| Git compatibility | P0 | **Core** | Fundamental design decision |
| Atomic writes | P0 | **Must Have** | Safety feature, but simple writes work for v0.1 |
| File locking | P1 | **Should Have** | Concurrency safety |
| Custom directory layout | P2 | **Good to Have** | Flexibility option |

### 3.2 Zvec Index

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| In-process index | P0 | **Core** | Fundamental architecture |
| Persistent storage | P0 | **Core** | Essential - index must survive restarts |
| Index co-location | P0 | **Must Have** | Good default, but could be configurable |
| Rebuild from source | P0 | **Core** | Essential recovery operation |
| Incremental indexing | P0 | **Must Have** | Performance, but full rebuild works for v0.1 |
| Index health check | P1 | **Should Have** | Diagnostic tool |
| Index corruption recovery | P1 | **Should Have** | Reliability feature |
| Multiple indexes | P2 | **Good to Have** | Multi-tenancy feature |

### 3.3 Backup & Recovery

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Export to archive | P1 | **Should Have** | Backup strategy, git can suffice initially |
| Import from archive | P1 | **Should Have** | Recovery capability |
| Point-in-time recovery | P1 | **Should Have** | Advanced recovery |
| Index snapshot | P2 | **Good to Have** | Fast recovery optimization |
| Cloud backup sync | P2 | **Good to Have** | Cloud integration |

---

## 4. API

### 4.1 REST Endpoints

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Create ticket (POST /tickets) | P0 | **Must Have** | API is secondary to CLI for v0.1 |
| Get ticket (GET /tickets/:id) | P0 | **Must Have** | Essential API operation |
| Update ticket (PATCH /tickets/:id) | P0 | **Must Have** | Essential API operation |
| Delete ticket (DELETE /tickets/:id) | P0 | **Must Have** | Essential API operation |
| List tickets (GET /tickets) | P0 | **Must Have** | Essential API operation |
| Search tickets (POST /search) | P0 | **Must Have** | Core value prop via API |
| Bulk create | P1 | **Should Have** | Efficiency feature |
| Bulk update | P1 | **Should Have** | Efficiency feature |
| Bulk delete | P1 | **Should Have** | Efficiency feature |
| Get stats | P1 | **Should Have** | Dashboard/reporting feature |
| Health check | P0 | **Must Have** | Operational requirement |
| OpenAPI spec | P1 | **Should Have** | Documentation, can be generated |

### 4.2 Response Formats

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| JSON responses | P0 | **Core** | Standard API requirement |
| Consistent envelope | P0 | **Must Have** | Good practice, but raw JSON works |
| Error envelope | P0 | **Must Have** | Good practice, but simple errors work |
| Markdown response | P1 | **Should Have** | Alternative format |
| CSV export endpoint | P2 | **Good to Have** | Export feature |
| Content negotiation | P2 | **Good to Have** | Advanced API feature |

### 4.3 Error Handling

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| HTTP status codes | P0 | **Core** | Standard HTTP requirement |
| Structured error body | P0 | **Core** | Essential for API usability |
| Validation errors | P0 | **Must Have** | Important for DX, but basic errors work |
| Request ID | P1 | **Should Have** | Debugging aid |
| Error reference docs | P2 | **Good to Have** | Documentation enhancement |
| Rate limit headers | P2 | **Good to Have** | Depends on rate limiting being implemented |

### 4.4 Pagination

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Offset pagination | P0 | **Core** | Essential for any list endpoint |
| Cursor pagination | P1 | **Should Have** | Better for large sets |
| Pagination metadata | P0 | **Must Have** | Essential for clients to navigate |
| Link headers | P2 | **Good to Have** | REST best practice, not required |

---

## 5. CLI

### 5.1 Core Commands

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| init | P0 | **Core** | Cannot use the tool without initialization |
| create | P0 | **Core** | Essential operation |
| get | P0 | **Core** | Essential operation |
| update | P0 | **Core** | Essential operation |
| delete | P0 | **Core** | Essential operation |
| list | P0 | **Core** | Essential operation |
| search | P0 | **Core** | Primary value proposition |
| serve | P0 | **Must Have** | API server is secondary to CLI |

### 5.2 Management Commands

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| reindex | P0 | **Must Have** | Maintenance operation, can be manual initially |
| config | P1 | **Should Have** | Configuration management |
| stats | P1 | **Should Have** | Reporting feature |
| validate | P1 | **Should Have** | Data quality tool |
| doctor | P1 | **Should Have** | Diagnostic tool |
| trash | P1 | **Should Have** | Soft-delete management |
| backup | P2 | **Good to Have** | Backup operations, git can suffice |
| migrate | P2 | **Good to Have** | Version upgrade tool |

### 5.3 Bulk Commands

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Bulk create | P1 | **Should Have** | Efficiency for imports |
| Bulk update | P1 | **Should Have** | Efficiency feature |
| Bulk delete | P1 | **Should Have** | Efficiency feature |
| Export | P1 | **Should Have** | Data portability |
| Import | P1 | **Should Have** | Data portability |

### 5.4 Output Formats

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Table output | P0 | **Core** | Human-readable CLI output is essential |
| JSON output | P0 | **Core** | Machine-readable output is essential |
| Markdown output | P1 | **Should Have** | Alternative format |
| YAML output | P2 | **Good to Have** | Alternative format |
| CSV output | P1 | **Should Have** | Export format |
| Quiet mode | P1 | **Should Have** | Scripting convenience |
| Verbose mode | P1 | **Should Have** | Debugging aid |
| Color control | P1 | **Should Have** | Accessibility/scripting |

### 5.5 Shell Integration

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Tab completion | P1 | **Should Have** | DX improvement |
| Completion install | P1 | **Should Have** | Setup convenience |
| Aliases | P2 | **Good to Have** | Shortcut convenience |
| Interactive mode | P2 | **Good to Have** | REPL experience |

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| **Core** | 26 | Product doesn't exist without these. Ships v0.1. |
| **Must Have** | 36 | Required for production use. Ships before v1.0. |
| **Should Have** | 43 | Important but not blocking. Can ship after v1.0. |
| **Good to Have** | 31 | Nice polish. Backlog. |

### Core Features (26) - v0.1 Ship List
**Ticket Lifecycle:** CLI creation, Auto-generated IDs, Timestamp auto-fill, Required field validation, Get by ID, Field-level updates, Automatic timestamp, Hard delete option, Built-in statuses

**Search:** Full-text search (BM25), Equality filters, Limit/offset pagination

**Storage:** Hierarchical directory structure, Human-readable format, Git compatibility, In-process index, Persistent storage, Rebuild from source

**API:** JSON responses, HTTP status codes, Structured error body, Offset pagination

**CLI:** init, create, get, update, delete, list, search, Table output, JSON output

### Key Downgrades from P0
- **API ticket creation**: P0 → Must Have (CLI is primary interface)
- **Semantic search features**: P0 → Must Have (BM25 alone is viable)
- **Soft delete**: P0 → Must Have (hard delete is also valid)
- **Most API endpoints**: P0 → Must Have (API is secondary to CLI)
- **Confirmation prompt**: P0 → Must Have (UX, not Core)
- **Atomic writes**: P0 → Must Have (safety, but simple writes work)
- **Incremental indexing**: P0 → Must Have (performance, full rebuild works)

### Philosophy Applied
- **Core** = Remove it and the product is broken/useless
- **Must Have** = Need it for production, but product works without it
- **Should Have** = Important for completeness, can ship post-v1.0
- **Good to Have** = Polish, backlog, implement if time permits

The v0.1 MVP should focus on the 26 Core features for a working ticket system with BM25 search. Semantic search, API server, and bulk operations can follow in subsequent releases before v1.0.

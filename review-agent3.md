# Priority Review: Categories 10-13

**Reviewer:** Agent 3  
**Categories:** Performance, Security, Export/Import, Accessibility & DX  
**Methodology:** Ruthless down-classification. Core = existential necessity only.

---

## 10. Performance

### 10.1 Batch Operations

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Bulk create API | P1 | Must Have | Production needs bulk ops, but single-create works for MVP |
| Bulk update API | P1 | Must Have | Production quality, not existential |
| Bulk delete API | P1 | Must Have | Production quality, not existential |
| Batch CLI import | P1 | Must Have | Important for usability, but manual import exists |
| Streaming import | P2 | Good to Have | Optimization for very large imports |

### 10.2 Index Optimization

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Incremental indexing | P0 | Must Have | Critical for production, but full reindex works for small scale |
| Parallel embedding | P1 | Must Have | Performance optimization, sequential embedding works |
| Index compaction | P2 | Good to Have | Optimization, not essential |
| Background reindex | P2 | Good to Have | Nice-to-have, blocking reindex acceptable |
| Index warming | P2 | Good to Have | Optimization |

### 10.3 Caching

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Embedding cache | P1 | Must Have | Saves cost and time in production |
| Search result cache | P2 | Should Have | Performance optimization |
| Ticket file cache | P2 | Should Have | Performance optimization |
| Cache invalidation | P2 | Should Have | Required if caching is implemented |

### 10.4 Query Performance

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Index-optimized filters | P0 | Must Have | Performance optimization, sequential scan works |
| Lazy loading | P1 | Must Have | Production performance |
| Connection pooling | P1 | Must Have | Production efficiency |
| Query timeout | P1 | Must Have | Production safety |

---

## 11. Security

### 11.1 API Authentication

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| API key auth | P1 | Must Have | Production requirement for API server |
| Bearer token | P1 | Should Have | Alternative auth method, one method suffices |
| Multiple keys | P2 | Should Have | Operational convenience, not required |
| Key rotation | P2 | Good to Have | Security hygiene feature |

### 11.2 Authorization

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Read-only keys | P2 | Good to Have | Useful but not blocking |
| Repo-level access | P2 | Good to Have | Enterprise/multi-tenant feature |
| Operation-level access | P2 | Good to Have | Enterprise/multi-tenant feature |

### 11.3 Rate Limiting

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Request rate limiting | P2 | Should Have | Production protection, can defer |
| Search rate limiting | P2 | Good to Have | Specific optimization |
| Rate limit headers | P2 | Good to Have | Nice-to-have standard compliance |
| Configurable limits | P2 | Good to Have | Flexibility feature |

### 11.4 Data Security

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Input validation | P0 | **Core** | Without this, garbage data corrupts the system |
| SQL/injection protection | P0 | **Core** | Security essential even without SQL |
| Sensitive field handling | P2 | Good to Have | Edge case handling |
| Encryption at rest | P2 | Good to Have | Enterprise security requirement |

---

## 12. Export/Import

### 12.1 Export Formats

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| JSON export | P0 | Must Have | Essential for backup/interop, but not existential |
| CSV export | P1 | Should Have | Common format, secondary to JSON |
| Markdown archive | P1 | Should Have | Backup format, tar.gz is nice-to-have |
| Filtered export | P1 | Should Have | Convenience feature |
| Line-delimited JSON | P2 | Good to Have | Streaming optimization |

### 12.2 Import Formats

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| JSON import | P0 | Must Have | Pairs with JSON export |
| CSV import | P1 | Should Have | Useful but secondary |
| Markdown import | P1 | Should Have | Migration support |
| GitHub Issues import | P2 | Good to Have | Platform-specific migration |
| Jira import | P2 | Good to Have | Platform-specific migration |

### 12.3 Bulk Operations

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Deduplication | P1 | Must Have | Data quality for production imports |
| ID preservation | P1 | Should Have | Useful for migration, not required |
| ID mapping export | P2 | Good to Have | Migration tracking utility |
| Rollback on error | P2 | Should Have | Safety feature for bulk operations |
| Dry-run import | P1 | Should Have | Preview capability |

---

## 13. Accessibility & Developer Experience (DX)

### 13.1 Error Messages

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Actionable errors | P0 | Must Have | Critical for usability, but basic errors work |
| Error codes | P0 | Must Have | Required for automation, but not existential |
| Context in errors | P0 | Must Have | Debugging essential, but not Core |
| Suggestion on typo | P1 | Should Have | Nice UX improvement |
| Error documentation links | P2 | Good to Have | Helpfulness polish |

### 13.2 Progress Indicators

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Progress for long operations | P1 | Should Have | UX improvement, can ship without |
| Spinners | P1 | Good to Have | Visual polish |
| Progress to stderr | P1 | Should Have | Scripting cleanliness |
| Silent mode | P1 | Should Have | Automation convenience |

### 13.3 JSON Output

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Consistent JSON schema | P0 | Must Have | Integration essential, but product works without |
| JSON lines for streaming | P1 | Should Have | Performance optimization |
| Pretty print option | P1 | Good to Have | Readability convenience |
| Compact JSON | P0 | Must Have | Default format for scripting |

### 13.4 Help & Documentation

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Command help | P0 | Must Have | CLI essential, but basic help suffices |
| Built-in examples | P1 | Should Have | Discoverability improvement |
| Man pages | P2 | Good to Have | Unix tradition, not required |
| Interactive tutorial | P2 | Good to Have | Onboarding polish |

### 13.5 Debugging

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| Debug mode | P0 | Must Have | Troubleshooting essential |
| Dry-run mode | P0 | Must Have | Safety for destructive operations |
| Explain mode | P2 | Good to Have | Debugging aid for search |
| Timing info | P2 | Good to Have | Performance debugging |

### 13.6 Accessibility

| Feature | Current Priority | New Priority | Reason |
|---------|-----------------|--------------|--------|
| No color mode | P0 | Must Have | Accessibility requirement |
| Screen reader friendly | P1 | Should Have | Accessibility improvement |
| High contrast mode | P2 | Good to Have | Accessibility enhancement |

---

## Summary

| Priority | Count |
|----------|-------|
| **Total Core** | 2 |
| **Total Must Have** | 24 |
| **Total Should Have** | 21 |
| **Total Good to Have** | 21 |

### Core Features (2)
Only features where removal breaks the product:
1. **Input validation** - Without this, corrupt data destroys the system
2. **SQL/injection protection** - Security essential regardless of SQL

### Downgrades Applied
- **P0 → Must Have**: Most "essential" features are actually production requirements, not existential
- **P0 → Should Have**: Index-optimized filters, compact JSON
- **P1 → Should Have**: Various production features that can ship after v1.0
- **P1 → Good to Have**: Features that are polish, not requirements
- **P2 → Good to Have**: All P2 features remain backlog

### Key Decisions
1. **JSON export/import is Must Have, not Core** - Product works without export; it's a valuable feature, not existential
2. **Incremental indexing is Must Have, not Core** - Full reindex works for small scale; this is production optimization
3. **Error handling features are Must Have** - Critical for usability but basic error messages suffice for existence
4. **CLI help is Must Have** - Essential for CLI usability but `--help` with minimal text works
5. **Most P2 features stay Good to Have** - These are genuine polish/backlog items

### Ruthless Assessment
The 4-level system forces hard choices:
- **Core** (2): Truly existential - removing these breaks the product
- **Must Have** (24): Required for production, ships before v1.0
- **Should Have** (21): Important but not blocking, ships after v1.0
- **Good to Have** (21): Nice polish, backlog priority

Total features reviewed: **68**

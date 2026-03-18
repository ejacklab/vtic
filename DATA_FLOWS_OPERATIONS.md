# vtic Data Flow Diagrams - API Operations

> Detailed data flow diagrams for all vtic operations showing exact steps, data formats, error paths, and storage operations.

---

## Diagram Legend

| Color | Meaning | Usage |
|-------|---------|-------|
| 🔵 Blue | Input | HTTP requests, CLI arguments, user input |
| 🟢 Green | Success | Successful responses, completion states |
| 🔴 Red | Error | Error states, failure paths |
| 🟠 Orange | Processing | Validation, generation, transformation |
| 🟣 Purple | Storage I/O | File operations, disk writes |
| 🔷 Cyan | Zvec Operations | Vector database operations |
| ⚪ Gray | Optional/Semantic | Conditional paths, embedding operations |

---

## 1. POST /tickets (Create Ticket)

```mermaid
flowchart TD
    subgraph Input["🔵 Input Layer"]
        A["HTTP POST /tickets<br/>JSON Body:<br/>{title, repo, category,<br/>severity, status,<br/>description, tags, file_refs}"]
    end

    subgraph Validation["🟠 Validation Layer"]
        B["validate_request()<br/>Check required fields"]
        B1{"Missing<br/>title/repo?"}
        B2{"Invalid<br/>severity?"}
        B3{"Repo format<br/>valid?"}
    end

    subgraph Generation["🟠 Generation Layer"]
        C["generate_ticket_id()<br/>Category prefix + number"]
        D["generate_slug()<br/>URL-safe from title"]
        E["auto_fill_timestamps()<br/>created/updated: ISO8601"]
        F{"Duplicate ID<br/>check"}
    end

    subgraph StorageWrite["🟣 Storage Write"]
        G["TicketPathResolver<br/>.ticket_to_path()"]
        H["AtomicFileWriter<br/>1. Write to .tmp<br/>2. fsync<br/>3. rename to .md"]
        I["tickets/{owner}/{repo}/<br/>{category}/{id}.md"]
    end

    subgraph ZvecIndex["🔷 Zvec Index Operations"]
        J["BM25EmbeddingFunction<br/>encode()"]
        K["Sparse Vector<br/>{token_id: weight}"]
        L["collection.add()<br/>with BM25 vector"]
        M{"Semantic<br/>enabled?"}
        N["EmbeddingProvider<br/>generate_embedding()"]
        O["Dense Vector<br/>[float, float, ...]"]
        P["collection.add()<br/>dense vectors"]
    end

    subgraph Response["🟢 Response"]
        Q["HTTP 201 Created<br/>Location: /tickets/{id}<br/>Body: Ticket JSON"]
    end

    subgraph Errors["🔴 Error Responses"]
        E400A["HTTP 400<br/>{error: 'Missing required field: title'}"]
        E400B["HTTP 400<br/>{error: 'Invalid severity: xyz'}"]
        E409["HTTP 409<br/>{error: 'Duplicate ID: C1'}"]
        E500A["HTTP 500<br/>{error: 'File write failed'}"]
        E500B["HTTP 500<br/>{error: 'Index operation failed'}"]
    end

    A --> B
    B --> B1
    B1 -->|"Missing fields"| E400A
    B1 -->|"OK"| B2
    B2 -->|"Invalid value"| E400B
    B2 -->|"OK"| B3
    B3 -->|"Invalid format"| E400A
    B3 -->|"OK"| C
    
    C --> D --> E --> F
    F -->|"Exists"| E409
    F -->|"Unique"| G
    
    G -->|"Path: Path obj"| H
    H -->|"Markdown string"| I
    H -.->|"Write fails"| E500A
    
    I -->|"Ticket dict"| J
    J -->|"Sparse vec"| K
    K -->|"Vector + metadata"| L
    L -.->|"Index error"| E500B
    
    L --> M
    M -->|"No"| Q
    M -->|"Yes"| N
    N -->|"Embedding array"| O
    O -->|"Dense vectors"| P
    P --> Q
```

### Data Formats

| Step | Format | Example |
|------|--------|---------|
| Request Body | JSON | `{"title": "CORS Bug", "repo": "ejacklab/open-dsearch"}` |
| Ticket ID | String | `"C1"`, `"S2"` |
| Slug | String | `"cors-wildcard"` |
| Timestamp | ISO8601 | `"2026-03-17T10:00:00Z"` |
| Markdown File | Frontmatter + MD | `---\nid: C1\n...\n---\n\n## Description` |
| BM25 Vector | Sparse dict | `{1024: 0.85, 2056: 0.72}` |
| Dense Vector | Float array | `[0.023, -0.156, ...]` (1536 dims) |

### Storage Operations

| Operation | Path | Content |
|-----------|------|---------|
| Atomic Write | `tickets/{owner}/{repo}/{category}/{id}.md.tmp` → `{id}.md` | Full markdown with YAML frontmatter (temp+rename) |
| Zvec Insert | `.vtic/zvec_index/collections/tickets` | BM25 sparse vector + metadata |
| Zvec Insert (opt) | `.vtic/zvec_index/collections/tickets` | Dense embedding vector |

---

## 2. GET /tickets/:id (Read Ticket)

```mermaid
flowchart TD
    subgraph Input["🔵 Input"]
        A["HTTP GET /tickets/:id<br/>Path param: {id}"]
    end

    subgraph Validation["🟠 Validation"]
        B["validate_id_format()<br/>Regex: [CFGHST]\d+"]
        B1{"Valid ID<br/>format?"}
    end

    subgraph ZvecFetch["🔷 Zvec Lookup"]
        C["collection.get()<br/>by ID"]
        C1{"Found in<br/>index?"}
    end

    subgraph FileFetch["🟣 File Fallback"]
        D["TicketPathResolver<br/>resolve_path()"]
        E["read_file()<br/>markdown"]
        F["parse_markdown_to_ticket()"]
        F1{"File<br/>exists?"}
    end

    subgraph Response["🟢 Response"]
        G["HTTP 200 OK<br/>Body: Ticket JSON"]
    end

    subgraph Errors["🔴 Errors"]
        E400["HTTP 400<br/>{error: 'Invalid ID format'}"]
        E404["HTTP 404<br/>{error: 'Ticket not found'}"]
    end

    A --> B
    B --> B1
    B1 -->|"Invalid"| E400
    B1 -->|"Valid"| C
    
    C --> C1
    C1 -->|"Yes"| G
    C1 -->|"No"| D
    
    D --> E
    E --> F1
    F1 -->|"No"| E404
    F1 -->|"Yes"| F
    F -->|"Ticket dict"| G
```

### Data Flow Details

| Step | Source | Destination | Data Format |
|------|--------|-------------|-------------|
| Zvec lookup | Index | API | `{id, metadata: {...}}` or `None` |
| File read | Disk | Parser | Raw markdown string |
| Parse | Parser | API | `Ticket` dataclass |
| Response | API | Client | JSON serialized ticket |

### Error Conditions

| Error | Condition | HTTP Status |
|-------|-----------|-------------|
| Invalid ID format | Regex mismatch `[A-Z]\d+` | 400 |
| Not found | Not in Zvec AND no file | 404 |

---

## 3. PATCH /tickets/:id (Update Ticket)

```mermaid
flowchart TD
    subgraph Input["🔵 Input"]
        A["HTTP PATCH /tickets/:id<br/>Path: {id}<br/>Body: {field: value, ...}"]
    end

    subgraph Validation["🟠 Validation"]
        B["validate_id_format()"]
        B1{"Valid ID?"}
        C["get_ticket_by_id()<br/>fetch existing"]
        C1{"Ticket<br/>exists?"}
        D["validate_updates()<br/>Check immutable fields"]
        D1{"Valid<br/>fields?"}
    end

    subgraph Processing["🟠 Processing"]
        E["merge_updates()<br/>existing + new fields"]
        F["auto_fill_timestamps()<br/>update 'updated' only"]
    end

    subgraph Storage["🟣 Storage Operations"]
        G["AtomicFileWriter<br/>1. Write to .tmp<br/>2. fsync<br/>3. rename to .md"]
        H["tickets/.../{id}.md<br/>atomic overwrite"]
    end

    subgraph ZvecUpdate["🔷 Zvec Update"]
        I["collection.upsert()<br/>update metadata"]
        J{"Semantic<br/>enabled AND<br/>text changed?"}
        K["EmbeddingProvider<br/>regenerate embedding"]
        L["collection.upsert()<br/>update dense vectors"]
    end

    subgraph Response["🟢 Response"]
        M["HTTP 200 OK<br/>Body: Updated Ticket JSON"]
    end

    subgraph Errors["🔴 Errors"]
        E400A["HTTP 400<br/>{error: 'Invalid ID format'}"]
        E404["HTTP 404<br/>{error: 'Ticket not found'}"]
        E400B["HTTP 400<br/>{error: 'Cannot update immutable field: id'}"]
        E500["HTTP 500<br/>{error: 'File write failed'}"]
    end

    A --> B
    B --> B1
    B1 -->|"Invalid"| E400A
    B1 -->|"Valid"| C
    C --> C1
    C1 -->|"No"| E404
    C1 -->|"Yes"| D
    D --> D1
    D1 -->|"Invalid"| E400B
    D1 -->|"Valid"| E
    
    E -->|"Merged ticket"| F
    F -->|"Ticket with new ts"| G
    G -->|"Markdown"| H
    G -.->|"Write fails"| E500
    
    H -->|"Ticket dict"| I
    I -->|"Check fields"| J
    J -->|"No change"| M
    J -->|"Changed"| K
    K -->|"New embedding"| L
    L --> M
```

### Immutable Fields (Cannot Update)

| Field | Reason |
|-------|--------|
| `id` | Primary identifier |
| `created` | Audit trail |
| `repo` | Ticket namespace |

### Semantic Re-embedding Triggers

| Field Changed | Re-embed? |
|---------------|-----------|
| `title` | ✅ Yes |
| `description` | ✅ Yes |
| `status` | ❌ No |
| `severity` | ❌ No |
| `tags` | ⚠️ Optional config |

### Storage Operations

| Operation | Type | Path |
|-----------|------|------|
| File write | Atomic overwrite (temp+rename) | `tickets/{owner}/{repo}/{category}/{id}.md` |
| Zvec upsert | Metadata update | Collection `tickets` |
| Zvec upsert (opt) | Dense vector update | Collection `tickets` |

---

## 4. DELETE /tickets/:id (Delete Ticket)

```mermaid
flowchart TD
    subgraph Input["🔵 Input"]
        A["HTTP DELETE /tickets/:id<br/>Path: {id}<br/>Query: ?force={bool}"]
    end

    subgraph Validation["🟠 Validation"]
        B["validate_id_format()"]
        B1{"Valid ID?"}
        C["ticket_exists()"]
        C1{"Ticket<br/>exists?"}
        D{"force=true<br/>param?"}
    end

    subgraph SoftDelete["🟣 Soft Delete Path"]
        E["ensure_trash_dir()<br/>create .trash/ if needed"]
        F["move_to_trash()<br/>preserve content"]
        G[".trash/{id}-{timestamp}.md"]
    end

    subgraph HardDelete["🟣 Hard Delete Path"]
        H["delete_file()<br/>permanent removal"]
    end

    subgraph ZvecDelete["🔷 Zvec Delete"]
        I["collection.delete()<br/>by ID"]
        I1{"Delete<br/>success?"}
    end

    subgraph Response["🟢 Response"]
        J["HTTP 200 OK<br/>Body: {deleted: true, id: 'C1'}"]
    end

    subgraph Errors["🔴 Errors"]
        E400["HTTP 400<br/>{error: 'Invalid ID format'}"]
        E404["HTTP 404<br/>{error: 'Ticket not found'}"]
        E400B["HTTP 400<br/>{error: 'Use ?force=true for hard delete'}"]
        E500["HTTP 500<br/>{error: 'Delete operation failed'}"]
    end

    A --> B
    B --> B1
    B1 -->|"Invalid"| E400
    B1 -->|"Valid"| C
    C --> C1
    C1 -->|"No"| E404
    C1 -->|"Yes"| D
    
    D -->|"false"| E
    D -->|"missing"| E
    D -->|"true"| H
    
    E --> F
    F -->|"Moved path"| G
    H -->|"Deleted"| I
    G --> I
    
    I --> I1
    I1 -.->|"Fails"| E500
    I1 -->|"OK"| J
```

### Delete Modes

| Mode | Parameter | Behavior | Recovery |
|------|-----------|----------|----------|
| Soft delete | (default) | Move to `.trash/` | `vtic restore {id}` |
| Hard delete | `?force=true` | Permanent removal | ❌ None |

### Storage Changes

| Operation | Source | Destination | Notes |
|-----------|--------|-------------|-------|
| Soft delete | `tickets/{o}/{r}/{c}/{id}.md` | `.trash/{id}-{ts}.md` | Timestamped backup |
| Hard delete | `tickets/{o}/{r}/{c}/{id}.md` | ❌ Removed | Irreversible |
| Zvec delete | Collection `tickets` | ❌ Removed | Index entry purged |

---

## 5. POST /search (Search Tickets)

```mermaid
flowchart TD
    subgraph Input["🔵 Input"]
        A["HTTP POST /search<br/>Body: {<br/>  query: string,<br/>  semantic: bool,<br/>  filters: {...},<br/>  limit: int,<br/>  skip: int<br/>}"]
    end

    subgraph Parse["🟠 Parse & Validate"]
        B["parse_search_request()"]
        B1{"Query<br/>valid?"}
        C["build_filter_expression()<br/>filters → Zvec expr"]
    end

    subgraph BM25Search["🔷 BM25 Search"]
        D["BM25EmbeddingFunction<br/>encode(query)"]
        E["Sparse Vector<br/>{token: weight}"]
        F["collection.query()<br/>with BM25 vector + filters"]
    end

    subgraph SemanticPath["⚪ Semantic Search (Optional)"]
        G{"semantic=<br/>true?"}
        H["check_index_initialized()"]
        H1{"Index<br/>ready?"}
        I["EmbeddingProvider<br/>embed_query()"]
        J["Dense Vector<br/>[float, ...]"]
        K["collection.query()<br/>dense vector search"]
    end

    subgraph HybridFusion["🟠 Result Fusion"]
        L{"Both<br/>searches?"}
        M["WeightedReRanker<br/>fuse_results()"]
        N["Reranked<br/>Results"]
        O["Simple rank<br/>BM25 only"]
    end

    subgraph Pagination["🟠 Pagination"]
        P["apply_pagination()<br/>skip + limit"]
        Q["PaginatedResult<br/>{tickets, total, has_more}"]
    end

    subgraph Response["🟢 Response"]
        R["HTTP 200 OK<br/>Body: {results, meta}"]
    end

    subgraph Errors["🔴 Errors"]
        E400["HTTP 400<br/>{error: 'Invalid query syntax'}"]
        E503["HTTP 503<br/>{error: 'Index not initialized'}"]
        E502["HTTP 502<br/>{error: 'Embedding provider error'}"]
    end

    A --> B
    B --> B1
    B1 -.->|"Invalid"| E400
    B1 -->|"Valid"| C
    C --> D
    D --> E
    E --> F
    F -->|"BM25 results"| L
    
    L -->|"No semantic"| O
    L -->|"Semantic requested"| G
    
    G -->|"false"| O
    G -->|"true"| H
    H --> H1
    H1 -.->|"Not ready"| E503
    H1 -->|"Ready"| I
    I -.->|"Provider fails"| E502
    I -->|"Embedding"| J
    J --> K
    
    K -->|"Dense results"| M
    O -->|"BM25 results"| M
    
    M -->|"Fused + scored"| N
    N --> P
    P --> Q
    Q --> R
```

### Search Data Flow

| Component | Input | Output | Purpose |
|-----------|-------|--------|---------|
| BM25 Encoder | Query string | Sparse vector | Keyword matching |
| Dense Encoder | Query string | Dense vector | Semantic matching |
| Zvec Query | Vector + filters | SearchResult[] | Retrieve candidates |
| ReRanker | Multiple result sets | Fused ranking | Combine scores |

### Filter Expression Building

| Filter Type | Example Input | Zvec Expression |
|-------------|---------------|-----------------|
| Equality | `{"severity": "critical"}` | `severity == 'critical'` |
| IN list | `{"status": ["open", "in_progress"]}` | `status in ['open', 'in_progress']` |
| Combined | `{"severity": "high", "repo": "x/y"}` | `severity == 'high' and repo == 'x/y'` |

### Fusion Scoring (WeightedReRanker)

```
final_score = (bm25_weight * bm25_score) + (semantic_weight * semantic_score)

Default weights:
  bm25_weight = 0.7
  semantic_weight = 0.3
```

### Response Format

```json
{
  "results": [
    {
      "id": "C1",
      "score": 0.89,
      "title": "CORS Issue",
      "bm25_score": 0.95,
      "semantic_score": 0.65
    }
  ],
  "meta": {
    "total": 42,
    "returned": 10,
    "skip": 0,
    "has_more": true,
    "query_time_ms": 45
  }
}
```

---

## 6. POST /reindex (Rebuild Index)

```mermaid
flowchart TD
    subgraph Input["🔵 Input"]
        A["HTTP POST /reindex<br/>Body: {} (empty)"]
    end

    subgraph Setup["🟠 Setup"]
        B["scan_markdown_files()<br/>recursive glob **/*.md"]
        C["filter_tickets_only()<br/>exclude .trash/"]
        D{"Tickets<br/>found?"}
    end

    subgraph Clear["🔷 Clear Existing"]
        E["collection.clear()<br/>or delete + recreate"]
    end

    subgraph BatchProcessing["🟠 Batch Processing"]
        F["For each file:<br/>parse_markdown_to_ticket()"]
        G{"Parse<br/>success?"}
        H["BM25EmbeddingFunction<br/>encode(ticket)"]
        I["collect_batch()<br/>accumulate vectors"]
        J{"Batch full<br/>or done?"}
        K["collection.add_batch()<br/>insert to Zvec"]
    end

    subgraph SemanticBatch["⚪ Semantic Embedding (Optional)"]
        L{"semantic<br/>enabled?"}
        M["EmbeddingProvider<br/>embed_batch()"]
        N["collection.add_batch()<br/>dense vectors"]
    end

    subgraph Finalize["🔷 Finalize"]
        O["collection.optimize()<br/>compact index"]
        P["persist_index()<br/>save to disk"]
    end

    subgraph Response["🟢 Response"]
        Q["HTTP 200 OK<br/>Body: {indexed: N, skipped: M, duration_ms: X}"]
    end

    subgraph Errors["🔴 Errors"]
        E200["HTTP 200<br/>{indexed: 0, message: 'No tickets found'}"]
        E500["HTTP 500<br/>{error: 'Zvec operation failed'}"]
        Warn["⚠️ Warning logged<br/>Corrupt file skipped"]
    end

    A --> B
    B --> C --> D
    D -->|"0 files"| E200
    D -->|"N files"| E
    
    E --> F
    F --> G
    G -.->|"Corrupt"| Warn
    Warn --> I
    G -->|"Success"| H
    H --> I
    I --> J
    J -->|"More files"| F
    J -->|"Batch ready"| K
    K --> L
    
    L -->|"No"| O
    L -->|"Yes"| M
    M -->|"Embeddings"| N
    N --> O
    
    O --> P
    P -->|"Stats dict"| Q
    K -.->|"Zvec error"| E500
```

### Batch Processing Details

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Batch size | 100 | Balance memory vs. throughput |
| Parallel parsing | 4 workers | I/O bound operations |
| Retry on fail | 3 attempts | Handle transient errors |

### Index Stats Response

```json
{
  "indexed": 156,
  "skipped": 3,
  "corrupt_files": ["tickets/x/y/z/bad.md"],
  "duration_ms": 2340,
  "bm25_vectors": 156,
  "dense_vectors": 156
}
```

### Storage Operations

| Step | Operation | Target |
|------|-----------|--------|
| Clear | Delete collection | `.vtic/zvec_index/collections/tickets` |
| Add | Batch insert | BM25 sparse vectors + metadata |
| Add (opt) | Batch insert | Dense embedding vectors |
| Optimize | Compact segments | Index storage |
| Persist | fsync | Disk persistence |

---

## 7. vtic init (Initialize)

```mermaid
flowchart TD
    subgraph Input["🔵 Input"]
        A["CLI: vtic init [directory]<br/>Default: ./tickets"]
    end

    subgraph Config["🟠 Configuration"]
        B["read_config()<br/>~/.config/vtic/config.toml<br/>./vtic.toml"]
        C["merge_with_defaults()<br/>apply sensible defaults"]
    end

    subgraph DirectorySetup["🟣 Directory Setup"]
        D["create_tickets_dir()<br/>mkdir -p {dir}"]
        E{"Directory<br/>exists?"}
        F["log_warning()<br/>'Directory already exists'"]
        G["create_vtic_dir()<br/>mkdir -p {dir}/.vtic"]
    end

    subgraph ZvecInit["🔷 Zvec Initialization"]
        H["LocalIndex(str(index_path))"]
        I["define_schema()<br/>id: string PK<br/>title: string<br/>description: text<br/>repo: string<br/>severity: string<br/>status: string<br/>category: string<br/>created: string<br/>updated: string<br/>sparse_vector: BM25<br/>dense_vector: float[]"]
        J["collection = index.create_collection(<br/>  'tickets',<br/>  schema=schema<br/>)"]
        K["create_indexes()<br/>BM25 index<br/>Dense index (if semantic)"]
        L["collection.create_and_open()"]
    end

    subgraph ConfigWrite["🟣 Config Write"]
        M["generate_default_config()<br/>create vtic.toml template"]
        N["write_config_file()<br/>{dir}/vtic.toml"]
    end

    subgraph Response["🟢 Response"]
        O["CLI Output:<br/>✓ Initialized vtic in {dir}<br/>✓ Created .vtic/ index<br/>✓ Wrote vtic.toml"]
    end

    subgraph Errors["🔴 Errors"]
        E500["Exit 1<br/>'Zvec initialization failed'"]
        EPerm["Exit 1<br/>'Permission denied: {dir}'"]
    end

    A --> B --> C --> D
    D --> E
    E -->|"Yes"| F
    E -->|"No"| G
    F --> G
    
    G --> H
    H --> I
    I --> J
    J --> K
    K --> L
    
    L -->|"Success"| M
    L -.->|"Fails"| E500
    G -.->|"No permission"| EPerm
    
    M --> N --> O
```

### Default Directory Structure Created

```
{dir}/
├── tickets/          # Markdown ticket storage
│   └── (empty, ready for tickets)
├── .vtic/            # Hidden vtic metadata
│   ├── zvec_index/   # Zvec vector database
│   │   ├── collections/
│   │   │   └── tickets/
│   │   └── metadata.json
│   └── config.json   # Runtime config cache
└── vtic.toml         # User configuration file
```

### Default vtic.toml Template

```toml
# vtic configuration file
# Generated by vtic init

[tickets]
dir = "./tickets"

[search]
# BM25 is always enabled (zero config)
# Dense embeddings are optional
enable_semantic = false
# embedding_provider = "openai"
# embedding_model = "text-embedding-3-small"
# embedding_dimensions = 1536

[api]
host = "127.0.0.1"
port = 8080
```

### Zvec Schema Definition

| Field | Type | Index | Purpose |
|-------|------|-------|---------|
| `id` | string | Primary Key | Unique identifier |
| `title` | string | Filterable | Ticket title |
| `description` | text | BM25 indexed | Full-text search |
| `repo` | string | Filterable | Namespace |
| `severity` | string | Filterable | Critical/High/Medium/Low |
| `status` | string | Filterable | Open/Fixed/etc |
| `category` | string | Filterable | Code/Security/etc |
| `sparse_vector` | BM25 | Vector index | Keyword search |
| `dense_vector` | float[] | Vector index | Semantic search |

---

## Summary: Storage Operations by Endpoint

| Endpoint | Markdown File | Zvec BM25 | Zvec Dense | Notes |
|----------|---------------|-----------|------------|-------|
| `POST /tickets` | ✅ Create (atomic) | ✅ Insert | ✅ Insert (opt) | Temp file + rename |
| `GET /tickets/:id` | ✅ Read (fallback) | ✅ Read | ❌ | Cache-first |
| `PATCH /tickets/:id` | ✅ Update (atomic) | ✅ Upsert | ✅ Upsert (opt) | Re-embed if text changes |
| `DELETE /tickets/:id` | ✅ Move/Delete | ✅ Delete | ✅ Delete | Soft or hard delete |
| `POST /search` | ❌ | ✅ Query | ✅ Query (opt) | BM25 always, dense optional |
| `POST /reindex` | ✅ Scan source | ✅ Recreate | ✅ Recreate (opt) | Full rebuild |
| `vtic init` | ✅ Create dir | ✅ Create collection | ✅ Create index | One-time setup |

---

## Error Code Reference

| Code | Endpoint | Condition |
|------|----------|-----------|
| `400` | All | Invalid input, missing required fields |
| `404` | GET/PATCH/DELETE | Ticket ID not found |
| `409` | POST | Duplicate ticket ID |
| `500` | All | Internal server error, file system errors |
| `502` | POST /search | Embedding provider unavailable |
| `503` | POST /search | Zvec index not initialized |

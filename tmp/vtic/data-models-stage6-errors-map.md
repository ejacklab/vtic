# Stage 6: Error Catalog & Module Map

Complete error definitions and module structure for vtic.

---

## 1. Error Catalog

### 1.1 Error Codes (from OpenAPI Spec)

The vtic API uses exactly 6 error codes, each mapped to an HTTP status:

| Error Code | HTTP Status | When Used |
|------------|-------------|-----------|
| `VALIDATION_ERROR` | 400 | Invalid request body, missing fields, invalid enum values |
| `NOT_FOUND` | 404 | Ticket, resource, or endpoint not found |
| `CONFLICT` | 409 | Duplicate ID, invalid state transition |
| `PAYLOAD_TOO_LARGE` | 413 | Request body exceeds size limit |
| `INTERNAL_ERROR` | 500 | Unexpected server error, index failure |
| `SERVICE_UNAVAILABLE` | 503 | Semantic search requested but no embedding provider |

### 1.2 ErrorResponse Schema (from OpenAPI)

```python
# src/vtic/errors.py
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Individual validation error detail.
    
    Attributes:
        field: The field that failed validation (optional).
        message: Human-readable error message.
        value: The invalid value that was provided (optional).
    """
    field: Optional[str] = None
    message: str
    value: Optional[str] = None


class ErrorObject(BaseModel):
    """Error object nested within ErrorResponse.
    
    Attributes:
        code: Machine-readable error code (e.g., VALIDATION_ERROR, NOT_FOUND).
        message: Human-readable error description.
        details: Optional list of specific validation errors.
        docs: Optional link to error documentation.
    """
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="List of specific validation errors"
    )
    docs: Optional[str] = Field(
        default=None,
        description="Link to error documentation"
    )


class ErrorResponse(BaseModel):
    """Error envelope for all error responses.
    
    This is the canonical error response structure from the OpenAPI spec.
    All API errors return this format.
    
    Example:
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Query string cannot be empty",
                "details": [
                    {"field": "query", "message": "Required field is missing or empty"}
                ]
            }
        }
    """
    error: ErrorObject
    meta: Optional[dict] = Field(
        default=None,
        description="Optional metadata like request_id"
    )
```

### 1.3 VticError Base Class

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class VticError(Exception):
    """Base error class for all vtic exceptions.
    
    All vtic errors have:
    - code: Machine-readable error code (one of 6 codes from OpenAPI)
    - status: HTTP status code
    - message: Human-readable error message
    - details: List of ErrorDetail objects (optional)
    - docs: Link to documentation (optional)
    """
    
    code: str = "INTERNAL_ERROR"
    status: int = 500
    message: str = "An unexpected error occurred"
    details: Optional[List[Dict[str, Any]]] = field(default=None)
    docs: Optional[str] = field(default=None)
    
    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        docs: Optional[str] = None,
        **kwargs
    ):
        """Initialize error with optional details and docs."""
        if message:
            self.message = message
        if details:
            self.details = details
        if docs:
            self.docs = docs
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        super().__init__(self.message)
    
    def to_response(self) -> Dict[str, Any]:
        """Convert error to ErrorResponse dictionary for JSON serialization.
        
        Returns:
            Dict matching ErrorResponse schema.
        """
        error_obj = {
            "code": self.code,
            "message": self.message,
        }
        
        if self.details:
            error_obj["details"] = self.details
        
        if self.docs:
            error_obj["docs"] = self.docs
        
        return {"error": error_obj}
    
    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.details:
            parts.append(f"details: {self.details}")
        return " ".join(parts)


# Specific error classes by code

class ValidationError(VticError):
    """Validation failure - missing or invalid fields."""
    code: str = "VALIDATION_ERROR"
    status: int = 400


class NotFoundError(VticError):
    """Resource not found."""
    code: str = "NOT_FOUND"
    status: int = 404


class ConflictError(VticError):
    """Conflict - duplicate or invalid state."""
    code: str = "CONFLICT"
    status: int = 409


class PayloadTooLargeError(VticError):
    """Request payload exceeds size limit."""
    code: str = "PAYLOAD_TOO_LARGE"
    status: int = 413


class InternalError(VticError):
    """Unexpected internal error."""
    code: str = "INTERNAL_ERROR"
    status: int = 500


class ServiceUnavailableError(VticError):
    """Service temporarily unavailable."""
    code: str = "SERVICE_UNAVAILABLE"
    status: int = 503
```

### 1.4 Error Factory Functions

```python
def ticket_not_found(ticket_id: str) -> NotFoundError:
    """Create a NOT_FOUND error for missing ticket."""
    return NotFoundError(
        message=f"Ticket '{ticket_id}' not found",
        details=[{"field": "ticket_id", "message": "No ticket exists with this ID"}]
    )


def validation_failed(field: str, message: str, value: Any = None) -> ValidationError:
    """Create a VALIDATION_ERROR for field validation failures."""
    detail = {"field": field, "message": message}
    if value is not None:
        detail["value"] = str(value)
    return ValidationError(
        message=f"Validation failed: {message}",
        details=[detail]
    )


def duplicate_ticket(ticket_id: str) -> ConflictError:
    """Create a CONFLICT error for duplicate ticket ID."""
    return ConflictError(
        message=f"Ticket '{ticket_id}' already exists",
        details=[{"field": "id", "message": "A ticket with this ID already exists"}]
    )


def semantic_search_unavailable() -> ServiceUnavailableError:
    """Create a SERVICE_UNAVAILABLE error for missing embedding provider."""
    return ServiceUnavailableError(
        message="Semantic search requested but no embedding provider is configured",
        details=[
            {"field": "semantic", "message": "Set 'semantic: false' or configure an embedding provider"}
        ],
        docs="https://vtic.ejai.ai/docs/semantic-search"
    )


def payload_too_large(max_size: int, actual_size: int) -> PayloadTooLargeError:
    """Create a PAYLOAD_TOO_LARGE error."""
    return PayloadTooLargeError(
        message=f"Request body too large: {actual_size} bytes (max: {max_size})",
        details=[{"field": "body", "message": f"Maximum allowed size is {max_size} bytes"}]
    )


def index_error(detail: str) -> InternalError:
    """Create an INTERNAL_ERROR for index failures."""
    return InternalError(
        message=f"Search index error: {detail}",
        details=[{"message": detail}]
    )
```

---

## 2. Module Map

Exact file structure with what lives where:

```
src/vtic/
├── __init__.py          # version, public API
├── models/
│   ├── __init__.py      # re-exports
│   ├── enums.py         # all enums (Stage 1)
│   ├── ticket.py        # Ticket, TicketCreate, TicketUpdate, TicketResponse (Stage 2)
│   ├── search.py        # SearchQuery, FilterSet, SearchHit, SearchResult (Stage 3)
│   ├── api.py           # TicketListResponse, ErrorResponse, HealthResponse, StatsResponse (Stage 4)
│   └── config.py        # Config, load_config (Stage 5)
├── errors.py            # VticError, error codes, factory functions (Stage 6)
├── store/
│   ├── __init__.py
│   ├── markdown.py      # ticket_to_markdown, markdown_to_ticket, file I/O
│   └── paths.py         # ticket_file_path, resolve_path
├── index/
│   ├── __init__.py
│   ├── schema.py        # Zvec schema definition
│   ├── client.py        # open/create/destroy/optimize collection
│   └── operations.py    # insert, upsert, update, delete, fetch, query
├── search/
│   ├── __init__.py
│   ├── bm25.py          # BM25 embedding + search
│   ├── semantic.py      # dense embedding + search
│   ├── hybrid.py        # WeightedReRanker, combined search
│   └── engine.py        # search orchestrator
├── embeddings/
│   ├── __init__.py
│   ├── base.py          # EmbeddingProvider interface
│   ├── openai.py        # OpenAI provider
│   └── local.py         # sentence-transformers provider
├── api/
│   ├── __init__.py
│   ├── app.py           # FastAPI application, lifespan
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tickets.py   # CRUD endpoints
│   │   ├── search.py    # search endpoint
│   │   └── system.py    # health, stats, reindex
│   └── deps.py          # FastAPI dependencies (get_config, get_index)
├── cli/
│   ├── __init__.py
│   └── main.py          # Typer CLI commands
└── __main__.py          # python -m vtic
```

### Public API by Module

#### `src/vtic/__init__.py`
```python
__version__: str = "0.1.0"
# Re-exports all models and VticError
```

#### `src/vtic/models/enums.py`
```python
class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    
    @property
    def weight(self) -> int
    @classmethod
    def values(cls) -> list[str]

class Status(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    CLOSED = "closed"
    
    @classmethod
    def values(cls) -> list[str]
    @property
    def is_terminal(self) -> bool
    @property
    def display_name(self) -> str
    def can_transition_to(self, target: "Status") -> bool

class Category(str, Enum):
    CRASH = "crash"           # Prefix: C
    HOTFIX = "hotfix"         # Prefix: H
    FEATURE = "feature"       # Prefix: F
    SECURITY = "security"     # Prefix: S
    GENERAL = "general"       # Prefix: G
    
    @classmethod
    def values(cls) -> list[str]
    @classmethod
    def get_prefix(cls, category: "Category | str") -> str
```

#### `src/vtic/models/ticket.py`
```python
class Ticket(BaseModel):
    """Full ticket representation."""
    id: str
    slug: str | None = None
    title: str
    description: str
    repo: str
    category: Category
    severity: Severity
    status: Status
    assignee: str | None = None
    fix: str | None = None
    tags: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    created: datetime
    updated: datetime
    
    def update_timestamp(self) -> None
    def is_terminal(self) -> bool
    @property
    def id_prefix(self) -> str

class TicketCreate(BaseModel):
    """Request body for creating a new ticket."""
    title: str
    description: str
    repo: str | None = None
    category: Category | None = None
    severity: Severity | None = None
    status: Status | None = None
    assignee: str | None = None
    fix: str | None = None
    tags: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    
    def apply_defaults(self, default_repo: str | None = None) -> "TicketCreateWithDefaults"

class TicketCreateWithDefaults(BaseModel):
    """TicketCreate with defaults applied."""
    title: str
    description: str
    repo: str
    category: Category
    severity: Severity
    status: Status
    assignee: str | None = None
    fix: str | None = None
    tags: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

class TicketUpdate(BaseModel):
    """Partial update — only include fields to change."""
    title: str | None = None
    description: str | None = None
    description_append: str | None = None
    category: Category | None = None
    severity: Severity | None = None
    status: Status | None = None
    assignee: str | None = None
    fix: str | None = None
    tags: list[str] | None = None
    references: list[str] | None = None
    
    def get_updates(self) -> dict[str, Any]

class TicketResponse(BaseModel):
    """Success envelope for single ticket operations."""
    data: Ticket
    meta: dict | None = None
    
    @classmethod
    def from_ticket(cls, ticket: Ticket) -> "TicketResponse"

class TicketSummary(BaseModel):
    """Lightweight ticket for list responses."""
    id: str
    title: str
    severity: Severity
    status: Status
    repo: str
    category: Category
    assignee: str | None = None
    created: datetime
    updated: datetime | None = None

class TicketListResponse(BaseModel):
    """Paginated list of tickets."""
    data: list[TicketSummary]
    meta: PaginationMeta
```

#### `src/vtic/models/search.py`
```python
class FilterSet(BaseModel):
    """Query filters applied post-search."""
    severity: list[Severity] | None = None
    status: list[Status] | None = None
    category: list[Category] | None = None
    repo: list[str] | None = None
    assignee: str | None = None
    tags: list[str] | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None
    
    def to_zvec_filter(self) -> str | None
    def is_empty(self) -> bool

class SearchQuery(BaseModel):
    """Search request with hybrid BM25 + semantic options."""
    query: str
    semantic: bool = False
    filters: FilterSet | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort: str = "-score"
    min_score: float | None = Field(default=0.0, ge=0.0, le=1.0)
    
    def is_semantic_enabled(self) -> bool

class SearchHit(BaseModel):
    """A single search result."""
    ticket_id: str
    score: float = Field(ge=0.0)
    source: Literal["bm25", "semantic", "hybrid"]
    bm25_score: float | None = None
    semantic_score: float | None = None
    highlight: str | None = None
    
    def is_hybrid_match(self) -> bool
    def is_high_confidence(self, threshold: float = 0.8) -> bool

class SearchResult(BaseModel):
    """Search response with hits and metadata."""
    query: str
    hits: list[SearchHit]
    total: int
    meta: SearchMeta | None = None
    
    def has_results(self) -> bool
    def get_hybrid_matches(self) -> list[SearchHit]

class SearchMeta(BaseModel):
    """Search metadata."""
    bm25_weight: float | None = None
    semantic_weight: float | None = None
    latency_ms: int | None = None
    semantic_used: bool | None = None
    request_id: str | None = None
```

#### `src/vtic/models/api.py`
```python
class ErrorDetail(BaseModel):
    """Individual validation error detail."""
    field: str | None = None
    message: str
    value: str | None = None

class ErrorObject(BaseModel):
    """Error object nested within ErrorResponse."""
    code: str
    message: str
    details: list[ErrorDetail] | None = None
    docs: str | None = None

class ErrorResponse(BaseModel):
    """Error envelope for all error responses."""
    error: ErrorObject
    meta: dict | None = None
    
    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: list[ErrorDetail] | None = None,
        docs: str | None = None
    ) -> "ErrorResponse"

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int
    limit: int
    offset: int
    has_more: bool
    request_id: str | None = None

class ReindexResult(BaseModel):
    """Result of a reindex operation."""
    processed: int
    skipped: int
    failed: int
    duration_ms: int
    errors: list[dict] = Field(default_factory=list)
    request_id: str | None = None

class StatsResponse(BaseModel):
    """Ticket statistics."""
    totals: dict
    by_status: dict
    by_severity: dict
    by_category: dict
    by_repo: dict | None = None
    date_range: dict | None = None
    request_id: str | None = None

class HealthResponse(BaseModel):
    """System health status."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    uptime_seconds: int | None = None
    index_status: dict
    embedding_provider: dict | None = None
    request_id: str | None = None

class DoctorResult(BaseModel):
    """Diagnostic check results."""
    overall: Literal["ok", "warnings", "errors"]
    checks: list[dict]
    request_id: str | None = None

class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    total: int
    succeeded: int
    failed: int
    results: list[dict] | None = None
    request_id: str | None = None
```

#### `src/vtic/models/config.py`
```python
class StorageConfig(BaseModel):
    dir: Path = Field(default=Path("./tickets"))

class ApiConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=8080, ge=1, le=65535)

class SearchConfig(BaseModel):
    bm25_enabled: bool = Field(default=True)
    semantic_enabled: bool = Field(default=False)
    bm25_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.4, ge=0.0, le=1.0)

class EmbeddingsConfig(BaseModel):
    provider: Literal["local", "openai", "custom", "none"] = Field(default="local")
    model: str | None = Field(default=None)
    dimension: int | None = Field(default=None, gt=0)

class Config(BaseModel):
    storage: StorageConfig = Field(default_factory=StorageConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)

class ConfigResponse(BaseModel):
    """Current configuration response from /config endpoint."""
    storage: StorageConfig
    search: SearchConfig
    embeddings: EmbeddingsConfig
    api: ApiConfig
    request_id: str | None = None

def load_config(path: Path | None = None) -> Config
def load_and_validate_config(path: Path | None = None) -> Config
def get_openai_api_key() -> str | None
```

#### `src/vtic/errors.py`
```python
# Error codes (exactly 6 from OpenAPI)
VALIDATION_ERROR = "VALIDATION_ERROR"      # 400
NOT_FOUND = "NOT_FOUND"                    # 404
CONFLICT = "CONFLICT"                      # 409
PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"    # 413
INTERNAL_ERROR = "INTERNAL_ERROR"          # 500
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"  # 503

@dataclass
class VticError(Exception):
    code: str
    status: int
    message: str
    details: list[dict] | None
    docs: str | None
    
    def __init__(self, message=None, details=None, docs=None, **kwargs)
    def to_response(self) -> dict
    def __str__(self) -> str

# Error classes by code
class ValidationError(VticError):          # code="VALIDATION_ERROR", status=400
class NotFoundError(VticError):            # code="NOT_FOUND", status=404
class ConflictError(VticError):            # code="CONFLICT", status=409
class PayloadTooLargeError(VticError):     # code="PAYLOAD_TOO_LARGE", status=413
class InternalError(VticError):            # code="INTERNAL_ERROR", status=500
class ServiceUnavailableError(VticError):  # code="SERVICE_UNAVAILABLE", status=503

# Error factory functions
def ticket_not_found(ticket_id: str) -> NotFoundError
def validation_failed(field: str, message: str, value: Any = None) -> ValidationError
def duplicate_ticket(ticket_id: str) -> ConflictError
def semantic_search_unavailable() -> ServiceUnavailableError
def payload_too_large(max_size: int, actual_size: int) -> PayloadTooLargeError
def index_error(detail: str) -> InternalError
```

#### `src/vtic/store/paths.py`
```python
def ticket_file_path(
    ticket_id: str,
    repo: str,
    category: str,
    base_dir: Path
) -> Path

def resolve_path(path: Path) -> Path
def extract_ticket_info(path: Path) -> dict

class TicketPathResolver:
    def __init__(self, base_dir: Path)
    def ticket_to_path(self, ticket_id: str, repo: str, category: str) -> Path
    def path_to_ticket_info(self, path: Path) -> dict
    def ensure_ticket_dir(self, repo: str, category: str) -> Path
```

#### `src/vtic/store/markdown.py`
```python
def ticket_to_markdown(ticket: Ticket) -> str
def markdown_to_ticket(content: str) -> Ticket
def atomic_write(path: Path, content: str) -> None
def read_ticket_file(path: Path) -> Ticket
def write_ticket_file(path: Path, ticket: Ticket) -> None
```

#### `src/vtic/index/schema.py`
```python
TICKET_SCHEMA: dict
def get_ticket_schema() -> dict
```

#### `src/vtic/index/client.py`
```python
class TicketIndex:
    def __init__(self, index_dir: Path)
    def initialize(self) -> None
    def is_initialized(self) -> bool
    def get_collection(self) -> Collection
    def destroy(self) -> None
    def optimize(self) -> None
```

#### `src/vtic/index/operations.py`
```python
def insert_ticket(collection: Collection, ticket: Ticket) -> None
def upsert_ticket(collection: Collection, ticket: Ticket) -> None
def update_ticket(collection: Collection, ticket_id: str, updates: dict) -> None
def delete_ticket(collection: Collection, ticket_id: str) -> None
def fetch_ticket(collection: Collection, ticket_id: str) -> dict | None
def query_tickets(collection: Collection, filter_expr: str, limit: int = 100) -> list[dict]
```

#### `src/vtic/search/bm25.py`
```python
def bm25_search(
    query: str,
    collection: Collection,
    limit: int = 20,
    filters: FilterSet | None = None
) -> list[SearchHit]
```

#### `src/vtic/search/semantic.py`
```python
def semantic_search(
    query: str,
    collection: Collection,
    provider: EmbeddingProvider,
    limit: int = 20,
    filters: FilterSet | None = None
) -> list[SearchHit]
```

#### `src/vtic/search/hybrid.py`
```python
class WeightedReRanker:
    def __init__(self, bm25_weight: float = 0.6, semantic_weight: float = 0.4)
    def rerank(
        bm25_results: list[SearchHit],
        semantic_results: list[SearchHit]
    ) -> list[SearchHit]

def combine_scores(bm25_score: float, semantic_score: float, bm25_weight: float, semantic_weight: float) -> float
```

#### `src/vtic/search/engine.py`
```python
class SearchEngine:
    def __init__(
        self,
        index: TicketIndex,
        provider: EmbeddingProvider | None = None
    )
    def search(self, request: SearchQuery) -> SearchResult
    def reindex_all(self) -> ReindexResult
```

#### `src/vtic/embeddings/base.py`
```python
class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]
    def embed_batch(self, texts: list[str]) -> list[list[float]]
    def dimension(self) -> int
```

#### `src/vtic/embeddings/openai.py`
```python
class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small")
    def embed(self, text: str) -> list[float]
    def embed_batch(self, texts: list[str]) -> list[list[float]]
    def dimension(self) -> int
```

#### `src/vtic/embeddings/local.py`
```python
class LocalProvider:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2")
    def embed(self, text: str) -> list[float]
    def embed_batch(self, texts: list[str]) -> list[list[float]]
    def dimension(self) -> int
```

#### `src/vtic/api/app.py`
```python
def create_app(config: Config) -> FastAPI
def lifespan(app: FastAPI) -> AsyncContextManager
```

#### `src/vtic/api/deps.py`
```python
def get_config() -> Config
def get_index() -> TicketIndex
def get_search_engine() -> SearchEngine
```

#### `src/vtic/api/routes/tickets.py`
```python
router = APIRouter()

@router.post("/tickets", response_model=TicketResponse, status_code=201)
async def create_ticket(data: TicketCreate, config: Config = Depends(get_config)) -> TicketResponse

@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str) -> TicketResponse

@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: str, data: TicketUpdate) -> TicketResponse

@router.delete("/tickets/{ticket_id}", status_code=204)
async def delete_ticket(ticket_id: str) -> None

@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="-created"),
    severity: list[Severity] | None = Query(default=None),
    status: list[Status] | None = Query(default=None),
    category: list[Category] | None = Query(default=None),
    repo: list[str] | None = Query(default=None)
) -> TicketListResponse
```

#### `src/vtic/api/routes/search.py`
```python
router = APIRouter()

@router.post("/search", response_model=SearchResult)
async def search(
    request: SearchQuery,
    engine: SearchEngine = Depends(get_search_engine)
) -> SearchResult
```

#### `src/vtic/api/routes/system.py`
```python
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse

@router.get("/stats", response_model=StatsResponse)
async def stats(by_repo: bool = False) -> StatsResponse

@router.post("/reindex", response_model=ReindexResult)
async def reindex(
    ticket_id: str | None = None,
    force: bool = False,
    provider: str | None = None
) -> ReindexResult

@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse

@router.patch("/config", response_model=ConfigResponse)
async def update_config(config: ConfigResponse) -> ConfigResponse
```

#### `src/vtic/cli/main.py`
```python
app = typer.Typer()

@app.command()
def init(dir: Path = Path(".")) -> None

@app.command()
def create(
    title: str,
    repo: str,
    description: str | None = None,
    category: Category = Category.GENERAL,
    severity: Severity = Severity.MEDIUM,
    status: Status = Status.OPEN,
    tags: list[str] = []
) -> None

@app.command()
def get(ticket_id: str, format: str = "table") -> None

@app.command()
def update(
    ticket_id: str,
    title: str | None = None,
    description: str | None = None,
    status: Status | None = None,
    severity: Severity | None = None
) -> None

@app.command()
def delete(ticket_id: str, force: bool = False, yes: bool = False) -> None

@app.command()
def list(
    repo: str | None = None,
    status: Status | None = None,
    severity: Severity | None = None,
    limit: int = 20
) -> None

@app.command()
def search(
    query: str,
    limit: int = 20,
    semantic: bool = False,
    filters: str | None = None
) -> None

@app.command()
def serve(
    host: str = "localhost",
    port: int = 8080,
    reload: bool = False
) -> None

@app.command()
def reindex(ticket_id: str | None = None, force: bool = False) -> None
```

#### `src/vtic/__main__.py`
```python
from vtic.cli.main import app

if __name__ == "__main__":
    app()
```

---

## 3. Field Name Mappings

### 3.1 Search Fields

| Old Name | OpenAPI Name | Notes |
|----------|--------------|-------|
| `topk` | `limit` | Maximum results to return |
| `match_type` | `source` | "bm25", "semantic", or "hybrid" |
| `ticket` | `ticket_id` | String ID reference in SearchHit |

### 3.2 Reindex Fields

| Old Name | OpenAPI Name | Notes |
|----------|--------------|-------|
| `indexed` | `processed` | Successfully processed tickets |
| `errors` | `failed` | Failed to process |
| `took_ms` | `duration_ms` | Total duration in milliseconds |

### 3.3 Timestamp Fields

| Old Name | OpenAPI Name | Notes |
|----------|--------------|-------|
| `created_at` | `created` | ISO 8601 datetime |
| `updated_at` | `updated` | ISO 8601 datetime |

### 3.4 Config Fields

| Old Name | OpenAPI Name | Notes |
|----------|--------------|-------|
| `tickets.dir` | `storage.dir` | Storage directory |
| `config.server.port` | `config.api.port` | API server port |
| `enable_semantic` | `semantic_enabled` | Semantic search toggle |
| `hybrid_weights_bm25` | `bm25_weight` | BM25 fusion weight |
| `hybrid_weights_semantic` | `semantic_weight` | Semantic fusion weight |

---

## 4. Error Response Examples

### 4.1 Validation Error (400)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Query string cannot be empty",
    "details": [
      {
        "field": "query",
        "message": "Required field is missing or empty"
      }
    ]
  }
}
```

### 4.2 Not Found (404)

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Ticket 'C999' not found",
    "details": [
      {
        "field": "ticket_id",
        "message": "No ticket exists with this ID"
      }
    ]
  }
}
```

### 4.3 Conflict (409)

```json
{
  "error": {
    "code": "CONFLICT",
    "message": "Ticket 'C1' already exists",
    "details": [
      {
        "field": "id",
        "message": "A ticket with this ID already exists"
      }
    ]
  }
}
```

### 4.4 Service Unavailable (503)

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Semantic search requested but no embedding provider is configured",
    "details": [
      {
        "field": "semantic",
        "message": "Set 'semantic: false' or configure an embedding provider"
      }
    ],
    "docs": "https://vtic.ejai.ai/docs/semantic-search"
  }
}
```

---

## 5. Summary

| Category | Count | Values |
|----------|-------|--------|
| Error Codes | 6 | VALIDATION_ERROR, NOT_FOUND, CONFLICT, PAYLOAD_TOO_LARGE, INTERNAL_ERROR, SERVICE_UNAVAILABLE |
| Enums | 3 | Severity (5), Status (6), Category (5) |
| Core Models | 4 | Ticket, SearchQuery, SearchHit, SearchResult |
| Config Sections | 4 | storage, api, search, embeddings |
| API Routes | ~20 | /tickets, /search, /health, /stats, /config, /reindex, etc. |

| Field Mapping | Old | New (OpenAPI) |
|---------------|-----|---------------|
| Results limit | `topk` | `limit` |
| Match source | `match_type` | `source` |
| Ticket reference | `ticket` (object) | `ticket_id` (string) |
| Reindex processed | `indexed` | `processed` |
| Reindex failures | `errors` | `failed` |
| Reindex duration | `took_ms` | `duration_ms` |
| Created timestamp | `created_at` | `created` |
| Updated timestamp | `updated_at` | `updated` |
| Storage directory | `tickets.dir` | `storage.dir` |
| Semantic toggle | `enable_semantic` | `semantic_enabled` |
| BM25 weight | `hybrid_weights_bm25` | `bm25_weight` |
| Semantic weight | `hybrid_weights_semantic` | `semantic_weight` |
| Embedding providers | openai, local, none | openai, local, **custom**, none |

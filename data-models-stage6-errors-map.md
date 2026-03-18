# Stage 6: Error Catalog & Module Map

Complete error definitions and module structure for vtic.

---

## 1. Error Catalog

Every error vtic can produce:

| Error Code | HTTP Status | Message Template | When | Field |
|------------|-------------|-----------------|------|-------|
| TICKET_NOT_FOUND | 404 | "Ticket {id} not found" | GET/PATCH/DELETE with non-existent ID | id |
| INVALID_TICKET_ID | 400 | "Invalid ticket ID format: {id}" | ID doesn't match pattern | id |
| MISSING_REQUIRED_FIELD | 400 | "Missing required field: {field}" | Create without title/repo | field |
| INVALID_SEVERITY | 400 | "Invalid severity: {value}. Must be one of: {allowed}" | Wrong enum value | severity |
| INVALID_STATUS | 400 | "Invalid status: {value}" | Wrong enum value | status |
| INVALID_CATEGORY | 400 | "Invalid category: {value}" | Wrong enum value | category |
| TICKET_ALREADY_EXISTS | 409 | "Ticket {id} already exists" | Create with duplicate ID | id |
| INVALID_FILTER | 400 | "Invalid filter: {field} {op} {value}" | Bad query parameter | field |
| SEARCH_QUERY_EMPTY | 400 | "Search query cannot be empty" | Empty search string | query |
| TOPK_OUT_OF_RANGE | 400 | "topk must be between 1 and 100" | Invalid topk | topk |
| INDEX_NOT_READY | 503 | "Search index not ready" | Query before init | - |
| INDEX_ERROR | 500 | "Search index error: {detail}" | Zvec failure | detail |
| EMBEDDING_PROVIDER_ERROR | 502 | "Embedding provider error: {detail}" | OpenAI/local failure | detail |
| CONFIG_ERROR | 500 | "Configuration error: {detail}" | Bad config | detail |
| FILE_WRITE_ERROR | 500 | "Failed to write ticket file: {detail}" | Disk I/O error | detail |
| FILE_READ_ERROR | 500 | "Failed to read ticket file: {detail}" | Disk I/O error | detail |
| REPO_FORMAT_INVALID | 400 | "Repo must be in format 'owner/repo', got: {value}" | Invalid repo format | repo |
| VALIDATION_ERROR | 400 | "Validation failed: {details}" | Multiple validation failures | - |
| IMMUTABLE_FIELD | 400 | "Field '{field}' cannot be modified after creation" | Attempt to change id/repo/created | field |
| SORT_FIELD_INVALID | 400 | "Invalid sort field: {field}" | Unknown field in sort param | field |
| PAGINATION_INVALID | 400 | "Invalid pagination: {detail}" | Negative offset or zero limit | - |
| RATE_LIMIT_EXCEEDED | 429 | "Rate limit exceeded. Retry after {retry_after}s" | Too many requests | - |
| UNPROCESSABLE_ENTITY | 422 | "Unable to process request: {detail}" | Semantic validation failure | - |
| INVALID_STATUS_TRANSITION | 400 | "Cannot transition from {from} to {to}" | Invalid status workflow | status |
| EMPTY_UPDATE | 400 | "At least one field required for update" | PATCH with no fields | - |
| SLUG_GENERATION_ERROR | 500 | "Failed to generate slug from title" | Title slugification fails | title |
| SEMANTIC_SEARCH_DISABLED | 400 | "Semantic search requires embedding provider" | semantic=true with no provider | semantic |
| EMBEDDING_DIMENSION_MISMATCH | 500 | "Embedding dimension mismatch: expected {expected}, got {actual}" | Wrong vector size | dimensions |
| TICKET_DIRECTORY_ERROR | 500 | "Failed to create ticket directory: {detail}" | Permission denied | dir |
| INDEX_CORRUPTED | 500 | "Index corrupted, rebuild required" | Zvec data corrupted | - |

### VticError Base Class

```python
# src/vtic/errors.py
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class VticError(Exception):
    """Base error class for all vtic exceptions.
    
    All vtic errors have:
    - code: Machine-readable error code for programmatic handling
    - status: HTTP status code (for API responses)
    - message: Human-readable error message
    - field: Related field name for validation errors (optional)
    - details: Additional context for debugging (optional)
    """
    
    code: str = "INTERNAL_ERROR"
    status: int = 500
    message: str = "An unexpected error occurred"
    field: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(
        self,
        message: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Initialize error with optional field and details."""
        if message:
            self.message = message
        if field:
            self.field = field
        if details:
            self.details = details
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
                "status": self.status,
            }
        }
        if self.field:
            result["error"]["field"] = self.field
        if self.details:
            result["error"]["details"] = self.details
        return result
    
    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.field:
            parts.append(f"(field: {self.field})")
        if self.details:
            parts.append(f"details: {self.details}")
        return " ".join(parts)
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
│   ├── search.py        # SearchRequest, SearchFilter, SearchResult, SearchResponse (Stage 3)
│   ├── api.py           # PaginatedResponse, ErrorResponse, HealthResponse, StatsResponse (Stage 4)
│   └── config.py        # Config, load_config (Stage 5)
├── errors.py            # VticError, all error codes (Stage 6)
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
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
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
    SECURITY = "security"       # Prefix: S
    AUTH = "auth"               # Prefix: A
    CODE_QUALITY = "code_quality"  # Prefix: C
    PERFORMANCE = "performance" # Prefix: P
    FRONTEND = "frontend"       # Prefix: F
    BACKEND = "backend"         # Prefix: B
    TESTING = "testing"         # Prefix: T
    DOCUMENTATION = "documentation"  # Prefix: D
    INFRASTRUCTURE = "infrastructure"  # Prefix: I
    CONFIGURATION = "configuration"  # Prefix: G
    API = "api"                 # Prefix: X
    DATA = "data"               # Prefix: DA
    UI = "ui"                   # Prefix: U
    DEPENDENCIES = "dependencies"  # Prefix: E
    BUILD = "build"             # Prefix: L
    OTHER = "other"             # Prefix: O
    
    @classmethod
    def values(cls) -> list[str]
    @classmethod
    def get_prefix(cls, category: "Category | str") -> str
```

#### `src/vtic/models/ticket.py`
```python
class Ticket(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    repo: str
    owner: Optional[str]
    category: Category
    severity: Severity
    status: Status
    tags: List[str]
    file: Optional[str]  # renamed from file_refs for clarity
    fix: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    def update_timestamp(self) -> None
    def is_terminal(self) -> bool
    @property
    def id_prefix(self) -> str

class TicketCreate(BaseModel):
    title: str
    description: str
    repo: Optional[str] = None
    category: Optional[Category] = None
    severity: Optional[Severity] = None
    status: Optional[Status] = None
    fix: Optional[str] = None
    file: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    def apply_defaults(self, default_repo: Optional[str] = None) -> "TicketCreateWithDefaults"

class TicketCreateWithDefaults(BaseModel):
    title: str
    description: str
    repo: str  # required after defaults applied
    category: Category
    severity: Severity
    status: Status
    fix: Optional[str] = None
    file: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    fix: Optional[str] = None
    category: Optional[Category] = None
    severity: Optional[Severity] = None
    status: Optional[Status] = None
    file: Optional[str] = None
    tags: Optional[List[str]] = None
    
    def get_updates(self) -> dict[str, Any]

class TicketResponse(Ticket):
    # Inherits all fields from Ticket
    # v0.1: No additional computed fields
    @classmethod
    def from_ticket(cls, ticket: Ticket) -> "TicketResponse"
```

#### `src/vtic/models/search.py`
```python
class SearchFilter(BaseModel):
    severity: Optional[Severity] = None
    status: Optional[Status] = None
    category: Optional[Category] = None
    repo: Optional[str] = None  # supports glob patterns
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    
    def to_zvec_filter(self) -> Optional[str]
    def is_empty(self) -> bool

class SearchRequest(BaseModel):
    query: str
    topk: int = Field(default=10, ge=1, le=100)
    filters: Optional[SearchFilter] = None
    semantic: bool = False
    sort_by: SortField = SortField.RELEVANCE
    sort_order: SortOrder = SortOrder.DESC
    
    def is_semantic_enabled(self) -> bool

class SearchResult(BaseModel):
    ticket: dict[str, Any]  # TicketResponse from stage2
    score: float = Field(ge=0.0, le=1.0)
    match_type: Literal["bm25", "semantic", "hybrid"]
    
    def is_hybrid_match(self) -> bool
    def is_high_confidence(self, threshold: float = 0.8) -> bool

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str
    semantic_used: bool
    topk: int
    took_ms: float
    
    def has_results(self) -> bool
    def get_hybrid_matches(self) -> list[SearchResult]
    def get_high_confidence_results(self, threshold: float = 0.8) -> list[SearchResult]
```

#### `src/vtic/models/api.py`
```python
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    limit: int
    offset: int
    has_more: bool
    
    @classmethod
    def create(cls, items: List[T], total: int, limit: int, offset: int) -> "PaginatedResponse[T]"

class ErrorResponse(BaseModel):
    class ErrorObject(BaseModel):
        code: str
        message: str
        details: Optional[List[ErrorDetail]] = None
    
    error: ErrorObject
    request_id: Optional[str] = None
    timestamp: datetime
    
    @classmethod
    def create(cls, code: str, message: str, details: Optional[List[ErrorDetail]] = None, 
               request_id: Optional[str] = None) -> "ErrorResponse"

class ComponentHealth(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    ticket_count: int
    index_status: Literal["ready", "building", "error", "uninitialized"]
    uptime_seconds: float
    checks: Optional[Dict[str, ComponentHealth]] = None
    
    @classmethod
    def create(cls, version: str, ticket_count: int, index_status: str, 
               uptime_seconds: float, embedding_provider: Optional[str] = None,
               storage_path: Optional[str] = None) -> "HealthResponse"

class StatsResponse(BaseModel):
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    by_repo: Dict[str, int]
    total: int
    
    @classmethod
    def empty(cls) -> "StatsResponse"
    def validate_totals(self) -> bool

class ReindexError(BaseModel):
    ticket_id: str
    error: str

class ReindexResponse(BaseModel):
    indexed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    errors: int = Field(ge=0)
    error_details: Optional[List[ReindexError]] = None
    took_ms: float
    
    @property
    def total_processed(self) -> int
    @property
    def success_rate(self) -> float
```

#### `src/vtic/models/config.py`
```python
class TicketsConfig(BaseModel):
    dir: Path = Field(default=Path("./tickets"))

class ApiConfig(BaseModel):
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8900, ge=1, le=65535)

class SearchConfig(BaseModel):
    bm25_enabled: bool = Field(default=True)
    enable_semantic: bool = Field(default=False)
    embedding_provider: Literal["openai", "local", "none"] = Field(default="openai")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536, gt=0)
    hybrid_weights_bm25: float = Field(default=0.7, ge=0.0, le=1.0)
    hybrid_weights_semantic: float = Field(default=0.3, ge=0.0, le=1.0)

class Config(BaseModel):
    tickets: TicketsConfig = Field(default_factory=TicketsConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)

def load_config(path: Optional[Path] = None) -> Config
def load_and_validate_config(path: Optional[Path] = None) -> Config
def get_openai_api_key() -> Optional[str]
```

#### `src/vtic/errors.py`
```python
@dataclass
class VticError(Exception):
    code: str
    status: int
    message: str
    field: Optional[str]
    details: Dict[str, Any]
    
    def __init__(self, message=None, field=None, details=None, **kwargs)
    def to_dict(self) -> Dict[str, Any]
    def __str__(self) -> str

# Specific error classes (all inherit from VticError)
class TicketNotFoundError(VticError)        # 404
class InvalidTicketIdError(VticError)       # 400
class MissingRequiredFieldError(VticError)  # 400
class InvalidSeverityError(VticError)       # 400
class InvalidStatusError(VticError)         # 400
class InvalidCategoryError(VticError)       # 400
class TicketAlreadyExistsError(VticError)   # 409
class InvalidFilterError(VticError)         # 400
class SearchQueryEmptyError(VticError)      # 400
class TopkOutOfRangeError(VticError)        # 400
class IndexNotReadyError(VticError)         # 503
class IndexError(VticError)                 # 500
class EmbeddingProviderError(VticError)     # 502
class ConfigError(VticError)                # 500
class FileWriteError(VticError)             # 500
class FileReadError(VticError)              # 500
class RepoFormatInvalidError(VticError)     # 400
class ValidationError(VticError)            # 400
class ImmutableFieldError(VticError)        # 400
class InvalidSortFieldError(VticError)      # 400
class InvalidPaginationError(VticError)     # 400
class RateLimitExceededError(VticError)     # 429
class UnprocessableEntityError(VticError)   # 422
class InvalidStatusTransitionError(VticError)  # 400
class EmptyUpdateError(VticError)           # 400
class SlugGenerationError(VticError)        # 500
class SemanticSearchDisabledError(VticError)  # 400
class EmbeddingDimensionMismatchError(VticError)  # 500
class TicketDirectoryError(VticError)       # 500
class IndexCorruptedError(VticError)        # 500
```

#### `src/vtic/store/paths.py`
```python
def ticket_file_path(
    ticket_id: str,
    owner: str,
    repo: str,
    category: str,
    base_dir: Path
) -> Path

def resolve_path(path: Path) -> Path
def extract_ticket_info(path: Path) -> dict

class TicketPathResolver:
    def __init__(self, base_dir: Path)
    def ticket_to_path(self, ticket_id: str, owner: str, repo: str, category: str) -> Path
    def path_to_ticket_info(self, path: Path) -> dict
    def ensure_ticket_dir(self, owner: str, repo: str, category: str) -> Path
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
def fetch_ticket(collection: Collection, ticket_id: str) -> Optional[dict]
def query_tickets(collection: Collection, filter_expr: str, limit: int = 100) -> list[dict]
```

#### `src/vtic/search/bm25.py`
```python
def bm25_search(
    query: str,
    collection: Collection,
    topk: int = 10,
    filters: Optional[dict] = None
) -> list[SearchResult]
```

#### `src/vtic/search/semantic.py`
```python
def semantic_search(
    query: str,
    collection: Collection,
    provider: EmbeddingProvider,
    topk: int = 10,
    filters: Optional[dict] = None
) -> list[SearchResult]
```

#### `src/vtic/search/hybrid.py`
```python
class WeightedReRanker:
    def __init__(self, alpha: float = 0.7)
    def rerank(
        bm25_results: list[SearchResult],
        semantic_results: list[SearchResult]
    ) -> list[SearchResult]

def combine_scores(bm25_score: float, semantic_score: float, alpha: float) -> float
```

#### `src/vtic/search/engine.py`
```python
class SearchEngine:
    def __init__(
        self,
        index: TicketIndex,
        provider: Optional[EmbeddingProvider] = None
    )
    def search(self, request: SearchRequest) -> SearchResponse
    def reindex_all(self) -> int
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

@router.get("/tickets", response_model=PaginatedResponse[TicketResponse])
async def list_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="-created_at"),
    severity: Optional[Severity] = Query(default=None),
    status: Optional[Status] = Query(default=None),
    category: Optional[Category] = Query(default=None),
    repo: Optional[str] = Query(default=None)
) -> PaginatedResponse[TicketResponse]
```

#### `src/vtic/api/routes/search.py`
```python
router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    engine: SearchEngine = Depends(get_search_engine)
) -> SearchResponse
```

#### `src/vtic/api/routes/system.py`
```python
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse

@router.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse

@router.post("/reindex")
async def reindex() -> dict
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
    description: Optional[str] = None,
    category: Category = Category.CODE,
    severity: Severity = Severity.MEDIUM,
    status: Status = Status.OPEN,
    tags: list[str] = []
) -> None

@app.command()
def get(ticket_id: str, format: str = "table") -> None

@app.command()
def update(
    ticket_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[Status] = None,
    severity: Optional[Severity] = None
) -> None

@app.command()
def delete(ticket_id: str, force: bool = False, yes: bool = False) -> None

@app.command()
def list(
    repo: Optional[str] = None,
    status: Optional[Status] = None,
    severity: Optional[Severity] = None,
    limit: int = 20
) -> None

@app.command()
def search(
    query: str,
    topk: int = 10,
    semantic: bool = False,
    filters: Optional[str] = None
) -> None

@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False
) -> None

@app.command()
def reindex() -> None
```

#### `src/vtic/__main__.py`
```python
from vtic.cli.main import app

if __name__ == "__main__":
    app()
```

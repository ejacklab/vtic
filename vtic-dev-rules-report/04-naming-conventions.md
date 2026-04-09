# Naming Conventions

**Project:** vtic — AI-first ticketing system  
**Source:** coding-standards.md, data model specs, codebase

---

## 1. File Naming

### General Rules

```
✅ lowercase_with_underscores.py
✅ descriptive_names.py
❌ CamelCase.py
❌ mixed-case.py
❌ abbreviations.py
```

### Python Files

```
# ✅ Module files
src/vtic/
├── __init__.py              # Package init
├── models/
│   ├── __init__.py
│   ├── ticket.py            # Ticket models
│   ├── search.py            # Search models
│   └── enums.py             # Enumerations
├── store/
│   ├── __init__.py
│   ├── markdown.py          # Markdown operations
│   └── paths.py             # Path utilities
└── api/
    ├── __init__.py
    ├── app.py               # FastAPI app
    ├── deps.py              # Dependencies
    └── routes/
        ├── __init__.py
        ├── tickets.py       # Ticket routes
        └── search.py        # Search routes

# ❌ Bad examples
tkt.py                       # Abbreviation
TicketModels.py              # CamelCase
data-flows.md                # Hyphen in Python file
```

### Test Files

```
# ✅ Co-located tests
ticket.py
ticket_test.py               # Or test_ticket.py

# ✅ Mirror directory structure
tests/
├── test_ticket_service.py
├── test_search_engine.py
└── test_api_routes.py
```

### Configuration Files

```
# ✅ Standard names
pyproject.toml
vtic.toml                    # Project-specific config
.gitignore
.env                         # Environment variables (never commit!)
.env.example                 # Template for env vars

# ❌ Bad
config.txt                   # Wrong extension
vtic_config.json             # Redundant
settings.ini                 # Old format
```

### Documentation Files

```
# ✅ Uppercase for visibility
README.md
CONTRIBUTING.md
LICENSE
CHANGELOG.md

# ✅ lowercase_with_underscores for detailed docs
data_models.md
execution_plan.md
api_reference.md
```

---

## 2. Directory Naming

```
# ✅ lowercase, descriptive
src/vtic/
├── models/                  # Data models
├── store/                   # Storage layer
├── index/                   # Search index
├── search/                  # Search engine
├── api/                     # REST API
└── cli/                     # Command line

# ❌ Bad
Models/                      # Capitalized
store-layer/                 # Hyphen (use underscore)
lib/                         # Too generic
utils/                       # Too vague
```

---

## 3. Variable Naming

### General Rules

| Type | Convention | Example |
|------|------------|---------|
| Regular variables | `snake_case` | `ticket_count`, `search_query` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_LIMIT`, `DEFAULT_TIMEOUT` |
| Private variables | `_leading_underscore` | `_internal_cache` |
| Class variables | `snake_case` | `default_config` |
| Type variables | `PascalCase` | `T`, `ModelType` |

### Boolean Variables

```python
# ✅ Prefix with is_, has_, can_, should_
is_valid = True
has_errors = False
can_write = True
should_retry = False

# ❌ Avoid
valid = True          # Ambiguous — is it a function?
error = False         # Is this an error object?
write = True          # Is this a write function?
```

### Collection Variables

```python
# ✅ Plural nouns for collections
tickets = [ticket1, ticket2]
results = {"hit1": score1, "hit2": score2}
severity_levels = ["low", "medium", "high", "critical"]

# ❌ Avoid
result_list = [...]   # Redundant suffix
ticket_array = [...]  # Implementation detail in name
```

### Counters/Indices

```python
# ✅ i, j, k for loop indices only
for i, ticket in enumerate(tickets):
    ...

# ✅ Descriptive names for meaningful indices
ticket_index = tickets.index(ticket_id)
page_number = 3
total_count = len(tickets)
```

---

## 4. Function Naming

### Verbs + Nouns

```python
# ✅ Verb + noun pattern
def create_ticket(data: TicketCreate) -> Ticket:
def get_ticket_by_id(ticket_id: str) -> Ticket | None:
def update_ticket_status(ticket_id: str, status: Status) -> Ticket:
def delete_tickets_by_filter(filter: FilterSet) -> int:
def search_tickets(query: str) -> SearchResult:

# ❌ Avoid
def ticket(data):           # Noun only — is this creating? getting?
def process(data):          # Vague verb
def handle(data):           # Vague verb
def do_something():         # Meaningless
```

### Action Prefixes

| Action | Prefix | Example |
|--------|--------|---------|
| Create | `create_` | `create_ticket()` |
| Read | `get_`, `fetch_` | `get_ticket()`, `fetch_user()` |
| Update | `update_` | `update_ticket()` |
| Delete | `delete_`, `remove_` | `delete_ticket()`, `remove_item()` |
| Check | `is_`, `has_`, `can_` | `is_valid()`, `has_permission()` |
| Transform | `to_`, `from_` | `to_dict()`, `from_json()` |
| Calculate | `calculate_`, `compute_` | `calculate_score()` |
| Validate | `validate_` | `validate_input()` |
| Build | `build_` | `build_query()` |
| Parse | `parse_` | `parse_markdown()` |

### Private Functions

```python
# ✅ Single leading underscore for internal use
def _validate_ticket_id(ticket_id: str) -> None:
def _build_search_query(filters: FilterSet) -> str:
def _persist_to_disk(ticket: Ticket) -> None:

# ❌ Double underscore (name mangling) — rarely needed
def __validate(ticket_id):  # Avoid unless necessary
```

---

## 5. Class Naming

### PascalCase for Classes

```python
# ✅ Classes use PascalCase
class Ticket(BaseModel):
    ...

class TicketService:
    ...

class SearchEngine:
    ...

class VticError(Exception):
    ...

# ❌ Avoid
class ticket:               # lowercase
class ticket_service:       # snake_case
class TICKET:               # UPPERCASE
```

### Abstract Base Classes

```python
# ✅ Prefix with Abstract or use ABC suffix
from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

# ✅ Or use Protocol for structural subtyping
from typing import Protocol

class Searchable(Protocol):
    def search(self, query: str) -> list[Result]:
        ...
```

### Exception Classes

```python
# ✅ Suffix with Error
class VticError(Exception):
    """Base exception."""
    pass

class TicketNotFoundError(VticError):
    """Ticket ID doesn't exist."""
    pass

class ValidationError(VticError):
    """Input validation failed."""
    pass

class SearchError(VticError):
    """Search operation failed."""
    pass

# ❌ Avoid
class NotFound(Exception):           # Too generic
class Invalid(Exception):            # Too vague
class TicketNotFound(Exception):     # Missing Error suffix
```

---

## 6. Enum Naming

### Enum Classes

```python
from enum import Enum

# ✅ Enum class names are PascalCase
class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Status(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    CLOSED = "closed"

class Category(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    SECURITY = "security"
    PERFORMANCE = "performance"

# ❌ Avoid
class severity(Enum):       # lowercase
class ticket_severity:      # snake_case
```

### Enum Members

```python
# ✅ UPPER_SNAKE_CASE for enum members
class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ❌ Avoid
class Severity(str, Enum):
    low = "low"              # lowercase
    Medium = "medium"        # PascalCase
```

---

## 7. Constant Naming

### Module-Level Constants

```python
# ✅ UPPER_SNAKE_CASE at module level
MAX_TITLE_LENGTH = 200
DEFAULT_SEARCH_LIMIT = 10
MIN_SEARCH_LIMIT = 1
MAX_SEARCH_LIMIT = 100

VALID_ID_PATTERN = re.compile(r"^[CFGHST]\\d+$")
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "vtic" / "config.toml"

# Category prefixes for ticket IDs
CATEGORY_PREFIXES = {
    "bug": "B",
    "feature": "F", 
    "security": "S",
    "performance": "P",
}

# ❌ Avoid
maxTitleLength = 200         # camelCase
default_limit = 10           # lowercase
```

### Class Constants

```python
class TicketService:
    # ✅ Class-level constants use UPPER_SNAKE_CASE
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    def __init__(self):
        self._page_size = self.DEFAULT_PAGE_SIZE
```

---

## 8. Type Variable Naming

```python
from typing import TypeVar, Generic

# ✅ Single letter for simple cases
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# ✅ Descriptive for complex cases
ModelType = TypeVar("ModelType", bound=BaseModel)
TicketType = TypeVar("TicketType", bound="Ticket")

class Repository(Generic[T]):
    def get(self, id: str) -> T | None:
        ...
```

---

## 9. Ticket ID Format

### ID Pattern

```python
# ✅ Format: {CATEGORY_PREFIX}{SEQUENCE_NUMBER}
# Examples: C1, C2, H5, F12, S3, G8

# Pattern validation
VALID_ID_PATTERN = re.compile(r"^[CFGHST]\\d+$")

# Category prefixes
CATEGORY_PREFIXES = {
    "config": "C",
    "feature": "F", 
    "security": "S",
    "performance": "P",
    "hybrid_search": "H",
    "general": "G",
}

# ✅ ID generation
def generate_id(category: str, sequence: int) -> str:
    prefix = CATEGORY_PREFIXES[category]
    return f"{prefix}{sequence}"

# Example: generate_id("feature", 12) → "F12"
```

---

## 10. URL/Route Naming

### REST API Routes

```python
# ✅ RESTful naming
GET    /tickets              # List tickets
POST   /tickets              # Create ticket
GET    /tickets/{id}         # Get ticket by ID
PATCH  /tickets/{id}         # Update ticket
DELETE /tickets/{id}         # Delete ticket
POST   /search               # Search tickets

# ✅ Actions as sub-resources
POST   /tickets/{id}/similar # Find similar tickets
POST   /reindex              # Rebuild index
GET    /health               # Health check
GET    /stats                # Statistics

# ❌ Avoid
GET    /getTicket/{id}       # Verb in URL
POST   /createTicket         # Verb in URL
POST   /tickets/search       # POST on collection for search
```

### Query Parameters

```python
# ✅ snake_case for query params
GET /tickets?repo=ejacklab/vtic&severity=critical&status=open
GET /tickets?limit=20&offset=40
GET /search?q=CORS&filters=severity:critical

# ❌ Avoid
GET /tickets?repoName=...    # camelCase
GET /tickets?RepoName=...    # PascalCase
```

---

## 11. Configuration Naming

### TOML Keys

```toml
# ✅ snake_case in TOML
[storage]
tickets_dir = "./tickets"
index_dir = "./.vtic"

[search]
default_limit = 10
bm25_weight = 0.7
semantic_weight = 0.3

[embeddings]
provider = "local"
dimension = 384
model_name = "sentence-transformers/all-MiniLM-L6-v2"

# ❌ Avoid
ticketsDir = "..."           # camelCase
TicketsDir = "..."           # PascalCase
```

### Environment Variables

```bash
# ✅ UPPER_SNAKE_CASE with PREFIX
VTIC_STORAGE_DIR=./tickets
VTIC_INDEX_DIR=./.vtic
VTIC_LOG_LEVEL=info
VTIC_API_PORT=8000

OPENAI_API_KEY=sk-...

# ❌ Avoid
vtic_storage_dir=...         # lowercase
vticStorageDir=...           # camelCase
```

---

## Quick Reference Card

| Element | Convention | Example |
|---------|------------|---------|
| Files | `snake_case.py` | `ticket_service.py` |
| Directories | `lowercase/` | `models/`, `store/` |
| Classes | `PascalCase` | `TicketService` |
| Functions | `snake_case()` | `create_ticket()` |
| Variables | `snake_case` | `ticket_count` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_LIMIT` |
| Private | `_leading_underscore` | `_internal_cache` |
| Enums | `PascalCase` | `Severity` |
| Enum members | `UPPER_SNAKE_CASE` | `CRITICAL` |
| Exceptions | `PascalCase` + `Error` | `TicketNotFoundError` |
| Type vars | `PascalCase` or single letter | `T`, `ModelType` |
| Query params | `snake_case` | `?limit=10` |
| Env vars | `UPPER_SNAKE_CASE` | `VTIC_API_PORT` |

---

## References

- `tmp/vtic/data-models-stage1-enums.md` — Enum definitions
- `tmp/vtic/openapi.yaml` — API route naming
- `rules/coding-standards.md` — Code quality rules

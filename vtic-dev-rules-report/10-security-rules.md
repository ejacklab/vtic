# Security Development Rules

**Project:** vtic — AI-first ticketing system  
**Source:** coding-standards.md, security best practices

---

## 1. Security Philosophy

### Default to Secure

vtic is local-first and single-user (v0.1), but security rules still apply:

1. **No secrets in code** — API keys, tokens → environment variables
2. **Input validation** — Validate all inputs at boundaries
3. **Output encoding** — Encode outputs for safe display
4. **Least privilege** — Request only necessary permissions

### v0.1 Scope

```
✅ In scope for v0.1:
- Input validation
- Path traversal prevention
- Error message sanitization
- No hardcoded secrets

❌ Not in scope for v0.1:
- Authentication (single-user local app)
- Authorization/RBAC
- Rate limiting
- Network security
```

---

## 2. Secrets Management

### Rule: Never Hardcode Secrets

```python
# ❌ Never do this
API_KEY = "sk-1234567890abcdef"
DB_PASSWORD = "secret"

# ❌ Never do this
response = requests.get(url, headers={"Authorization": f"Bearer {token}"})

# ❌ Never commit this
# .env file with real secrets
```

### Environment Variables

```python
# ✅ Do this
import os

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ConfigError("OPENAI_API_KEY not set")

# ✅ Or with pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    
    class Config:
        env_prefix = "VTIC_"

settings = Settings()
```

### .env File Handling

```bash
# .env.example — Template, commit this
OPENAI_API_KEY=
VTIC_STORAGE_DIR=./tickets

# .env — Real secrets, NEVER commit
OPENAI_API_KEY=sk-1234567890abcdef
VTIC_STORAGE_DIR=/home/user/tickets
```

```bash
# .gitignore — Ensure .env is ignored
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
```

### Secret Scanning

```bash
# Check for leaked secrets before committing
grep -r "sk-" . --include="*.py" --include="*.toml"
grep -r "password\s*=" . --include="*.py"
```

---

## 3. Input Validation

### Validate All Inputs

```python
# ✅ Validate at boundaries
@router.post("/tickets")
async def create_ticket(data: TicketCreate):
    # Pydantic validates automatically
    ticket = await service.create(data)
    return ticket

# ❌ Don't trust raw input
@router.post("/tickets")
async def create_ticket(data: dict):
    # data comes from untrusted source!
    title = data["title"]  # Could raise KeyError
```

### Path Traversal Prevention

```python
# ❌ Vulnerable to path traversal
def read_ticket(filename: str):
    path = Path(f"tickets/{filename}")
    return path.read_text()

# Request: "../../etc/passwd"
# Result: tickets/../../etc/passwd → /etc/passwd

# ✅ Safe: Validate and sanitize
def read_ticket(ticket_id: str):
    # Validate ticket ID format
    if not VALID_ID_PATTERN.match(ticket_id):
        raise ValidationError(f"Invalid ticket ID: {ticket_id}")
    
    # Build path safely
    path = tickets_dir / ticket_id[:1] / ticket_id
    
    # Ensure it's within tickets directory
    path = path.resolve()
    if not str(path).startswith(str(tickets_dir.resolve())):
        raise ValidationError("Invalid ticket ID")
    
    return path.read_text()
```

### SQL/NoSQL Injection Prevention

```python
# ✅ Use parameterized queries (Zvec handles this)
results = await collection.query(
    "SELECT * WHERE repo = ?",
    [repo]  # Safe: parameterized
)

# ❌ Never string-concatenate into queries
query = f"SELECT * WHERE repo = '{repo}'"  # Vulnerable!
```

---

## 4. Output Encoding

### HTML Encoding

```python
# For web interfaces (future)
from html import escape

def render_ticket_html(ticket):
    # Escape user content to prevent XSS
    return f"""
    <h1>{escape(ticket.title)}</h1>
    <p>{escape(ticket.description)}</p>
    """
```

### JSON Response Safety

```python
# FastAPI handles JSON encoding safely
@router.get("/tickets/{id}")
async def get_ticket(id: str):
    # FastAPI automatically encodes special chars
    return ticket  # Safe
```

---

## 5. Error Message Security

### Don't Leak Sensitive Info

```python
# ❌ Leaks internal details
try:
    await db.execute(query)
except DatabaseError as e:
    return {"error": f"Database error: {e.sql}"}  # Leaks query!

# ✅ Generic error messages
try:
    await db.execute(query)
except DatabaseError:
    logger.error("Database error", extra={"query": query})  # Log internally
    return {"error": "An internal error occurred"}  # Generic message
```

### Sanitize Error Responses

```python
# FastAPI exception handler
@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    # Don't expose internal error details to users
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )

# But log everything for debugging
logger.error(
    "Unhandled exception",
    extra={
        "path": request.url,
        "method": request.method,
        "error": str(exc),
        "traceback": traceback.format_exc()
    }
)
```

---

## 6. File System Security

### Restrict File Access

```python
# ✅ Use restricted file operations
ALLOWED_EXTENSIONS = {".md", ".txt"}

def read_ticket(path: Path):
    if path.suffix not in ALLOWED_EXTENSIONS:
        raise ValidationError("File type not allowed")
    
    if not path.exists():
        raise TicketNotFoundError()
    
    return path.read_text(encoding="utf-8")
```

### Temporary Files

```python
# ✅ Use secure temp file creation
import tempfile
import os

# Create temp file in secure location
with tempfile.NamedTemporaryFile(
    mode='w',
    dir=temp_dir,
    delete=False,
    prefix='vtic_',
    suffix='.tmp'
) as f:
    f.write(content)
    temp_path = Path(f.name)

# Atomic rename
target_path.rename(temp_path)

# Clean up on failure
try:
    ...
except:
    temp_path.unlink(missing_ok=True)
    raise
```

---

## 7. Configuration Security

### Validate Config Values

```python
@dataclass
class StorageConfig:
    tickets_dir: Path
    index_dir: Path
    
    def __post_init__(self):
        # Validate directories exist or can be created
        if not self.tickets_dir.is_absolute():
            raise ConfigError("tickets_dir must be absolute path")
        
        # Ensure directories are within allowed paths
        home = Path.home()
        if not str(self.tickets_dir).startswith(str(home)):
            raise ConfigError("tickets_dir must be under home directory")
```

### Restrict Permissions

```python
import os
import stat

# Set secure file permissions on config files
config_path = Path("vtic.toml")
config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # Owner read/write only

# Ensure .env files are not readable by others
env_path = Path(".env")
if env_path.exists():
    env_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
```

---

## 8. Logging Security

### What to Log

```python
# ✅ Log for debugging (safe)
logger.info("Ticket created", extra={
    "ticket_id": ticket.id,
    "repo": ticket.repo,
    "user": os.environ.get("USER")
})

# ✅ Log errors
logger.error("Search failed", extra={
    "query": query,  # User input, but for debugging
    "error": str(exc)
})
```

### What NOT to Log

```python
# ❌ Never log secrets
logger.info("API call", extra={
    "api_key": api_key  # NEVER!
})

# ❌ Never log passwords or tokens
logger.debug("Auth", extra={
    "token": request.headers.get("Authorization")  # NEVER!
})

# ❌ Never log sensitive user data
logger.info("User action", extra={
    "ssn": user.ssn,  # NEVER!
    "password": "***"   # NEVER!
})
```

### Log Redaction

```python
import re

def redact_sensitive(data: dict) -> dict:
    """Redact sensitive fields from log data."""
    sensitive_keys = {"api_key", "token", "password", "secret", "ssn"}
    redacted = data.copy()
    
    for key in sensitive_keys:
        if key in redacted:
            redacted[key] = "***REDACTED***"
    
    return redacted
```

---

## 9. Dependency Security

### Keep Dependencies Updated

```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
uv pip compile --upgrade pyproject.toml
uv sync
```

### Pin Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "fastapi>=0.100.0,<1.0.0",  # Pin major versions
    "pydantic>=2.0.0,<3.0.0",
]

# uv.lock — Commit this for reproducible builds
```

### Avoid Dangerous Dependencies

```bash
# Check before adding
pip-audit ./pyproject.toml
```

---

## 10. Future Security (Post v0.1)

### Authentication

```python
# Future: API key authentication
@app.middleware
async def auth_middleware(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "UNAUTHORIZED"}}
        )
    
    if not validate_api_key(api_key):
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "FORBIDDEN"}}
        )
    
    return await call_next(request)
```

### Rate Limiting

```python
# Future: Rate limiting
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/tickets")
@limiter.limit("100/minute")
async def create_ticket(request: Request):
    ...
```

---

## Security Checklist

### Before Release

- [ ] No hardcoded secrets in code
- [ ] All inputs validated
- [ ] Error messages don't leak internals
- [ ] Dependencies audited (`pip-audit`)
- [ ] Dependencies pinned in lock file
- [ ] Config files have restricted permissions
- [ ] Sensitive data redacted in logs
- [ ] Path traversal prevented
- [ ] .env files in .gitignore

---

## Quick Reference Card

| Aspect | Rule |
|--------|------|
| Secrets | Never hardcode, use env vars |
| Input | Validate at all boundaries |
| Paths | Prevent traversal attacks |
| Errors | Generic messages, detailed logs |
| Logs | No secrets, sensitive data redacted |
| Config | Validate values, restrict permissions |
| Dependencies | Pin versions, audit regularly |

---

## References

- `rules/coding-standards.md` — Section 4 (No secrets)
- `tmp/vtic/.gitignore` — Excluded files
- <https://owasp.org/> — Security guidelines

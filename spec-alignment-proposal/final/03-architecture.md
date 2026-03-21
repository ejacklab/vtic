# Architecture: spec-alignment-checker

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                               │
│                    (spec_align/cli.py)                              │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
         ┌──────────────────┐      ┌──────────────────┐
         │  Discovery Engine │      │   Config Loader  │
         │  (find all specs) │      │  (spec-align.yaml)│
         └────────┬─────────┘      └────────┬─────────┘
                  │                         │
                  └───────────┬─────────────┘
                              ▼
         ┌─────────────────────────────────────────────────┐
         │              Normalization Layer                 │
         │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │
         │  │OpenAPI  │ │Pydantic │ │TypeScript│ │ JSON  │ │
         │  │ Parser  │ │ Parser  │ │ Parser  │ │Parser │ │
         │  └────┬────┘ └────┬────┘ └────┬────┘ └───┬───┘ │
         │       │           │           │          │     │
         │       └───────────┴───────────┴──────────┘     │
         │                       │                        │
         │                       ▼                        │
         │            ┌──────────────────┐                │
         │            │ Canonical Schema │                │
         │            │   (IR Format)    │                │
         │            └────────┬─────────┘                │
         └─────────────────────┼──────────────────────────┘
                               ▼
         ┌─────────────────────────────────────────────────┐
         │            Comparison Engine                     │
         │  ┌────────────────┐  ┌────────────────┐         │
         │  │  Type Checker  │  │ Constraint     │         │
         │  │                │  │ Validator      │         │
         │  └────────┬───────┘  └────────┬───────┘         │
         │           │                   │                 │
         │           └─────────┬─────────┘                 │
         │                     ▼                           │
         │          ┌──────────────────┐                   │
         │          │ Contradiction    │                   │
         │          │ Detector         │                   │
         │          └────────┬─────────┘                   │
         └───────────────────┼─────────────────────────────┘
                             ▼
         ┌─────────────────────────────────────────────────┐
         │              Report Generator                    │
         │  ┌─────────┐ ┌─────────┐ ┌─────────┐           │
         │  │Console  │ │   JSON  │ │   SARIF │           │
         │  │Reporter │ │Reporter │ │Reporter │           │
         │  └─────────┘ └─────────┘ └─────────┘           │
         └─────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Canonical Schema Model

**Purpose**: Unified representation for all spec formats

```python
# spec_align/schema.py

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"

@dataclass
class TypeRef:
    """Reference to a type with full metadata."""
    base_type: FieldType
    format: Optional[str] = None        # date-time, uuid, email, etc.
    enum_values: Optional[list[str]] = None
    array_item: Optional["TypeRef"] = None
    object_fields: Optional[dict[str, "FieldSpec"]] = None
    nullable: bool = False
    
    def matches(self, other: "TypeRef") -> bool:
        """Check if two types are compatible."""
        if self.base_type != other.base_type:
            return False
        if self.enum_values and other.enum_values:
            return set(self.enum_values) == set(other.enum_values)
        return True

@dataclass
class FieldSpec:
    """A single field in a schema."""
    name: str
    type_ref: TypeRef
    required: bool = True
    default: Any = None
    constraints: dict[str, Any] = field(default_factory=dict)
    source: "SourceLocation" = None
    
    # Constraints can include: min_length, max_length, pattern, minimum, maximum

@dataclass
class EndpointSpec:
    """REST API endpoint definition."""
    path: str
    method: str  # GET, POST, PUT, PATCH, DELETE
    request_body: Optional[FieldSpec] = None
    response: Optional[FieldSpec] = None
    parameters: list[FieldSpec] = field(default_factory=list)
    source: "SourceLocation" = None

@dataclass
class SchemaModel:
    """Complete schema model from one source."""
    name: str
    source_type: str  # "openapi", "pydantic", "typescript"
    models: dict[str, FieldSpec] = field(default_factory=dict)
    endpoints: list[EndpointSpec] = field(default_factory=list)
    
    def get_model(self, name: str) -> Optional[FieldSpec]:
        return self.models.get(name)

@dataclass
class SourceLocation:
    """Where a definition came from."""
    file: str
    line: int
    column: int = 0
    
    def __str__(self):
        return f"{self.file}:{self.line}"
```

---

### 2. Parsers

#### OpenAPI Parser

```python
# spec_align/parsers/openapi.py

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename
from typing import Dict
from ..schema import SchemaModel, FieldSpec, TypeRef, FieldType, EndpointSpec

class OpenAPIParser:
    """Parse OpenAPI 3.x specification into canonical schema model."""
    
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self._spec: Dict = None
    
    def parse(self) -> SchemaModel:
        """Parse and validate OpenAPI spec."""
        # Read and validate
        self._spec = read_from_filename(self.spec_path)
        validate(self._spec)
        
        model = SchemaModel(
            name=self.spec_path,
            source_type="openapi"
        )
        
        # Parse components/schemas
        self._parse_schemas(model)
        
        # Parse paths (endpoints)
        self._parse_endpoints(model)
        
        return model
    
    def _parse_schemas(self, model: SchemaModel) -> None:
        """Extract schema definitions."""
        schemas = self._spec.get('components', {}).get('schemas', {})
        
        for name, schema_def in schemas.items():
            field_spec = self._parse_schema_object(schema_def, name)
            model.models[name] = field_spec
    
    def _parse_schema_object(self, obj: dict, name: str = None) -> FieldSpec:
        """Parse a single schema object."""
        type_str = obj.get('type', 'object')
        field_type = self._map_type(type_str)
        
        type_ref = TypeRef(
            base_type=field_type,
            format=obj.get('format'),
            enum_values=obj.get('enum'),
            nullable=obj.get('nullable', False)
        )
        
        # Handle nested objects
        if field_type == FieldType.OBJECT and 'properties' in obj:
            type_ref.object_fields = {}
            for prop_name, prop_def in obj['properties'].items():
                type_ref.object_fields[prop_name] = self._parse_schema_object(
                    prop_def, prop_name
                )
        
        # Handle arrays
        if field_type == FieldType.ARRAY and 'items' in obj:
            type_ref.array_item = self._parse_schema_object(obj['items'])
        
        required = name in obj.get('required', []) if 'required' in obj else True
        
        return FieldSpec(
            name=name or "anonymous",
            type_ref=type_ref,
            required=required,
            default=obj.get('default'),
            constraints={
                'min_length': obj.get('minLength'),
                'max_length': obj.get('maxLength'),
                'pattern': obj.get('pattern'),
                'minimum': obj.get('minimum'),
                'maximum': obj.get('maximum'),
            }
        )
    
    def _map_type(self, type_str: str) -> FieldType:
        """Map OpenAPI type to FieldType."""
        mapping = {
            'string': FieldType.STRING,
            'integer': FieldType.INTEGER,
            'number': FieldType.NUMBER,
            'boolean': FieldType.BOOLEAN,
            'array': FieldType.ARRAY,
            'object': FieldType.OBJECT,
        }
        return mapping.get(type_str, FieldType.OBJECT)
    
    def _parse_endpoints(self, model: SchemaModel) -> None:
        """Extract endpoint definitions."""
        paths = self._spec.get('paths', {})
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                    continue
                
                endpoint = EndpointSpec(
                    path=path,
                    method=method.upper(),
                )
                
                # Parse request body
                if 'requestBody' in operation:
                    content = operation['requestBody'].get('content', {})
                    if 'application/json' in content:
                        schema = content['application/json'].get('schema', {})
                        endpoint.request_body = self._parse_schema_object(schema)
                
                # Parse response
                if 'responses' in operation:
                    for status, response in operation['responses'].items():
                        if status.startswith('2'):  # 2xx responses
                            content = response.get('content', {})
                            if 'application/json' in content:
                                schema = content['application/json'].get('schema', {})
                                endpoint.response = self._parse_schema_object(schema)
                            break
                
                model.endpoints.append(endpoint)
```

#### Pydantic Parser

```python
# spec_align/parsers/pydantic.py

import ast
import importlib.util
from pathlib import Path
from typing import List
from ..schema import SchemaModel, FieldSpec, TypeRef, FieldType

class PydanticParser:
    """Parse Pydantic models into canonical schema model."""
    
    def __init__(self, model_dirs: List[str]):
        self.model_dirs = [Path(d) for d in model_dirs]
    
    def parse(self) -> SchemaModel:
        """Parse all Pydantic models from directories."""
        model = SchemaModel(
            name="pydantic",
            source_type="pydantic"
        )
        
        for model_dir in self.model_dirs:
            for py_file in model_dir.rglob("*.py"):
                self._parse_file(py_file, model)
        
        return model
    
    def _parse_file(self, file_path: Path, model: SchemaModel) -> None:
        """Parse a single Python file for Pydantic models."""
        with open(file_path) as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_pydantic_model(node, tree):
                    field_spec = self._parse_model_class(node, file_path)
                    if field_spec:
                        model.models[node.name] = field_spec
    
    def _is_pydantic_model(self, node: ast.ClassDef, tree: ast.AST) -> bool:
        """Check if class inherits from BaseModel."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                return True
            if isinstance(base, ast.Attribute) and base.attr == 'BaseModel':
                return True
        return False
    
    def _parse_model_class(self, node: ast.ClassDef, file_path: Path) -> FieldSpec:
        """Parse a Pydantic model class."""
        type_ref = TypeRef(base_type=FieldType.OBJECT, object_fields={})
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                field_name = item.target.id if isinstance(item.target, ast.Name) else None
                if not field_name:
                    continue
                
                field_type = self._parse_annotation(item.annotation)
                required = item.value is None
                default = self._parse_default(item.value) if item.value else None
                
                type_ref.object_fields[field_name] = FieldSpec(
                    name=field_name,
                    type_ref=field_type,
                    required=required,
                    default=default,
                    source=SourceLocation(file=str(file_path), line=item.lineno)
                )
        
        return FieldSpec(
            name=node.name,
            type_ref=type_ref,
            source=SourceLocation(file=str(file_path), line=node.lineno)
        )
    
    def _parse_annotation(self, annotation: ast.AST) -> TypeRef:
        """Parse type annotation to TypeRef."""
        if isinstance(annotation, ast.Name):
            type_map = {
                'str': FieldType.STRING,
                'int': FieldType.INTEGER,
                'float': FieldType.NUMBER,
                'bool': FieldType.BOOLEAN,
                'list': FieldType.ARRAY,
                'dict': FieldType.OBJECT,
            }
            return TypeRef(base_type=type_map.get(annotation.id, FieldType.OBJECT))
        
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == 'Optional':
                    inner = self._parse_annotation(annotation.slice)
                    inner.nullable = True
                    return inner
                if annotation.value.id == 'List':
                    inner = self._parse_annotation(annotation.slice)
                    return TypeRef(base_type=FieldType.ARRAY, array_item=inner)
        
        return TypeRef(base_type=FieldType.OBJECT)
    
    def _parse_default(self, value: ast.AST) -> Any:
        """Parse default value."""
        if isinstance(value, ast.Constant):
            return value.value
        if isinstance(value, ast.Name):
            return value.id
        return None
```

---

### 3. Comparison Engine

```python
# spec_align/comparison/engine.py

from dataclasses import dataclass
from typing import List
from ..schema import SchemaModel, FieldSpec, TypeRef

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class Contradiction:
    """A detected contradiction between specs."""
    id: str
    category: str          # TYPE_MISMATCH, REQUIRED_CONFLICT, etc.
    severity: Severity
    field_name: str
    source1: SourceLocation
    source2: SourceLocation
    value1: str
    value2: str
    impact: str
    suggestion: str

class ComparisonEngine:
    """Compare schema models and detect contradictions."""
    
    def compare(self, models: List[SchemaModel]) -> List[Contradiction]:
        """Compare multiple schema models."""
        contradictions = []
        
        if len(models) < 2:
            return contradictions
        
        # Use first model as canonical
        canonical = models[0]
        
        for other in models[1:]:
            contradictions.extend(self._compare_models(canonical, other))
        
        return contradictions
    
    def _compare_models(self, model1: SchemaModel, model2: SchemaModel) -> List[Contradiction]:
        """Compare two schema models."""
        contradictions = []
        
        # Compare models
        for name, spec1 in model1.models.items():
            if name not in model2.models:
                contradictions.append(Contradiction(
                    id=f"missing-{name}",
                    category="MISSING_MODEL",
                    severity=Severity.HIGH,
                    field_name=name,
                    source1=spec1.source,
                    source2=None,
                    value1=f"Model {name}",
                    value2="Not found",
                    impact=f"Model {name} exists in {model1.name} but not in {model2.name}",
                    suggestion=f"Add model {name} to {model2.name}"
                ))
                continue
            
            spec2 = model2.models[name]
            contradictions.extend(self._compare_fields(spec1, spec2))
        
        return contradictions
    
    def _compare_fields(self, spec1: FieldSpec, spec2: FieldSpec) -> List[Contradiction]:
        """Compare two field specs."""
        contradictions = []
        
        # Compare type
        if not spec1.type_ref.matches(spec2.type_ref):
            contradictions.append(Contradiction(
                id=f"type-{spec1.name}",
                category="TYPE_MISMATCH",
                severity=Severity.CRITICAL,
                field_name=spec1.name,
                source1=spec1.source,
                source2=spec2.source,
                value1=str(spec1.type_ref.base_type),
                value2=str(spec2.type_ref.base_type),
                impact=f"Type mismatch: {spec1.type_ref.base_type} vs {spec2.type_ref.base_type}",
                suggestion=f"Align types to {spec1.type_ref.base_type}"
            ))
        
        # Compare required
        if spec1.required != spec2.required:
            contradictions.append(Contradiction(
                id=f"required-{spec1.name}",
                category="REQUIRED_CONFLICT",
                severity=Severity.HIGH,
                field_name=spec1.name,
                source1=spec1.source,
                source2=spec2.source,
                value1="required" if spec1.required else "optional",
                value2="required" if spec2.required else "optional",
                impact=f"Required status differs",
                suggestion=f"Mark as {'required' if spec1.required else 'optional'} in both"
            ))
        
        # Compare enum values
        if spec1.type_ref.enum_values and spec2.type_ref.enum_values:
            set1 = set(spec1.type_ref.enum_values)
            set2 = set(spec2.type_ref.enum_values)
            if set1 != set2:
                contradictions.append(Contradiction(
                    id=f"enum-{spec1.name}",
                    category="ENUM_DRIFT",
                    severity=Severity.HIGH,
                    field_name=spec1.name,
                    source1=spec1.source,
                    source2=spec2.source,
                    value1=str(sorted(set1)),
                    value2=str(sorted(set2)),
                    impact=f"Enum values differ: {set1.symmetric_difference(set2)}",
                    suggestion=f"Sync enum values: {sorted(set1 | set2)}"
                ))
        
        return contradictions
```

---

### 4. Report Generators

#### Console Reporter

```python
# spec_align/reporting/console.py

from rich.console import Console
from rich.table import Table
from ..comparison.engine import Contradiction, Severity

class ConsoleReporter:
    """Human-readable console output."""
    
    def __init__(self):
        self.console = Console()
    
    def report(self, contradictions: List[Contradiction]) -> None:
        """Print contradictions to console."""
        if not contradictions:
            self.console.print("[green]✓ No contradictions found[/green]")
            return
        
        self.console.print(f"\n[red]CONTRADICTIONS FOUND: {len(contradictions)}[/red]\n")
        
        for c in contradictions:
            self._print_contradiction(c)
        
        self._print_summary(contradictions)
    
    def _print_contradiction(self, c: Contradiction) -> None:
        """Print a single contradiction."""
        severity_colors = {
            Severity.CRITICAL: "red",
            Severity.HIGH: "yellow",
            Severity.MEDIUM: "blue",
            Severity.LOW: "dim",
        }
        
        color = severity_colors.get(c.severity, "white")
        icon = "❌" if c.severity == Severity.CRITICAL else "⚠️"
        
        self.console.print(f"[{color}]{icon} {c.category}: {c.field_name}[/{color}]")
        self.console.print(f"   Severity: [{color}]{c.severity.value.upper()}[/{color}]")
        self.console.print(f"   {c.source1}: {c.value1}")
        self.console.print(f"   {c.source2}: {c.value2}")
        self.console.print(f"   Impact: {c.impact}")
        self.console.print(f"   Fix: {c.suggestion}")
        self.console.print()
    
    def _print_summary(self, contradictions: List[Contradiction]) -> None:
        """Print summary table."""
        table = Table(title="Summary")
        table.add_column("Severity", style="bold")
        table.add_column("Count", justify="right")
        
        for severity in Severity:
            count = sum(1 for c in contradictions if c.severity == severity)
            if count > 0:
                table.add_row(severity.value.upper(), str(count))
        
        self.console.print(table)
```

---

## File Structure

```
spec-alignment-checker/
├── spec_align/
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── schema.py               # Canonical schema model
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py             # Parser interface
│   │   ├── openapi.py          # OpenAPI parser
│   │   ├── pydantic.py         # Pydantic parser
│   │   ├── typescript.py       # TypeScript parser
│   │   └── jsonschema.py       # JSON Schema parser
│   ├── comparison/
│   │   ├── __init__.py
│   │   ├── engine.py           # Comparison logic
│   │   └── rules.py            # Comparison rules
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── console.py          # Human-readable output
│   │   ├── json_report.py      # JSON output
│   │   └── sarif.py            # SARIF output
│   └── utils/
│       ├── __init__.py
│       └── config.py           # Config file handling
├── tests/
│   ├── test_parsers/
│   ├── test_comparison/
│   └── test_reporting/
├── examples/
│   ├── petstore/
│   └── vtic/
├── pyproject.toml
├── README.md
└── spec-align.yaml             # Example config
```

---

## Technology Choices

| Component | Technology | Why |
|-----------|------------|-----|
| CLI | Typer + Rich | Beautiful terminal output |
| OpenAPI parsing | openapi-spec-validator | Mature, spec-compliant |
| Pydantic parsing | Python AST | No runtime import needed |
| TypeScript parsing | TypeScript compiler API | Official, accurate |
| Comparison | Custom Python | Domain-specific logic |
| Output | Rich + JSON + SARIF | Multiple consumers |
| Config | YAML | Standard for dev tools |
| Testing | pytest | Industry standard |

---

## Performance Considerations

### Caching

```python
# Cache parsed models
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def parse_cached(file_path: str, content_hash: str) -> SchemaModel:
    """Parse with caching."""
    return parser.parse(file_path)

def get_content_hash(file_path: str) -> str:
    """Get hash of file content for cache invalidation."""
    with open(file_path) as f:
        return hashlib.md5(f.read().encode()).hexdigest()
```

### Incremental Checking

```python
def check_incremental(changed_files: List[str]) -> List[Contradiction]:
    """Only re-check affected models."""
    affected_models = get_affected_models(changed_files)
    return compare(affected_models)
```

### Parallel Parsing

```python
from concurrent.futures import ThreadPoolExecutor

def parse_parallel(files: List[str]) -> List[SchemaModel]:
    """Parse files in parallel."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        return list(executor.map(parse_file, files))
```

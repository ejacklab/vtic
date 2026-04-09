# Architecture: Spec Alignment Checker

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        spec-alignment-checker                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │ OpenAPI      │    │ Pydantic     │    │ Code         │         │
│  │ Parser       │    │ Parser       │    │ Parser       │         │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘         │
│         │                   │                    │                  │
│         v                   v                    v                  │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              Canonical Schema Model                      │      │
│  │  ┌───────────┐  ┌───────────┐  ┌─────────────────────┐  │      │
│  │  │ Models    │  │ Endpoints │  │ Type Definitions    │  │      │
│  │  └───────────┘  └───────────┘  └─────────────────────┘  │      │
│  └──────────────────────────┬──────────────────────────────┘      │
│                             │                                       │
│                             v                                       │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              Comparison Engine                           │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │      │
│  │  │ Type         │  │ Required     │  │ Enum          │  │      │
│  │  │ Comparator   │  │ Comparator   │  │ Comparator    │  │      │
│  │  └──────────────┘  └──────────────┘  └───────────────┘  │      │
│  └──────────────────────────┬──────────────────────────────┘      │
│                             │                                       │
│                             v                                       │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              Report Generator                            │      │
│  │  ┌───────────┐  ┌───────────┐  ┌─────────────────────┐  │      │
│  │  │ Human     │  │ JSON      │  │ SARIF (CI/CD)       │  │      │
│  │  │ Reporter  │  │ Reporter  │  │ Reporter            │  │      │
│  │  └───────────┘  └───────────┘  └─────────────────────┘  │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Parsers

#### OpenAPI Parser

**Purpose**: Parse OpenAPI 3.x specs (YAML/JSON) into canonical schema model

**Technology**: `openapi-spec-validator` + custom parsing logic

```python
# spec_alignment_checker/parsers/openapi.py

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename
from typing import Dict, List
from ..schema import SchemaModel, EndpointSchema, FieldSchema, FieldType

class OpenAPIParser:
    """Parse OpenAPI 3.x specification into canonical schema model."""
    
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self._spec: Dict = None
    
    def parse(self) -> SchemaModel:
        """Parse and validate OpenAPI spec, return canonical model."""
        # Read and validate spec
        self._spec = read_from_filename(self.spec_path)
        validate(self._spec)
        
        model = SchemaModel()
        
        # Parse components/schemas (reusable models)
        self._parse_schemas(model)
        
        # Parse paths (endpoints)
        self._parse_endpoints(model)
        
        return model
    
    def _parse_schemas(self, model: SchemaModel) -> None:
        """Extract schema definitions from components/schemas."""
        schemas = self._spec.get('components', {}).get('schemas', {})
        
        for name, schema_def in schemas.items():
            field_schema = self._parse_schema_object(schema_def)
            model.models[name] = field_schema
    
    def _parse_endpoints(self, model: SchemaModel) -> None:
        """Extract endpoint definitions from paths."""
        paths = self._spec.get('paths', {})
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    endpoint = self._parse_operation(path, method, operation)
                    key = f"{method.upper()} {path}"
                    model.endpoints[key] = endpoint
    
    def _parse_schema_object(self, schema_def: Dict) -> FieldSchema:
        """Convert OpenAPI schema object to FieldSchema."""
        field_type = self._map_type(schema_def.get('type', 'object'))
        
        return FieldSchema(
            name=schema_def.get('name', ''),
            type=field_type,
            required=schema_def.get('required', False),
            default=schema_def.get('default'),
            enum_values=schema_def.get('enum'),
            format=schema_def.get('format'),
            description=schema_def.get('description'),
            constraints=self._extract_constraints(schema_def)
        )
    
    def _map_type(self, openapi_type: str) -> FieldType:
        """Map OpenAPI type to canonical FieldType."""
        type_map = {
            'string': FieldType.STRING,
            'integer': FieldType.INTEGER,
            'number': FieldType.NUMBER,
            'boolean': FieldType.BOOLEAN,
            'array': FieldType.ARRAY,
            'object': FieldType.OBJECT,
        }
        return type_map.get(openapi_type, FieldType.ANY)
```

#### Pydantic Parser

**Purpose**: Extract schema from Pydantic v2 models using AST analysis

**Technology**: `ast` module for static analysis, `pydantic` for runtime introspection

```python
# spec_alignment_checker/parsers/pydantic.py

import ast
import importlib.util
from pathlib import Path
from typing import List, Dict, Set
from ..schema import SchemaModel, FieldSchema, FieldType

class PydanticParser:
    """Parse Pydantic models from Python files into canonical schema."""
    
    def __init__(self, model_paths: List[str]):
        self.model_paths = [Path(p) for p in model_paths]
    
    def parse(self) -> SchemaModel:
        """Scan all Python files and extract Pydantic models."""
        model = SchemaModel()
        
        for path in self.model_paths:
            if path.is_dir():
                py_files = path.rglob('*.py')
            else:
                py_files = [path]
            
            for py_file in py_files:
                self._parse_file(py_file, model)
        
        return model
    
    def _parse_file(self, file_path: Path, model: SchemaModel) -> None:
        """Parse a single Python file for Pydantic models."""
        source = file_path.read_text()
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_pydantic_model(node):
                    field_schema = self._extract_model_schema(node, file_path)
                    model.models[node.name] = field_schema
    
    def _is_pydantic_model(self, class_node: ast.ClassDef) -> bool:
        """Check if class inherits from BaseModel."""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                return True
            if isinstance(base, ast.Attribute) and base.attr == 'BaseModel':
                return True
        return False
    
    def _extract_model_schema(self, class_node: ast.ClassDef, 
                               file_path: Path) -> FieldSchema:
        """Extract field information from Pydantic model."""
        fields = {}
        required_fields = set()
        
        for item in class_node.body:
            if isinstance(item, ast.AnnAssign):
                # Field with type annotation
                field_name = item.target.id
                field_type = self._resolve_type(item.annotation)
                is_required = item.value is None
                default_value = self._extract_default(item.value)
                
                fields[field_name] = FieldSchema(
                    name=field_name,
                    type=field_type,
                    required=is_required,
                    default=default_value,
                    location=file_path,
                    line=item.lineno
                )
        
        return FieldSchema(
            name=class_node.name,
            type=FieldType.OBJECT,
            properties=fields,
            required=list(required_fields)
        )
    
    def _resolve_type(self, annotation: ast.expr) -> FieldType:
        """Convert Python type annotation to FieldType."""
        if isinstance(annotation, ast.Name):
            type_map = {
                'str': FieldType.STRING,
                'int': FieldType.INTEGER,
                'float': FieldType.NUMBER,
                'bool': FieldType.BOOLEAN,
                'list': FieldType.ARRAY,
                'dict': FieldType.OBJECT,
            }
            return type_map.get(annotation.id, FieldType.ANY)
        
        if isinstance(annotation, ast.Subscript):
            # Handle Optional[str], List[int], etc.
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == 'Optional':
                    # Optional means it can be None (not required)
                    return self._resolve_type(annotation.slice)
                if annotation.value.id == 'List':
                    return FieldType.ARRAY
        
        return FieldType.ANY
```

#### Code Parser

**Purpose**: Extract schemas from function signatures and type hints in code

**Technology**: `ast` module + `inspect` for runtime introspection

```python
# spec_alignment_checker/parsers/code.py

import ast
from pathlib import Path
from typing import List, Dict, Optional
from ..schema import SchemaModel, EndpointSchema, FieldSchema

class CodeParser:
    """Parse implementation code for type hints and docstrings."""
    
    def __init__(self, code_paths: List[str]):
        self.code_paths = [Path(p) for p in code_paths]
    
    def parse(self) -> SchemaModel:
        """Extract schemas from code files."""
        model = SchemaModel()
        
        for path in self.code_paths:
            if path.is_dir():
                py_files = path.rglob('*.py')
            else:
                py_files = [path]
            
            for py_file in py_files:
                self._parse_file(py_file, model)
        
        return model
    
    def _parse_file(self, file_path: Path, model: SchemaModel) -> None:
        """Parse Python file for API handlers and schemas."""
        source = file_path.read_text()
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Look for route decorators
                endpoint = self._extract_endpoint(node, file_path)
                if endpoint:
                    model.endpoints[endpoint.key()] = endpoint
    
    def _extract_endpoint(self, func: ast.FunctionDef, 
                          file_path: Path) -> Optional[EndpointSchema]:
        """Extract endpoint info from function with route decorator."""
        route_info = self._parse_route_decorator(func)
        if not route_info:
            return None
        
        method, path = route_info
        
        # Extract from type hints
        request_type = self._get_request_type(func)
        return_type = self._get_return_type(func)
        
        return EndpointSchema(
            path=path,
            method=method,
            request_body=request_type,
            response_schema={200: return_type} if return_type else {},
            location=file_path,
            line=func.lineno
        )
    
    def _parse_route_decorator(self, func: ast.FunctionDef) -> Optional[tuple]:
        """Extract HTTP method and path from decorator."""
        for decorator in func.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    # @app.post("/path") or @router.get("/path")
                    method = decorator.func.attr.upper()
                    if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        if decorator.args:
                            path = decorator.args[0].value
                            return (method, path)
        return None
```

### 2. Canonical Schema Model

**Purpose**: Unified representation that all sources map to

```python
# spec_alignment_checker/schema.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

class FieldType(Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"
    NULL = "null"

@dataclass
class FieldSchema:
    """Canonical representation of a field/schema."""
    name: str
    type: FieldType
    required: bool = True
    default: Optional[Any] = None
    enum_values: Optional[List[str]] = None
    format: Optional[str] = None  # uuid, date-time, email, uri
    description: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, 'FieldSchema'] = field(default_factory=dict)
    items: Optional['FieldSchema'] = None  # For arrays
    location: Optional[Path] = None
    line: Optional[int] = None
    
    def matches(self, other: 'FieldSchema') -> tuple[bool, List[str]]:
        """Check if this schema matches another, return issues."""
        issues = []
        
        if self.type != other.type:
            issues.append(f"Type mismatch: {self.type.value} vs {other.type.value}")
        
        if self.required != other.required:
            issues.append(f"Required mismatch: {self.required} vs {other.required}")
        
        if self.enum_values and other.enum_values:
            if set(self.enum_values) != set(other.enum_values):
                issues.append(f"Enum mismatch: {self.enum_values} vs {other.enum_values}")
        
        return len(issues) == 0, issues

@dataclass
class EndpointSchema:
    """Canonical representation of an API endpoint."""
    path: str
    method: str
    request_body: Optional[FieldSchema] = None
    response_schema: Dict[int, FieldSchema] = field(default_factory=dict)
    parameters: List['ParameterSchema'] = field(default_factory=list)
    location: Optional[Path] = None
    line: Optional[int] = None
    
    def key(self) -> str:
        """Unique identifier for this endpoint."""
        return f"{self.method} {self.path}"

@dataclass
class SchemaModel:
    """Complete canonical schema model."""
    endpoints: Dict[str, EndpointSchema] = field(default_factory=dict)
    models: Dict[str, FieldSchema] = field(default_factory=dict)
    
    def merge(self, other: 'SchemaModel') -> None:
        """Merge another schema model into this one."""
        self.endpoints.update(other.endpoints)
        self.models.update(other.models)
```

### 3. Comparison Engine

**Purpose**: Detect contradictions between schema sources

```python
# spec_alignment_checker/comparison/engine.py

from dataclasses import dataclass
from typing import List, Dict, Tuple
from enum import Enum
from ..schema import SchemaModel, FieldSchema, EndpointSchema

class ContradictionType(Enum):
    TYPE_MISMATCH = "type_mismatch"
    REQUIRED_MISMATCH = "required_mismatch"
    ENUM_MISMATCH = "enum_mismatch"
    FORMAT_MISMATCH = "format_mismatch"
    MISSING_FIELD = "missing_field"
    EXTRA_FIELD = "extra_field"
    ENDPOINT_MISMATCH = "endpoint_mismatch"

class Severity(Enum):
    CRITICAL = "critical"  # Runtime failure
    HIGH = "high"          # Test failure
    MEDIUM = "medium"      # Client issue
    LOW = "low"            # Documentation drift

@dataclass
class Contradiction:
    """A detected contradiction between sources."""
    type: ContradictionType
    severity: Severity
    field_name: str
    sources: Dict[str, FieldSchema]  # source_name -> schema
    message: str
    suggestion: str
    locations: List[Tuple[str, int]]  # (file, line)

class ComparisonEngine:
    """Compare schema models and detect contradictions."""
    
    def compare(self, models: Dict[str, SchemaModel]) -> List[Contradiction]:
        """
        Compare multiple schema models and find contradictions.
        
        Args:
            models: Dict mapping source name to schema model
                   e.g., {"openapi": model1, "pydantic": model2}
        
        Returns:
            List of detected contradictions
        """
        contradictions = []
        
        # Compare models (schemas)
        contradictions.extend(self._compare_models(models))
        
        # Compare endpoints
        contradictions.extend(self._compare_endpoints(models))
        
        return contradictions
    
    def _compare_models(self, models: Dict[str, SchemaModel]) -> List[Contradiction]:
        """Compare model definitions across sources."""
        contradictions = []
        
        # Get all model names across all sources
        all_model_names = set()
        for model in models.values():
            all_model_names.update(model.models.keys())
        
        for model_name in all_model_names:
            # Get this model from each source that has it
            sources_with_model = {}
            for source_name, model in models.items():
                if model_name in model.models:
                    sources_with_model[source_name] = model.models[model_name]
            
            if len(sources_with_model) > 1:
                # Compare field by field
                contradictions.extend(
                    self._compare_model_fields(model_name, sources_with_model)
                )
        
        return contradictions
    
    def _compare_model_fields(self, model_name: str, 
                               sources: Dict[str, FieldSchema]) -> List[Contradiction]:
        """Compare fields within a model across sources."""
        contradictions = []
        
        # Get all field names
        all_fields = set()
        for schema in sources.values():
            all_fields.update(schema.properties.keys())
        
        for field_name in all_fields:
            field_schemas = {}
            for source_name, schema in sources.items():
                if field_name in schema.properties:
                    field_schemas[source_name] = schema.properties[field_name]
            
            if len(field_schemas) > 1:
                # Compare the field across sources
                contradictions.extend(
                    self._compare_field(field_name, field_schemas)
                )
        
        return contradictions
    
    def _compare_field(self, field_name: str, 
                       sources: Dict[str, FieldSchema]) -> List[Contradiction]:
        """Compare a single field across sources."""
        contradictions = []
        source_names = list(sources.keys())
        
        # Use first source as reference
        reference = sources[source_names[0]]
        
        for source_name in source_names[1:]:
            other = sources[source_name]
            
            # Type check
            if reference.type != other.type:
                contradictions.append(Contradiction(
                    type=ContradictionType.TYPE_MISMATCH,
                    severity=Severity.CRITICAL,
                    field_name=field_name,
                    sources={source_names[0]: reference, source_name: other},
                    message=f"Type mismatch: {reference.type.value} vs {other.type.value}",
                    suggestion=f"Align types in {source_name} to match {source_names[0]}",
                    locations=[
                        (str(reference.location), reference.line),
                        (str(other.location), other.line)
                    ]
                ))
            
            # Required check
            if reference.required != other.required:
                contradictions.append(Contradiction(
                    type=ContradictionType.REQUIRED_MISMATCH,
                    severity=Severity.HIGH,
                    field_name=field_name,
                    sources={source_names[0]: reference, source_name: other},
                    message=f"Required mismatch: {reference.required} vs {other.required}",
                    suggestion=f"Mark field as {'required' if reference.required else 'optional'} in {source_name}",
                    locations=[
                        (str(reference.location), reference.line),
                        (str(other.location), other.line)
                    ]
                ))
            
            # Enum check
            if reference.enum_values and other.enum_values:
                ref_enum = set(reference.enum_values)
                other_enum = set(other.enum_values)
                if ref_enum != other_enum:
                    contradictions.append(Contradiction(
                        type=ContradictionType.ENUM_MISMATCH,
                        severity=Severity.HIGH,
                        field_name=field_name,
                        sources={source_names[0]: reference, source_name: other},
                        message=f"Enum values differ: {ref_enum} vs {other_enum}",
                        suggestion=f"Synchronize enum values across sources",
                        locations=[
                            (str(reference.location), reference.line),
                            (str(other.location), other.line)
                        ]
                    ))
        
        return contradictions
```

### 4. Report Generator

```python
# spec_alignment_checker/reporting/generator.py

from typing import List
from ..comparison.engine import Contradiction, Severity

class ReportGenerator:
    """Generate human and machine-readable reports."""
    
    def generate_human_report(self, contradictions: List[Contradiction]) -> str:
        """Generate terminal-friendly report."""
        lines = []
        lines.append("=" * 70)
        lines.append("SPEC ALIGNMENT REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Summary
        critical = sum(1 for c in contradictions if c.severity == Severity.CRITICAL)
        high = sum(1 for c in contradictions if c.severity == Severity.HIGH)
        medium = sum(1 for c in contradictions if c.severity == Severity.MEDIUM)
        
        lines.append(f"Total Contradictions: {len(contradictions)}")
        lines.append(f"  ❌ Critical: {critical}")
        lines.append(f"  ⚠️  High: {high}")
        lines.append(f"  ℹ️  Medium: {medium}")
        lines.append("")
        
        # Group by severity
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM]:
            issues = [c for c in contradictions if c.severity == severity]
            if issues:
                lines.append(f"{severity.value.upper()} ISSUES")
                lines.append("-" * 40)
                for i, c in enumerate(issues, 1):
                    lines.append(f"{i}. [{c.type.value}] {c.field_name}")
                    lines.append(f"   {c.message}")
                    lines.append(f"   Fix: {c.suggestion}")
                    lines.append("")
        
        return "\n".join(lines)
    
    def generate_json_report(self, contradictions: List[Contradiction]) -> dict:
        """Generate JSON report for CI/CD."""
        return {
            "summary": {
                "total": len(contradictions),
                "critical": sum(1 for c in contradictions if c.severity == Severity.CRITICAL),
                "high": sum(1 for c in contradictions if c.severity == Severity.HIGH),
                "medium": sum(1 for c in contradictions if c.severity == Severity.MEDIUM),
            },
            "contradictions": [
                {
                    "type": c.type.value,
                    "severity": c.severity.value,
                    "field": c.field_name,
                    "message": c.message,
                    "suggestion": c.suggestion,
                    "locations": [{"file": loc[0], "line": loc[1]} for loc in c.locations]
                }
                for c in contradictions
            ]
        }
```

---

## File Structure

```
spec-alignment-checker/
├── pyproject.toml                 # Package config
├── README.md                      # Usage docs
├── spec_alignment_checker/
│   ├── __init__.py
│   ├── cli.py                     # CLI entry point
│   ├── schema.py                  # Canonical schema model
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py                # Base parser interface
│   │   ├── openapi.py             # OpenAPI parser
│   │   ├── pydantic.py            # Pydantic parser
│   │   └── code.py                # Code parser
│   ├── comparison/
│   │   ├── __init__.py
│   │   ├── engine.py              # Comparison logic
│   │   └── rules.py               # Contradiction detection rules
│   └── reporting/
│       ├── __init__.py
│       ├── generator.py           # Report generation
│       ├── human.py               # Human-readable formatter
│       ├── json_report.py         # JSON formatter
│       └── sarif.py               # SARIF (GitHub) formatter
├── tests/
│   ├── test_parsers/
│   ├── test_comparison/
│   └── test_reporting/
└── examples/
    ├── sample-openapi.yaml
    ├── sample-models.py
    └── sample-code.py
```

---

## Technology Choices

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Language** | Python 3.10+ | Matches target ecosystem (Pydantic, FastAPI) |
| **OpenAPI Parsing** | openapi-spec-validator | Mature, well-maintained |
| **Code Parsing** | ast (stdlib) | No dependencies, fast, reliable |
| **Pydantic Analysis** | ast + pydantic.v2 | Static analysis preferred, runtime fallback |
| **CLI** | typer + rich | Modern CLI with great DX |
| **Testing** | pytest + pytest-cov | Standard, excellent tooling |
| **Packaging** | poetry | Modern dependency management |

---

## Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Parse time** | <1s per 100 files | Fast enough for pre-commit |
| **Comparison time** | <1s per 1000 fields | Negligible compared to parsing |
| **Memory usage** | <100MB typical | CI-friendly |
| **Total runtime** | <5s for typical project | Fast feedback loop |

---

## Extension Points

1. **Custom Parsers**: Implement `BaseParser` to add new sources
2. **Custom Rules**: Add comparison rules via plugin system
3. **Custom Reporters**: Implement new output formats
4. **Language Support**: Add parsers for TypeScript, Go, etc.

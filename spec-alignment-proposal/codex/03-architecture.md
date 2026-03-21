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

## Component Design

### 1. CLI Entry Point

```python
# spec_align/cli.py
import click
from .core import AlignmentChecker

@click.group()
def cli():
    """Spec Alignment Checker - Detect contradictions between specs"""
    pass

@cli.command()
@click.option('--openapi', multiple=True, help='OpenAPI spec files')
@click.option('--pydantic', multiple=True, help='Pydantic model directories')
@click.option('--typescript', multiple=True, help='TypeScript type directories')
@click.option('--config', default='spec-align.yaml', help='Config file')
@click.option('--fail-on', default='critical', help='Severities that cause exit 1')
@click.option('--format', 'output_format', default='console', 
              type=click.Choice(['console', 'json', 'sarif']))
@click.option('--quick', is_flag=True, help='Fast check, skip deep analysis')
def check(openapi, pydantic, typescript, config, fail_on, output_format, quick):
    """Check alignment between specifications"""
    checker = AlignmentChecker.from_config(config)
    result = checker.check(
        openapi_specs=openapi,
        pydantic_dirs=pydantic,
        typescript_dirs=typescript,
        quick_mode=quick
    )
    
    reporter = get_reporter(output_format)
    reporter.report(result)
    
    if result.has_severity(fail_on):
        raise SystemExit(1)

@cli.command()
def watch():
    """Watch for changes and recheck continuously"""
    pass

@cli.command()
@click.argument('contradiction_id')
def explain(contradiction_id):
    """Explain a contradiction and suggest fixes"""
    pass

@cli.command()
@click.argument('contradiction_id')
@click.option('--strategy', type=click.Choice(['openapi', 'pydantic', 'typescript']))
def fix(contradiction_id, strategy):
    """Auto-fix a contradiction"""
    pass
```

### 2. Discovery Engine

```python
# spec_align/discovery.py
from pathlib import Path
from typing import List, Dict
import fnmatch

class SpecDiscovery:
    """Find all spec files in a project"""
    
    PATTERNS = {
        'openapi': ['openapi.yaml', 'openapi.yml', 'openapi.json', 'api-spec.yaml'],
        'pydantic': ['*.py'],  # Will filter for BaseModel subclasses
        'typescript': ['*.ts', '*.tsx'],  # Will filter for interfaces
        'jsonschema': ['*.schema.json', 'schemas/*.json'],
    }
    
    def __init__(self, root: Path, config: Dict):
        self.root = root
        self.config = config
        self.ignore_patterns = config.get('ignore', ['node_modules', '.git', '__pycache__'])
    
    def discover(self) -> Dict[str, List[Path]]:
        """Find all relevant spec files"""
        results = {
            'openapi': [],
            'pydantic': [],
            'typescript': [],
            'jsonschema': [],
        }
        
        for file_path in self._walk():
            category = self._categorize(file_path)
            if category:
                results[category].append(file_path)
        
        return results
    
    def _walk(self) -> List[Path]:
        """Walk directory tree, respecting ignores"""
        for path in self.root.rglob('*'):
            if path.is_file() and not self._should_ignore(path):
                yield path
    
    def _should_ignore(self, path: Path) -> bool:
        for pattern in self.ignore_patterns:
            if pattern in str(path):
                return True
        return False
    
    def _categorize(self, path: Path) -> str:
        """Determine which category a file belongs to"""
        name = path.name
        suffix = path.suffix
        
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if fnmatch.fnmatch(name, pattern):
                    # Secondary check for content
                    if self._verify_category(path, category):
                        return category
        return None
    
    def _verify_category(self, path: Path, category: str) -> bool:
        """Verify file actually contains relevant content"""
        # Quick content check to avoid false positives
        try:
            content = path.read_text()[:5000]  # Sample first 5KB
            
            if category == 'openapi':
                return 'openapi:' in content or '"openapi"' in content
            elif category == 'pydantic':
                return 'BaseModel' in content
            elif category == 'typescript':
                return 'interface ' in content or 'type ' in content
            elif category == 'jsonschema':
                return '$schema' in content
            
        except Exception:
            return False
```

### 3. Normalization Layer

The key innovation: canonical intermediate representation.

```python
# spec_align/normalize/canonical.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum

class BaseType(Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"
    ANY = "any"

@dataclass
class SourceLocation:
    file: str
    line: int
    column: int
    
    def __str__(self):
        return f"{self.file}:{self.line}:{self.column}"

@dataclass
class TypeRef:
    """Canonical type reference"""
    base_type: BaseType
    format: Optional[str] = None  # date-time, uuid, etc.
    enum_values: Optional[List[str]] = None
    array_item: Optional['TypeRef'] = None
    object_fields: Optional[Dict[str, 'FieldSpec']] = None
    nullable: bool = False
    union_types: Optional[List['TypeRef']] = None

@dataclass
class FieldSpec:
    """Canonical field specification"""
    name: str
    type_ref: TypeRef
    required: bool
    default: Optional[Any] = None
    description: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    source: SourceLocation = None
    examples: List[Any] = field(default_factory=list)
    
    # Constraints examples:
    # - min_length, max_length (strings)
    # - minimum, maximum (numbers)
    # - pattern (regex)
    # - min_items, max_items (arrays)

@dataclass
class SchemaSpec:
    """Canonical schema specification"""
    name: str
    fields: Dict[str, FieldSpec]
    source: SourceLocation
    description: Optional[str] = None
    extends: Optional[List[str]] = None
```

### 4. Parsers (Normalization Implementations)

```python
# spec_align/normalize/openapi_parser.py
import yaml
from pathlib import Path
from .canonical import SchemaSpec, FieldSpec, TypeRef, BaseType, SourceLocation

class OpenAPIParser:
    """Convert OpenAPI schemas to canonical format"""
    
    def parse(self, file_path: Path) -> List[SchemaSpec]:
        with open(file_path) as f:
            spec = yaml.safe_load(f)
        
        schemas = []
        components = spec.get('components', {}).get('schemas', {})
        
        for name, schema in components.items():
            schemas.append(self._parse_schema(name, schema, file_path))
        
        return schemas
    
    def _parse_schema(self, name: str, schema: dict, file_path: Path) -> SchemaSpec:
        fields = {}
        required = set(schema.get('required', []))
        properties = schema.get('properties', {})
        
        for prop_name, prop_spec in properties.items():
            location = SourceLocation(
                file=str(file_path),
                line=self._find_line(file_path, prop_name),
                column=0
            )
            fields[prop_name] = FieldSpec(
                name=prop_name,
                type_ref=self._parse_type(prop_spec),
                required=prop_name in required,
                default=prop_spec.get('default'),
                description=prop_spec.get('description'),
                constraints=self._extract_constraints(prop_spec),
                source=location
            )
        
        return SchemaSpec(
            name=name,
            fields=fields,
            source=SourceLocation(str(file_path), 0, 0),
            description=schema.get('description')
        )
    
    def _parse_type(self, spec: dict) -> TypeRef:
        if 'enum' in spec:
            return TypeRef(
                base_type=BaseType.STRING,
                enum_values=spec['enum']
            )
        
        type_str = spec.get('type', 'object')
        base = BaseType(type_str)
        
        if base == BaseType.ARRAY:
            items = spec.get('items', {})
            return TypeRef(
                base_type=base,
                array_item=self._parse_type(items)
            )
        
        if base == BaseType.OBJECT:
            # Nested object
            fields = {}
            required = set(spec.get('required', []))
            for name, prop in spec.get('properties', {}).items():
                fields[name] = FieldSpec(
                    name=name,
                    type_ref=self._parse_type(prop),
                    required=name in required
                )
            return TypeRef(
                base_type=base,
                object_fields=fields
            )
        
        return TypeRef(
            base_type=base,
            format=spec.get('format'),
            nullable=spec.get('nullable', False)
        )
```

```python
# spec_align/normalize/pydantic_parser.py
import ast
from pathlib import Path
from typing import List
from .canonical import SchemaSpec, FieldSpec, TypeRef, BaseType, SourceLocation

class PydanticParser:
    """Convert Pydantic models to canonical format"""
    
    def parse(self, file_path: Path) -> List[SchemaSpec]:
        source = file_path.read_text()
        tree = ast.parse(source)
        
        schemas = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_pydantic_model(node):
                    schemas.append(self._parse_model(node, file_path, source))
        
        return schemas
    
    def _is_pydantic_model(self, node: ast.ClassDef) -> bool:
        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in ('BaseModel', 'Document', 'Model'):
                    return True
            elif isinstance(base, ast.Attribute):
                if base.attr in ('BaseModel', 'Document', 'Model'):
                    return True
        return False
    
    def _parse_model(self, node: ast.ClassDef, file_path: Path, source: str) -> SchemaSpec:
        fields = {}
        
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                field_name = item.target.id
                field_spec = self._parse_field(item, file_path)
                fields[field_name] = field_spec
        
        return SchemaSpec(
            name=node.name,
            fields=fields,
            source=SourceLocation(str(file_path), node.lineno, node.col_offset)
        )
    
    def _parse_field(self, node: ast.AnnAssign, file_path: Path) -> FieldSpec:
        type_ref = self._parse_annotation(node.annotation)
        
        has_default = node.value is not None
        is_field_call = isinstance(node.value, ast.Call) and \
                        isinstance(node.value.func, ast.Name) and \
                        node.value.func.id == 'Field'
        
        default = None
        if has_default and not is_field_call:
            default = self._eval_default(node.value)
        
        return FieldSpec(
            name=node.target.id,
            type_ref=type_ref,
            required=not has_default,
            default=default,
            source=SourceLocation(str(file_path), node.lineno, node.col_offset)
        )
    
    def _parse_annotation(self, annotation) -> TypeRef:
        # Handle simple types
        if isinstance(annotation, ast.Name):
            type_map = {
                'str': BaseType.STRING,
                'int': BaseType.INTEGER,
                'float': BaseType.NUMBER,
                'bool': BaseType.BOOLEAN,
                'list': BaseType.ARRAY,
                'dict': BaseType.OBJECT,
            }
            base = type_map.get(annotation.id, BaseType.ANY)
            return TypeRef(base_type=base)
        
        # Handle Optional[X]
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == 'Optional':
                    inner = self._parse_annotation(annotation.slice)
                    inner.nullable = True
                    return inner
                elif annotation.value.id == 'List':
                    inner = self._parse_annotation(annotation.slice)
                    return TypeRef(base_type=BaseType.ARRAY, array_item=inner)
        
        # Handle Enum
        # TODO: Look up enum definition
        
        return TypeRef(base_type=BaseType.ANY)
```

### 5. Comparison Engine

```python
# spec_align/compare/engine.py
from typing import List, Tuple
from ..normalize.canonical import SchemaSpec, FieldSpec, TypeRef
from .contradiction import Contradiction, ContradictionType, Severity

class ComparisonEngine:
    """Compare canonical schemas and detect contradictions"""
    
    def compare(self, schemas: List[Tuple[str, SchemaSpec]]) -> List[Contradiction]:
        """
        schemas: List of (source_name, schema_spec) pairs
        Returns: List of detected contradictions
        """
        contradictions = []
        
        # Group schemas by name
        by_name = {}
        for source, schema in schemas:
            if schema.name not in by_name:
                by_name[schema.name] = []
            by_name[schema.name].append((source, schema))
        
        # Compare schemas with same name across sources
        for name, sources in by_name.items():
            if len(sources) > 1:
                contradictions.extend(self._compare_schemas(name, sources))
        
        return contradictions
    
    def _compare_schemas(self, name: str, sources: List[Tuple[str, SchemaSpec]]) -> List[Contradiction]:
        contradictions = []
        base_source, base_schema = sources[0]
        
        for other_source, other_schema in sources[1:]:
            # Compare fields
            all_fields = set(base_schema.fields.keys()) | set(other_schema.fields.keys())
            
            for field_name in all_fields:
                base_field = base_schema.fields.get(field_name)
                other_field = other_schema.fields.get(field_name)
                
                if base_field is None:
                    contradictions.append(Contradiction(
                        type=ContradictionType.MISSING_FIELD,
                        severity=Severity.MEDIUM,
                        schema_name=name,
                        field_name=field_name,
                        sources={
                            base_source: "present",
                            other_source: "missing"
                        },
                        message=f"Field {field_name} missing in {base_source}"
                    ))
                    continue
                
                if other_field is None:
                    contradictions.append(Contradiction(
                        type=ContradictionType.MISSING_FIELD,
                        severity=Severity.MEDIUM,
                        schema_name=name,
                        field_name=field_name,
                        sources={
                            base_source: "present",
                            other_source: "missing"
                        },
                        message=f"Field {field_name} missing in {other_source}"
                    ))
                    continue
                
                # Both have the field, compare it
                contradictions.extend(
                    self._compare_fields(name, field_name, base_field, other_field, 
                                         base_source, other_source)
                )
        
        return contradictions
    
    def _compare_fields(self, schema_name: str, field_name: str,
                        field1: FieldSpec, field2: FieldSpec,
                        source1: str, source2: str) -> List[Contradiction]:
        contradictions = []
        
        # Check required status
        if field1.required != field2.required:
            contradictions.append(Contradiction(
                type=ContradictionType.REQUIRED_CONFLICT,
                severity=Severity.HIGH,
                schema_name=schema_name,
                field_name=field_name,
                sources={
                    source1: f"required={field1.required}",
                    source2: f"required={field2.required}"
                },
                message=f"Required status mismatch for {field_name}"
            ))
        
        # Check type
        type_contradiction = self._compare_types(
            schema_name, field_name, field1.type_ref, field2.type_ref,
            source1, source2
        )
        if type_contradiction:
            contradictions.append(type_contradiction)
        
        # Check default
        if field1.default != field2.default and field1.default is not None and field2.default is not None:
            contradictions.append(Contradiction(
                type=ContradictionType.DEFAULT_CONFLICT,
                severity=Severity.MEDIUM,
                schema_name=schema_name,
                field_name=field_name,
                sources={
                    source1: f"default={field1.default}",
                    source2: f"default={field2.default}"
                },
                message=f"Default value mismatch for {field_name}"
            ))
        
        return contradictions
    
    def _compare_types(self, schema_name: str, field_name: str,
                       type1: TypeRef, type2: TypeRef,
                       source1: str, source2: str) -> Contradiction:
        # Check base type
        if type1.base_type != type2.base_type:
            return Contradiction(
                type=ContradictionType.TYPE_MISMATCH,
                severity=Severity.CRITICAL,
                schema_name=schema_name,
                field_name=field_name,
                sources={
                    source1: f"type={type1.base_type.value}",
                    source2: f"type={type2.base_type.value}"
                },
                message=f"Type mismatch for {field_name}"
            )
        
        # Check enum values
        if type1.enum_values and type2.enum_values:
            set1 = set(type1.enum_values)
            set2 = set(type2.enum_values)
            if set1 != set2:
                return Contradiction(
                    type=ContradictionType.ENUM_DRIFT,
                    severity=Severity.HIGH,
                    schema_name=schema_name,
                    field_name=field_name,
                    sources={
                        source1: f"enum={sorted(set1)}",
                        source2: f"enum={sorted(set2)}"
                    },
                    message=f"Enum values differ for {field_name}"
                )
        
        # Check format
        if type1.format != type2.format and type1.format and type2.format:
            return Contradiction(
                type=ContradictionType.FORMAT_MISMATCH,
                severity=Severity.MEDIUM,
                schema_name=schema_name,
                field_name=field_name,
                sources={
                    source1: f"format={type1.format}",
                    source2: f"format={type2.format}"
                },
                message=f"Format mismatch for {field_name}"
            )
        
        return None
```

### 6. Report Generator

```python
# spec_align/report/console.py
from rich.console import Console
from rich.table import Table
from ..compare.contradiction import Contradiction, Severity

class ConsoleReporter:
    def __init__(self):
        self.console = Console()
    
    def report(self, result: 'AlignmentResult'):
        self.console.print()
        
        if not result.contradictions:
            self.console.print("[green]✓ No contradictions found[/green]")
            return
        
        # Summary
        by_severity = {}
        for c in result.contradictions:
            by_severity[c.severity] = by_severity.get(c.severity, 0) + 1
        
        self.console.print(f"[red]CONTRADICTIONS FOUND: {len(result.contradictions)}[/red]\n")
        
        # Details
        for i, c in enumerate(result.contradictions, 1):
            self._print_contradiction(i, c)
        
        # Summary table
        self._print_summary(by_severity)
    
    def _print_contradiction(self, index: int, c: Contradiction):
        severity_colors = {
            Severity.CRITICAL: "red",
            Severity.HIGH: "yellow",
            Severity.MEDIUM: "blue",
            Severity.LOW: "white",
            Severity.INFO: "dim",
        }
        color = severity_colors.get(c.severity, "white")
        
        self.console.print(f"[{color}]{'━' * 70}[/{color}]")
        self.console.print(f"[{color}]❌ {c.type.value.upper()}: {c.schema_name}.{c.field_name}[/{color}]")
        self.console.print(f"   Severity: [{color}]{c.severity.value.upper()}[/{color}]")
        self.console.print(f"   {c.message}")
        
        for source, value in c.sources.items():
            self.console.print(f"   {source}: {value}")
        
        self.console.print()
    
    def _print_summary(self, by_severity: dict):
        table = Table(title="Summary")
        table.add_column("Severity")
        table.add_column("Count", justify="right")
        
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            count = by_severity.get(severity, 0)
            if count > 0:
                table.add_row(severity.value.upper(), str(count))
        
        self.console.print(table)
```

## File Structure

```
spec-alignment-checker/
├── pyproject.toml
├── spec_align/
│   ├── __init__.py
│   ├── cli.py                    # CLI entry point
│   ├── core.py                   # Main AlignmentChecker class
│   ├── config.py                 # Configuration loading
│   ├── discovery.py              # File discovery
│   ├── normalize/
│   │   ├── __init__.py
│   │   ├── canonical.py          # Canonical schema types
│   │   ├── openapi_parser.py     # OpenAPI → Canonical
│   │   ├── pydantic_parser.py    # Pydantic → Canonical
│   │   ├── typescript_parser.py  # TypeScript → Canonical
│   │   └── jsonschema_parser.py  # JSON Schema → Canonical
│   ├── compare/
│   │   ├── __init__.py
│   │   ├── engine.py             # Comparison logic
│   │   └── contradiction.py      # Contradiction types
│   ├── report/
│   │   ├── __init__.py
│   │   ├── console.py            # Rich console output
│   │   ├── json_reporter.py      # JSON output
│   │   └── sarif.py              # SARIF for GitHub
│   └── fix/
│       ├── __init__.py
│       └── suggester.py          # Fix suggestions
└── tests/
    ├── test_openapi_parser.py
    ├── test_pydantic_parser.py
    ├── test_comparison.py
    └── fixtures/
        ├── sample_openapi.yaml
        └── sample_pydantic.py
```

## Tech Choices

### Language: Python 3.10+

- Rich ecosystem for AST parsing (Python) and YAML handling
- Good CLI tools (click, rich)
- Easy to integrate with OpenClaw (also Python)

### Key Libraries

| Library | Purpose |
|---------|---------|
| click | CLI framework |
| rich | Beautiful console output |
| pyyaml | OpenAPI parsing |
| pydantic | Internal config validation |
| AST (stdlib) | Python code parsing |
| tree-sitter | TypeScript parsing (via py-tree-sitter) |
| jsonschema | JSON Schema validation |

### Why Not TypeScript?

Considered TypeScript (better TS parsing), but:
- Python better for AST parsing of Pydantic
- OpenClaw is Python
- Can still parse TS via tree-sitter

### Why Not Use Existing Tools?

| Tool | What It Does | What It Doesn't Do |
|------|--------------|-------------------|
| Spectral | OpenAPI linting | Cross-format comparison |
| datamodel-code-generator | Generates Pydantic from OpenAPI | Detects drift in existing code |
| openapi-typescript | Generates TS from OpenAPI | Doesn't check existing TS |
| mypy | Python type checking | Doesn't check against OpenAPI |

`spec-alignment-checker` fills the gap: **cross-format contradiction detection**.

## Performance Considerations

### Incremental Checking

```python
# Cache normalized schemas
class CachedParser:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
    
    def parse(self, file_path: Path) -> List[SchemaSpec]:
        cache_key = self._get_cache_key(file_path)
        cached = self._load_cache(cache_key)
        
        if cached and cached.mtime >= file_path.stat().st_mtime:
            return cached.schemas
        
        schemas = self._parse_fresh(file_path)
        self._save_cache(cache_key, schemas)
        return schemas
```

### Parallel Parsing

```python
from concurrent.futures import ThreadPoolExecutor

def parse_all(files: List[Path]) -> List[SchemaSpec]:
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(parser.parse, files)
    return list(results)
```

Target: Check 100 schemas in <5 seconds on first run, <1 second on cached runs.

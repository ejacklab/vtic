"""Tests for API Response Models (Stage 4)

Tests for ErrorResponse, PaginatedResponse, HealthResponse, StatsResponse,
ReindexResult, DoctorResult, and related nested models.
"""

import json
import pytest
from datetime import datetime, timezone
from typing import List
from pydantic import ValidationError

from vtic.models.api import (
    ErrorDetail,
    ErrorObject,
    ErrorResponse,
    PaginationMeta,
    PaginatedResponse,
    IndexStatus,
    EmbeddingProviderInfo,
    HealthResponse,
    StatsTotals,
    DateRange,
    StatsResponse,
    ReindexError,
    ReindexResult,
    DoctorCheck,
    DoctorResult,
    ERROR_CODES,
)


# =============================================================================
# ErrorDetail Tests
# =============================================================================

class TestErrorDetail:
    """Test ErrorDetail model."""
    
    def test_required_message(self):
        """ErrorDetail requires message."""
        detail = ErrorDetail(message="Invalid value")
        assert detail.message == "Invalid value"
    
    def test_optional_fields(self):
        """ErrorDetail has optional field and value."""
        detail = ErrorDetail(
            field="severity",
            message="Invalid value. Expected one of: critical, high, medium, low, info",
            value="urgent"
        )
        assert detail.field == "severity"
        assert detail.value == "urgent"
    
    def test_serialization(self):
        """ErrorDetail serializes to valid JSON."""
        detail = ErrorDetail(field="query", message="Required field is missing", value=None)
        data = json.loads(detail.model_dump_json())
        assert data["field"] == "query"
        assert data["message"] == "Required field is missing"
        assert data["value"] is None


# =============================================================================
# ErrorObject Tests
# =============================================================================

class TestErrorObject:
    """Test ErrorObject model."""
    
    def test_required_fields(self):
        """ErrorObject requires code and message."""
        error = ErrorObject(code="VALIDATION_ERROR", message="Query string cannot be empty")
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Query string cannot be empty"
    
    def test_optional_fields(self):
        """ErrorObject has optional details and docs."""
        error = ErrorObject(
            code="SERVICE_UNAVAILABLE",
            message="Semantic search requested but no embedding provider configured",
            details=[
                ErrorDetail(field="semantic", message="Set 'semantic: false'", value=True)
            ],
            docs="https://vtic.ejai.ai/docs/semantic-search"
        )
        assert error.details is not None
        assert len(error.details) == 1
        assert error.docs == "https://vtic.ejai.ai/docs/semantic-search"


# =============================================================================
# ErrorResponse Tests
# =============================================================================

class TestErrorResponse:
    """Test ErrorResponse model with nested structure (matches OpenAPI exactly)."""
    
    def test_nested_structure(self):
        """ErrorResponse uses nested error object per OpenAPI spec."""
        response = ErrorResponse(
            error=ErrorObject(
                code="VALIDATION_ERROR",
                message="Query string cannot be empty"
            )
        )
        assert response.error.code == "VALIDATION_ERROR"
        assert response.error.message == "Query string cannot be empty"
    
    def test_with_details(self):
        """ErrorResponse with field-level validation errors."""
        response = ErrorResponse(
            error=ErrorObject(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details=[
                    ErrorDetail(field="query", message="Required field is missing", value=None),
                    ErrorDetail(field="limit", message="Must be between 1 and 100", value=200)
                ]
            )
        )
        assert len(response.error.details) == 2
    
    def test_create_factory_method(self):
        """ErrorResponse.create() factory method."""
        response = ErrorResponse.create(
            code="NOT_FOUND",
            message="Ticket 'S1' not found",
            docs="https://vtic.ejai.ai/docs/errors"
        )
        assert response.error.code == "NOT_FOUND"
        assert response.error.message == "Ticket 'S1' not found"
        assert response.error.docs == "https://vtic.ejai.ai/docs/errors"
    
    def test_validation_error_factory(self):
        """ErrorResponse.validation_error() factory method."""
        response = ErrorResponse.validation_error(
            message="Query string cannot be empty",
            details=[ErrorDetail(field="query", message="Required field is missing")]
        )
        assert response.error.code == "VALIDATION_ERROR"
    
    def test_not_found_factory(self):
        """ErrorResponse.not_found() factory method."""
        response = ErrorResponse.not_found(resource="Ticket", identifier="S1")
        assert response.error.code == "NOT_FOUND"
        assert "S1" in response.error.message
    
    def test_serialization(self):
        """ErrorResponse serializes to valid JSON with nested structure."""
        response = ErrorResponse(
            error=ErrorObject(
                code="SERVICE_UNAVAILABLE",
                message="Semantic search requested but no embedding provider is configured",
                details=[
                    ErrorDetail(
                        field="semantic",
                        message="Set 'semantic: false' or configure an embedding provider",
                        value=True
                    )
                ],
                docs="https://vtic.ejai.ai/docs/semantic-search"
            )
        )
        
        json_str = response.model_dump_json()
        data = json.loads(json_str)
        
        # Verify nested structure matches OpenAPI
        assert "error" in data
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert data["error"]["message"] == "Semantic search requested but no embedding provider is configured"
        assert len(data["error"]["details"]) == 1
        assert data["error"]["docs"] == "https://vtic.ejai.ai/docs/semantic-search"


# =============================================================================
# PaginationMeta Tests
# =============================================================================

class TestPaginationMeta:
    """Test PaginationMeta model."""
    
    def test_required_fields(self):
        """PaginationMeta requires total, limit, offset, has_more."""
        meta = PaginationMeta(total=100, limit=20, offset=0, has_more=True)
        assert meta.total == 100
        assert meta.limit == 20
        assert meta.offset == 0
        assert meta.has_more is True
    
    def test_request_id_optional(self):
        """request_id is optional."""
        meta = PaginationMeta(total=100, limit=20, offset=0, has_more=True, request_id="req_abc123")
        assert meta.request_id == "req_abc123"
        
        meta = PaginationMeta(total=100, limit=20, offset=0, has_more=True)
        assert meta.request_id is None
    
    def test_create_factory(self):
        """PaginationMeta.create() calculates has_more automatically."""
        # has_more = True when offset + limit < total
        meta = PaginationMeta.create(total=100, limit=20, offset=0)
        assert meta.has_more is True
        
        # At offset 79, items 79-98, one more item at index 99
        meta = PaginationMeta.create(total=100, limit=20, offset=79)
        assert meta.has_more is True
        
        # At offset 80, items 80-99, exactly the last page
        meta = PaginationMeta.create(total=100, limit=20, offset=80)
        assert meta.has_more is False
        
        meta = PaginationMeta.create(total=100, limit=20, offset=100)
        assert meta.has_more is False
    
    def test_validation_total_ge_0(self):
        """total must be >= 0."""
        with pytest.raises(ValidationError):
            PaginationMeta(total=-1, limit=20, offset=0, has_more=False)
    
    def test_validation_limit_ge_1(self):
        """limit must be >= 1."""
        with pytest.raises(ValidationError):
            PaginationMeta(total=100, limit=0, offset=0, has_more=False)
    
    def test_validation_offset_ge_0(self):
        """offset must be >= 0."""
        with pytest.raises(ValidationError):
            PaginationMeta(total=100, limit=20, offset=-1, has_more=False)


# =============================================================================
# PaginatedResponse Tests
# =============================================================================

class TestPaginatedResponse:
    """Test PaginatedResponse generic model."""
    
    def test_generic_typing(self):
        """PaginatedResponse works as a generic type."""
        # Using dict items for simplicity
        response: PaginatedResponse[dict] = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}],
            meta=PaginationMeta(total=10, limit=2, offset=0, has_more=True)
        )
        assert len(response.data) == 2
        assert response.data[0]["id"] == 1
    
    def test_create_factory(self):
        """PaginatedResponse.create() factory method."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = PaginatedResponse.create(
            items=items,
            total=10,
            limit=3,
            offset=0,
            request_id="req_123"
        )
        assert len(response.data) == 3
        assert response.meta.total == 10
        assert response.meta.has_more is True
        assert response.meta.request_id == "req_123"
    
    def test_empty_data(self):
        """PaginatedResponse can have empty data."""
        response = PaginatedResponse(
            data=[],
            meta=PaginationMeta(total=0, limit=20, offset=0, has_more=False)
        )
        assert response.data == []
    
    def test_serialization(self):
        """PaginatedResponse serializes to valid JSON."""
        response = PaginatedResponse(
            data=[{"name": "item1"}, {"name": "item2"}],
            meta=PaginationMeta(
                total=100,
                limit=2,
                offset=0,
                has_more=True,
                request_id="req_abc123"
            )
        )
        
        json_str = response.model_dump_json()
        data = json.loads(json_str)
        
        assert "data" in data
        assert "meta" in data
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == 100
        assert data["meta"]["request_id"] == "req_abc123"


# =============================================================================
# IndexStatus Tests
# =============================================================================

class TestIndexStatus:
    """Test IndexStatus model."""
    
    def test_required_fields(self):
        """IndexStatus requires zvec and ticket_count."""
        status = IndexStatus(zvec="available", ticket_count=82)
        assert status.zvec == "available"
        assert status.ticket_count == 82
    
    def test_zvec_values(self):
        """zvec must be available, unavailable, or corrupted."""
        IndexStatus(zvec="available", ticket_count=82)
        IndexStatus(zvec="unavailable", ticket_count=82)
        IndexStatus(zvec="corrupted", ticket_count=82)
        
        with pytest.raises(ValidationError):
            IndexStatus(zvec="invalid", ticket_count=82)
    
    def test_last_reindex_optional(self):
        """last_reindex is optional."""
        dt = datetime(2026, 3, 17, 8, 0, 0, tzinfo=timezone.utc)
        status = IndexStatus(zvec="available", ticket_count=82, last_reindex=dt)
        assert status.last_reindex == dt
        
        status = IndexStatus(zvec="available", ticket_count=82)
        assert status.last_reindex is None


# =============================================================================
# EmbeddingProviderInfo Tests
# =============================================================================

class TestEmbeddingProviderInfo:
    """Test EmbeddingProviderInfo model."""
    
    def test_required_name(self):
        """EmbeddingProviderInfo requires name."""
        info = EmbeddingProviderInfo(name="local")
        assert info.name == "local"
    
    def test_name_values(self):
        """name must be local, openai, custom, or none."""
        EmbeddingProviderInfo(name="local")
        EmbeddingProviderInfo(name="openai")
        EmbeddingProviderInfo(name="custom")
        EmbeddingProviderInfo(name="none")
        
        with pytest.raises(ValidationError):
            EmbeddingProviderInfo(name="invalid")
    
    def test_optional_fields(self):
        """model and dimension are optional."""
        info = EmbeddingProviderInfo(name="local", model="all-MiniLM-L6-v2", dimension=384)
        assert info.model == "all-MiniLM-L6-v2"
        assert info.dimension == 384


# =============================================================================
# HealthResponse Tests
# =============================================================================

class TestHealthResponse:
    """Test HealthResponse model with nested objects."""
    
    def test_required_fields(self):
        """HealthResponse requires status, version, and index_status."""
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            index_status=IndexStatus(zvec="available", ticket_count=82)
        )
        assert response.status == "healthy"
        assert response.version == "0.1.0"
    
    def test_status_values(self):
        """status must be healthy, degraded, or unhealthy."""
        HealthResponse(
            status="healthy",
            version="0.1.0",
            index_status=IndexStatus(zvec="available", ticket_count=82)
        )
        HealthResponse(
            status="degraded",
            version="0.1.0",
            index_status=IndexStatus(zvec="available", ticket_count=82)
        )
        HealthResponse(
            status="unhealthy",
            version="0.1.0",
            index_status=IndexStatus(zvec="corrupted", ticket_count=0)
        )
        
        with pytest.raises(ValidationError):
            HealthResponse(
                status="invalid",
                version="0.1.0",
                index_status=IndexStatus(zvec="available", ticket_count=82)
            )
    
    def test_with_nested_objects(self):
        """HealthResponse with nested IndexStatus and EmbeddingProviderInfo."""
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            uptime_seconds=86400,
            index_status=IndexStatus(
                zvec="available",
                ticket_count=82,
                last_reindex=datetime(2026, 3, 17, 8, 0, 0, tzinfo=timezone.utc)
            ),
            embedding_provider=EmbeddingProviderInfo(
                name="local",
                model="all-MiniLM-L6-v2",
                dimension=384
            )
        )
        assert response.uptime_seconds == 86400
        assert response.index_status.ticket_count == 82
        assert response.embedding_provider.model == "all-MiniLM-L6-v2"
    
    def test_create_factory_healthy(self):
        """HealthResponse.create() with healthy status."""
        response = HealthResponse.create(
            version="0.1.0",
            uptime_seconds=86400,
            zvec_status="available",
            ticket_count=82,
            last_reindex=datetime(2026, 3, 17, 8, 0, 0, tzinfo=timezone.utc),
            provider_name="local",
            provider_model="all-MiniLM-L6-v2",
            provider_dimension=384
        )
        assert response.status == "healthy"
    
    def test_create_factory_degraded(self):
        """HealthResponse.create() with degraded status."""
        # Degraded when provider is none
        response = HealthResponse.create(
            version="0.1.0",
            uptime_seconds=3600,
            zvec_status="available",
            ticket_count=82,
            last_reindex=None,
            provider_name="none"
        )
        assert response.status == "degraded"
        
        # Degraded when zvec is unavailable
        response = HealthResponse.create(
            version="0.1.0",
            uptime_seconds=3600,
            zvec_status="unavailable",
            ticket_count=82,
            last_reindex=None,
            provider_name="local"
        )
        assert response.status == "degraded"
    
    def test_create_factory_unhealthy(self):
        """HealthResponse.create() with unhealthy status."""
        response = HealthResponse.create(
            version="0.1.0",
            uptime_seconds=120,
            zvec_status="corrupted",
            ticket_count=0,
            last_reindex=None,
            provider_name="none"
        )
        assert response.status == "unhealthy"
    
    def test_serialization(self):
        """HealthResponse serializes to valid JSON with nested objects."""
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            uptime_seconds=86400,
            index_status=IndexStatus(
                zvec="available",
                ticket_count=82,
                last_reindex=datetime(2026, 3, 17, 8, 0, 0, tzinfo=timezone.utc)
            ),
            embedding_provider=EmbeddingProviderInfo(
                name="local",
                model="all-MiniLM-L6-v2",
                dimension=384
            )
        )
        
        json_str = response.model_dump_json()
        data = json.loads(json_str)
        
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["uptime_seconds"] == 86400
        assert data["index_status"]["zvec"] == "available"
        assert data["index_status"]["ticket_count"] == 82
        assert data["embedding_provider"]["name"] == "local"
        assert data["embedding_provider"]["model"] == "all-MiniLM-L6-v2"


# =============================================================================
# StatsTotals Tests
# =============================================================================

class TestStatsTotals:
    """Test StatsTotals model."""
    
    def test_required_fields(self):
        """StatsTotals requires all, open, closed."""
        totals = StatsTotals(all=82, open=23, closed=59)
        assert totals.all == 82
        assert totals.open == 23
        assert totals.closed == 59
    
    def test_validation_ge_0(self):
        """All counts must be >= 0."""
        with pytest.raises(ValidationError):
            StatsTotals(all=-1, open=0, closed=0)


# =============================================================================
# StatsResponse Tests
# =============================================================================

class TestStatsResponse:
    """Test StatsResponse model with totals and breakdowns."""
    
    def test_required_fields(self):
        """StatsResponse requires totals, by_status, by_severity, by_category."""
        response = StatsResponse(
            totals=StatsTotals(all=82, open=23, closed=59),
            by_status={"open": 15, "in_progress": 8, "fixed": 42},
            by_severity={"critical": 2, "high": 10, "medium": 35, "low": 25, "info": 10},
            by_category={"crash": 8, "hotfix": 5, "feature": 22, "security": 12, "general": 35}
        )
        assert response.totals.all == 82
        assert response.by_status["open"] == 15
        assert response.by_severity["critical"] == 2
        assert response.by_category["crash"] == 8
    
    def test_optional_fields(self):
        """by_repo and date_range are optional."""
        response = StatsResponse(
            totals=StatsTotals(all=82, open=23, closed=59),
            by_status={"open": 15},
            by_severity={"critical": 2},
            by_category={"crash": 8},
            by_repo={"ejacklab/open-dsearch": 45, "ejacklab/vtic": 25},
            date_range=DateRange(
                earliest=datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc),
                latest=datetime(2024, 12, 20, 14, 45, 0, tzinfo=timezone.utc)
            )
        )
        assert response.by_repo is not None
        assert response.date_range is not None
    
    def test_create_factory(self):
        """StatsResponse.create() factory method."""
        response = StatsResponse.create(
            all_count=82,
            open_count=23,
            closed_count=59,
            by_status={"open": 15, "in_progress": 8, "fixed": 42, "closed": 12},
            by_severity={"critical": 2, "high": 10, "medium": 35, "low": 25, "info": 10},
            by_category={"crash": 8, "hotfix": 5, "feature": 22, "security": 12, "general": 35}
        )
        assert response.totals.all == 82
        assert response.totals.open == 23
        assert response.totals.closed == 59
    
    def test_serialization(self):
        """StatsResponse serializes to valid JSON."""
        response = StatsResponse(
            totals=StatsTotals(all=82, open=23, closed=59),
            by_status={"open": 15, "in_progress": 8, "fixed": 42, "closed": 12},
            by_severity={"critical": 2, "high": 10, "medium": 35, "low": 25, "info": 10},
            by_category={"crash": 8, "hotfix": 5, "feature": 22, "security": 12, "general": 35}
        )
        
        json_str = response.model_dump_json()
        data = json.loads(json_str)
        
        assert data["totals"]["all"] == 82
        assert data["totals"]["open"] == 23
        assert data["totals"]["closed"] == 59
        assert data["by_status"]["open"] == 15
        assert data["by_severity"]["critical"] == 2
        assert data["by_category"]["crash"] == 8


# =============================================================================
# ReindexResult Tests
# =============================================================================

class TestReindexResult:
    """Test ReindexResult model."""
    
    def test_required_fields(self):
        """ReindexResult requires processed, failed, duration_ms."""
        result = ReindexResult(processed=80, failed=0, duration_ms=12340.0)
        assert result.processed == 80
        assert result.failed == 0
        assert result.duration_ms == 12340.0
    
    def test_skipped_default_0(self):
        """skipped defaults to 0."""
        result = ReindexResult(processed=80, failed=0, duration_ms=12340.0)
        assert result.skipped == 0
    
    def test_errors_default_empty(self):
        """errors defaults to empty list."""
        result = ReindexResult(processed=80, failed=0, duration_ms=12340.0)
        assert result.errors == []
    
    def test_with_errors(self):
        """ReindexResult with errors."""
        result = ReindexResult(
            processed=78,
            skipped=2,
            failed=2,
            duration_ms=14500,
            errors=[
                ReindexError(ticket_id="C15", message="Failed to generate embedding: API timeout"),
                ReindexError(ticket_id="H3", message="Invalid markdown format in frontmatter")
            ]
        )
        assert result.processed == 78
        assert result.skipped == 2
        assert result.failed == 2
        assert len(result.errors) == 2
    
    def test_total_processed_property(self):
        """total_processed returns sum of processed, skipped, failed."""
        result = ReindexResult(processed=78, skipped=2, failed=2, duration_ms=14500)
        assert result.total_processed == 82
    
    def test_success_rate_property(self):
        """success_rate returns percentage."""
        result = ReindexResult(processed=80, skipped=0, failed=0, duration_ms=1000)
        assert result.success_rate == 100.0
        
        result = ReindexResult(processed=78, skipped=2, failed=2, duration_ms=1000)
        assert result.success_rate == pytest.approx(95.12, rel=0.01)
    
    def test_serialization(self):
        """ReindexResult serializes to valid JSON."""
        result = ReindexResult(
            processed=80,
            skipped=2,
            failed=0,
            duration_ms=12340.0,
            errors=[]
        )
        
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        
        assert data["processed"] == 80
        assert data["skipped"] == 2
        assert data["failed"] == 0
        assert data["duration_ms"] == 12340.0
        assert data["errors"] == []


# =============================================================================
# DoctorCheck Tests
# =============================================================================

class TestDoctorCheck:
    """Test DoctorCheck model."""
    
    def test_required_fields(self):
        """DoctorCheck requires name and status."""
        check = DoctorCheck(name="zvec_index", status="ok")
        assert check.name == "zvec_index"
        assert check.status == "ok"
    
    def test_status_values(self):
        """status must be ok, warning, or error."""
        DoctorCheck(name="test", status="ok")
        DoctorCheck(name="test", status="warning")
        DoctorCheck(name="test", status="error")
        
        with pytest.raises(ValidationError):
            DoctorCheck(name="test", status="invalid")
    
    def test_optional_fields(self):
        """message and fix are optional."""
        check = DoctorCheck(
            name="config_file",
            status="warning",
            message="Using deprecated config key",
            fix="Update to 'embeddings.provider' in vtic.toml"
        )
        assert check.message == "Using deprecated config key"
        assert check.fix == "Update to 'embeddings.provider' in vtic.toml"


# =============================================================================
# DoctorResult Tests
# =============================================================================

class TestDoctorResult:
    """Test DoctorResult model."""
    
    def test_required_fields(self):
        """DoctorResult requires overall and checks."""
        result = DoctorResult(
            overall="ok",
            checks=[
                DoctorCheck(name="zvec_index", status="ok", message="Index is healthy with 82 tickets")
            ]
        )
        assert result.overall == "ok"
        assert len(result.checks) == 1
    
    def test_overall_values(self):
        """overall must be ok, warnings, or errors."""
        DoctorResult(overall="ok", checks=[])
        DoctorResult(overall="warnings", checks=[])
        DoctorResult(overall="errors", checks=[])
        
        with pytest.raises(ValidationError):
            DoctorResult(overall="invalid", checks=[])
    
    def test_create_factory_ok(self):
        """DoctorResult.create() with all ok checks."""
        checks = [
            DoctorCheck(name="zvec_index", status="ok"),
            DoctorCheck(name="config_file", status="ok"),
        ]
        result = DoctorResult.create(checks)
        assert result.overall == "ok"
    
    def test_create_factory_warnings(self):
        """DoctorResult.create() with warning checks."""
        checks = [
            DoctorCheck(name="zvec_index", status="ok"),
            DoctorCheck(name="config_file", status="warning"),
        ]
        result = DoctorResult.create(checks)
        assert result.overall == "warnings"
    
    def test_create_factory_errors(self):
        """DoctorResult.create() with error checks."""
        checks = [
            DoctorCheck(name="zvec_index", status="error"),
            DoctorCheck(name="config_file", status="ok"),
        ]
        result = DoctorResult.create(checks)
        assert result.overall == "errors"
    
    def test_get_errors(self):
        """get_errors returns checks with error status."""
        checks = [
            DoctorCheck(name="zvec_index", status="error"),
            DoctorCheck(name="config_file", status="ok"),
            DoctorCheck(name="file_permissions", status="error"),
        ]
        result = DoctorResult(overall="errors", checks=checks)
        errors = result.get_errors()
        assert len(errors) == 2
    
    def test_get_warnings(self):
        """get_warnings returns checks with warning status."""
        checks = [
            DoctorCheck(name="zvec_index", status="ok"),
            DoctorCheck(name="config_file", status="warning"),
            DoctorCheck(name="embedding_provider", status="warning"),
        ]
        result = DoctorResult(overall="warnings", checks=checks)
        warnings = result.get_warnings()
        assert len(warnings) == 2
    
    def test_serialization(self):
        """DoctorResult serializes to valid JSON."""
        result = DoctorResult(
            overall="ok",
            checks=[
                DoctorCheck(name="zvec_index", status="ok", message="Index is healthy with 82 tickets"),
                DoctorCheck(name="config_file", status="ok", message="Configuration valid"),
            ]
        )
        
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        
        assert data["overall"] == "ok"
        assert len(data["checks"]) == 2
        assert data["checks"][0]["name"] == "zvec_index"


# =============================================================================
# Sample JSON Outputs
# =============================================================================

class TestSampleJsonOutputs:
    """Generate and verify sample JSON outputs for documentation."""
    
    def test_error_response_json(self):
        """Sample ErrorResponse JSON."""
        response = ErrorResponse(
            error=ErrorObject(
                code="SERVICE_UNAVAILABLE",
                message="Semantic search requested but no embedding provider is configured",
                details=[
                    ErrorDetail(
                        field="semantic",
                        message="Set 'semantic: false' or configure an embedding provider",
                        value=True
                    )
                ],
                docs="https://vtic.ejai.ai/docs/semantic-search"
            )
        )
        print("\n--- ErrorResponse Sample JSON ---")
        print(response.model_dump_json(indent=2))
    
    def test_paginated_response_json(self):
        """Sample PaginatedResponse JSON."""
        response = PaginatedResponse(
            data=[{"id": "C1", "title": "CORS error"}, {"id": "C2", "title": "Auth failure"}],
            meta=PaginationMeta(
                total=100,
                limit=2,
                offset=0,
                has_more=True,
                request_id="req_abc123"
            )
        )
        print("\n--- PaginatedResponse Sample JSON ---")
        print(response.model_dump_json(indent=2))
    
    def test_health_response_json(self):
        """Sample HealthResponse JSON."""
        response = HealthResponse(
            status="healthy",
            version="0.1.0",
            uptime_seconds=86400,
            index_status=IndexStatus(
                zvec="available",
                ticket_count=82,
                last_reindex=datetime(2026, 3, 17, 8, 0, 0, tzinfo=timezone.utc)
            ),
            embedding_provider=EmbeddingProviderInfo(
                name="local",
                model="all-MiniLM-L6-v2",
                dimension=384
            )
        )
        print("\n--- HealthResponse Sample JSON ---")
        print(response.model_dump_json(indent=2))
    
    def test_stats_response_json(self):
        """Sample StatsResponse JSON."""
        response = StatsResponse(
            totals=StatsTotals(all=82, open=23, closed=59),
            by_status={"open": 15, "in_progress": 8, "fixed": 42, "wont_fix": 3, "closed": 12},
            by_severity={"critical": 2, "high": 10, "medium": 35, "low": 25, "info": 10},
            by_category={"crash": 8, "hotfix": 5, "feature": 22, "security": 12, "general": 35}
        )
        print("\n--- StatsResponse Sample JSON ---")
        print(response.model_dump_json(indent=2))
    
    def test_reindex_result_json(self):
        """Sample ReindexResult JSON."""
        result = ReindexResult(
            processed=78,
            skipped=2,
            failed=2,
            duration_ms=14500.0,
            errors=[
                ReindexError(ticket_id="C15", message="Failed to generate embedding: API timeout"),
                ReindexError(ticket_id="H3", message="Invalid markdown format in frontmatter")
            ]
        )
        print("\n--- ReindexResult Sample JSON ---")
        print(result.model_dump_json(indent=2))
    
    def test_doctor_result_json(self):
        """Sample DoctorResult JSON."""
        result = DoctorResult(
            overall="warnings",
            checks=[
                DoctorCheck(name="zvec_index", status="ok", message="Index is healthy with 82 tickets"),
                DoctorCheck(name="config_file", status="warning", message="Using deprecated config key", fix="Update to 'embeddings.provider' in vtic.toml"),
                DoctorCheck(name="embedding_provider", status="ok", message="Local provider using all-MiniLM-L6-v2"),
            ]
        )
        print("\n--- DoctorResult Sample JSON ---")
        print(result.model_dump_json(indent=2))


# =============================================================================
# Error Codes Test
# =============================================================================

class TestErrorCodes:
    """Test that ERROR_CODES constant is available."""

    def test_error_codes_defined(self):
        """ERROR_CODES constant is defined with expected codes."""
        assert "VALIDATION_ERROR" in ERROR_CODES
        assert "NOT_FOUND" in ERROR_CODES
        assert "SERVICE_UNAVAILABLE" in ERROR_CODES
        assert "INTERNAL_ERROR" in ERROR_CODES

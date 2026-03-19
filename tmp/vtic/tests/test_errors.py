"""Tests for vtic errors module."""

import json

import pytest

from vtic.errors import (
    # Error codes
    VALIDATION_ERROR,
    NOT_FOUND,
    CONFLICT,
    PAYLOAD_TOO_LARGE,
    INTERNAL_ERROR,
    SERVICE_UNAVAILABLE,
    # Models
    ErrorDetail,
    ErrorObject,
    ErrorResponse,
    # Exceptions
    VticError,
    ValidationError,
    NotFoundError,
    ConflictError,
    PayloadTooLargeError,
    InternalError,
    ServiceUnavailableError,
    # Factory functions
    ticket_not_found,
    validation_failed,
    duplicate_ticket,
    semantic_search_unavailable,
    payload_too_large,
    index_error,
)


class TestErrorCodes:
    """Tests for error code constants."""

    def test_all_error_codes_defined(self):
        """Test all 6 error codes are defined."""
        assert VALIDATION_ERROR == "VALIDATION_ERROR"
        assert NOT_FOUND == "NOT_FOUND"
        assert CONFLICT == "CONFLICT"
        assert PAYLOAD_TOO_LARGE == "PAYLOAD_TOO_LARGE"
        assert INTERNAL_ERROR == "INTERNAL_ERROR"
        assert SERVICE_UNAVAILABLE == "SERVICE_UNAVAILABLE"

    def test_error_code_values_are_strings(self):
        """Test error codes are string values."""
        codes = [
            VALIDATION_ERROR,
            NOT_FOUND,
            CONFLICT,
            PAYLOAD_TOO_LARGE,
            INTERNAL_ERROR,
            SERVICE_UNAVAILABLE,
        ]
        for code in codes:
            assert isinstance(code, str)


class TestErrorDetail:
    """Tests for ErrorDetail model."""

    def test_error_detail_creation(self):
        """Test creating ErrorDetail."""
        detail = ErrorDetail(field="name", message="Name is required")
        assert detail.field == "name"
        assert detail.message == "Name is required"
        assert detail.value is None

    def test_error_detail_with_value(self):
        """Test ErrorDetail with value."""
        detail = ErrorDetail(
            field="age",
            message="Age must be positive",
            value="-5"
        )
        assert detail.value == "-5"

    def test_error_detail_optional_fields(self):
        """Test ErrorDetail with optional fields omitted."""
        detail = ErrorDetail(message="Something went wrong")
        assert detail.field is None
        assert detail.value is None

    def test_error_detail_serialization(self):
        """Test ErrorDetail serialization."""
        detail = ErrorDetail(field="email", message="Invalid email", value="invalid")
        data = detail.model_dump()
        assert data["field"] == "email"
        assert data["message"] == "Invalid email"
        assert data["value"] == "invalid"


class TestErrorObject:
    """Tests for ErrorObject model."""

    def test_error_object_creation(self):
        """Test creating ErrorObject."""
        error = ErrorObject(
            code=VALIDATION_ERROR,
            message="Validation failed"
        )
        assert error.code == VALIDATION_ERROR
        assert error.message == "Validation failed"
        assert error.details is None
        assert error.docs is None

    def test_error_object_with_details(self):
        """Test ErrorObject with details."""
        details = [
            ErrorDetail(field="name", message="Name is required"),
            ErrorDetail(field="email", message="Invalid email"),
        ]
        error = ErrorObject(
            code=VALIDATION_ERROR,
            message="Validation failed",
            details=details
        )
        assert len(error.details) == 2
        assert error.details[0].field == "name"

    def test_error_object_with_docs(self):
        """Test ErrorObject with docs link."""
        error = ErrorObject(
            code=NOT_FOUND,
            message="Resource not found",
            docs="https://docs.example.com/errors/not-found"
        )
        assert error.docs == "https://docs.example.com/errors/not-found"


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_error_response_creation(self):
        """Test creating ErrorResponse."""
        error_obj = ErrorObject(
            code=VALIDATION_ERROR,
            message="Query string cannot be empty"
        )
        response = ErrorResponse(error=error_obj)
        assert response.error.code == VALIDATION_ERROR
        assert response.error.message == "Query string cannot be empty"

    def test_error_response_serialization_to_json(self):
        """Test ErrorResponse serialization to JSON."""
        details = [
            ErrorDetail(field="query", message="Required field is missing or empty")
        ]
        error_obj = ErrorObject(
            code=VALIDATION_ERROR,
            message="Query string cannot be empty",
            details=details
        )
        response = ErrorResponse(error=error_obj)
        
        # Serialize to JSON string
        json_str = response.model_dump_json()
        
        # Parse back to dict
        data = json.loads(json_str)
        
        assert data["error"]["code"] == VALIDATION_ERROR
        assert data["error"]["message"] == "Query string cannot be empty"
        assert len(data["error"]["details"]) == 1
        assert data["error"]["details"][0]["field"] == "query"

    def test_error_response_with_meta(self):
        """Test ErrorResponse with metadata."""
        error_obj = ErrorObject(code=NOT_FOUND, message="Not found")
        response = ErrorResponse(
            error=error_obj,
            meta={"request_id": "abc123"}
        )
        assert response.meta["request_id"] == "abc123"

    def test_error_response_full_example(self):
        """Test full ErrorResponse example from spec."""
        response = ErrorResponse(
            error=ErrorObject(
                code=VALIDATION_ERROR,
                message="Query string cannot be empty",
                details=[
                    ErrorDetail(
                        field="query",
                        message="Required field is missing or empty"
                    )
                ]
            )
        )
        
        json_str = response.model_dump_json()
        data = json.loads(json_str)
        
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "Query string cannot be empty"
        assert data["error"]["details"][0]["field"] == "query"


class TestVticErrorBaseClass:
    """Tests for VticError base exception class."""

    def test_default_error(self):
        """Test VticError with default values."""
        error = VticError()
        assert error.code == INTERNAL_ERROR
        assert error.status == 500
        assert error.message == "An unexpected error occurred"
        assert error.details is None
        assert error.docs is None

    def test_custom_message(self):
        """Test VticError with custom message."""
        error = VticError(message="Something specific went wrong")
        assert error.message == "Something specific went wrong"

    def test_custom_details(self):
        """Test VticError with details."""
        details = [{"field": "name", "message": "Required"}]
        error = VticError(details=details)
        assert error.details == details

    def test_custom_docs(self):
        """Test VticError with docs."""
        error = VticError(docs="https://docs.example.com")
        assert error.docs == "https://docs.example.com"

    def test_to_response(self):
        """Test VticError to_response method."""
        error = VticError(
            code=VALIDATION_ERROR,
            message="Validation failed",
            details=[{"field": "email", "message": "Invalid"}],
            docs="https://docs.example.com"
        )
        response = error.to_response()
        
        assert response["error"]["code"] == VALIDATION_ERROR
        assert response["error"]["message"] == "Validation failed"
        assert response["error"]["details"] == [{"field": "email", "message": "Invalid"}]
        assert response["error"]["docs"] == "https://docs.example.com"

    def test_to_response_without_optional_fields(self):
        """Test to_response without details and docs."""
        error = VticError(code=NOT_FOUND, message="Not found")
        response = error.to_response()
        
        assert "details" not in response["error"]
        assert "docs" not in response["error"]

    def test_str_representation(self):
        """Test VticError string representation."""
        error = VticError(code=NOT_FOUND, message="Ticket not found")
        assert str(error) == "[NOT_FOUND] Ticket not found"

    def test_str_with_details(self):
        """Test string representation with details."""
        error = VticError(
            code=VALIDATION_ERROR,
            message="Validation failed",
            details=[{"field": "name", "message": "Required"}]
        )
        str_repr = str(error)
        assert "[VALIDATION_ERROR] Validation failed" in str_repr
        assert "details:" in str_repr

    def test_exception_inheritance(self):
        """Test VticError inherits from Exception."""
        error = VticError()
        assert isinstance(error, Exception)

    def test_can_be_raised(self):
        """Test that VticError can be raised and caught."""
        with pytest.raises(VticError) as exc_info:
            raise VticError(message="Test error")
        assert exc_info.value.message == "Test error"


class TestSpecificErrorClasses:
    """Tests for specific error classes."""

    def test_validation_error(self):
        """Test ValidationError has correct defaults."""
        error = ValidationError()
        assert error.code == VALIDATION_ERROR
        assert error.status == 400

    def test_not_found_error(self):
        """Test NotFoundError has correct defaults."""
        error = NotFoundError()
        assert error.code == NOT_FOUND
        assert error.status == 404

    def test_conflict_error(self):
        """Test ConflictError has correct defaults."""
        error = ConflictError()
        assert error.code == CONFLICT
        assert error.status == 409

    def test_payload_too_large_error(self):
        """Test PayloadTooLargeError has correct defaults."""
        error = PayloadTooLargeError()
        assert error.code == PAYLOAD_TOO_LARGE
        assert error.status == 413

    def test_internal_error(self):
        """Test InternalError has correct defaults."""
        error = InternalError()
        assert error.code == INTERNAL_ERROR
        assert error.status == 500

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError has correct defaults."""
        error = ServiceUnavailableError()
        assert error.code == SERVICE_UNAVAILABLE
        assert error.status == 503


class TestErrorFactoryFunctions:
    """Tests for error factory functions."""

    def test_ticket_not_found(self):
        """Test ticket_not_found factory."""
        error = ticket_not_found("C123")
        assert error.code == NOT_FOUND
        assert error.status == 404
        assert "C123" in error.message
        assert error.details == [{"field": "ticket_id", "message": "No ticket exists with this ID"}]

    def test_validation_failed(self):
        """Test validation_failed factory."""
        error = validation_failed("email", "Invalid email format")
        assert error.code == VALIDATION_ERROR
        assert "email" in str(error.details)
        assert "Invalid email format" in str(error.details)

    def test_validation_failed_with_value(self):
        """Test validation_failed with value."""
        error = validation_failed("age", "Must be positive", value=-5)
        assert error.details[0]["value"] == "-5"

    def test_duplicate_ticket(self):
        """Test duplicate_ticket factory."""
        error = duplicate_ticket("F42")
        assert error.code == CONFLICT
        assert "F42" in error.message
        assert "already exists" in error.message

    def test_semantic_search_unavailable(self):
        """Test semantic_search_unavailable factory."""
        error = semantic_search_unavailable()
        assert error.code == SERVICE_UNAVAILABLE
        assert error.status == 503
        assert "embedding provider" in error.message.lower()
        assert error.docs == "https://vtic.ejai.ai/docs/semantic-search"

    def test_payload_too_large(self):
        """Test payload_too_large factory."""
        error = payload_too_large(max_size=1048576, actual_size=2097152)
        assert error.code == PAYLOAD_TOO_LARGE
        assert error.status == 413
        assert "2097152" in error.message
        assert "1048576" in error.message

    def test_index_error(self):
        """Test index_error factory."""
        error = index_error("Index corrupted")
        assert error.code == INTERNAL_ERROR
        assert error.status == 500
        assert "Index corrupted" in error.message


class TestErrorResponseExamples:
    """Tests matching examples from the spec."""

    def test_validation_error_400_example(self):
        """Test Validation Error (400) example from spec."""
        response = ErrorResponse(
            error=ErrorObject(
                code=VALIDATION_ERROR,
                message="Query string cannot be empty",
                details=[
                    ErrorDetail(
                        field="query",
                        message="Required field is missing or empty"
                    )
                ]
            )
        )

        # Use exclude_none to match expected output without null values
        data = json.loads(response.model_dump_json(exclude_none=True))
        expected = {
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
        assert data == expected

    def test_not_found_404_example(self):
        """Test Not Found (404) example from spec."""
        response = ErrorResponse(
            error=ErrorObject(
                code=NOT_FOUND,
                message="Ticket 'C999' not found",
                details=[
                    ErrorDetail(
                        field="ticket_id",
                        message="No ticket exists with this ID"
                    )
                ]
            )
        )
        
        data = json.loads(response.model_dump_json())
        assert data["error"]["code"] == "NOT_FOUND"
        assert "C999" in data["error"]["message"]

    def test_conflict_409_example(self):
        """Test Conflict (409) example from spec."""
        response = ErrorResponse(
            error=ErrorObject(
                code=CONFLICT,
                message="Ticket 'C1' already exists",
                details=[
                    ErrorDetail(
                        field="id",
                        message="A ticket with this ID already exists"
                    )
                ]
            )
        )
        
        data = json.loads(response.model_dump_json())
        assert data["error"]["code"] == "CONFLICT"
        assert "C1" in data["error"]["message"]

    def test_service_unavailable_503_example(self):
        """Test Service Unavailable (503) example from spec."""
        response = ErrorResponse(
            error=ErrorObject(
                code=SERVICE_UNAVAILABLE,
                message="Semantic search requested but no embedding provider is configured",
                details=[
                    ErrorDetail(
                        field="semantic",
                        message="Set 'semantic: false' or configure an embedding provider"
                    )
                ],
                docs="https://vtic.ejai.ai/docs/semantic-search"
            )
        )
        
        data = json.loads(response.model_dump_json())
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert data["error"]["docs"] == "https://vtic.ejai.ai/docs/semantic-search"

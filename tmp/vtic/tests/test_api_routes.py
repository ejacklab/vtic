"""Tests for vtic API routes."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import httpx
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from vtic.api.app import create_app
from vtic.models.config import Config, StorageConfig, ApiConfig
from vtic.models.ticket import (
    Ticket,
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketSummary,
)
from vtic.models.enums import Category, Severity, Status
from vtic.errors import NotFoundError, ValidationError


# Test fixtures

@pytest.fixture
def test_config(tmp_path) -> Config:
    """Create a test configuration."""
    return Config(
        storage=StorageConfig(dir=tmp_path / "tickets"),
        api=ApiConfig(host="localhost", port=8080),
    )


@pytest.fixture
def mock_ticket_service():
    """Create a mock TicketService."""
    service = MagicMock()
    
    # Mock create_ticket
    async def mock_create(data: TicketCreate) -> Ticket:
        now = datetime.now(timezone.utc)
        return Ticket(
            id="C1",
            title=data.title,
            description=data.description,
            repo=data.repo,
            category=data.category or Category.GENERAL,
            severity=data.severity or Severity.MEDIUM,
            status=data.status or Status.OPEN,
            assignee=data.assignee,
            tags=data.tags or [],
            references=data.references or [],
            created=now,
            updated=now,
        )
    
    # Mock get_ticket
    async def mock_get(ticket_id: str) -> Ticket:
        if ticket_id != "C1":
            raise NotFoundError(message=f"Ticket '{ticket_id}' not found")
        now = datetime.now(timezone.utc)
        return Ticket(
            id=ticket_id,
            title="Test Ticket",
            description="Test description",
            repo="test/repo",
            category=Category.GENERAL,
            severity=Severity.MEDIUM,
            status=Status.OPEN,
            created=now,
            updated=now,
        )
    
    # Mock update_ticket
    async def mock_update(ticket_id: str, data: TicketUpdate) -> Ticket:
        if ticket_id != "C1":
            raise NotFoundError(message=f"Ticket '{ticket_id}' not found")
        now = datetime.now(timezone.utc)
        return Ticket(
            id=ticket_id,
            title=data.title or "Test Ticket",
            description=data.description or "Test description",
            repo="test/repo",
            category=data.category or Category.GENERAL,
            severity=data.severity or Severity.MEDIUM,
            status=data.status or Status.OPEN,
            created=now,
            updated=now,
        )
    
    # Mock delete_ticket
    async def mock_delete(ticket_id: str, mode: str = "soft") -> None:
        if ticket_id != "C1":
            raise NotFoundError(message=f"Ticket '{ticket_id}' not found")
    
    # Mock list_tickets
    async def mock_list(**kwargs) -> list[TicketSummary]:
        now = datetime.now(timezone.utc)
        tickets = [
            TicketSummary(
                id="C1",
                title="Test Ticket 1",
                severity=Severity.HIGH,
                status=Status.OPEN,
                repo="test/repo1",
                category=Category.CRASH,
                created=now,
            ),
            TicketSummary(
                id="H1",
                title="Test Ticket 2",
                severity=Severity.MEDIUM,
                status=Status.IN_PROGRESS,
                repo="test/repo2",
                category=Category.HOTFIX,
                created=now,
            ),
        ]
        
        # Apply filters
        if kwargs.get("repo"):
            tickets = [t for t in tickets if t.repo == kwargs["repo"]]
        if kwargs.get("category"):
            tickets = [t for t in tickets if t.category == kwargs["category"]]
        
        return tickets[kwargs.get("offset", 0):kwargs.get("offset", 0) + kwargs.get("limit", 20)]
    
    # Mock count_tickets
    async def mock_count(**kwargs) -> int:
        return 2
    
    # Mock initialize
    async def mock_initialize():
        pass
    
    # Mock close
    async def mock_close():
        pass
    
    service.create_ticket = AsyncMock(side_effect=mock_create)
    service.get_ticket = AsyncMock(side_effect=mock_get)
    service.update_ticket = AsyncMock(side_effect=mock_update)
    service.delete_ticket = AsyncMock(side_effect=mock_delete)
    service.list_tickets = AsyncMock(side_effect=mock_list)
    service.count_tickets = AsyncMock(side_effect=mock_count)
    service.initialize = AsyncMock(side_effect=mock_initialize)
    service.close = AsyncMock(side_effect=mock_close)
    
    return service


@pytest.fixture
async def client(test_config, mock_ticket_service) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with mocked service."""
    from vtic.api import deps
    
    app = create_app(test_config)
    
    # Override the ticket service
    app.state.ticket_service = mock_ticket_service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# Test cases

@pytest.mark.asyncio
async def test_post_ticket_201(client: AsyncClient):
    """Test creating a ticket returns 201 with all fields."""
    response = await client.post("/tickets", json={
        "title": "Test Ticket",
        "description": "Test description",
        "repo": "test/repo",
        "category": "crash",
        "severity": "high",
        "status": "open",
        "assignee": "testuser",
        "tags": ["bug", "urgent"],
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "data" in data
    ticket = data["data"]
    assert ticket["id"] == "C1"
    assert ticket["title"] == "Test Ticket"
    assert ticket["description"] == "Test description"
    assert ticket["repo"] == "test/repo"
    assert ticket["category"] == "crash"
    assert ticket["severity"] == "high"
    assert ticket["status"] == "open"
    assert ticket["assignee"] == "testuser"
    assert ticket["tags"] == ["bug", "urgent"]
    assert "created" in ticket
    assert "updated" in ticket


@pytest.mark.asyncio
async def test_post_ticket_returns_id_in_response(client: AsyncClient):
    """Test creating a ticket returns the ticket ID."""
    response = await client.post("/tickets", json={
        "title": "Test Ticket",
        "description": "Test description",
        "repo": "test/repo",
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "data" in data
    assert "id" in data["data"]
    # ID should match pattern ^[CFGHST]\d+$
    assert len(data["data"]["id"]) >= 2
    assert data["data"]["id"][0] in "CFGHST"


@pytest.mark.asyncio
async def test_get_ticket_200(client: AsyncClient):
    """Test getting an existing ticket returns 200."""
    # First create a ticket
    create_response = await client.post("/tickets", json={
        "title": "Test Ticket",
        "description": "Test description",
        "repo": "test/repo",
    })
    assert create_response.status_code == 201
    
    # Get the ticket
    response = await client.get("/tickets/C1")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == "C1"


@pytest.mark.asyncio
async def test_get_ticket_404(client: AsyncClient):
    """Test getting a non-existent ticket returns 404."""
    response = await client.get("/tickets/X999")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_ticket_200(client: AsyncClient):
    """Test updating a ticket returns 200."""
    # First create a ticket
    create_response = await client.post("/tickets", json={
        "title": "Test Ticket",
        "description": "Test description",
        "repo": "test/repo",
    })
    assert create_response.status_code == 201
    
    # Update the ticket
    response = await client.patch("/tickets/C1", json={
        "title": "Updated Title",
        "status": "in_progress",
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["title"] == "Updated Title"
    assert data["data"]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_patch_ticket_404(client: AsyncClient):
    """Test updating a non-existent ticket returns 404."""
    response = await client.patch("/tickets/X999", json={
        "title": "Updated Title",
    })
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_ticket_204(client: AsyncClient):
    """Test deleting a ticket returns 204."""
    # First create a ticket
    create_response = await client.post("/tickets", json={
        "title": "Test Ticket",
        "description": "Test description",
        "repo": "test/repo",
    })
    assert create_response.status_code == 201
    
    # Delete the ticket
    response = await client.delete("/tickets/C1")
    
    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_delete_ticket_404(client: AsyncClient):
    """Test deleting a non-existent ticket returns 404."""
    response = await client.delete("/tickets/X999")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_tickets_200(client: AsyncClient):
    """Test listing tickets returns 200."""
    # Create multiple tickets
    for i in range(3):
        await client.post("/tickets", json={
            "title": f"Test Ticket {i}",
            "description": f"Description {i}",
            "repo": f"test/repo{i}",
        })
    
    response = await client.get("/tickets")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)
    assert "total" in data["meta"]
    assert "limit" in data["meta"]
    assert "offset" in data["meta"]
    assert "has_more" in data["meta"]


@pytest.mark.asyncio
async def test_list_tickets_filter_by_repo(client: AsyncClient):
    """Test filtering tickets by repository."""
    response = await client.get("/tickets?repo=test/repo1")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should only return tickets for the specified repo
    for ticket in data["data"]:
        assert ticket["repo"] == "test/repo1"


@pytest.mark.asyncio
async def test_list_tickets_filter_by_category(client: AsyncClient):
    """Test filtering tickets by category."""
    response = await client.get("/tickets?category=crash")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should only return tickets with the specified category
    for ticket in data["data"]:
        assert ticket["category"] == "crash"


@pytest.mark.asyncio
async def test_list_tickets_pagination_limit_offset(client: AsyncClient):
    """Test pagination with limit and offset."""
    # Test with limit
    response = await client.get("/tickets?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 1
    assert data["meta"]["limit"] == 1
    
    # Test with offset
    response = await client.get("/tickets?offset=1")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["offset"] == 1


@pytest.mark.asyncio
async def test_error_response_format(client: AsyncClient):
    """Test error responses match OpenAPI ErrorResponse schema."""
    response = await client.get("/tickets/X999")
    
    assert response.status_code == 404
    data = response.json()
    
    # Check ErrorResponse structure
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert "message" in error
    assert isinstance(error["code"], str)
    assert isinstance(error["message"], str)
    
    # Optional fields - can be None or list
    if "details" in error and error["details"] is not None:
        assert isinstance(error["details"], list)
    if "docs" in error:
        assert isinstance(error["docs"], (str, type(None)))


@pytest.mark.asyncio
async def test_invalid_input_400(client: AsyncClient):
    """Test invalid input returns validation error (400 or 422)."""
    response = await client.post("/tickets", json={
        # Missing required fields: title, description, repo
    })
    
    # FastAPI returns 422 by default for Pydantic validation errors
    # We map this to VALIDATION_ERROR with 400 in our custom handler
    assert response.status_code in (400, 422)
    data = response.json()
    
    # Check error structure
    if "error" in data:
        # Our custom format
        assert data["error"]["code"] == "VALIDATION_ERROR"
    else:
        # FastAPI's default format - still has error details
        assert "detail" in data or "errors" in data


@pytest.mark.asyncio
async def test_list_tickets_filter_by_severity(client: AsyncClient):
    """Test filtering tickets by severity."""
    response = await client.get("/tickets?severity=high")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_list_tickets_filter_by_status(client: AsyncClient):
    """Test filtering tickets by status."""
    response = await client.get("/tickets?status=open")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_ticket_response_has_meta(client: AsyncClient):
    """Test ticket responses include meta field."""
    response = await client.post("/tickets", json={
        "title": "Test Ticket",
        "description": "Test description",
        "repo": "test/repo",
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "meta" in data


@pytest.mark.asyncio
async def test_create_ticket_minimal_fields(client: AsyncClient):
    """Test creating a ticket with only required fields."""
    response = await client.post("/tickets", json={
        "title": "Minimal Ticket",
        "description": "Minimal description",
        "repo": "test/repo",
    })
    
    assert response.status_code == 201
    data = response.json()
    ticket = data["data"]
    assert ticket["title"] == "Minimal Ticket"
    # Should have defaults for optional fields
    assert "category" in ticket
    assert "severity" in ticket
    assert "status" in ticket

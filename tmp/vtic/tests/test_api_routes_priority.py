"""Tests for priority API routes."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from vtic.api.app import create_app
from vtic.api.deps import get_ticket_service
from vtic.models.config import Config, StorageConfig, ApiConfig, PriorityConfig
from vtic.models.ticket import Ticket, TicketUpdate
from vtic.models.enums import Category, Severity, Status, Urgency, Impact
from vtic.errors import NotFoundError


# Test fixtures

@pytest.fixture
def test_config(tmp_path) -> Config:
    """Create a test configuration."""
    return Config(
        storage=StorageConfig(dir=tmp_path / "tickets"),
        api=ApiConfig(host="localhost", port=8080),
    )


@pytest.fixture
def mock_ticket_service(test_config):
    """Create a mock TicketService."""
    service = MagicMock()
    service.config = test_config
    
    # Mock get_ticket - returns a ticket with priority fields
    async def mock_get(ticket_id: str) -> Ticket:
        if ticket_id == "C1":
            now = datetime.now(timezone.utc)
            return Ticket(
                id=ticket_id,
                title="Test Ticket",
                description="Test description",
                repo="test/repo",
                category=Category.GENERAL,
                severity=Severity.MEDIUM,
                status=Status.OPEN,
                urgency=Urgency.HIGH,
                impact=Impact.MEDIUM,
                created=now,
                updated=now,
            )
        elif ticket_id == "C2":
            # Ticket without priority fields
            now = datetime.now(timezone.utc)
            return Ticket(
                id=ticket_id,
                title="No Priority Ticket",
                description="Test description",
                repo="test/repo",
                category=Category.GENERAL,
                severity=Severity.MEDIUM,
                status=Status.OPEN,
                urgency=None,
                impact=None,
                created=now,
                updated=now,
            )
        else:
            raise NotFoundError(message=f"Ticket '{ticket_id}' not found")
    
    # Mock update_ticket
    async def mock_update(ticket_id: str, data: TicketUpdate) -> Ticket:
        if ticket_id == "C99999":
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
            urgency=data.urgency or Urgency.HIGH,
            impact=data.impact or Impact.MEDIUM,
            created=now,
            updated=now,
        )
    
    service.get_ticket = AsyncMock(side_effect=mock_get)
    service.update_ticket = AsyncMock(side_effect=mock_update)
    
    return service


@pytest.fixture
def app(test_config, mock_ticket_service):
    """Create a test app with mocked service."""
    app = create_app(test_config)
    app.state.ticket_service = mock_ticket_service
    app.state.config = test_config
    return app


pytestmark = pytest.mark.asyncio


async def test_get_priority_endpoint_exists(app):
    """Test that the priority GET endpoint exists."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tickets/C1/priority")
        # Should return 200 for existing ticket
        assert response.status_code == 200


async def test_get_priority_not_found(app):
    """Test that non-existent ticket returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tickets/C99999/priority")
        assert response.status_code == 404


async def test_get_priority_no_urgency_impact(app):
    """Test getting priority when ticket has no urgency/impact."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tickets/C2/priority")
        assert response.status_code == 200
        data = response.json()
        assert data["ticket_id"] == "C2"
        assert data["urgency"] is None
        assert data["impact"] is None
        assert data["breakdown"] is None


async def test_get_priority_with_breakdown(app):
    """Test getting priority when ticket has urgency/impact."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tickets/C1/priority")
        assert response.status_code == 200
        data = response.json()
        assert data["ticket_id"] == "C1"
        assert data["urgency"] == "high"
        assert data["impact"] == "medium"
        assert data["breakdown"] is not None
        
        # Check breakdown structure
        breakdown = data["breakdown"]
        assert "base_score" in breakdown
        assert "base_label" in breakdown
        assert "category" in breakdown
        assert "category_multiplier" in breakdown
        assert "final_score" in breakdown
        assert "priority_level" in breakdown


async def test_update_priority_endpoint_exists(app):
    """Test that the priority PUT endpoint exists."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/tickets/C1/priority",
            json={"urgency": "high", "impact": "medium"},
        )
        assert response.status_code == 200


async def test_update_priority_not_found(app):
    """Test that updating non-existent ticket returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/tickets/C99999/priority",
            json={"urgency": "high", "impact": "medium"},
        )
        assert response.status_code == 404


async def test_update_priority_validation(app):
    """Test that priority update validates urgency/impact values."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test with invalid urgency value - should get 400 or 422
        response = await client.put(
            "/api/tickets/C1/priority",
            json={"urgency": "invalid_value", "impact": "medium"},
        )
        # Should return 400 (validation error) or 422
        assert response.status_code in [400, 422]


async def test_update_priority_partial_urgency(app):
    """Test updating only urgency."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/tickets/C1/priority",
            json={"urgency": "critical"},
        )
        assert response.status_code == 200


async def test_update_priority_partial_impact(app):
    """Test updating only impact."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/tickets/C1/priority",
            json={"impact": "critical"},
        )
        assert response.status_code == 200


async def test_priority_breakdown_scoring(app):
    """Test that priority breakdown has correct scoring."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tickets/C1/priority")
        assert response.status_code == 200
        data = response.json()
        
        breakdown = data["breakdown"]
        assert breakdown is not None
        
        # Validate types
        assert isinstance(breakdown["base_score"], int)
        assert isinstance(breakdown["final_score"], int)
        assert isinstance(breakdown["category_multiplier"], (int, float))
        
        # Validate ranges
        assert 0 <= breakdown["base_score"] <= 100
        assert 0 <= breakdown["final_score"] <= 100
        
        # Validate priority level
        assert breakdown["priority_level"] in ["p0", "p1", "p2", "p3", "p4"]

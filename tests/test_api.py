"""Tests for the FastAPI application endpoints."""

import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set test environment
os.environ["LLM_MOCK_MODE"] = "true"
os.environ["GITHUB_DRY_RUN"] = "true"
os.environ["SIMULATOR_ENABLED"] = "true"
os.environ["SCAN_INTERVAL"] = "300"  # Long interval to avoid auto-scans during tests
os.environ["DATABASE_URL"] = "sqlite:///./data/test_incidents.db"

from src.database import init_db
from src.main import app

# Ensure tables exist before tests run
init_db()


@pytest.fixture
async def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Tests for health and root endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test the root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI DevOps Incident Copilot"
        assert "version" in data
        assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test the health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestPipelineEndpoints:
    """Tests for pipeline control endpoints."""

    @pytest.mark.asyncio
    async def test_get_status(self, client):
        """Test getting pipeline status."""
        response = await client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "simulator_running" in data
        assert "total_logs_processed" in data
        assert "total_anomalies_detected" in data
        assert "total_incidents_created" in data


class TestLogEndpoints:
    """Tests for log-related endpoints."""

    @pytest.mark.asyncio
    async def test_get_recent_logs(self, client):
        """Test getting recent logs."""
        response = await client.get("/api/v1/logs?count=10")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "logs" in data
        assert isinstance(data["logs"], list)


class TestDetectorEndpoints:
    """Tests for detector endpoints."""

    @pytest.mark.asyncio
    async def test_get_detector_stats(self, client):
        """Test getting detector statistics."""
        response = await client.get("/api/v1/detector/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_logs_analyzed" in data
        assert "rules_loaded" in data


class TestScanEndpoints:
    """Tests for manual scan endpoint."""

    @pytest.mark.asyncio
    async def test_manual_scan(self, client):
        """Test triggering a manual scan."""
        response = await client.post("/api/v1/scan")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "incidents" in data


class TestIncidentEndpoints:
    """Tests for incident endpoints."""

    @pytest.mark.asyncio
    async def test_list_incidents(self, client):
        """Test listing incidents."""
        response = await client.get("/api/v1/incidents")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "incidents" in data

    @pytest.mark.asyncio
    async def test_get_incident_not_found(self, client):
        """Test getting a non-existent incident."""
        response = await client.get("/api/v1/incidents/99999")
        assert response.status_code == 404

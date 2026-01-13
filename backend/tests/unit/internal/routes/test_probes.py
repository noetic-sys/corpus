"""Tests for internal k8s probe endpoints."""

import pytest
from httpx import AsyncClient


class TestProbeEndpoints:
    """Tests for /healthz and /readyz probe endpoints."""

    @pytest.mark.asyncio
    async def test_healthz_returns_200(self, client: AsyncClient):
        """Healthz endpoint should return 200 OK."""
        response = await client.get("/healthz")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_healthz_returns_ok_status(self, client: AsyncClient):
        """Healthz endpoint should return status ok."""
        response = await client.get("/healthz")
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_readyz_returns_200(self, client: AsyncClient):
        """Readyz endpoint should return 200 OK."""
        response = await client.get("/readyz")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_readyz_returns_ok_status(self, client: AsyncClient):
        """Readyz endpoint should return status ok."""
        response = await client.get("/readyz")
        assert response.json() == {"status": "ok"}


class TestProbesNotInSchema:
    """Ensure probe endpoints are not exposed in OpenAPI schema."""

    @pytest.mark.asyncio
    async def test_healthz_not_in_openapi(self, client: AsyncClient):
        """Healthz should not appear in OpenAPI schema."""
        response = await client.get("/openapi.json")
        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})
            assert "/healthz" not in paths
            assert "/readyz" not in paths

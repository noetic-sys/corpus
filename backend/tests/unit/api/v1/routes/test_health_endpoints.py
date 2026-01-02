from httpx import AsyncClient


class TestHealthEndpoints:
    """Integration tests for health check endpoints."""

    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "corpus-service"}

    async def test_db_health_check(self, client: AsyncClient):
        """Test database health check endpoint."""
        response = await client.get("/api/v1/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

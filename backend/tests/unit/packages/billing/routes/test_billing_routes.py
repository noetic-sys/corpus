"""
Unit tests for billing API routes.

Tests API endpoints with mocked external providers.
"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_metering_provider():
    """Mock metering provider for route tests."""
    provider = AsyncMock()
    provider.create_customer = AsyncMock(
        return_value={"customer_id": None, "subscription_id": None}
    )
    provider.get_customer_usage = AsyncMock(return_value={})
    return provider


@pytest.fixture
def mock_payment_provider():
    """Mock payment provider for route tests."""
    provider = AsyncMock()
    provider.create_checkout_session = AsyncMock(
        return_value=("https://checkout.stripe.com/test123", "cus_test123")
    )
    provider.create_customer_portal_session = AsyncMock(
        return_value="https://billing.stripe.com/test123"
    )
    return provider


@pytest.mark.asyncio
class TestBillingRoutes:
    """Tests for billing API routes."""

    async def test_get_subscription_status(self, client, sample_subscription):
        """Test GET /api/v1/billing/status."""
        response = await client.get("/api/v1/billing/status")

        assert response.status_code == 200
        data = response.json()
        assert data["company_id"] == sample_subscription.company_id
        assert data["tier"] == sample_subscription.tier.value
        assert data["status"] == sample_subscription.status.value
        assert data["has_access"] is True

    async def test_get_usage_stats(
        self, client, sample_subscription, sample_usage_event
    ):
        """Test GET /api/v1/billing/usage."""
        response = await client.get("/api/v1/billing/usage")

        assert response.status_code == 200
        data = response.json()
        assert data["company_id"] == sample_subscription.company_id
        assert data["tier"] == sample_subscription.tier.value
        assert "cell_operations" in data
        assert "agentic_qa" in data
        assert "workflows" in data
        assert "storage_bytes" in data
        assert "documents" in data
        assert "documents_limit" in data
        assert "documents_percentage" in data

    async def test_check_cell_operation_quota(self, client, sample_subscription):
        """Test GET /api/v1/billing/quota/cell-operations."""
        response = await client.get("/api/v1/billing/quota/cell-operations")

        assert response.status_code == 200
        data = response.json()
        assert data["metric_name"] == "cell_operations"
        assert "current_usage" in data
        assert "limit" in data
        assert "remaining" in data

    async def test_create_checkout_session(self, client, mock_payment_provider):
        """Test POST /api/v1/billing/checkout."""
        with patch(
            "packages.billing.services.subscription_service.get_payment_provider",
            return_value=mock_payment_provider,
        ):
            response = await client.post(
                "/api/v1/billing/checkout",
                json={
                    "tier": "starter",
                    "success_url": "http://localhost:3000/success",
                    "cancel_url": "http://localhost:3000/cancel",
                    "billing_email": "test@example.com",
                },
            )

            # May fail if subscription already exists, but should not be 500
            assert response.status_code in [200, 400]
            if response.status_code == 200:
                data = response.json()
                assert "checkout_url" in data

    async def test_create_portal_session(
        self, client, sample_subscription, mock_payment_provider
    ):
        """Test POST /api/v1/billing/portal."""
        with patch(
            "packages.billing.services.subscription_service.get_payment_provider",
            return_value=mock_payment_provider,
        ):
            response = await client.post(
                "/api/v1/billing/portal",
                json={"return_url": "http://localhost:3000/billing"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "portal_url" in data
            assert data["portal_url"] == "https://billing.stripe.com/test123"

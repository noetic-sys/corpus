import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai_model.services.ai_model_service import AIModelService
from packages.ai_model.models.database.ai_provider import AIProviderEntity
from packages.ai_model.models.database.ai_model import AIModelEntity


class TestAIModelService:
    """Test AIModelService methods."""

    @pytest.fixture
    async def service(self, test_db: AsyncSession):
        """Create service instance."""
        return AIModelService(test_db)

    @pytest.fixture
    async def sample_provider(self, test_db: AsyncSession):
        """Create a sample AI provider."""
        provider = AIProviderEntity(
            name="test_provider", display_name="Test Provider", enabled=True
        )
        test_db.add(provider)
        await test_db.commit()
        await test_db.refresh(provider)
        return provider

    @pytest.fixture
    async def sample_model(self, test_db: AsyncSession, sample_provider):
        """Create a sample AI model."""
        model = AIModelEntity(
            provider_id=sample_provider.id,
            model_name="test-model-v1",
            display_name="Test Model v1",
            default_temperature=0.7,
            default_max_tokens=1000,
            enabled=True,
        )
        test_db.add(model)
        await test_db.commit()
        await test_db.refresh(model)
        return model

    async def test_get_provider_exists(self, service, sample_provider):
        """Test getting existing provider."""
        result = await service.get_provider(sample_provider.id)

        assert result is not None
        assert result.id == sample_provider.id
        assert result.name == sample_provider.name
        assert result.display_name == sample_provider.display_name

    async def test_get_provider_not_exists(self, service):
        """Test getting non-existent provider."""
        result = await service.get_provider(999)
        assert result is None

    async def test_get_provider_by_name(self, service, sample_provider):
        """Test getting provider by name."""
        result = await service.get_provider_by_name(sample_provider.name)

        assert result is not None
        assert result.id == sample_provider.id
        assert result.name == sample_provider.name

    async def test_get_all_providers(self, service, test_db):
        """Test getting all providers."""
        # Create multiple providers
        providers_data = [
            {"name": "provider1", "display_name": "Provider 1", "enabled": True},
            {"name": "provider2", "display_name": "Provider 2", "enabled": False},
            {"name": "provider3", "display_name": "Provider 3", "enabled": True},
        ]

        for data in providers_data:
            provider = AIProviderEntity(**data)
            test_db.add(provider)
        await test_db.commit()

        results = await service.get_all_providers()

        assert len(results) >= 3
        provider_names = [p.name for p in results]
        assert "provider1" in provider_names
        assert "provider2" in provider_names
        assert "provider3" in provider_names

    async def test_get_enabled_providers(self, service, test_db):
        """Test getting only enabled providers."""
        # Create mixed enabled/disabled providers
        providers_data = [
            {"name": "enabled1", "display_name": "Enabled 1", "enabled": True},
            {"name": "disabled1", "display_name": "Disabled 1", "enabled": False},
            {"name": "enabled2", "display_name": "Enabled 2", "enabled": True},
        ]

        for data in providers_data:
            provider = AIProviderEntity(**data)
            test_db.add(provider)
        await test_db.commit()

        results = await service.get_enabled_providers()

        # Should only get enabled providers
        enabled_names = [p.name for p in results if p.enabled]
        assert "enabled1" in enabled_names
        assert "enabled2" in enabled_names
        assert all(p.enabled for p in results)

    async def test_get_model_exists(self, service, sample_model):
        """Test getting existing model."""
        result = await service.get_model(sample_model.id)

        assert result is not None
        assert result.id == sample_model.id
        assert result.model_name == sample_model.model_name

    async def test_get_model_with_provider(
        self, service, sample_model, sample_provider
    ):
        """Test getting model with provider information."""
        result = await service.get_model_with_provider(sample_model.id)

        assert result is not None
        assert result.id == sample_model.id
        assert result.provider is not None
        assert result.provider.id == sample_provider.id

    async def test_get_all_models(self, service, test_db, sample_provider):
        """Test getting all models."""
        # Create multiple models
        models_data = [
            {
                "provider_id": sample_provider.id,
                "model_name": "model1",
                "display_name": "Model 1",
                "enabled": True,
            },
            {
                "provider_id": sample_provider.id,
                "model_name": "model2",
                "display_name": "Model 2",
                "enabled": False,
            },
        ]

        for data in models_data:
            model = AIModelEntity(**data)
            test_db.add(model)
        await test_db.commit()

        results = await service.get_all_models()

        assert len(results) >= 2
        model_names = [m.model_name for m in results]
        assert "model1" in model_names
        assert "model2" in model_names

    async def test_get_enabled_models(self, service, test_db, sample_provider):
        """Test getting only enabled models with provider info."""
        # Create mixed enabled/disabled models
        models_data = [
            {
                "provider_id": sample_provider.id,
                "model_name": "enabled-model",
                "display_name": "Enabled Model",
                "enabled": True,
            },
            {
                "provider_id": sample_provider.id,
                "model_name": "disabled-model",
                "display_name": "Disabled Model",
                "enabled": False,
            },
        ]

        for data in models_data:
            model = AIModelEntity(**data)
            test_db.add(model)
        await test_db.commit()

        results = await service.get_enabled_models()

        # Should only get enabled models
        assert all(m.enabled for m in results)
        enabled_names = [m.model_name for m in results if m.enabled]
        assert "enabled-model" in enabled_names

    async def test_get_models_by_provider(self, service, sample_provider, sample_model):
        """Test getting models for a specific provider."""
        results = await service.get_models_by_provider(sample_provider.id)

        assert len(results) >= 1
        assert any(m.id == sample_model.id for m in results)
        assert all(m.provider_id == sample_provider.id for m in results)

    async def test_get_enabled_models_by_provider(
        self, service, test_db, sample_provider
    ):
        """Test getting enabled models for a specific provider."""
        # Create mixed enabled/disabled models
        enabled_model = AIModelEntity(
            provider_id=sample_provider.id,
            model_name="enabled-prov-model",
            display_name="Enabled Provider Model",
            enabled=True,
        )
        disabled_model = AIModelEntity(
            provider_id=sample_provider.id,
            model_name="disabled-prov-model",
            display_name="Disabled Provider Model",
            enabled=False,
        )
        test_db.add(enabled_model)
        test_db.add(disabled_model)
        await test_db.commit()

        results = await service.get_enabled_models_by_provider(sample_provider.id)

        assert all(m.enabled for m in results)
        assert all(m.provider_id == sample_provider.id for m in results)
        model_names = [m.model_name for m in results]
        assert "enabled-prov-model" in model_names
        assert "disabled-prov-model" not in model_names

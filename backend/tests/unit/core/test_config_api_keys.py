"""Unit tests for API key list configuration."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Test settings class that mimics the real Settings class for API keys."""

    model_config = SettingsConfigDict()

    # API keys as lists (only the ones we still use)
    openai_api_keys: List[str]
    gemini_api_keys: List[str]
    voyage_api_keys: Optional[List[str]] = None


class TestAPIKeyListConfiguration:
    """Test that API keys are properly loaded as lists from environment."""

    def test_load_single_api_key_as_list(self):
        """Test loading a single API key in JSON array format."""
        os.environ["OPENAI_API_KEYS"] = '["sk-single-openai-key"]'
        os.environ["GEMINI_API_KEYS"] = '["single-gemini-key"]'

        try:
            settings = TestSettings()
            assert settings.openai_api_keys == ["sk-single-openai-key"]
            assert settings.gemini_api_keys == ["single-gemini-key"]
        finally:
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]

    def test_load_multiple_api_keys_as_list(self):
        """Test loading multiple API keys in JSON array format."""
        os.environ["OPENAI_API_KEYS"] = (
            '["sk-key1", "sk-key2", "sk-key3", "sk-key4", "sk-key5"]'
        )
        os.environ["GEMINI_API_KEYS"] = '["gem-key1", "gem-key2"]'

        try:
            settings = TestSettings()
            assert settings.openai_api_keys == [
                "sk-key1",
                "sk-key2",
                "sk-key3",
                "sk-key4",
                "sk-key5",
            ]
            assert settings.gemini_api_keys == ["gem-key1", "gem-key2"]
        finally:
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]

    def test_api_keys_with_spaces_in_json(self):
        """Test that JSON format handles spaces correctly."""
        os.environ["OPENAI_API_KEYS"] = (
            '[ "sk-key1", "sk-key2" , "sk-key3",  "sk-key4" ]'
        )
        os.environ["GEMINI_API_KEYS"] = '["gem-key1", "gem-key2"]'

        try:
            settings = TestSettings()
            assert settings.openai_api_keys == [
                "sk-key1",
                "sk-key2",
                "sk-key3",
                "sk-key4",
            ]
            assert settings.gemini_api_keys == ["gem-key1", "gem-key2"]
        finally:
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]

    def test_empty_api_keys_list(self):
        """Test that empty JSON array results in empty list."""
        os.environ["OPENAI_API_KEYS"] = "[]"
        os.environ["GEMINI_API_KEYS"] = "[]"

        try:
            settings = TestSettings()
            assert settings.openai_api_keys == []
            assert settings.gemini_api_keys == []
        finally:
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]

    def test_optional_voyage_keys(self):
        """Test that voyage keys are optional."""
        os.environ["OPENAI_API_KEYS"] = '["sk-key1"]'
        os.environ["GEMINI_API_KEYS"] = '["gem-key1"]'

        try:
            settings = TestSettings()
            assert settings.voyage_api_keys is None
        finally:
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]

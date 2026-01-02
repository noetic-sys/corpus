"""Unit tests for API key list configuration."""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Test settings class that mimics the real Settings class for API keys."""

    model_config = SettingsConfigDict()

    # API keys as lists
    openai_api_keys: List[str]
    anthropic_api_keys: List[str]
    gemini_api_keys: List[str]
    xai_api_keys: List[str]


class TestAPIKeyListConfiguration:
    """Test that API keys are properly loaded as lists from environment."""

    def test_load_single_api_key_as_list(self):
        """Test loading a single API key in JSON array format."""
        # Set real environment variables in JSON array format
        os.environ["OPENAI_API_KEYS"] = '["sk-single-openai-key"]'
        os.environ["ANTHROPIC_API_KEYS"] = '["sk-single-anthropic-key"]'
        os.environ["GEMINI_API_KEYS"] = '["single-gemini-key"]'
        os.environ["XAI_API_KEYS"] = '["single-xai-key"]'

        try:
            settings = TestSettings()
            assert settings.openai_api_keys == ["sk-single-openai-key"]
            assert settings.anthropic_api_keys == ["sk-single-anthropic-key"]
            assert settings.gemini_api_keys == ["single-gemini-key"]
            assert settings.xai_api_keys == ["single-xai-key"]
        finally:
            # Clean up
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["ANTHROPIC_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]
            del os.environ["XAI_API_KEYS"]

    def test_load_multiple_api_keys_as_list(self):
        """Test loading multiple API keys in JSON array format."""
        # Set real environment variables with multiple keys in JSON format
        os.environ["OPENAI_API_KEYS"] = (
            '["sk-key1", "sk-key2", "sk-key3", "sk-key4", "sk-key5"]'
        )
        os.environ["ANTHROPIC_API_KEYS"] = '["ant-key1", "ant-key2", "ant-key3"]'
        os.environ["GEMINI_API_KEYS"] = '["gem-key1", "gem-key2"]'
        os.environ["XAI_API_KEYS"] = '["xai-key1", "xai-key2", "xai-key3", "xai-key4"]'

        try:
            settings = TestSettings()
            assert settings.openai_api_keys == [
                "sk-key1",
                "sk-key2",
                "sk-key3",
                "sk-key4",
                "sk-key5",
            ]
            assert settings.anthropic_api_keys == ["ant-key1", "ant-key2", "ant-key3"]
            assert settings.gemini_api_keys == ["gem-key1", "gem-key2"]
            assert settings.xai_api_keys == [
                "xai-key1",
                "xai-key2",
                "xai-key3",
                "xai-key4",
            ]
        finally:
            # Clean up
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["ANTHROPIC_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]
            del os.environ["XAI_API_KEYS"]

    def test_api_keys_with_spaces_in_json(self):
        """Test that JSON format handles spaces correctly."""
        # Set real environment variables with spaces in JSON (spaces should be preserved in values)
        os.environ["OPENAI_API_KEYS"] = (
            '[ "sk-key1", "sk-key2" , "sk-key3",  "sk-key4" ]'
        )
        os.environ["ANTHROPIC_API_KEYS"] = '["ant-key1", "ant-key2", "ant-key3"]'
        os.environ["GEMINI_API_KEYS"] = '["gem-key1", "gem-key2"]'
        os.environ["XAI_API_KEYS"] = '["xai-key1", "xai-key2"]'

        try:
            settings = TestSettings()
            assert settings.openai_api_keys == [
                "sk-key1",
                "sk-key2",
                "sk-key3",
                "sk-key4",
            ]
            assert settings.anthropic_api_keys == ["ant-key1", "ant-key2", "ant-key3"]
            assert settings.gemini_api_keys == ["gem-key1", "gem-key2"]
            assert settings.xai_api_keys == ["xai-key1", "xai-key2"]
        finally:
            # Clean up
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["ANTHROPIC_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]
            del os.environ["XAI_API_KEYS"]

    def test_empty_api_keys_list(self):
        """Test that empty JSON array results in empty list."""
        # Set real environment variables as empty JSON arrays
        os.environ["OPENAI_API_KEYS"] = "[]"
        os.environ["ANTHROPIC_API_KEYS"] = "[]"
        os.environ["GEMINI_API_KEYS"] = "[]"
        os.environ["XAI_API_KEYS"] = "[]"

        try:
            settings = TestSettings()
            assert settings.openai_api_keys == []
            assert settings.anthropic_api_keys == []
            assert settings.gemini_api_keys == []
            assert settings.xai_api_keys == []
        finally:
            # Clean up
            del os.environ["OPENAI_API_KEYS"]
            del os.environ["ANTHROPIC_API_KEYS"]
            del os.environ["GEMINI_API_KEYS"]
            del os.environ["XAI_API_KEYS"]

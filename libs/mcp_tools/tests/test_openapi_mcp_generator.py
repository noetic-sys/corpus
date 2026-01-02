"""Unit tests for OpenAPI MCP generator module."""

from pathlib import Path

from mcp_tools.openapi_mcp_generator import _load_openapi_spec


class TestLoadOpenAPISpec:
    """Test _load_openapi_spec function."""

    def test_bundled_spec_exists(self):
        """Test that the bundled OpenAPI spec file exists."""
        spec_path = Path(__file__).parent.parent / "mcp_tools" / "openapi.json"
        assert spec_path.exists(), f"Bundled OpenAPI spec not found at {spec_path}"

    def test_load_openapi_spec_returns_dict(self):
        """Test that _load_openapi_spec returns a dictionary."""
        spec = _load_openapi_spec()
        assert isinstance(spec, dict)

    def test_spec_has_required_keys(self):
        """Test that loaded spec has required OpenAPI keys."""
        spec = _load_openapi_spec()
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec

    def test_spec_has_paths(self):
        """Test that loaded spec has API paths defined."""
        spec = _load_openapi_spec()
        assert len(spec["paths"]) > 0

    def test_spec_version_is_valid(self):
        """Test that spec has valid OpenAPI version."""
        spec = _load_openapi_spec()
        assert spec["openapi"].startswith("3.")

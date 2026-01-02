"""
Tests for environment validation module.
"""

import os
from unittest.mock import patch

import pytest

from src.env_validator import (
    cleanup_sensitive_env_vars,
    debug_skills_availability,
    validate_environment,
)


class TestValidateEnvironment:
    """Tests for environment variable validation."""

    def test_validate_environment_success(self):
        """Test successful environment validation with all required variables."""
        env_vars = {
            "EXECUTION_ID": "123",
            "WORKFLOW_ID": "456",
            "WORKSPACE_ID": "789",
            "API_ENDPOINT": "http://api.example.com",
            "API_KEY": "test-key-789",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            execution_id, workflow_id, workspace_id, api_endpoint, api_key = (
                validate_environment()
            )

            assert execution_id == 123
            assert workflow_id == 456
            assert workspace_id == 789
            assert api_endpoint == "http://api.example.com"
            assert api_key == "test-key-789"

    def test_validate_environment_missing_execution_id(self):
        """Test validation fails when EXECUTION_ID is missing."""
        env_vars = {
            "WORKFLOW_ID": "456",
            "WORKSPACE_ID": "789",
            "API_ENDPOINT": "http://api.example.com",
            "API_KEY": "test-key-789",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError, match="Missing required environment variables"
            ):
                validate_environment()

    def test_validate_environment_missing_workflow_id(self):
        """Test validation fails when WORKFLOW_ID is missing."""
        env_vars = {
            "EXECUTION_ID": "123",
            "WORKSPACE_ID": "789",
            "API_ENDPOINT": "http://api.example.com",
            "API_KEY": "test-key-789",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError, match="Missing required environment variables"
            ):
                validate_environment()

    def test_validate_environment_missing_workspace_id(self):
        """Test validation fails when WORKSPACE_ID is missing."""
        env_vars = {
            "EXECUTION_ID": "123",
            "WORKFLOW_ID": "456",
            "API_ENDPOINT": "http://api.example.com",
            "API_KEY": "test-key-789",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError, match="Missing required environment variables"
            ):
                validate_environment()

    def test_validate_environment_missing_api_endpoint(self):
        """Test validation fails when API_ENDPOINT is missing."""
        env_vars = {
            "EXECUTION_ID": "123",
            "WORKFLOW_ID": "456",
            "WORKSPACE_ID": "789",
            "API_KEY": "test-key-789",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError, match="Missing required environment variables"
            ):
                validate_environment()

    def test_validate_environment_missing_api_key(self):
        """Test validation fails when API_KEY is missing."""
        env_vars = {
            "EXECUTION_ID": "123",
            "WORKFLOW_ID": "456",
            "WORKSPACE_ID": "789",
            "API_ENDPOINT": "http://api.example.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(
                ValueError, match="Missing required environment variables"
            ):
                validate_environment()

    def test_validate_environment_all_missing(self):
        """Test validation fails when all required variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="Missing required environment variables"
            ):
                validate_environment()


class TestCleanupSensitiveEnvVars:
    """Tests for sensitive environment variable cleanup."""

    def test_cleanup_removes_api_key(self):
        """Test that API_KEY is removed from environment."""
        with patch.dict(
            os.environ, {"API_KEY": "secret", "OTHER": "value"}, clear=False
        ):
            cleanup_sensitive_env_vars()

            assert "API_KEY" not in os.environ
            assert os.environ.get("OTHER") == "value"

    def test_cleanup_removes_api_endpoint(self):
        """Test that API_ENDPOINT is removed from environment."""
        with patch.dict(
            os.environ,
            {"API_ENDPOINT": "http://api.com", "OTHER": "value"},
            clear=False,
        ):
            cleanup_sensitive_env_vars()

            assert "API_ENDPOINT" not in os.environ
            assert os.environ.get("OTHER") == "value"

    def test_cleanup_removes_both(self):
        """Test that both API_KEY and API_ENDPOINT are removed."""
        env_vars = {
            "API_KEY": "secret",
            "API_ENDPOINT": "http://api.com",
            "KEEP_THIS": "value",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            cleanup_sensitive_env_vars()

            assert "API_KEY" not in os.environ
            assert "API_ENDPOINT" not in os.environ
            assert os.environ.get("KEEP_THIS") == "value"

    def test_cleanup_when_already_missing(self):
        """Test cleanup works when variables don't exist."""
        with patch.dict(os.environ, {"OTHER": "value"}, clear=True):
            # Should not raise an error
            cleanup_sensitive_env_vars()

            assert "API_KEY" not in os.environ
            assert "API_ENDPOINT" not in os.environ


class TestDebugSkillsAvailability:
    """Tests for skills availability debug utility."""

    def test_debug_skills_availability_outputs(self, capsys):
        """Test that debug function produces expected output."""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            debug_skills_availability()

            captured = capsys.readouterr()
            assert "Checking for skills..." in captured.out
            assert "/workspace/.claude/skills" in captured.out
            assert "/home/agentuser/.claude/skills" in captured.out
            assert ".claude/skills" in captured.out

    def test_debug_skills_availability_found_directory(self, capsys, tmp_path):
        """Test debug output when skills directory exists."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "skill1.py").touch()

        with patch("os.path.exists") as mock_exists, patch(
            "os.listdir"
        ) as mock_listdir:
            mock_exists.side_effect = lambda path: path == str(skills_dir)
            mock_listdir.return_value = ["skill1.py"]

            with patch("os.path.expanduser", return_value=str(tmp_path)):
                debug_skills_availability()

            captured = capsys.readouterr()
            assert "Checking for skills..." in captured.out

    def test_debug_skills_availability_with_subdirectories(self, capsys, tmp_path):
        """Test debug output when skills directory has subdirectories."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        subdir = skills_dir / "subdir"
        subdir.mkdir()
        (subdir / "file.py").touch()

        with patch("os.path.exists") as mock_exists, patch(
            "os.listdir"
        ) as mock_listdir, patch("os.path.isdir") as mock_isdir:

            def exists_side_effect(path):
                return path == str(skills_dir) or path == str(subdir)

            def listdir_side_effect(path):
                if path == str(skills_dir):
                    return ["subdir"]
                elif path == str(subdir):
                    return ["file.py"]
                return []

            def isdir_side_effect(path):
                return path == str(subdir)

            mock_exists.side_effect = exists_side_effect
            mock_listdir.side_effect = listdir_side_effect
            mock_isdir.side_effect = isdir_side_effect

            with patch("os.path.expanduser", return_value=str(tmp_path)):
                debug_skills_availability()

            captured = capsys.readouterr()
            assert "Checking for skills..." in captured.out

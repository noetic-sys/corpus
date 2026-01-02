"""
Tests for workflow configuration loading module.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from src.workflow_loader import (
    fetch_workflow,
    load_task_prompt,
)


class TestFetchWorkflow:
    """Tests for fetching workflow configuration."""

    @patch("src.workflow_loader.requests.get")
    def test_fetch_workflow_success(self, mock_get):
        """Test successfully fetching workflow configuration."""
        expected_workflow = {
            "id": "wf-123",
            "name": "Test Workflow",
            "description": "A test workflow",
            "output_type": "excel",
            "source_workspace_id": "ws-456",
        }

        mock_response = Mock()
        mock_response.json.return_value = expected_workflow
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_workflow("http://api.test.com", "wf-123", "key-456")

        assert result == expected_workflow
        mock_get.assert_called_once_with(
            "http://api.test.com/api/v1/workflows/wf-123",
            headers={"X-API-Key": "key-456"},
            timeout=30,
        )

    @patch("src.workflow_loader.requests.get")
    def test_fetch_workflow_http_error(self, mock_get):
        """Test handling of HTTP error when fetching workflow."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_workflow("http://api.test.com", "wf-123", "key-456")

    @patch("src.workflow_loader.requests.get")
    def test_fetch_workflow_network_error(self, mock_get):
        """Test handling of network error when fetching workflow."""
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Network unreachable"
        )

        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_workflow("http://api.test.com", "wf-123", "key-456")

    @patch("src.workflow_loader.requests.get")
    def test_fetch_workflow_timeout(self, mock_get):
        """Test handling of timeout when fetching workflow."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            fetch_workflow("http://api.test.com", "wf-123", "key-456")

    @patch("src.workflow_loader.requests.get")
    def test_fetch_workflow_invalid_json(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with pytest.raises(ValueError):
            fetch_workflow("http://api.test.com", "wf-123", "key-456")


class TestLoadTaskPrompt:
    """Tests for loading task prompt template."""

    def test_load_task_prompt_with_all_fields(self):
        """Test loading prompt with all workflow fields present."""
        workflow = {
            "id": "wf-123",
            "name": "Test Workflow",
            "description": "A test workflow for automation",
            "output_type": "excel",
            "source_workspace_id": "ws-456",
        }

        template_content = """
Workflow ID: {workflow_id}
Name: {workflow_name}
Description: {workflow_description}
Output Type: {output_type}
Workspace: {source_workspace_id}
"""

        with patch("pathlib.Path.read_text", return_value=template_content):
            result = load_task_prompt(workflow)

            assert "wf-123" in result
            assert "Test Workflow" in result
            assert "A test workflow for automation" in result
            assert "excel" in result
            assert "ws-456" in result

    def test_load_task_prompt_with_missing_fields(self):
        """Test loading prompt with missing optional fields uses defaults."""
        workflow = {
            "id": "wf-123",
            # Missing: name, description, output_type, source_workspace_id
        }

        template_content = """
Workflow ID: {workflow_id}
Name: {workflow_name}
Description: {workflow_description}
Output Type: {output_type}
Workspace: {source_workspace_id}
"""

        with patch("pathlib.Path.read_text", return_value=template_content):
            result = load_task_prompt(workflow)

            assert "wf-123" in result
            assert "Unnamed Workflow" in result
            assert "No description" in result
            assert "documents" in result
            assert "not specified" in result

    def test_load_task_prompt_with_empty_workflow(self):
        """Test loading prompt with empty workflow dict uses defaults."""
        workflow = {}

        template_content = """
Workflow ID: {workflow_id}
Name: {workflow_name}
"""

        with patch("pathlib.Path.read_text", return_value=template_content):
            result = load_task_prompt(workflow)

            assert "unknown" in result
            assert "Unnamed Workflow" in result

    def test_load_task_prompt_file_not_found(self):
        """Test handling when template file doesn't exist."""
        workflow = {"id": "wf-123"}

        with patch(
            "pathlib.Path.read_text",
            side_effect=FileNotFoundError("Template not found"),
        ):
            with pytest.raises(FileNotFoundError):
                load_task_prompt(workflow)

    def test_load_task_prompt_with_special_characters(self):
        """Test loading prompt with special characters in workflow fields."""
        workflow = {
            "id": "wf-123",
            "name": "Test & Workflow <html>",
            "description": "A workflow with 'quotes' and \"double quotes\"",
            "output_type": "pdf",
        }

        template_content = """
Name: {workflow_name}
Description: {workflow_description}
"""

        with patch("pathlib.Path.read_text", return_value=template_content):
            result = load_task_prompt(workflow)

            assert "Test & Workflow <html>" in result
            assert "A workflow with 'quotes' and \"double quotes\"" in result

    def test_load_task_prompt_with_none_values(self):
        """Test loading prompt when workflow fields are None."""
        workflow = {
            "id": None,
            "name": None,
            "description": None,
        }

        template_content = """
Workflow ID: {workflow_id}
Name: {workflow_name}
Description: {workflow_description}
"""

        with patch("pathlib.Path.read_text", return_value=template_content):
            result = load_task_prompt(workflow)

            # When dict contains None values, .get() returns None (not the default)
            # So the formatted string will contain "None"
            assert "None" in result

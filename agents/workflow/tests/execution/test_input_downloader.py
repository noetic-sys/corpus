"""
Tests for input file downloading module.
"""

from unittest.mock import Mock, mock_open, patch

import pytest
import requests

from src.input_downloader import download_input_files


class TestDownloadInputFiles:
    """Tests for input file downloading."""

    @patch("src.input_downloader.requests.get")
    def test_download_no_input_files(self, mock_get, capsys):
        """Test downloading when no input files exist."""
        # Mock the list response
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        download_input_files("http://api.test.com", "wf-123", "key-456")

        # Verify list endpoint was called
        mock_get.assert_called_once_with(
            "http://api.test.com/api/v1/workflows/wf-123/input-files",
            headers={"X-Api-Key": "key-456"},
            timeout=30,
        )

        captured = capsys.readouterr()
        assert "No input files to download" in captured.out

    @patch("src.input_downloader.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_single_input_file(self, mock_file, mock_get, capsys):
        """Test downloading a single input file."""
        # Mock the list response
        list_response = Mock()
        list_response.json.return_value = [
            {
                "id": "file-1",
                "name": "template.xlsx",
                "fileSize": 2048,
            }
        ]
        list_response.raise_for_status.return_value = None

        # Mock the download response
        download_response = Mock()
        download_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        download_response.raise_for_status.return_value = None

        mock_get.side_effect = [list_response, download_response]

        download_input_files("http://api.test.com", "wf-123", "key-456")

        # Verify both endpoints were called
        assert mock_get.call_count == 2
        mock_get.assert_any_call(
            "http://api.test.com/api/v1/workflows/wf-123/input-files",
            headers={"X-Api-Key": "key-456"},
            timeout=30,
        )
        mock_get.assert_any_call(
            "http://api.test.com/api/v1/workflows/wf-123/input-files/file-1/download",
            headers={"X-Api-Key": "key-456"},
            timeout=60,
            stream=True,
        )

        captured = capsys.readouterr()
        assert "Downloading 1 input file(s)..." in captured.out
        assert "✓ Downloaded: template.xlsx (2048 bytes)" in captured.out
        assert "All input files downloaded successfully" in captured.out

    @patch("src.input_downloader.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_multiple_input_files(self, mock_file, mock_get, capsys):
        """Test downloading multiple input files."""
        # Mock the list response
        list_response = Mock()
        list_response.json.return_value = [
            {
                "id": "file-1",
                "name": "template.xlsx",
                "fileSize": 2048,
            },
            {
                "id": "file-2",
                "name": "data.csv",
                "fileSize": 1024,
            },
        ]
        list_response.raise_for_status.return_value = None

        # Mock the download responses
        download_response_1 = Mock()
        download_response_1.iter_content.return_value = [b"chunk1"]
        download_response_1.raise_for_status.return_value = None

        download_response_2 = Mock()
        download_response_2.iter_content.return_value = [b"chunk2"]
        download_response_2.raise_for_status.return_value = None

        mock_get.side_effect = [list_response, download_response_1, download_response_2]

        download_input_files("http://api.test.com", "wf-123", "key-456")

        # Verify all endpoints were called
        assert mock_get.call_count == 3

        captured = capsys.readouterr()
        assert "Downloading 2 input file(s)..." in captured.out
        assert "✓ Downloaded: template.xlsx (2048 bytes)" in captured.out
        assert "✓ Downloaded: data.csv (1024 bytes)" in captured.out
        assert "All input files downloaded successfully" in captured.out

    @patch("src.input_downloader.requests.get")
    def test_download_list_request_fails(self, mock_get):
        """Test handling of list request failure."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(requests.exceptions.RequestException):
            download_input_files("http://api.test.com", "wf-123", "key-456")

    @patch("src.input_downloader.requests.get")
    def test_download_file_request_fails(self, mock_get):
        """Test handling of download request failure."""
        # Mock successful list response
        list_response = Mock()
        list_response.json.return_value = [
            {
                "id": "file-1",
                "name": "template.xlsx",
                "fileSize": 2048,
            }
        ]
        list_response.raise_for_status.return_value = None

        # Mock failed download response
        download_response = Mock()
        download_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )

        mock_get.side_effect = [list_response, download_response]

        with pytest.raises(requests.exceptions.HTTPError):
            download_input_files("http://api.test.com", "wf-123", "key-456")

    @patch("src.input_downloader.requests.get")
    @patch("builtins.open", side_effect=IOError("Disk full"))
    def test_download_file_write_fails(self, mock_file, mock_get):
        """Test handling of file write failure."""
        # Mock successful responses
        list_response = Mock()
        list_response.json.return_value = [
            {
                "id": "file-1",
                "name": "template.xlsx",
                "fileSize": 2048,
            }
        ]
        list_response.raise_for_status.return_value = None

        download_response = Mock()
        download_response.iter_content.return_value = [b"chunk1"]
        download_response.raise_for_status.return_value = None

        mock_get.side_effect = [list_response, download_response]

        with pytest.raises(IOError, match="Disk full"):
            download_input_files("http://api.test.com", "wf-123", "key-456")

    @patch("src.input_downloader.requests.get")
    def test_download_with_http_error_status(self, mock_get):
        """Test handling of HTTP error status codes."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "403 Forbidden"
        )
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            download_input_files("http://api.test.com", "wf-123", "key-456")

    @patch("src.input_downloader.requests.get")
    def test_download_with_timeout(self, mock_get):
        """Test handling of request timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            download_input_files("http://api.test.com", "wf-123", "key-456")

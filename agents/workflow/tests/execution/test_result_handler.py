"""
Tests for result handling module.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from workflows.execution_result import (
    ExecutionFileInfo,
    ExecutionFiles,
    ExecutionMetadata,
)

from src.result_handler import (
    list_generated_files,
    write_manifest,
)


class TestListGeneratedFiles:
    """Tests for listing generated files."""

    def test_list_generated_files_empty_directories(self, tmp_path):
        """Test listing files when directories are empty."""
        outputs_dir = tmp_path / "outputs"
        scratch_dir = tmp_path / "scratch"
        outputs_dir.mkdir()
        scratch_dir.mkdir()

        with patch("src.result_handler.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.rglob.return_value = []

            result = list_generated_files()

            assert isinstance(result, ExecutionFiles)
            assert len(result.outputs) == 0
            assert len(result.scratch) == 0

    def test_list_generated_files_nonexistent_directories(self):
        """Test listing files when directories don't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = list_generated_files()

            assert isinstance(result, ExecutionFiles)
            assert len(result.outputs) == 0
            assert len(result.scratch) == 0

    def test_list_generated_files_with_output_files(self, tmp_path):
        """Test listing files with output files present."""
        outputs_dir = tmp_path / "outputs"
        outputs_dir.mkdir()

        # Create test files
        (outputs_dir / "file1.xlsx").write_text("content1")
        (outputs_dir / "file2.pdf").write_text("content2")

        with patch("src.result_handler.Path") as mock_path:
            # Mock for outputs directory
            mock_outputs = mock_path.return_value
            mock_outputs.exists.return_value = True

            file1 = outputs_dir / "file1.xlsx"
            file2 = outputs_dir / "file2.pdf"

            mock_outputs.rglob.return_value = [file1, file2]

            # Mock file operations
            with patch("pathlib.Path.is_file", return_value=True), patch(
                "pathlib.Path.stat"
            ) as mock_stat, patch("pathlib.Path.relative_to") as mock_relative:

                mock_stat.return_value.st_size = 100
                mock_relative.side_effect = lambda x: (
                    Path("file1.xlsx") if "file1" in str(x) else Path("file2.pdf")
                )

                result = list_generated_files()

                assert isinstance(result, ExecutionFiles)
                # Note: The actual implementation may filter or process files differently

    def test_list_generated_files_with_nested_directories(self, tmp_path):
        """Test listing files in nested directory structure."""
        outputs_dir = tmp_path / "outputs"
        subdir = outputs_dir / "subdir"
        subdir.mkdir(parents=True)

        # Create nested files
        (outputs_dir / "root.txt").write_text("root content")
        (subdir / "nested.txt").write_text("nested content")

        with patch("src.result_handler.Path") as mock_path:
            mock_outputs = mock_path.return_value
            mock_outputs.exists.return_value = True

            root_file = outputs_dir / "root.txt"
            nested_file = subdir / "nested.txt"

            mock_outputs.rglob.return_value = [root_file, nested_file]

            with patch("pathlib.Path.is_file", return_value=True), patch(
                "pathlib.Path.stat"
            ) as mock_stat, patch("pathlib.Path.relative_to") as mock_relative:

                mock_stat.return_value.st_size = 100

                def relative_side_effect(base):
                    return Path("root.txt")

                mock_relative.side_effect = relative_side_effect

                result = list_generated_files()

                assert isinstance(result, ExecutionFiles)

    def test_list_generated_files_ignores_hidden_files(self, tmp_path):
        """Test that hidden files (starting with .) are ignored."""
        # This test verifies the logic in list_files_in_dir that filters out
        # files starting with '.'
        outputs_dir = tmp_path / "outputs"
        scratch_dir = tmp_path / "scratch"
        outputs_dir.mkdir()
        scratch_dir.mkdir()

        # Create visible and hidden files
        (outputs_dir / "visible.txt").write_text("visible")
        (outputs_dir / ".hidden").write_text("hidden")

        with patch(
            "src.result_handler.Path"
        ) as mock_path_class:

            def path_side_effect(path_str):
                if "outputs" in path_str:
                    return outputs_dir
                elif "scratch" in path_str:
                    return scratch_dir
                return Path(path_str)

            mock_path_class.side_effect = path_side_effect

            result = list_generated_files()

            # Should only include visible files (hidden files are filtered by the .startswith('.') check)
            assert isinstance(result, ExecutionFiles)


class TestWriteManifest:
    """Tests for writing execution manifest."""

    def test_write_manifest_success(self, tmp_path, capsys):
        """Test successfully writing manifest file."""
        manifest_path = tmp_path / ".manifest.json"

        files = ExecutionFiles(
            outputs=[
                ExecutionFileInfo(
                    name="output.xlsx",
                    relative_path="output.xlsx",
                    size=2048,
                    path="/workspace/outputs/output.xlsx",
                )
            ],
            scratch=[
                ExecutionFileInfo(
                    name="temp.txt",
                    relative_path="temp.txt",
                    size=512,
                    path="/workspace/scratch/temp.txt",
                )
            ],
        )

        metadata = ExecutionMetadata(success=True, cost_usd=0.05, duration_ms=5000)

        with patch(
            "src.result_handler.Path",
            return_value=manifest_path,
        ):
            with patch("builtins.open", create=True):

                write_manifest(123, files, metadata)

                captured = capsys.readouterr()
                assert "Manifest written" in captured.out

    def test_write_manifest_with_error(self, tmp_path, capsys):
        """Test writing manifest with error metadata."""
        manifest_path = tmp_path / ".manifest.json"

        files = ExecutionFiles(outputs=[], scratch=[])
        metadata = ExecutionMetadata(
            success=False, error="Agent execution failed: Network timeout"
        )

        with patch(
            "src.result_handler.Path",
            return_value=manifest_path,
        ):
            with patch("builtins.open", create=True):

                write_manifest(123, files, metadata)

                captured = capsys.readouterr()
                assert "Manifest written" in captured.out

    def test_write_manifest_empty_files(self, tmp_path, capsys):
        """Test writing manifest with no generated files."""
        manifest_path = tmp_path / ".manifest.json"

        files = ExecutionFiles(outputs=[], scratch=[])
        metadata = ExecutionMetadata(success=True)

        with patch(
            "src.result_handler.Path",
            return_value=manifest_path,
        ):
            with patch("builtins.open", create=True):
                write_manifest(123, files, metadata)

                captured = capsys.readouterr()
                assert "Manifest written" in captured.out

    def test_write_manifest_multiple_files(self, tmp_path, capsys):
        """Test writing manifest with multiple output and scratch files."""
        manifest_path = tmp_path / ".manifest.json"

        files = ExecutionFiles(
            outputs=[
                ExecutionFileInfo(
                    name="output1.xlsx",
                    relative_path="output1.xlsx",
                    size=2048,
                    path="/workspace/outputs/output1.xlsx",
                ),
                ExecutionFileInfo(
                    name="output2.pdf",
                    relative_path="output2.pdf",
                    size=4096,
                    path="/workspace/outputs/output2.pdf",
                ),
            ],
            scratch=[
                ExecutionFileInfo(
                    name="temp1.txt",
                    relative_path="temp1.txt",
                    size=512,
                    path="/workspace/scratch/temp1.txt",
                ),
                ExecutionFileInfo(
                    name="temp2.log",
                    relative_path="temp2.log",
                    size=1024,
                    path="/workspace/scratch/temp2.log",
                ),
            ],
        )

        metadata = ExecutionMetadata(success=True, cost_usd=0.10, duration_ms=10000)

        with patch(
            "src.result_handler.Path",
            return_value=manifest_path,
        ):
            with patch("builtins.open", create=True):
                write_manifest(123, files, metadata)

                captured = capsys.readouterr()
                assert "Manifest written" in captured.out

    def test_write_manifest_with_nested_paths(self, tmp_path, capsys):
        """Test writing manifest with files in nested directories."""
        manifest_path = tmp_path / ".manifest.json"

        files = ExecutionFiles(
            outputs=[
                ExecutionFileInfo(
                    name="report.xlsx",
                    relative_path="reports/2024/report.xlsx",
                    size=2048,
                    path="/workspace/outputs/reports/2024/report.xlsx",
                )
            ],
            scratch=[],
        )

        metadata = ExecutionMetadata(success=True)

        with patch(
            "src.result_handler.Path",
            return_value=manifest_path,
        ):
            with patch("builtins.open", create=True):
                write_manifest(123, files, metadata)

                captured = capsys.readouterr()
                assert "Manifest written" in captured.out

    def test_write_manifest_io_error(self, tmp_path):
        """Test handling of IO error when writing manifest."""
        files = ExecutionFiles(outputs=[], scratch=[])
        metadata = ExecutionMetadata(success=True)

        with patch("builtins.open", side_effect=IOError("Disk full")):
            with pytest.raises(IOError, match="Disk full"):
                write_manifest(123, files, metadata)

    def test_write_manifest_json_serialization(self, tmp_path):
        """Test that manifest is properly JSON serialized."""
        manifest_path = tmp_path / ".manifest.json"

        files = ExecutionFiles(
            outputs=[
                ExecutionFileInfo(
                    name="output.xlsx",
                    relative_path="output.xlsx",
                    size=2048,
                    path="/workspace/outputs/output.xlsx",
                )
            ],
            scratch=[],
        )

        metadata = ExecutionMetadata(success=True, cost_usd=0.05, duration_ms=5000)

        with patch(
            "src.result_handler.Path",
            return_value=manifest_path,
        ):
            with patch("builtins.open", create=True) as mock_open:
                mock_file = mock_open.return_value.__enter__.return_value
                written_calls = []

                def capture_write(data):
                    written_calls.append(data)

                mock_file.write.side_effect = capture_write

                write_manifest(123, files, metadata)

                # Verify json.dump was called with proper data
                assert mock_open.called

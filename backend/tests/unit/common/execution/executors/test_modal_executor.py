import pytest
from unittest.mock import patch, MagicMock

from common.execution.executors.modal_executor import ModalExecutor
from common.execution.job_spec import JobSpec


class TestModalExecutor:
    """Tests for ModalExecutor with mocked Modal SDK."""

    @pytest.fixture
    def executor(self):
        with patch(
            "common.execution.executors.modal_executor.modal"
        ) as mock_modal:
            mock_app = MagicMock()
            mock_modal.App.lookup.return_value = mock_app

            executor = ModalExecutor()
            executor._mock_modal = mock_modal
            yield executor

    @patch("common.execution.executors.modal_executor.settings")
    def test_launch_job(self, mock_settings, executor):
        mock_settings.workflow_agent_image_tag = "v1.2.3"

        mock_sandbox = MagicMock()
        mock_sandbox.object_id = "sb-123456"
        executor._mock_modal.Sandbox.create.return_value = mock_sandbox

        job_spec = JobSpec(
            container_name="workflow-exec-123",
            template_name="workflow_job.yaml.j2",
            image_name="corpus/workflow-agent",
            image_tag="latest",
            env_vars={
                "API_ENDPOINT": "http://test:8000",
                "API_KEY": "sa_test_key",
            },
            template_vars={"timeout": 600},
        )

        result = executor.launch(job_spec)

        assert result["mode"] == "modal"
        assert result["sandbox_id"] == "sb-123456"
        assert result["job_name"] == "workflow-exec-123"

        executor._mock_modal.Sandbox.create.assert_called_once()
        call_kwargs = executor._mock_modal.Sandbox.create.call_args[1]
        assert call_kwargs["timeout"] == 600
        assert call_kwargs["cpu"] == 1.0
        assert call_kwargs["memory"] == 1024
        assert call_kwargs["env"]["API_ENDPOINT"] == "http://test:8000"

    def test_launch_job_default_timeout(self, executor):
        mock_sandbox = MagicMock()
        mock_sandbox.object_id = "sb-789"
        executor._mock_modal.Sandbox.create.return_value = mock_sandbox

        with patch("common.execution.executors.modal_executor.settings") as mock_settings:
            mock_settings.workflow_agent_image_tag = "latest"

            job_spec = JobSpec(
                container_name="test-job",
                template_name="agent_qa_job.yaml.j2",
                image_name="corpus/agent-qa",
                env_vars={},
                template_vars={},  # No timeout specified
            )

            result = executor.launch(job_spec)

            call_kwargs = executor._mock_modal.Sandbox.create.call_args[1]
            assert call_kwargs["timeout"] == 900  # Default

    def test_check_status_running(self, executor):
        mock_sandbox = MagicMock()
        mock_sandbox.poll.return_value = None
        executor._mock_modal.Sandbox.from_id.return_value = mock_sandbox

        result = executor.check_status({"sandbox_id": "sb-123"})

        assert result["status"] == "running"

    def test_check_status_completed(self, executor):
        mock_sandbox = MagicMock()
        mock_sandbox.poll.return_value = 0
        executor._mock_modal.Sandbox.from_id.return_value = mock_sandbox

        result = executor.check_status({"sandbox_id": "sb-123"})

        assert result["status"] == "completed"
        assert result["exit_code"] == 0

    def test_check_status_failed(self, executor):
        mock_sandbox = MagicMock()
        mock_sandbox.poll.return_value = 1
        executor._mock_modal.Sandbox.from_id.return_value = mock_sandbox

        result = executor.check_status({"sandbox_id": "sb-123"})

        assert result["status"] == "failed"
        assert result["exit_code"] == 1

    def test_check_status_not_found(self, executor):
        executor._mock_modal.Sandbox.from_id.side_effect = Exception("Not found")

        result = executor.check_status({"sandbox_id": "sb-missing"})

        assert result["status"] == "failed"
        assert "not found" in result["error"].lower()

    def test_cleanup_success(self, executor):
        mock_sandbox = MagicMock()
        executor._mock_modal.Sandbox.from_id.return_value = mock_sandbox

        executor.cleanup({"sandbox_id": "sb-123", "job_name": "test-job"})

        mock_sandbox.terminate.assert_called_once()

    def test_cleanup_already_terminated(self, executor):
        executor._mock_modal.Sandbox.from_id.side_effect = Exception("Not found")

        # Should not raise
        executor.cleanup({"sandbox_id": "sb-missing", "job_name": "test-job"})

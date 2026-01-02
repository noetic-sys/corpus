import pytest
from kubernetes.config import ConfigException
from kubernetes.client.rest import ApiException
from unittest.mock import patch, MagicMock
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from common.execution.executors.k8s import K8sExecutor
from common.execution.job_spec import JobSpec


class TestK8sExecutor:
    """Tests for K8sExecutor with mocked K8s but real DB."""

    @pytest.fixture
    def executor(self):
        """Create K8sExecutor instance with mocked K8s clients."""
        with patch("common.execution.executors.k8s.config") as mock_config:
            # Mock config loading

            mock_config.ConfigException = ConfigException
            mock_config.load_incluster_config.side_effect = ConfigException(
                "Not in cluster"
            )
            mock_config.load_kube_config.return_value = None

            with patch("common.execution.executors.k8s.client") as mock_client:
                # Mock API clients
                mock_batch_v1 = MagicMock()
                mock_core_v1 = MagicMock()
                mock_client.BatchV1Api.return_value = mock_batch_v1
                mock_client.CoreV1Api.return_value = mock_core_v1

                # Create executor
                executor = K8sExecutor()
                executor.batch_v1 = mock_batch_v1
                executor.core_v1 = mock_core_v1

                yield executor

    @patch("common.execution.executors.k8s.client")
    def test_launch_job(self, mock_client, executor):
        """Test launching a Kubernetes job."""
        # Mock the API client deserialize (external K8s service)
        mock_job = MagicMock()
        mock_client.ApiClient().deserialize.return_value = mock_job

        # Mock successful job creation
        executor.batch_v1.create_namespaced_job.return_value = mock_job

        # Create JobSpec
        job_spec = JobSpec(
            container_name="workflow-exec-123",
            template_name="workflow_job.yaml.j2",
            image_name="workflow-agent",
            image_tag="latest",
            env_vars={
                "API_ENDPOINT": "http://test:8000",
                "API_KEY": "sa_test_key",
            },
            template_vars={
                "execution_id": 123,
                "workflow_id": 456,
                "workspace_id": 789,
            },
        )

        # Call launch
        result = executor.launch(job_spec)

        # Assertions
        assert result["mode"] == "k8s"
        assert result["job_name"] == "workflow-exec-123"

        # Verify job creation was called
        executor.batch_v1.create_namespaced_job.assert_called_once()
        call_kwargs = executor.batch_v1.create_namespaced_job.call_args[1]
        assert call_kwargs["namespace"] == "corpus"

    @patch("common.execution.executors.k8s.client")
    def test_launch_job_failure(self, mock_client, executor):
        """Test launch failure when K8s API fails."""
        # Mock the API client deserialize
        mock_job = MagicMock()
        mock_client.ApiClient().deserialize.return_value = mock_job

        # Mock job creation failure (external K8s service)

        executor.batch_v1.create_namespaced_job.side_effect = ApiException(
            status=500, reason="Internal Server Error"
        )

        # Create JobSpec
        job_spec = JobSpec(
            container_name="workflow-exec-123",
            template_name="workflow_job.yaml.j2",
            image_name="workflow-agent",
            image_tag="latest",
            env_vars={
                "API_ENDPOINT": "http://test:8000",
                "API_KEY": "sa_test_key",
            },
            template_vars={
                "execution_id": 123,
                "workflow_id": 456,
                "workspace_id": 789,
            },
        )

        # Call launch and expect exception
        with pytest.raises(Exception):
            executor.launch(job_spec)

    def test_check_status_completed(self, executor):
        """Test checking status of completed job."""
        # Mock job with succeeded status (external K8s service)
        mock_job = MagicMock()
        mock_job.status.succeeded = 1
        mock_job.status.failed = None
        executor.batch_v1.read_namespaced_job.return_value = mock_job

        execution_info = {"job_name": "workflow-exec-123"}

        # Call check_status
        result = executor.check_status(execution_info)

        # Assertions
        assert result["status"] == "completed"
        assert result["exit_code"] == 0

    def test_check_status_failed(self, executor):
        """Test checking status of failed job."""
        # Mock job with failed status (external K8s service)
        mock_job = MagicMock()
        mock_job.status.succeeded = None
        mock_job.status.failed = 1
        executor.batch_v1.read_namespaced_job.return_value = mock_job

        execution_info = {"job_name": "workflow-exec-123"}

        # Call check_status
        result = executor.check_status(execution_info)

        # Assertions
        assert result["status"] == "failed"
        assert result["exit_code"] == 1

    def test_check_status_running(self, executor):
        """Test checking status of running job."""
        # Mock job with no completion status (external K8s service)
        mock_job = MagicMock()
        mock_job.status.succeeded = None
        mock_job.status.failed = None
        executor.batch_v1.read_namespaced_job.return_value = mock_job

        execution_info = {"job_name": "workflow-exec-123"}

        # Call check_status
        result = executor.check_status(execution_info)

        # Assertions
        assert result["status"] == "running"

    def test_check_status_not_found(self, executor):
        """Test checking status when job not found."""
        # Mock job not found (external K8s service)

        executor.batch_v1.read_namespaced_job.side_effect = ApiException(
            status=404, reason="Not Found"
        )

        execution_info = {"job_name": "workflow-exec-123"}

        # Call check_status
        result = executor.check_status(execution_info)

        # Assertions
        assert result["status"] == "failed"
        assert "not found" in result["error"].lower()

    def test_cleanup_success(self, executor):
        """Test successful cleanup of job."""
        # Mock successful deletion (external K8s service)
        executor.batch_v1.delete_namespaced_job.return_value = None

        execution_info = {"job_name": "workflow-exec-123"}

        # Call cleanup
        executor.cleanup(execution_info)

        # Verify deletion was called
        executor.batch_v1.delete_namespaced_job.assert_called_once()
        call_kwargs = executor.batch_v1.delete_namespaced_job.call_args[1]
        assert call_kwargs["name"] == "workflow-exec-123"
        assert call_kwargs["namespace"] == "corpus"
        assert call_kwargs["propagation_policy"] == "Background"

    def test_cleanup_already_deleted(self, executor):
        """Test cleanup when job already deleted."""
        # Mock job not found (external K8s service)

        executor.batch_v1.delete_namespaced_job.side_effect = ApiException(
            status=404, reason="Not Found"
        )

        execution_info = {"job_name": "workflow-exec-123"}

        # Call cleanup - should not raise
        executor.cleanup(execution_info)


class TestK8sJobTemplate:
    """Tests for K8s job template rendering."""

    def test_template_renders_correctly(self):
        """Test that the Jinja2 template renders with all required fields."""

        # Get project root and navigate to template directory
        # From: tests/unit/common/execution/executors/test_k8s.py
        # Go up: executors -> execution -> common -> unit -> tests -> backend
        test_file = Path(__file__).resolve()
        backend_root = test_file.parents[5]  # Go up 5 levels to backend root
        template_dir = backend_root / "job_templates"

        jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = jinja_env.get_template("workflow_job.yaml.j2")

        # Render with test data
        rendered = template.render(
            job_name="test-job",
            namespace="corpus",
            execution_id=123,
            image="us-central1-docker.pkg.dev/test/corpus/workflow-agent:latest",
            env_vars=[
                {"name": "EXECUTION_ID", "value": "123"},
                {"name": "WORKFLOW_ID", "value": "456"},
                {"name": "WORKSPACE_ID", "value": "789"},
                {"name": "API_ENDPOINT", "value": "http://backend:8000"},
                {"name": "API_KEY", "value": "sa_test_key"},
            ],
        )

        # Assertions - check key values are in rendered template
        assert "test-job" in rendered
        assert 'execution_id: "123"' in rendered  # In metadata labels
        assert "name: WORKFLOW_ID" in rendered  # WORKFLOW_ID env var name
        assert 'value: "456"' in rendered  # WORKFLOW_ID env var value
        assert "name: WORKSPACE_ID" in rendered  # WORKSPACE_ID env var name
        assert 'value: "789"' in rendered  # WORKSPACE_ID env var value
        assert "http://backend:8000" in rendered
        assert "sa_test_key" in rendered
        assert "runtimeClassName: gvisor" in rendered
        assert "ttlSecondsAfterFinished: 300" in rendered
        assert "activeDeadlineSeconds: 1800" in rendered

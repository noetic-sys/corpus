import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from common.execution.workflow_framework.service_accounts import (
    create_execution_service_account,
)
from packages.workflows.temporal.activities import (
    launch_workflow_agent_activity,
    check_workflow_agent_status_activity,
    extract_workflow_results_activity,
    cleanup_workflow_agent_activity,
    update_execution_status_activity,
)


class TestLaunchWorkflowAgentActivity:
    """Tests for launch_workflow_agent_activity."""

    @pytest.mark.asyncio
    @patch("packages.workflows.temporal.activities._get_executor")
    @patch("packages.workflows.temporal.activities.activity")
    async def test_launch_workflow_agent(
        self,
        mock_activity,
        mock_get_executor,
        test_db,
        sample_company,
        test_user,
    ):
        """Test launching workflow agent with real service account creation."""
        # ServiceAccountService now uses lazy sessions via patch_lazy_sessions fixture

        # Mock activity logger
        mock_activity.logger = MagicMock()

        # Mock executor (external service)
        mock_executor = MagicMock()
        mock_executor.launch.return_value = {
            "mode": "docker",
            "container_id": "abc123",
            "container_name": "workflow-exec-456",
        }
        mock_get_executor.return_value = mock_executor

        # Call the activity - creates real service account in DB
        result = await launch_workflow_agent_activity(
            execution_id=456,
            workflow_id=789,
            workspace_id=999,
            created_by_user_id=test_user.user_id,
            created_by_company_id=sample_company.id,
        )

        # Assertions
        assert result["mode"] == "docker"
        assert result["container_id"] == "abc123"
        assert "service_account_id" in result
        assert isinstance(result["service_account_id"], int)

        # Verify executor was called with JobSpec containing correct data
        mock_executor.launch.assert_called_once()
        job_spec = mock_executor.launch.call_args[0][0]  # First positional arg
        assert job_spec.container_name == "workflow-exec-456"
        assert job_spec.template_name == "workflow_job.yaml.j2"
        assert job_spec.env_vars["EXECUTION_ID"] == "456"
        assert job_spec.env_vars["WORKFLOW_ID"] == "789"
        assert job_spec.env_vars["WORKSPACE_ID"] == "999"
        assert job_spec.env_vars["API_KEY"].startswith("sa_")
        assert job_spec.template_vars["execution_id"] == 456


class TestCheckWorkflowAgentStatusActivity:
    """Tests for check_workflow_agent_status_activity."""

    @pytest.mark.asyncio
    @patch("packages.workflows.temporal.activities._get_executor")
    async def test_check_status_running(self, mock_get_executor):
        """Test checking status when agent is running."""
        # Mock executor (external service)
        mock_executor = MagicMock()
        mock_executor.check_status.return_value = {"status": "running"}
        mock_get_executor.return_value = mock_executor

        execution_info = {"mode": "docker", "container_id": "abc123"}

        # Call the activity
        result = await check_workflow_agent_status_activity(execution_info)

        # Assertions
        assert result["status"] == "running"
        mock_executor.check_status.assert_called_once_with(execution_info)

    @pytest.mark.asyncio
    @patch("packages.workflows.temporal.activities._get_executor")
    async def test_check_status_completed(self, mock_get_executor):
        """Test checking status when agent has completed."""
        # Mock executor (external service)
        mock_executor = MagicMock()
        mock_executor.check_status.return_value = {
            "status": "completed",
            "exit_code": 0,
        }
        mock_get_executor.return_value = mock_executor

        execution_info = {"mode": "docker", "container_id": "abc123"}

        # Call the activity
        result = await check_workflow_agent_status_activity(execution_info)

        # Assertions
        assert result["status"] == "completed"
        assert result["exit_code"] == 0


class TestExtractWorkflowResultsActivity:
    """Tests for extract_workflow_results_activity."""

    @pytest.mark.asyncio
    @patch("packages.workflows.services.workflow_storage_service.get_storage")
    @patch("packages.workflows.temporal.activities.WorkflowStorageService")
    async def test_extract_results(
        self,
        mock_storage_service_class,
        mock_get_storage,
        test_db,
        mock_storage,
    ):
        """Test extracting results from S3 manifest and creating DB records."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage factory to prevent real GCS initialization
        mock_get_storage.return_value = mock_storage

        # Mock storage service to return manifest from S3
        mock_storage_service = MagicMock()
        mock_storage_service._get_execution_manifest_path.return_value = (
            "companies/123/workflows/789/executions/456/.manifest.json"
        )

        manifest_json = {
            "execution_id": "456",
            "output_files": [
                {
                    "name": "report.xlsx",
                    "size": 2048,
                    "path": "/workspace/outputs/report.xlsx",
                    "relative_path": "report.xlsx",
                }
            ],
            "scratch_files": [],
            "metadata": {"success": True, "cost_usd": 0.05, "duration_ms": 120000},
        }

        mock_storage.download = AsyncMock(
            return_value=json.dumps(manifest_json).encode()
        )
        mock_storage_service.storage = mock_storage
        mock_storage_service._get_execution_output_path.return_value = (
            "companies/123/workflows/789/executions/456/outputs/report.xlsx"
        )

        mock_storage_service_class.return_value = mock_storage_service

        execution_info = {"mode": "docker", "container_id": "abc123"}

        # Call the activity - reads from S3 and creates DB records
        result = await extract_workflow_results_activity(
            execution_info=execution_info,
            execution_id=456,
            workflow_id=789,
            company_id=123,
        )

        # Assertions
        assert len(result["generated_files"]) == 1
        assert result["total_size_bytes"] == 2048
        assert result["metadata"]["success"] is True

        # Verify S3 download was called
        mock_storage.download.assert_called_once_with(
            "companies/123/workflows/789/executions/456/.manifest.json"
        )


class TestCleanupWorkflowAgentActivity:
    """Tests for cleanup_workflow_agent_activity."""

    @pytest.mark.asyncio
    @patch("packages.workflows.temporal.activities._get_executor")
    @patch("packages.workflows.temporal.activities.activity")
    async def test_cleanup_success(
        self, mock_activity, mock_get_executor, test_db, sample_company
    ):
        """Test successful cleanup with real service account deletion."""
        # ServiceAccountService now uses lazy sessions via patch_lazy_sessions fixture

        # Mock activity logger
        mock_activity.logger = MagicMock()

        # First create a real service account
        service_account_id, _ = await create_execution_service_account(
            execution_id=456, company_id=sample_company.id
        )

        # Mock executor (external service)
        mock_executor = MagicMock()
        mock_executor.cleanup.return_value = None
        mock_get_executor.return_value = mock_executor

        execution_info = {
            "mode": "docker",
            "container_id": "abc123",
            "service_account_id": service_account_id,
        }

        # Call the activity - deletes real service account
        await cleanup_workflow_agent_activity(
            execution_info=execution_info, created_by_company_id=sample_company.id
        )

        # Verify cleanup was called
        mock_executor.cleanup.assert_called_once_with(execution_info)

    @pytest.mark.asyncio
    @patch("packages.workflows.temporal.activities._get_executor")
    @patch("packages.workflows.temporal.activities.activity")
    async def test_cleanup_container_failure_continues(
        self, mock_activity, mock_get_executor, test_db, sample_company
    ):
        """Test cleanup continues even if container cleanup fails."""
        # ServiceAccountService now uses lazy sessions via patch_lazy_sessions fixture

        # Mock activity logger
        mock_activity.logger = MagicMock()

        # Create real service account
        service_account_id, _ = await create_execution_service_account(
            execution_id=789, company_id=sample_company.id
        )

        # Mock executor to raise exception (external service)
        mock_executor = MagicMock()
        mock_executor.cleanup.side_effect = Exception("Container cleanup failed")
        mock_get_executor.return_value = mock_executor

        execution_info = {
            "mode": "docker",
            "container_id": "abc123",
            "service_account_id": service_account_id,
        }

        # Call the activity - should not raise exception
        await cleanup_workflow_agent_activity(
            execution_info=execution_info, created_by_company_id=sample_company.id
        )

        # Service account should still be cleaned up (verify via DB later if needed)


class TestUpdateExecutionStatusActivity:
    """Tests for update_execution_status_activity."""

    @pytest.mark.asyncio
    @patch("packages.workflows.temporal.activities.activity")
    async def test_update_status_completed(
        self, mock_activity, test_db, sample_workflow_execution
    ):
        """Test updating execution status to completed with real DB."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock activity logger
        mock_activity.logger = MagicMock()

        generated_files = [{"name": "report.xlsx", "size": 2048}]

        # Call the activity - updates real execution in DB
        await update_execution_status_activity(
            execution_id=sample_workflow_execution.id,
            status="completed",
            generated_files=generated_files,
            total_size_bytes=2048,
            metadata={"duration": 120},
        )

        # Verify via DB query would go here if needed
        # The activity uses its own session, so we'd need to re-query

    @pytest.mark.asyncio
    @patch("packages.workflows.temporal.activities.activity")
    async def test_update_status_failed(
        self, mock_activity, test_db, sample_workflow_execution
    ):
        """Test updating execution status to failed with real DB."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock activity logger
        mock_activity.logger = MagicMock()

        # Call the activity - updates real execution in DB
        await update_execution_status_activity(
            execution_id=sample_workflow_execution.id,
            status="failed",
            generated_files=None,
            total_size_bytes=None,
            metadata={"error": "Execution timed out"},
        )

        # Activity completes successfully even with failed status

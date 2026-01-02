import pytest
from datetime import datetime, timezone
from packages.workflows.models.database.workflow import WorkflowExecutionEntity
from sqlalchemy.ext.asyncio import AsyncSession

from packages.workflows.models.domain.execution_file import ExecutionFileCreateModel
from packages.workflows.repositories.execution_file_repository import (
    ExecutionFileRepository,
)
from packages.workflows.models.database.execution_file import (
    WorkflowExecutionFile,
    ExecutionFileType,
)


class TestExecutionFileRepository:
    """Test ExecutionFileRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return ExecutionFileRepository(test_db)

    async def test_get_execution_file_by_id(
        self, repository, sample_workflow_execution_file
    ):
        """Test getting an execution file by ID."""
        result = await repository.get(sample_workflow_execution_file.id)

        assert result is not None
        assert result.id == sample_workflow_execution_file.id
        assert result.execution_id == sample_workflow_execution_file.execution_id
        assert result.company_id == sample_workflow_execution_file.company_id
        assert result.name == "test_output.xlsx"
        assert result.file_type == ExecutionFileType.OUTPUT

    async def test_list_by_execution(
        self, repository, sample_workflow_execution, sample_company, test_db
    ):
        """Test listing files for an execution."""
        # Create multiple files
        output_file = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.OUTPUT.value,
            name="output.xlsx",
            storage_path=f"workflows/executions/{sample_workflow_execution.id}/outputs/output.xlsx",
            file_size=4096,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        scratch_file = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.SCRATCH.value,
            name="debug.txt",
            storage_path=f"workflows/executions/{sample_workflow_execution.id}/scratch/debug.txt",
            file_size=512,
            mime_type="text/plain",
        )
        test_db.add_all([output_file, scratch_file])
        await test_db.commit()

        results = await repository.list_by_execution(sample_workflow_execution.id)

        assert len(results) == 2
        file_names = {f.name for f in results}
        assert "output.xlsx" in file_names
        assert "debug.txt" in file_names

    async def test_list_by_execution_filtered_by_type(
        self, repository, sample_workflow_execution, sample_company, test_db
    ):
        """Test listing files filtered by file type."""
        # Create multiple files of different types
        output_file = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.OUTPUT.value,
            name="output.xlsx",
            storage_path=f"workflows/executions/{sample_workflow_execution.id}/outputs/output.xlsx",
            file_size=4096,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        scratch_file = WorkflowExecutionFile(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.SCRATCH.value,
            name="debug.txt",
            storage_path=f"workflows/executions/{sample_workflow_execution.id}/scratch/debug.txt",
            file_size=512,
            mime_type="text/plain",
        )
        test_db.add_all([output_file, scratch_file])
        await test_db.commit()

        # List only output files
        output_results = await repository.list_by_execution(
            sample_workflow_execution.id, file_type=ExecutionFileType.OUTPUT
        )
        assert len(output_results) == 1
        assert output_results[0].file_type == ExecutionFileType.OUTPUT
        assert output_results[0].name == "output.xlsx"

        # List only scratch files
        scratch_results = await repository.list_by_execution(
            sample_workflow_execution.id, file_type=ExecutionFileType.SCRATCH
        )
        assert len(scratch_results) == 1
        assert scratch_results[0].file_type == ExecutionFileType.SCRATCH
        assert scratch_results[0].name == "debug.txt"

    async def test_list_by_execution_empty(self, repository, sample_workflow_execution):
        """Test listing files for execution with no files."""
        results = await repository.list_by_execution(sample_workflow_execution.id)
        assert len(results) == 0

    async def test_list_by_execution_multiple_executions(
        self, repository, sample_workflow, sample_company, test_db
    ):
        """Test that files are isolated per execution."""

        # Create two executions
        execution1 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="completed",
        )
        execution2 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="completed",
        )
        test_db.add_all([execution1, execution2])
        await test_db.commit()
        await test_db.refresh(execution1)
        await test_db.refresh(execution2)

        # Create files for each execution
        file1 = WorkflowExecutionFile(
            execution_id=execution1.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.OUTPUT.value,
            name="execution1_output.xlsx",
            storage_path=f"workflows/executions/{execution1.id}/outputs/output.xlsx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        file2 = WorkflowExecutionFile(
            execution_id=execution2.id,
            company_id=sample_company.id,
            file_type=ExecutionFileType.OUTPUT.value,
            name="execution2_output.xlsx",
            storage_path=f"workflows/executions/{execution2.id}/outputs/output.xlsx",
            file_size=3072,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        test_db.add_all([file1, file2])
        await test_db.commit()

        # List files for execution1
        results1 = await repository.list_by_execution(execution1.id)
        assert len(results1) == 1
        assert results1[0].name == "execution1_output.xlsx"

        # List files for execution2
        results2 = await repository.list_by_execution(execution2.id)
        assert len(results2) == 1
        assert results2[0].name == "execution2_output.xlsx"

    async def test_create_execution_file(
        self, repository, sample_workflow_execution, sample_company
    ):
        """Test creating a new execution file."""

        file_data = ExecutionFileCreateModel(
            execution_id=sample_workflow_execution.id,
            company_id=sample_company.id,
            file_type="output",
            name="report.pdf",
            storage_path=f"workflows/executions/{sample_workflow_execution.id}/outputs/report.pdf",
            file_size=8192,
            mime_type="application/pdf",
        )

        result = await repository.create(file_data)

        assert result is not None
        assert result.name == "report.pdf"
        assert result.execution_id == sample_workflow_execution.id
        assert result.company_id == sample_company.id
        assert result.file_type == ExecutionFileType.OUTPUT
        assert result.file_size == 8192

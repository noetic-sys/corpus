import pytest
from packages.workflows.models.domain.input_file import (
    InputFileCreateModel,
    InputFileUpdateModel,
)
from sqlalchemy.ext.asyncio import AsyncSession
from packages.workflows.repositories.input_file_repository import InputFileRepository
from packages.workflows.models.database.input_file import WorkflowInputFile


class TestInputFileRepository:
    """Test InputFileRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return InputFileRepository(test_db)

    async def test_get_input_file_by_id(self, repository, sample_workflow_input_file):
        """Test getting an input file by ID."""
        result = await repository.get(sample_workflow_input_file.id)

        assert result is not None
        assert result.id == sample_workflow_input_file.id
        assert result.workflow_id == sample_workflow_input_file.workflow_id
        assert result.company_id == sample_workflow_input_file.company_id
        assert result.name == "test_template.xlsx"

    async def test_get_with_company_filter(
        self, repository, sample_workflow_input_file, second_company
    ):
        """Test getting file with company filtering."""
        # Should not find file from different company
        result = await repository.get(
            sample_workflow_input_file.id, company_id=second_company.id
        )
        assert result is None

        # Should find file from correct company
        result = await repository.get(
            sample_workflow_input_file.id,
            company_id=sample_workflow_input_file.company_id,
        )
        assert result is not None
        assert result.id == sample_workflow_input_file.id

    async def test_get_excludes_deleted(
        self, repository, sample_workflow, sample_company, test_db
    ):
        """Test that get excludes soft deleted files."""
        # Create deleted file
        deleted_file = WorkflowInputFile(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            name="deleted.xlsx",
            storage_path="workflows/1/inputs/deleted.xlsx",
            file_size=1024,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            deleted=True,
        )
        test_db.add(deleted_file)
        await test_db.commit()
        await test_db.refresh(deleted_file)

        result = await repository.get(deleted_file.id)
        assert result is None

    async def test_list_by_workflow(
        self, repository, sample_workflow, sample_company, test_db
    ):
        """Test listing input files for a workflow."""
        # Create multiple files
        file1 = WorkflowInputFile(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            name="template1.xlsx",
            storage_path="workflows/1/inputs/template1.xlsx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        file2 = WorkflowInputFile(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            name="template2.xlsx",
            storage_path="workflows/1/inputs/template2.xlsx",
            file_size=3072,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        test_db.add_all([file1, file2])
        await test_db.commit()

        results = await repository.list_by_workflow(sample_workflow.id)

        assert len(results) == 2
        file_names = {f.name for f in results}
        assert "template1.xlsx" in file_names
        assert "template2.xlsx" in file_names

    async def test_list_by_workflow_with_company_filter(
        self, repository, sample_workflow, sample_company, second_company, test_db
    ):
        """Test listing files with company filtering."""
        # Create file for first company
        file1 = WorkflowInputFile(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            name="company1.xlsx",
            storage_path="workflows/1/inputs/company1.xlsx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        test_db.add(file1)
        await test_db.commit()

        # List with correct company
        results = await repository.list_by_workflow(
            sample_workflow.id, company_id=sample_company.id
        )
        assert len(results) == 1
        assert results[0].name == "company1.xlsx"

        # List with different company
        results = await repository.list_by_workflow(
            sample_workflow.id, company_id=second_company.id
        )
        assert len(results) == 0

    async def test_list_by_workflow_excludes_deleted(
        self, repository, sample_workflow, sample_company, test_db
    ):
        """Test that list excludes soft deleted files."""
        # Create active and deleted files
        active_file = WorkflowInputFile(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            name="active.xlsx",
            storage_path="workflows/1/inputs/active.xlsx",
            file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            deleted=False,
        )
        deleted_file = WorkflowInputFile(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            name="deleted.xlsx",
            storage_path="workflows/1/inputs/deleted.xlsx",
            file_size=1024,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            deleted=True,
        )
        test_db.add_all([active_file, deleted_file])
        await test_db.commit()

        results = await repository.list_by_workflow(sample_workflow.id)

        assert len(results) == 1
        assert results[0].name == "active.xlsx"

    async def test_soft_delete(self, repository, sample_workflow_input_file):
        """Test soft deleting an input file."""
        success = await repository.delete(sample_workflow_input_file.id)
        assert success is True

        # Verify file is soft deleted (not returned by get)
        result = await repository.get(sample_workflow_input_file.id)
        assert result is None

    async def test_soft_delete_with_company_filter(
        self, repository, sample_workflow_input_file, second_company
    ):
        """Test soft delete with company filtering."""
        # Try to delete with wrong company
        success = await repository.delete(
            sample_workflow_input_file.id, company_id=second_company.id
        )
        assert success is False

        # File should still exist
        result = await repository.get(sample_workflow_input_file.id)
        assert result is not None

        # Delete with correct company
        success = await repository.delete(
            sample_workflow_input_file.id,
            company_id=sample_workflow_input_file.company_id,
        )
        assert success is True

        # File should now be deleted
        result = await repository.get(sample_workflow_input_file.id)
        assert result is None

    async def test_create_input_file(self, repository, sample_workflow, sample_company):
        """Test creating a new input file."""

        file_data = InputFileCreateModel(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            name="new_template.xlsx",
            description="A new Excel template",
            storage_path="workflows/1/inputs/new_template.xlsx",
            file_size=4096,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        result = await repository.create(file_data)

        assert result is not None
        assert result.name == "new_template.xlsx"
        assert result.workflow_id == sample_workflow.id
        assert result.company_id == sample_company.id
        assert result.file_size == 4096

    async def test_update_input_file(self, repository, sample_workflow_input_file):
        """Test updating an input file."""

        update_data = InputFileUpdateModel(
            name="updated_template.xlsx",
            description="Updated description",
        )

        result = await repository.update(sample_workflow_input_file.id, update_data)

        assert result is not None
        assert result.name == "updated_template.xlsx"
        assert result.description == "Updated description"
        assert result.workflow_id == sample_workflow_input_file.workflow_id

    async def test_list_by_workflow_empty(self, repository, sample_workflow):
        """Test listing files for workflow with no files."""
        results = await repository.list_by_workflow(sample_workflow.id)
        assert len(results) == 0

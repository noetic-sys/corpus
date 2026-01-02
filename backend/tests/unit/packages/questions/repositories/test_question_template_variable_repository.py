import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from packages.questions.repositories.question_template_variable_repository import (
    QuestionTemplateVariableRepository,
)
from packages.questions.models.database.question_template_variable import (
    QuestionTemplateVariableEntity,
)
from packages.matrices.models.database.matrix_template_variable import (
    MatrixTemplateVariableEntity,
)
from packages.questions.models.database.question import QuestionEntity
from packages.questions.models.domain.question_template_variable import (
    QuestionTemplateVariableCreateModel,
)


class TestQuestionTemplateVariableRepository:
    """Test QuestionTemplateVariableRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return QuestionTemplateVariableRepository(test_db)

    async def test_create_association(
        self, repository, sample_question, sample_template_variable, sample_company
    ):
        """Test creating a question-template variable association."""
        assoc_data = QuestionTemplateVariableCreateModel(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_company.id,
        )

        result = await repository.create(assoc_data)

        assert result.question_id == sample_question.id
        assert result.template_variable_id == sample_template_variable.id
        assert result.company_id == sample_company.id
        assert result.deleted is False

    async def test_get_association_by_id(self, repository, sample_association):
        """Test getting association by ID."""
        result = await repository.get(sample_association.id)

        assert result is not None
        assert result.id == sample_association.id
        assert result.question_id == sample_association.question_id
        assert result.template_variable_id == sample_association.template_variable_id

    async def test_get_association_not_found(self, repository):
        """Test getting non-existent association."""
        result = await repository.get(999)
        assert result is None

    async def test_get_by_question_id(
        self, repository, sample_question, test_db, sample_matrix, sample_company
    ):
        """Test getting all template variable associations for a question."""
        # Create multiple template variables and associations
        template_vars = []
        for i in range(3):
            var = MatrixTemplateVariableEntity(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                template_string=f"var{i}",
                value=f"value{i}",
            )
            test_db.add(var)
            template_vars.append(var)

        await test_db.commit()

        for var in template_vars:
            await test_db.refresh(var)

        # Create associations
        for var in template_vars:
            assoc = QuestionTemplateVariableEntity(
                question_id=sample_question.id,
                template_variable_id=var.id,
                company_id=sample_company.id,
            )
            test_db.add(assoc)

        await test_db.commit()

        # Test retrieval
        results = await repository.get_by_question_id(sample_question.id)

        assert len(results) >= 3  # At least our created associations
        var_ids = [assoc.template_variable_id for assoc in results]
        for var in template_vars:
            assert var.id in var_ids

    async def test_get_by_question_id_excludes_deleted(
        self, repository, sample_question, sample_template_variable, test_db
    ):
        """Test that get_by_question_id excludes soft deleted associations."""
        # Create active and deleted associations
        active_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=False,
        )
        deleted_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=True,
        )
        test_db.add(active_assoc)
        test_db.add(deleted_assoc)
        await test_db.commit()

        results = await repository.get_by_question_id(sample_question.id)

        # Should only return the active association
        assert len([r for r in results if not r.deleted]) == 1
        assert all(not r.deleted for r in results)

    async def test_get_by_template_variable_id(
        self,
        repository,
        sample_template_variable,
        test_db,
        sample_matrix,
        sample_company,
    ):
        """Test getting all questions using a specific template variable."""
        # Create multiple questions
        questions = []
        for i in range(3):
            question = QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text=f"Question {i} about #{{1}}",
                question_type_id=1,
                company_id=sample_company.id,
            )
            test_db.add(question)
            questions.append(question)

        await test_db.commit()

        for question in questions:
            await test_db.refresh(question)

        # Create associations
        for question in questions:
            assoc = QuestionTemplateVariableEntity(
                question_id=question.id,
                template_variable_id=sample_template_variable.id,
                company_id=sample_company.id,
            )
            test_db.add(assoc)

        await test_db.commit()

        # Test retrieval
        results = await repository.get_by_template_variable_id(
            sample_template_variable.id
        )

        assert len(results) >= 3  # At least our created associations
        question_ids = [assoc.question_id for assoc in results]
        for question in questions:
            assert question.id in question_ids

    async def test_get_by_template_variable_id_excludes_deleted(
        self, repository, sample_template_variable, sample_question, test_db
    ):
        """Test that get_by_template_variable_id excludes soft deleted associations."""
        # Create active and deleted associations
        active_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=False,
        )
        deleted_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=True,
        )
        test_db.add(active_assoc)
        test_db.add(deleted_assoc)
        await test_db.commit()

        results = await repository.get_by_template_variable_id(
            sample_template_variable.id
        )

        # Should only return the active association
        assert len([r for r in results if not r.deleted]) == 1
        assert all(not r.deleted for r in results)

    async def test_get_questions_by_template_variable(
        self,
        repository,
        sample_template_variable,
        test_db,
        sample_matrix,
        sample_company,
    ):
        """Test getting question IDs that use a specific template variable."""
        # Create multiple questions and associations
        questions = []
        for i in range(3):
            question = QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text=f"Question {i} about #{{1}}",
                question_type_id=1,
                company_id=sample_company.id,
            )
            test_db.add(question)
            questions.append(question)

        await test_db.commit()

        for question in questions:
            await test_db.refresh(question)

        # Create associations
        for question in questions:
            assoc = QuestionTemplateVariableEntity(
                question_id=question.id,
                template_variable_id=sample_template_variable.id,
                company_id=sample_company.id,
            )
            test_db.add(assoc)

        await test_db.commit()

        # Test retrieval
        question_ids = await repository.get_questions_by_template_variable(
            sample_template_variable.id
        )

        assert len(question_ids) >= 3
        for question in questions:
            assert question.id in question_ids

    async def test_bulk_get_questions_by_variables(
        self, repository, test_db, sample_matrix, sample_company
    ):
        """Test getting all question IDs that use any of the specified template variables."""
        # Create template variables
        vars_data = [
            {"template_string": "var1", "value": "value1"},
            {"template_string": "var2", "value": "value2"},
            {"template_string": "var3", "value": "value3"},
        ]

        template_vars = []
        for data in vars_data:
            var = MatrixTemplateVariableEntity(
                company_id=sample_company.id, matrix_id=sample_matrix.id, **data
            )
            test_db.add(var)
            template_vars.append(var)

        # Create questions
        questions_data = [
            {"question_text": "Question 1", "question_type_id": 1},
            {"question_text": "Question 2", "question_type_id": 1},
            {"question_text": "Question 3", "question_type_id": 1},
        ]

        questions = []
        for data in questions_data:
            question = QuestionEntity(
                company_id=sample_company.id, matrix_id=sample_matrix.id, **data
            )
            test_db.add(question)
            questions.append(question)

        await test_db.commit()

        for var in template_vars:
            await test_db.refresh(var)
        for question in questions:
            await test_db.refresh(question)

        # Create associations: Q1 uses V1, Q2 uses V1+V2, Q3 uses V3
        associations = [
            (questions[0].id, template_vars[0].id),  # Q1 -> V1
            (questions[1].id, template_vars[0].id),  # Q2 -> V1
            (questions[1].id, template_vars[1].id),  # Q2 -> V2
            (questions[2].id, template_vars[2].id),  # Q3 -> V3
        ]

        for question_id, var_id in associations:
            assoc = QuestionTemplateVariableEntity(
                question_id=question_id,
                template_variable_id=var_id,
                company_id=sample_company.id,
            )
            test_db.add(assoc)

        await test_db.commit()

        # Test: Get questions using V1 and V3
        var_ids = [template_vars[0].id, template_vars[2].id]
        question_ids = await repository.bulk_get_questions_by_variables(var_ids)

        # Should return Q1 (uses V1), Q2 (uses V1), Q3 (uses V3)
        assert len(question_ids) == 3
        assert questions[0].id in question_ids
        assert questions[1].id in question_ids
        assert questions[2].id in question_ids

    async def test_bulk_get_questions_by_variables_empty_list(self, repository):
        """Test bulk get with empty variable list."""
        question_ids = await repository.bulk_get_questions_by_variables([])
        assert question_ids == []

    async def test_bulk_get_questions_by_variables_excludes_deleted(
        self, repository, sample_question, sample_template_variable, test_db
    ):
        """Test that bulk get excludes soft deleted associations."""
        # Create active and deleted associations
        active_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=False,
        )
        deleted_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=True,
        )
        test_db.add(active_assoc)
        test_db.add(deleted_assoc)
        await test_db.commit()

        question_ids = await repository.bulk_get_questions_by_variables(
            [sample_template_variable.id]
        )

        # Should only return question once (from active association)
        assert question_ids == [sample_question.id]

    async def test_delete_by_question_id(
        self, repository, sample_question, test_db, sample_matrix, sample_company
    ):
        """Test soft deleting all associations for a question."""
        # Create multiple associations
        template_vars = []
        for i in range(3):
            var = MatrixTemplateVariableEntity(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                template_string=f"var{i}",
                value=f"value{i}",
            )
            test_db.add(var)
            template_vars.append(var)

        await test_db.commit()

        for var in template_vars:
            await test_db.refresh(var)

        for var in template_vars:
            assoc = QuestionTemplateVariableEntity(
                question_id=sample_question.id,
                template_variable_id=var.id,
                company_id=sample_company.id,
            )
            test_db.add(assoc)

        await test_db.commit()

        # Verify associations exist
        before_delete = await repository.get_by_question_id(sample_question.id)
        assert len(before_delete) == 3

        # Delete all associations for the question
        deleted_count = await repository.delete_by_question_id(sample_question.id)
        assert deleted_count == 3

        # Verify associations are soft deleted
        after_delete = await repository.get_by_question_id(sample_question.id)
        assert len(after_delete) == 0

    async def test_exists(
        self, repository, sample_question, sample_template_variable, sample_association
    ):
        """Test checking if association exists."""
        # Test existing association
        exists = await repository.exists(
            sample_question.id, sample_template_variable.id
        )
        assert exists is True

        # Test non-existing association
        exists = await repository.exists(sample_question.id, 999)
        assert exists is False

    async def test_exists_excludes_deleted(
        self, repository, sample_question, sample_template_variable, test_db
    ):
        """Test that exists excludes soft deleted associations."""
        # Create soft deleted association
        deleted_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=True,
        )
        test_db.add(deleted_assoc)
        await test_db.commit()

        exists = await repository.exists(
            sample_question.id, sample_template_variable.id
        )
        assert exists is False

    async def test_soft_delete(self, repository, sample_association):
        """Test soft deleting a specific association."""
        success = await repository.soft_delete(sample_association.id)
        assert success is True

        # Verify it's soft deleted
        result = await repository.get(sample_association.id)
        assert result is None

    async def test_soft_delete_not_found(self, repository):
        """Test soft deleting non-existent association."""
        success = await repository.soft_delete(999)
        assert success is False

    async def test_hard_delete(self, repository, sample_association):
        """Test permanently deleting an association."""
        association_id = sample_association.id

        success = await repository.hard_delete(association_id)
        assert success is True

        # Verify it's permanently deleted
        result = await repository.get(association_id)
        assert result is None

    async def test_hard_delete_not_found(self, repository):
        """Test hard deleting non-existent association."""
        success = await repository.hard_delete(999)
        assert success is False

    async def test_find_soft_deleted_association(
        self, repository, sample_question, sample_template_variable, test_db
    ):
        """Test finding soft deleted association."""
        # Create soft deleted association
        deleted_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=True,
        )
        test_db.add(deleted_assoc)
        await test_db.commit()
        await test_db.refresh(deleted_assoc)

        # Find the soft deleted association
        result = await repository.find_soft_deleted_association(
            sample_question.id, sample_template_variable.id
        )

        assert result is not None
        assert result.question_id == sample_question.id
        assert result.template_variable_id == sample_template_variable.id
        assert result.deleted is True

    async def test_find_soft_deleted_association_not_found(
        self, repository, sample_question
    ):
        """Test finding non-existent soft deleted association."""
        result = await repository.find_soft_deleted_association(sample_question.id, 999)
        assert result is None

    async def test_restore_soft_deleted_association(
        self, repository, sample_question, sample_template_variable, test_db
    ):
        """Test restoring a soft deleted association."""
        # Create soft deleted association
        deleted_assoc = QuestionTemplateVariableEntity(
            question_id=sample_question.id,
            template_variable_id=sample_template_variable.id,
            company_id=sample_question.company_id,
            deleted=True,
        )
        test_db.add(deleted_assoc)
        await test_db.commit()
        await test_db.refresh(deleted_assoc)

        # Restore the association
        success = await repository.restore_soft_deleted_association(deleted_assoc.id)
        assert success is True

        # Verify it's restored (appears in normal queries)
        result = await repository.get(deleted_assoc.id)
        assert result is not None
        assert result.deleted is False

    async def test_restore_soft_deleted_association_not_found(self, repository):
        """Test restoring non-existent soft deleted association."""
        success = await repository.restore_soft_deleted_association(999)
        assert success is False

    async def test_delete_override_uses_soft_delete(
        self, repository, sample_association
    ):
        """Test that delete method uses soft delete instead of hard delete."""
        association_id = sample_association.id

        success = await repository.delete(association_id)
        assert success is True

        # Verify it's soft deleted (not returned in normal queries)
        result = await repository.get(association_id)
        assert result is None

        # But can be found as soft deleted
        soft_deleted = await repository.find_soft_deleted_association(
            sample_association.question_id, sample_association.template_variable_id
        )
        assert soft_deleted is not None

    async def test_repository_initialization(self, test_db):
        """Test repository properly initializes."""
        repository = QuestionTemplateVariableRepository(test_db)

        assert repository.db_session == test_db
        assert repository.entity_class == QuestionTemplateVariableEntity

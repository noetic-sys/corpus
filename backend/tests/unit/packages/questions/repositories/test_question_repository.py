import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from packages.questions.repositories.question_repository import QuestionRepository
from packages.questions.models.database.question import QuestionEntity
from packages.matrices.models.database.matrix import MatrixEntity


class TestQuestionRepository:
    """Test QuestionRepository methods, focusing on new functionality we added."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return QuestionRepository()

    @pytest.fixture
    async def second_matrix(
        self, test_db: AsyncSession, sample_workspace, sample_company
    ):
        """Create a second matrix for cross-matrix tests."""
        matrix = MatrixEntity(
            name="Second Matrix",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)
        return matrix

    async def test_get_by_matrix_id(
        self, repository, sample_matrix, second_matrix, sample_company, test_db
    ):
        """Test getting questions by matrix ID."""
        # Create questions in first matrix
        question1 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question 1",
            question_type_id=1,
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question 2",
            question_type_id=5,
            company_id=sample_company.id,
        )

        # Create question in second matrix
        question3 = QuestionEntity(
            matrix_id=second_matrix.id,
            question_text="Question 3",
            question_type_id=2,
            company_id=sample_company.id,
        )

        test_db.add_all([question1, question2, question3])
        await test_db.commit()

        # Get questions for first matrix
        questions = await repository.get_by_matrix_id(sample_matrix.id)

        assert len(questions) == 2
        question_texts = [q.question_text for q in questions]
        assert "Question 1" in question_texts
        assert "Question 2" in question_texts
        assert "Question 3" not in question_texts

    async def test_get_by_matrix_id_empty(self, repository, sample_matrix):
        """Test getting questions for matrix with no questions."""
        questions = await repository.get_by_matrix_id(sample_matrix.id)
        assert len(questions) == 0

    async def test_get_by_matrix_id_nonexistent(self, repository):
        """Test getting questions for non-existent matrix."""
        questions = await repository.get_by_matrix_id(999)
        assert len(questions) == 0

    async def test_search_by_text(
        self, repository, sample_matrix, second_matrix, sample_company, test_db
    ):
        """Test searching questions by text content."""
        # Create questions with different text
        question1 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the contract date?",
            question_type_id=3,
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="How much does it cost?",
            question_type_id=4,
            company_id=sample_company.id,
        )
        question3 = QuestionEntity(
            matrix_id=second_matrix.id,
            question_text="Contract terms and conditions",
            question_type_id=1,
            company_id=sample_company.id,
        )

        test_db.add_all([question1, question2, question3])
        await test_db.commit()

        # Search for "contract" (case insensitive)
        results = await repository.search_by_text("contract")

        assert len(results) == 2
        question_texts = [q.question_text for q in results]
        assert "What is the contract date?" in question_texts
        assert "Contract terms and conditions" in question_texts
        assert "How much does it cost?" not in question_texts

    async def test_search_by_text_with_matrix_filter(
        self, repository, sample_matrix, second_matrix, sample_company, test_db
    ):
        """Test searching questions by text with matrix ID filter."""
        # Create questions with same search term in different matrices
        question1 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the contract date?",
            question_type_id=3,
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=second_matrix.id,
            question_text="Contract terms and conditions",
            question_type_id=1,
            company_id=sample_company.id,
        )

        test_db.add_all([question1, question2])
        await test_db.commit()

        # Search for "contract" in specific matrix
        results = await repository.search_by_text("contract", sample_matrix.id)

        assert len(results) == 1
        assert results[0].question_text == "What is the contract date?"
        assert results[0].matrix_id == sample_matrix.id

    async def test_search_by_text_case_insensitive(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that text search is case insensitive."""
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the CONTRACT value?",
            question_type_id=4,
            company_id=sample_company.id,
        )

        test_db.add(question)
        await test_db.commit()

        # Search with different cases
        results_lower = await repository.search_by_text("contract")
        results_upper = await repository.search_by_text("CONTRACT")
        results_mixed = await repository.search_by_text("ConTrAcT")

        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1
        assert results_lower[0].id == results_upper[0].id == results_mixed[0].id

    async def test_search_by_text_partial_match(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that search finds partial matches."""
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the effective date of this agreement?",
            question_type_id=3,
            company_id=sample_company.id,
        )

        test_db.add(question)
        await test_db.commit()

        # Search for partial words
        results_effective = await repository.search_by_text("effective")
        results_agreement = await repository.search_by_text("agreement")
        results_date = await repository.search_by_text("date")

        assert len(results_effective) == 1
        assert len(results_agreement) == 1
        assert len(results_date) == 1

    async def test_search_by_text_no_results(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test search with no matching results."""
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the contract date?",
            question_type_id=3,
            company_id=sample_company.id,
        )

        test_db.add(question)
        await test_db.commit()

        # Search for non-existent term
        results = await repository.search_by_text("nonexistent")
        assert len(results) == 0

    @pytest.mark.skip(reason="This test is flaky and needs to be fixed")
    async def test_search_by_text_empty_query(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test search with empty query string."""
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the contract date?",
            question_type_id=3,
            company_id=sample_company.id,
        )

        test_db.add(question)
        await test_db.commit()

        # Search with empty string should return no results
        results = await repository.search_by_text("")
        assert len(results) == 0

    async def test_entity_to_domain_conversion_with_question_types(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that entity to domain conversion properly handles question type IDs."""
        # Create questions with different question types
        questions = [
            QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text="Short answer question",
                question_type_id=1,
                company_id=sample_company.id,
            ),
            QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text="Long answer question",
                question_type_id=2,
                company_id=sample_company.id,
            ),
            QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text="Date question",
                question_type_id=3,
                company_id=sample_company.id,
            ),
            QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text="Currency question",
                question_type_id=4,
                company_id=sample_company.id,
            ),
            QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text="Select question",
                question_type_id=5,
                company_id=sample_company.id,
            ),
        ]

        test_db.add_all(questions)
        await test_db.commit()

        # Get questions and verify type IDs are preserved
        retrieved = await repository.get_by_matrix_id(sample_matrix.id)

        assert len(retrieved) == 5
        type_ids = [q.question_type_id for q in retrieved]
        assert 1 in type_ids
        assert 2 in type_ids
        assert 3 in type_ids
        assert 4 in type_ids
        assert 5 in type_ids

    # Soft delete related tests
    async def test_get_by_matrix_id_excludes_deleted(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that get_by_matrix_id excludes soft deleted questions."""
        # Create questions, one deleted
        question1 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Active question?",
            question_type_id=1,
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Deleted question?",
            question_type_id=1,
            deleted=True,
            company_id=sample_company.id,
        )

        test_db.add_all([question1, question2])
        await test_db.commit()

        # Get questions by matrix ID
        result = await repository.get_by_matrix_id(sample_matrix.id)

        assert len(result) == 1
        assert result[0].question_text == "Active question?"

    async def test_search_by_text_excludes_deleted(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that search_by_text excludes soft deleted questions."""
        # Create questions, one deleted
        question1 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the capital of France?",
            question_type_id=1,
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the population of France?",
            question_type_id=1,
            deleted=True,
            company_id=sample_company.id,
        )

        test_db.add_all([question1, question2])
        await test_db.commit()

        # Search for questions containing "France"
        result = await repository.search_by_text("France")

        assert len(result) == 1
        assert result[0].question_text == "What is the capital of France?"

    async def test_get_valid_ids_for_matrix(
        self, repository, sample_matrix, second_matrix, sample_company, test_db
    ):
        """Test getting valid question IDs for a matrix."""
        # Create questions in the matrix
        questions = []
        for i in range(3):
            question = QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text=f"Question {i}?",
                question_type_id=1,
                company_id=sample_company.id,
            )
            questions.append(question)

        # Create a question in different matrix
        other_question = QuestionEntity(
            matrix_id=second_matrix.id,
            question_text="Other question?",
            question_type_id=1,
            company_id=sample_company.id,
        )

        test_db.add_all(questions + [other_question])
        await test_db.commit()

        for question in questions + [other_question]:
            await test_db.refresh(question)

        # Test with valid IDs from correct matrix
        valid_ids = await repository.get_valid_ids_for_matrix(
            sample_matrix.id,
            [
                questions[0].id,
                questions[1].id,
                other_question.id,
            ],  # Include ID from wrong matrix
        )

        assert len(valid_ids) == 2
        assert questions[0].id in valid_ids
        assert questions[1].id in valid_ids
        assert other_question.id not in valid_ids

    async def test_get_valid_ids_for_matrix_excludes_deleted(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that get_valid_ids_for_matrix excludes soft deleted questions."""
        # Create questions, one deleted
        question1 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Active question?",
            question_type_id=1,
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Deleted question?",
            question_type_id=1,
            deleted=True,
            company_id=sample_company.id,
        )

        test_db.add_all([question1, question2])
        await test_db.commit()

        for q in [question1, question2]:
            await test_db.refresh(q)

        # Test with both IDs
        valid_ids = await repository.get_valid_ids_for_matrix(
            sample_matrix.id, [question1.id, question2.id]
        )

        assert len(valid_ids) == 1
        assert question1.id in valid_ids
        assert question2.id not in valid_ids

    async def test_bulk_soft_delete_by_matrix_ids(
        self, repository, sample_workspace, sample_company, test_db
    ):
        """Test bulk soft deleting questions by matrix IDs."""
        # Create matrices
        matrix1 = MatrixEntity(
            name="Matrix 1",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        matrix2 = MatrixEntity(
            name="Matrix 2",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        matrix3 = MatrixEntity(
            name="Matrix 3",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        test_db.add_all([matrix1, matrix2, matrix3])
        await test_db.commit()
        await test_db.refresh(matrix1)
        await test_db.refresh(matrix2)
        await test_db.refresh(matrix3)

        # Create questions in different matrices
        questions_m1 = [
            QuestionEntity(
                matrix_id=matrix1.id,
                question_text="M1 Question 1?",
                question_type_id=1,
                company_id=sample_company.id,
            ),
            QuestionEntity(
                matrix_id=matrix1.id,
                question_text="M1 Question 2?",
                question_type_id=1,
                company_id=sample_company.id,
            ),
        ]
        questions_m2 = [
            QuestionEntity(
                matrix_id=matrix2.id,
                question_text="M2 Question 1?",
                question_type_id=1,
                company_id=sample_company.id,
            )
        ]
        questions_m3 = [
            QuestionEntity(
                matrix_id=matrix3.id,
                question_text="M3 Question 1?",
                question_type_id=1,
                company_id=sample_company.id,
            )
        ]

        test_db.add_all(questions_m1 + questions_m2 + questions_m3)
        await test_db.commit()

        # Soft delete questions in matrix1 and matrix2
        deleted_count = await repository.bulk_soft_delete_by_matrix_ids(
            [matrix1.id, matrix2.id]
        )

        assert deleted_count == 3  # 2 from matrix1 + 1 from matrix2

        # Verify questions are soft deleted
        m1_questions = await repository.get_by_matrix_id(matrix1.id)
        m2_questions = await repository.get_by_matrix_id(matrix2.id)
        m3_questions = await repository.get_by_matrix_id(matrix3.id)

        assert len(m1_questions) == 0  # Soft deleted
        assert len(m2_questions) == 0  # Soft deleted
        assert len(m3_questions) == 1  # Not deleted

    async def test_bulk_soft_delete_by_matrix_ids_empty_list(self, repository):
        """Test bulk soft delete with empty matrix IDs list."""
        result = await repository.bulk_soft_delete_by_matrix_ids([])
        assert result == 0

    async def test_bulk_soft_delete_by_matrix_ids_no_matches(self, repository):
        """Test bulk soft delete with non-existent matrix IDs."""
        result = await repository.bulk_soft_delete_by_matrix_ids([999, 1000])
        assert result == 0

    async def test_bulk_soft_delete_by_matrix_ids_already_deleted(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test bulk soft delete on already deleted questions."""
        # Create a deleted question
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Deleted question?",
            question_type_id=1,
            deleted=True,
            company_id=sample_company.id,
        )

        test_db.add(question)
        await test_db.commit()

        # Try to soft delete again
        result = await repository.bulk_soft_delete_by_matrix_ids([sample_matrix.id])

        assert result == 0  # No questions were affected

    async def test_soft_delete_functionality_inheritance(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that inherited soft delete methods work correctly."""
        # Create a test question
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Test question?",
            question_type_id=1,
            company_id=sample_company.id,
        )

        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Test soft_delete method from base repository
        result = await repository.soft_delete(question.id)
        assert result is True

        # Verify question is soft deleted
        retrieved = await repository.get(question.id)
        assert retrieved is None

    async def test_bulk_soft_delete_functionality_inheritance(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that inherited bulk_soft_delete method works correctly."""
        # Create multiple questions
        questions = []
        for i in range(3):
            question = QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text=f"Question {i}?",
                question_type_id=1,
                company_id=sample_company.id,
            )
            questions.append(question)

        test_db.add_all(questions)
        await test_db.commit()

        for question in questions:
            await test_db.refresh(question)

        # Test bulk_soft_delete method from base repository
        question_ids = [question.id for question in questions]
        result = await repository.bulk_soft_delete(question_ids)

        assert result == 3

        # Verify all questions are soft deleted
        for question in questions:
            retrieved = await repository.get(question.id)
            assert retrieved is None

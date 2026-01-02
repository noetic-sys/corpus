"""Unit tests for message builder utilities."""

from packages.qa.utils.message_builders import MessageBuilder, DocumentContext
from questions.question_type import QuestionTypeName
from common.providers.ai.models import InputMessage, MessageRole


class TestMessageBuilder:
    """Test MessageBuilder class."""

    def _get_combined_content(self, messages):
        """Helper to combine all message content for easier testing."""
        return "\n".join(msg.content for msg in messages)

    def test_build_user_message_no_type(self):
        """Test building user message with no question type."""
        documents = [
            DocumentContext(document_id=123, content="This is test document content.")
        ]
        question = "What is this about?"

        result = MessageBuilder.build_user_message(documents, question)

        # Should return list of InputMessage objects
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(msg, InputMessage) for msg in result)

        # First message should be document content with ID
        assert result[0].role == MessageRole.USER
        assert "Document 123:" in result[0].content
        assert "This is test document content." in result[0].content

        # Second message should be question with instructions
        assert result[1].role == MessageRole.USER
        assert "Question: " + question in result[1].content
        assert "brief, concise answer" in result[1].content  # SHORT_ANSWER default
        assert "under 200 characters" in result[1].content

    def test_build_user_message_date_type(self):
        """Test building user message for DATE type."""
        documents = [
            DocumentContext(
                document_id=456, content="The contract was signed on December 25, 2023."
            )
        ]
        question = "When was the contract signed?"

        result = MessageBuilder.build_user_message(
            documents, question, QuestionTypeName.DATE
        )

        # Should return list of InputMessage objects
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(msg, InputMessage) for msg in result)

        # First message should be document content with ID
        assert result[0].role == MessageRole.USER
        assert "Document 456:" in result[0].content
        assert "The contract was signed on December 25, 2023." in result[0].content

        # Second message should be question with DATE instructions
        assert result[1].role == MessageRole.USER
        assert "Question: " + question in result[1].content
        assert "YYYY-MM-DD" in result[1].content
        assert "No date found" in result[1].content

    def test_build_user_message_currency_type(self):
        """Test building user message for CURRENCY type."""
        documents = [
            DocumentContext(document_id=789, content="The total cost is $1,500.00.")
        ]
        question = "How much does it cost?"

        result = MessageBuilder.build_user_message(
            documents, question, QuestionTypeName.CURRENCY
        )

        # Should return list of InputMessage objects
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(msg, InputMessage) for msg in result)

        # First message should be document content with ID
        assert result[0].role == MessageRole.USER
        assert "Document 789:" in result[0].content
        assert "The total cost is $1,500.00." in result[0].content

        # Second message should be question with CURRENCY instructions
        assert result[1].role == MessageRole.USER
        assert "Question: " + question in result[1].content
        assert "monetary amount" in result[1].content
        assert "No amount found" in result[1].content

    def test_build_user_message_short_answer_type(self):
        """Test building user message for SHORT_ANSWER type."""
        documents = [
            DocumentContext(
                document_id=111, content="Python is a programming language."
            )
        ]
        question = "What is Python?"

        result = MessageBuilder.build_user_message(
            documents, question, QuestionTypeName.SHORT_ANSWER
        )

        # Should return list of InputMessage objects
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(msg, InputMessage) for msg in result)

        # First message should be document content with ID
        assert result[0].role == MessageRole.USER
        assert "Document 111:" in result[0].content
        assert "Python is a programming language." in result[0].content

        # Second message should be question with SHORT_ANSWER instructions
        assert result[1].role == MessageRole.USER
        assert "Question: " + question in result[1].content
        assert "brief, concise answer" in result[1].content
        assert "under 200 characters" in result[1].content

    def test_build_user_message_long_answer_type(self):
        """Test building user message for LONG_ANSWER type."""
        documents = [
            DocumentContext(
                document_id=222, content="Python is a high-level programming language."
            )
        ]
        question = "Explain Python in detail."

        result = MessageBuilder.build_user_message(
            documents, question, QuestionTypeName.LONG_ANSWER
        )

        # Should return list of InputMessage objects
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(msg, InputMessage) for msg in result)

        # First message should be document content with ID
        assert result[0].role == MessageRole.USER
        assert "Document 222:" in result[0].content
        assert "Python is a high-level programming language." in result[0].content

        # Second message should be question with LONG_ANSWER instructions
        assert result[1].role == MessageRole.USER
        assert "Question: " + question in result[1].content
        assert "detailed, comprehensive answer" in result[1].content

    def test_build_select_instructions_with_options(self):
        """Test building select instructions with options."""
        options = ["Option A", "Option B", "Option C"]

        result = MessageBuilder._build_select_instructions(options)

        expected_parts = [
            "select from those that are relevant",
            '"Option A"',
            '"Option B"',
            '"Option C"',
            "Use the exact option text provided",
        ]

        for part in expected_parts:
            assert part in result

    def test_build_select_instructions_no_options(self):
        """Test building select instructions without options."""
        result = MessageBuilder._build_select_instructions([])
        assert "No options configured for this question" in result

    def test_build_select_instructions_single_option(self):
        """Test building select instructions with single option."""
        options = ["Only Option"]

        result = MessageBuilder._build_select_instructions(options)

        expected_parts = [
            "select from those that are relevant",
            '"Only Option"',
            "Use the exact option text provided",
        ]

        for part in expected_parts:
            assert part in result

    def test_build_select_instructions_special_characters(self):
        """Test building select instructions with special characters in options."""
        options = ["Yes, definitely!", "No & Never", "Maybe (50/50)"]

        result = MessageBuilder._build_select_instructions(options)

        expected_parts = ['"Yes, definitely!"', '"No & Never"', '"Maybe (50/50)"']

        for part in expected_parts:
            assert part in result

    def test_build_select_instructions_with_programming_options(self):
        """Test building select instructions with programming language options."""
        options = ["Python", "JavaScript", "Go"]

        result = MessageBuilder._build_select_instructions(options)

        expected_parts = [
            "select from those that are relevant",
            '"Python"',
            '"JavaScript"',
            '"Go"',
            "Be inclusive",
            "Use the exact option text provided",
        ]

        for part in expected_parts:
            assert part in result

    def test_build_select_instructions_unified_behavior(self):
        """Test unified select instructions behavior."""
        options = ["Option A", "Option B"]

        result = MessageBuilder._build_select_instructions(options)

        # Unified select should support both single and multiple selection
        assert "select from those that are relevant" in result
        assert "Be inclusive" in result
        assert "Use the exact option text provided" in result

    def test_message_structure_consistency(self):
        """Test that all message types follow consistent structure."""
        documents = [DocumentContext(document_id=999, content="Test document content")]
        question = "Test question"

        for question_type in QuestionTypeName:
            if question_type == QuestionTypeName.SELECT:
                # Test with options for select types
                result = MessageBuilder.build_user_message(
                    documents, question, question_type, ["Option1", "Option2"]
                )
            else:
                result = MessageBuilder.build_user_message(
                    documents, question, question_type
                )

            # All messages should have consistent structure
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(msg, InputMessage) for msg in result)

            # First message: document content with ID
            assert result[0].role == MessageRole.USER
            assert "Document 999:" in result[0].content
            assert "Test document content" in result[0].content

            # Second message: question
            assert result[1].role == MessageRole.USER
            assert "Question: " + question in result[1].content

    def test_empty_inputs_handling(self):
        """Test handling of empty inputs."""
        # Empty document
        documents = [DocumentContext(document_id=1, content="")]
        result = MessageBuilder.build_user_message(documents, "What is this?")
        assert isinstance(result, list)
        assert len(result) == 2
        assert "Document 1:" in result[0].content
        assert "Question: What is this?" in result[1].content

        # Empty question
        documents = [DocumentContext(document_id=2, content="Test doc")]
        result = MessageBuilder.build_user_message(documents, "")
        assert isinstance(result, list)
        assert len(result) == 2
        assert "Document 2:" in result[0].content
        assert "Question: " in result[1].content

    def test_multiline_document_handling(self):
        """Test handling of multiline document content."""
        multiline_doc = """Line 1 of document
Line 2 of document
Line 3 of document"""
        documents = [DocumentContext(document_id=555, content=multiline_doc)]
        question = "What does this document contain?"

        result = MessageBuilder.build_user_message(documents, question)

        assert isinstance(result, list)
        assert len(result) == 2
        assert "Document 555:" in result[0].content
        assert "Line 1 of document" in result[0].content
        assert "Line 2 of document" in result[0].content
        assert "Line 3 of document" in result[0].content
        assert "Question: " + question in result[1].content

    def test_build_user_message_select_with_options(self):
        """Test building user message for SELECT with options."""
        documents = [
            DocumentContext(
                document_id=333,
                content="The document discusses Python and JavaScript programming.",
            )
        ]
        question = "What programming languages are mentioned?"
        options = ["Python", "JavaScript", "Go", "Rust"]

        result = MessageBuilder.build_user_message(
            documents, question, QuestionTypeName.SELECT, options
        )

        # Should return list of InputMessage objects
        assert isinstance(result, list)
        assert len(result) == 2

        # Check combined content for easier assertion
        combined_content = self._get_combined_content(result)

        expected_parts = [
            "Document 333:",
            "The document discusses Python and JavaScript programming.",
            "Question: " + question,
            "select from those that are relevant",
            '"Python"',
            '"JavaScript"',
            '"Go"',
            '"Rust"',
            "Be inclusive",
            "Use the exact option text provided",
            "Provide exactly 1 answer",  # Default constraint from min=1, max=1
        ]

        for part in expected_parts:
            assert part in combined_content

    def test_build_user_message_select_no_options(self):
        """Test building user message for SELECT without options."""
        documents = [
            DocumentContext(
                document_id=444, content="The document discusses programming."
            )
        ]
        question = "What languages are mentioned?"

        result = MessageBuilder.build_user_message(
            documents, question, QuestionTypeName.SELECT
        )

        # Should return list of InputMessage objects
        assert isinstance(result, list)
        assert len(result) == 2

        # Check combined content for easier assertion
        combined_content = self._get_combined_content(result)

        expected_parts = [
            "Document 444:",
            "The document discusses programming.",
            "Question: " + question,
            "No options configured for this question",
        ]

        for part in expected_parts:
            assert part in combined_content

    def test_build_user_message_select_empty_options(self):
        """Test building user message for SELECT with empty options list."""
        documents = [
            DocumentContext(
                document_id=666, content="The document discusses programming."
            )
        ]
        question = "What languages are mentioned?"
        options = []

        result = MessageBuilder.build_user_message(
            documents, question, QuestionTypeName.SELECT, options
        )

        # Should return list of InputMessage objects
        assert isinstance(result, list)
        assert len(result) == 2

        # Check combined content for easier assertion
        combined_content = self._get_combined_content(result)

        expected_parts = [
            "Document 666:",
            "The document discusses programming.",
            "Question: " + question,
            "No options configured for this question",
        ]

        for part in expected_parts:
            assert part in combined_content

    def test_build_user_message_multiple_documents(self):
        """Test building user message with multiple documents (correlation)."""
        documents = [
            DocumentContext(document_id=100, content="Document A discusses Python."),
            DocumentContext(
                document_id=200, content="Document B discusses JavaScript."
            ),
        ]
        question = "Compare the programming languages."

        result = MessageBuilder.build_user_message(documents, question)

        # Should return list of InputMessage objects (2 docs + 1 question)
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(msg, InputMessage) for msg in result)

        # First message: first document
        assert result[0].role == MessageRole.USER
        assert "Document 100:" in result[0].content
        assert "Document A discusses Python." in result[0].content

        # Second message: second document
        assert result[1].role == MessageRole.USER
        assert "Document 200:" in result[1].content
        assert "Document B discusses JavaScript." in result[1].content

        # Third message: question
        assert result[2].role == MessageRole.USER
        assert "Question: " + question in result[2].content

    def test_answer_count_constraints_exact_single(self):
        """Test answer count constraint for exactly 1 answer."""
        result = MessageBuilder._build_answer_count_constraint_text(1, 1)
        assert result == "\n\nProvide exactly 1 answer."

    def test_answer_count_constraints_exact_multiple(self):
        """Test answer count constraint for exactly N answers."""
        result = MessageBuilder._build_answer_count_constraint_text(3, 3)
        assert result == "\n\nProvide exactly 3 answers."

    def test_answer_count_constraints_range(self):
        """Test answer count constraint for range of answers."""
        result = MessageBuilder._build_answer_count_constraint_text(2, 5)
        assert result == "\n\nProvide between 2 and 5 answers."

    def test_answer_count_constraints_unlimited_min_one(self):
        """Test answer count constraint for unlimited with min=1."""
        result = MessageBuilder._build_answer_count_constraint_text(1, None)
        assert result == "\n\nProvide at least 1 answer (or more if found)."

    def test_answer_count_constraints_unlimited_min_multiple(self):
        """Test answer count constraint for unlimited with min>1."""
        result = MessageBuilder._build_answer_count_constraint_text(3, None)
        assert result == "\n\nProvide at least 3 answers (or more if found)."

    def test_answer_count_constraints_up_to_max(self):
        """Test answer count constraint for up to max answers."""
        result = MessageBuilder._build_answer_count_constraint_text(1, 2)
        assert result == "\n\nProvide between 1 and 2 answers."

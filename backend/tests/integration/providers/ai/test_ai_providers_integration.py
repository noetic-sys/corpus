import pytest
import json

from common.providers.ai.openai_provider import OpenAIProvider
from common.providers.ai.anthropic_provider import AnthropicProvider
from common.core.config import settings


class TestAIProvidersIntegration:
    """Integration tests for AI providers that call real APIs."""

    @pytest.fixture(
        params=[
            ("openai", OpenAIProvider),
            ("anthropic", AnthropicProvider),
        ],
        ids=["openai", "anthropic"],
    )
    def ai_provider(self, request):
        """Create AI provider with API key from settings."""
        provider_name, provider_class = request.param

        try:
            if provider_name == "openai":
                api_key = (
                    settings.openai_api_keys[0] if settings.openai_api_keys else None
                )
                if not api_key:
                    pytest.skip("OpenAI API key not configured in settings")
                return provider_class(api_key=api_key)
            elif provider_name == "anthropic":
                api_key = getattr(settings, "anthropic_api_key", None)
                if not api_key:
                    pytest.skip("Anthropic API key not configured in settings")
                return provider_class(api_key=api_key)
        except Exception:
            pytest.skip(f"{provider_name} API key not configured in settings")

    @pytest.fixture
    def sample_document_content(self):
        """Sample document content for testing."""
        return """
        Python Programming Language
        
        Python is a high-level, interpreted programming language with dynamic semantics. 
        Its high-level built in data structures, combined with dynamic typing and dynamic binding, 
        make it very attractive for Rapid Application Development, as well as for use as a 
        scripting or glue language to connect existing components together.
        
        Python's simple, easy to learn syntax emphasizes readability and therefore reduces 
        the cost of program maintenance. Python supports modules and packages, which encourages 
        program modularity and code reuse.
        
        Key Features:
        - Easy to learn and use
        - Interpreted language
        - Cross-platform compatibility
        - Extensive standard library
        - Large community support
        """

    @pytest.mark.asyncio
    async def test_send_message_integration(self, ai_provider, sample_document_content):
        """Test sending messages using real AI API."""
        system_prompt = "You are a helpful assistant that answers questions based on provided document content. Answer the question using only the information from the document. If the answer cannot be found in the document, say 'The answer is not available in the provided document.' Be concise and accurate."
        question = "What are the key features of Python mentioned in the document?"
        user_message = f"""Document Content:
{sample_document_content}

Question: {question}

Please answer the question based on the document content above."""

        answer = await ai_provider.send_message(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,
            max_tokens=1000,
        )

        assert isinstance(answer, str)
        assert len(answer) > 0
        assert "easy to learn" in answer.lower() or "interpreted" in answer.lower()
        print(f"Provider: {ai_provider.__class__.__name__}")
        print(f"Question: {question}")
        print(f"Answer: {answer}")

    @pytest.mark.asyncio
    async def test_send_message_not_in_document(
        self, ai_provider, sample_document_content
    ):
        """Test answering questions about information not in the document."""
        system_prompt = "You are a helpful assistant that answers questions based on provided document content. Answer the question using only the information from the document. If the answer cannot be found in the document, say 'The answer is not available in the provided document.' Be concise and accurate."
        question = "What is the current stock price of Apple?"
        user_message = f"""Document Content:
{sample_document_content}

Question: {question}

Please answer the question based on the document content above."""

        answer = await ai_provider.send_message(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,
            max_tokens=1000,
        )

        assert isinstance(answer, str)
        assert len(answer) > 0
        assert "not available" in answer.lower() or "not found" in answer.lower()
        print(f"Provider: {ai_provider.__class__.__name__}")
        print(f"Question: {question}")
        print(f"Answer: {answer}")

    @pytest.mark.asyncio
    async def test_summarize_document_integration(
        self, ai_provider, sample_document_content
    ):
        """Test document summarization using real AI API."""
        system_prompt = "You are a helpful assistant that creates concise summaries of documents. Provide a clear, structured summary that captures the main points and key information."
        user_message = f"""Please provide a concise summary of the following document. do not extrapolate or add information:

{sample_document_content}"""

        summary = await ai_provider.send_message(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.3,
            max_tokens=500,
        )

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) < len(sample_document_content)  # Summary should be shorter
        assert "python" in summary.lower()
        print(f"Provider: {ai_provider.__class__.__name__}")
        print(f"Summary: {summary}")

    @pytest.mark.asyncio
    async def test_extract_key_information_integration(
        self, ai_provider, sample_document_content
    ):
        """Test key information extraction using real AI API."""
        system_prompt = "You are a helpful assistant that extracts key information from documents. Return the information as a structured JSON object with relevant fields."
        info_type = "programming language features"
        user_message = f"""Extract key information from this document (focus on {info_type} information):

{sample_document_content}

Please return a JSON object with the extracted information."""

        response = await ai_provider.send_message(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,
            max_tokens=800,
        )

        # Try to parse as JSON, fallback to text if it fails
        try:
            key_info = json.loads(response)
        except json.JSONDecodeError:
            key_info = {"extracted_text": response}

        assert isinstance(key_info, dict)
        assert len(key_info) > 0
        print(f"Provider: {ai_provider.__class__.__name__}")
        print(f"Extracted key information: {key_info}")

    @pytest.mark.asyncio
    async def test_invalid_api_key_handling(self, request):
        """Test handling of invalid API key for each provider."""
        # Get the current provider type from the parameterized test
        if hasattr(request, "node") and hasattr(request.node, "callspec"):
            provider_name, provider_class = request.node.callspec.params.get(
                "ai_provider", ("openai", OpenAIProvider)
            )
        else:
            # Fallback - test both
            for provider_name, provider_class in [
                ("openai", OpenAIProvider),
                ("anthropic", AnthropicProvider),
            ]:
                invalid_provider = provider_class(api_key="invalid-key-123")

                with pytest.raises(Exception) as exc_info:
                    await invalid_provider.send_message(
                        system_prompt="You are a helpful assistant.",
                        user_message="Test message",
                        temperature=0.7,
                    )

                assert "Failed to get response from" in str(exc_info.value)
            return

        invalid_provider = provider_class(api_key="invalid-key-123")

        with pytest.raises(Exception) as exc_info:
            await invalid_provider.send_message(
                system_prompt="You are a helpful assistant.",
                user_message="Test message",
                temperature=0.7,
            )

        assert "Failed to get response from" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_document_handling(self, ai_provider):
        """Test handling of empty document content."""
        system_prompt = "You are a helpful assistant that answers questions based on provided document content. Answer the question using only the information from the document. If the answer cannot be found in the document, say 'The answer is not available in the provided document.' Be concise and accurate."
        user_message = """Document Content:


Question: What is this document about?

Please answer the question based on the document content above."""

        answer = await ai_provider.send_message(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,
            max_tokens=1000,
        )

        assert isinstance(answer, str)
        assert len(answer) > 0
        assert "not available" in answer.lower() or "empty" in answer.lower()
        print(f"Provider: {ai_provider.__class__.__name__}")
        print(f"Empty document answer: {answer}")

    @pytest.mark.asyncio
    async def test_temperature_parameter(self, ai_provider, sample_document_content):
        """Test that temperature parameter affects response variability."""
        system_prompt = "You are a creative assistant."
        user_message = "Write a very short creative story about programming."

        # Test with low temperature (more deterministic)
        response_low = await ai_provider.send_message(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,
            max_tokens=100,
        )

        # Test with high temperature (more creative)
        response_high = await ai_provider.send_message(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.9,
            max_tokens=100,
        )

        assert isinstance(response_low, str)
        assert isinstance(response_high, str)
        assert len(response_low) > 0
        assert len(response_high) > 0

        print(f"Provider: {ai_provider.__class__.__name__}")
        print(f"Low temp response: {response_low}")
        print(f"High temp response: {response_high}")

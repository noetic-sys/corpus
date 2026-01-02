import pytest
from unittest.mock import AsyncMock, patch

from packages.agents.tools.base import ToolPermission, ToolContext
from packages.agents.tools.tools.search import (
    SearchTool,
    SearchParameters,
    SearchSuccessResult,
    SearchErrorResult,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from common.providers.web_search import SearchResponse, SearchResult


class TestSearchTool:
    """Test SearchTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return SearchTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = SearchTool.definition()

        assert definition.name == "search"
        assert "Search the web using intelligent search" in definition.description
        assert "properties" in definition.parameters
        assert "query" in definition.parameters["properties"]
        assert "num_results" in definition.parameters["properties"]
        assert "search_type" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""
        permissions = SearchTool.permissions()
        assert permissions == ToolPermission.READ

    def test_allowed_contexts(self):
        """Test tool is allowed in correct contexts."""
        contexts = SearchTool.allowed_contexts()
        assert ToolContext.GENERAL_AGENT in contexts
        assert ToolContext.WORKFLOW_AGENT in contexts

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = SearchTool.parameter_class()
        assert param_class == SearchParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters with only required fields
        params = SearchParameters(query="machine learning")
        assert params.query == "machine learning"
        assert params.num_results == 10  # default
        assert params.search_type == "auto"  # default

        # Valid parameters with all fields
        params = SearchParameters(
            query="AI research",
            num_results=20,
            search_type="neural",
            category="research paper",
            include_domains=["arxiv.org", "scholar.google.com"],
            exclude_domains=["example.com"],
            start_published_date="2024-01-01",
            end_published_date="2024-12-31",
        )
        assert params.query == "AI research"
        assert params.num_results == 20
        assert params.search_type == "neural"
        assert params.category == "research paper"
        assert params.include_domains == ["arxiv.org", "scholar.google.com"]
        assert params.exclude_domains == ["example.com"]
        assert params.start_published_date == "2024-01-01"
        assert params.end_published_date == "2024-12-31"

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            SearchParameters()  # Missing required query

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = SearchTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check query parameter
        query_param = definition.parameters["properties"]["query"]
        assert "type" in query_param
        assert "description" in query_param
        assert "search query" in query_param["description"].lower()

        # Check num_results parameter
        num_results_param = definition.parameters["properties"]["num_results"]
        assert "type" in num_results_param
        assert "description" in num_results_param
        assert "default" in num_results_param

        # Check optional parameters exist
        assert "search_type" in definition.parameters["properties"]
        assert "category" in definition.parameters["properties"]
        assert "include_domains" in definition.parameters["properties"]
        assert "exclude_domains" in definition.parameters["properties"]
        assert "start_published_date" in definition.parameters["properties"]
        assert "end_published_date" in definition.parameters["properties"]

    async def test_execute_success(self, tool, mock_user, test_db):
        """Test successful tool execution."""
        # Create mock search response
        mock_results = [
            SearchResult(
                title="Machine Learning Basics",
                url="https://example.com/ml-basics",
                published_date="2024-01-15",
                author="John Doe",
                score=0.95,
            ),
            SearchResult(
                title="Advanced AI Techniques",
                url="https://example.com/advanced-ai",
                published_date="2024-02-20",
                score=0.88,
            ),
        ]
        mock_response = SearchResponse(
            results=mock_results,
            request_id="test-request-123",
            search_type="neural",
        )

        # Mock the web search provider
        with patch(
            "packages.agents.tools.tools.search.get_web_search_provider"
        ) as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.search = AsyncMock(return_value=mock_response)
            mock_get_provider.return_value = mock_provider

            params = SearchParameters(
                query="machine learning", num_results=2, search_type="neural"
            )
            result = await tool.execute(params, test_db, mock_user)

            # Verify provider was called correctly
            mock_provider.search.assert_called_once_with(
                query="machine learning",
                num_results=2,
                search_type="neural",
                category=None,
                include_domains=None,
                exclude_domains=None,
                start_published_date=None,
                end_published_date=None,
            )

            # Verify result
            assert result.error is None
            assert result.result is not None
            assert isinstance(result.result, SearchSuccessResult)
            assert result.result.search_response == mock_response
            assert len(result.result.search_response.results) == 2
            assert (
                result.result.search_response.results[0].title
                == "Machine Learning Basics"
            )
            assert result.result.search_response.request_id == "test-request-123"

    async def test_execute_with_filters(self, tool, mock_user, test_db):
        """Test tool execution with domain and date filters."""
        mock_response = SearchResponse(
            results=[
                SearchResult(
                    title="Research Paper",
                    url="https://arxiv.org/paper1",
                    published_date="2024-06-01",
                    score=0.92,
                )
            ],
            request_id="test-request-456",
            search_type="keyword",
        )

        with patch(
            "packages.agents.tools.tools.search.get_web_search_provider"
        ) as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.search = AsyncMock(return_value=mock_response)
            mock_get_provider.return_value = mock_provider

            params = SearchParameters(
                query="quantum computing",
                num_results=5,
                category="research paper",
                include_domains=["arxiv.org", "scholar.google.com"],
                exclude_domains=["wikipedia.org"],
                start_published_date="2024-01-01",
                end_published_date="2024-12-31",
            )
            result = await tool.execute(params, test_db, mock_user)

            # Verify provider was called with all filters
            mock_provider.search.assert_called_once_with(
                query="quantum computing",
                num_results=5,
                search_type="auto",
                category="research paper",
                include_domains=["arxiv.org", "scholar.google.com"],
                exclude_domains=["wikipedia.org"],
                start_published_date="2024-01-01",
                end_published_date="2024-12-31",
            )

            assert result.error is None
            assert result.result is not None

    async def test_execute_error(self, tool, mock_user, test_db):
        """Test tool execution when provider raises an error."""
        with patch(
            "packages.agents.tools.tools.search.get_web_search_provider"
        ) as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.search = AsyncMock(
                side_effect=Exception("API rate limit exceeded")
            )
            mock_get_provider.return_value = mock_provider

            params = SearchParameters(query="test query")
            result = await tool.execute(params, test_db, mock_user)

            # Verify error is returned
            assert result.error is not None
            assert isinstance(result.error, SearchErrorResult)
            assert "API rate limit exceeded" in result.error.error
            assert result.result is None

    async def test_execute_empty_results(self, tool, mock_user, test_db):
        """Test tool execution with empty search results."""
        mock_response = SearchResponse(
            results=[],
            request_id="test-request-789",
            search_type="auto",
        )

        with patch(
            "packages.agents.tools.tools.search.get_web_search_provider"
        ) as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.search = AsyncMock(return_value=mock_response)
            mock_get_provider.return_value = mock_provider

            params = SearchParameters(query="very obscure query that returns nothing")
            result = await tool.execute(params, test_db, mock_user)

            assert result.error is None
            assert result.result is not None
            assert len(result.result.search_response.results) == 0

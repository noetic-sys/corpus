from typing import Optional, Type, List

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import override

from common.providers.web_search import get_web_search_provider, SearchResponse
from packages.agents.tools.base import (
    ToolDefinition,
    ToolResult,
    ToolPermission,
    ToolContext,
    ToolParameters,
    ToolSuccessResult,
    ToolErrorResult,
    Tool,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


class SearchErrorResult(ToolErrorResult):
    error: str


class SearchSuccessResult(ToolSuccessResult):
    search_response: SearchResponse


class SearchParameters(ToolParameters):
    query: str = Field(description="The search query to find relevant web content")
    num_results: int = Field(
        description="Number of results to return (max 10 for keyword; max 100 for neural)",
        default=10,
    )
    search_type: Optional[str] = Field(
        description="Search method: 'keyword', 'neural', 'fast', or 'auto' (default)",
        default="auto",
    )
    category: Optional[str] = Field(
        description="Focus search on category: news, research paper, company, github, linkedin profile, etc.",
        default=None,
    )
    include_domains: Optional[List[str]] = Field(
        description="List of domains to restrict results to", default=None
    )
    exclude_domains: Optional[List[str]] = Field(
        description="List of domains to exclude from results", default=None
    )
    start_published_date: Optional[str] = Field(
        description="Filter results published after this date (ISO 8601 format)",
        default=None,
    )
    end_published_date: Optional[str] = Field(
        description="Filter results published before this date (ISO 8601 format)",
        default=None,
    )


class SearchTool(Tool[SearchParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="search",
            description="Search the web using intelligent search. Supports both keyword and neural search with filtering by domain, date, and category.",
            parameters=SearchParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[SearchParameters]:
        return SearchParameters

    @override
    async def execute(
        self,
        parameters: SearchParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Get the web search provider
            provider = get_web_search_provider()

            # Perform the search
            search_response = await provider.search(
                query=parameters.query,
                num_results=parameters.num_results,
                search_type=parameters.search_type,
                category=parameters.category,
                include_domains=parameters.include_domains,
                exclude_domains=parameters.exclude_domains,
                start_published_date=parameters.start_published_date,
                end_published_date=parameters.end_published_date,
            )

            return ToolResult.ok(SearchSuccessResult(search_response=search_response))

        except Exception as e:
            return ToolResult.err(SearchErrorResult(error=str(e)))

from typing import Type

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import override

from common.providers.web_search import get_web_search_provider
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


class GetPageContentErrorResult(ToolErrorResult):
    error: str


class GetPageContentSuccessResult(ToolSuccessResult):
    content: str
    url: str


class GetPageContentParameters(ToolParameters):
    url: str = Field(description="The URL to fetch content from")


class GetPageContentTool(Tool[GetPageContentParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_page_content",
            description="Fetch and extract the full text content from a webpage URL",
            parameters=GetPageContentParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[GetPageContentParameters]:
        return GetPageContentParameters

    @override
    async def execute(
        self,
        parameters: GetPageContentParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Get the web search provider
            provider = get_web_search_provider()

            # Fetch the page content
            content = await provider.get_page_content(parameters.url)

            return ToolResult.ok(
                GetPageContentSuccessResult(content=content, url=parameters.url)
            )

        except Exception as e:
            return ToolResult.err(GetPageContentErrorResult(error=str(e)))

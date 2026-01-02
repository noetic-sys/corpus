from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Optional, Any, Self, Generic, TypeVar, Type, List

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


class ToolPermission(StrEnum):
    READ = "read"
    WRITE = "write"


class ToolContext(StrEnum):
    """Context determines where a tool can be used.

    GENERAL_AGENT: General agent conversations with full CRUD on business entities
    WORKFLOW_AGENT: Workflow executions - read data + file operations only
    """

    GENERAL_AGENT = "general_agent"
    WORKFLOW_AGENT = "workflow_agent"


class ToolParameters(BaseModel):
    pass


class ToolSuccessResult(BaseModel):
    pass


class ToolErrorResult(BaseModel):
    pass


class GenericToolErrorResult(ToolErrorResult):
    """Generic error result for tool execution failures."""

    error: str


SuccessVar = TypeVar("SuccessVar", bound=ToolSuccessResult)
ErrorVar = TypeVar("ErrorVar", bound=ToolErrorResult)
ParametersVar = TypeVar("ParametersVar", bound=ToolParameters)


class ToolResult(BaseModel):
    result: Optional[ToolSuccessResult] = None
    error: Optional[ToolErrorResult] = None

    @classmethod
    def ok(cls, success: SuccessVar) -> Self:
        return ToolResult(result=success)

    @classmethod
    def err(cls, error: ErrorVar) -> Self:
        return ToolResult(error=error)


class ToolDefinition(BaseModel):
    name: str
    description: str
    # THE ONLY REASON IS THAT PARAMETERS IS A JSON SCHEMA
    parameters: dict[str, Any]


class Tool(ABC, Generic[ParametersVar]):
    @classmethod
    @abstractmethod
    def permissions(cls) -> ToolPermission:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def allowed_contexts(cls) -> List[ToolContext]:
        """Define which contexts can use this tool.

        Examples:
        - Read tools: [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]
        - Business write tools: [ToolContext.GENERAL_AGENT]
        - File operation tools: [ToolContext.WORKFLOW_AGENT]
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def definition(cls) -> ToolDefinition:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def parameter_class(cls) -> Type[ParametersVar]:
        raise NotImplementedError()

    @abstractmethod
    async def execute(
        self,
        parameters: ParametersVar,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        raise NotImplementedError()

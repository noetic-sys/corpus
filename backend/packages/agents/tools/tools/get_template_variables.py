from typing import List, Type

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import override

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
from packages.matrices.models.schemas.matrix_template_variable import (
    MatrixTemplateVariableResponse,
)
from packages.matrices.routes.matrix_template_variables import (
    get_matrix_template_variables,
)


class GetTemplateVariablesErrorResult(ToolErrorResult):
    error: str


class GetTemplateVariablesSuccessResult(ToolSuccessResult):
    template_variables: List[MatrixTemplateVariableResponse]


class GetTemplateVariablesParameters(ToolParameters):
    matrix_id: int = Field(description="the matrix id to get template variables for")


class GetTemplateVariablesTool(Tool[GetTemplateVariablesParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_template_variables",
            description="Get all template variables for a specific matrix",
            parameters=GetTemplateVariablesParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[GetTemplateVariablesParameters]:
        return GetTemplateVariablesParameters

    @override
    async def execute(
        self,
        parameters: GetTemplateVariablesParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Call the get_matrix_template_variables route function directly
            template_variables = await get_matrix_template_variables(
                matrix_id=parameters.matrix_id,
                current_user=as_user,
                db=session,
            )

            return ToolResult.ok(
                GetTemplateVariablesSuccessResult(template_variables=template_variables)
            )

        except Exception as e:
            return ToolResult.err(GetTemplateVariablesErrorResult(error=str(e)))

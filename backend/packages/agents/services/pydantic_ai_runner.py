"""PydanticAI agent runner service.

Wraps PydanticAI's Agent to provide:
- Dynamic tool registration from our registry
- Streaming support for real-time responses
- Integration with existing conversation/message persistence
"""

import os
from functools import lru_cache
from typing import Optional, Callable, Awaitable, Any

from pydantic_ai import Agent, Tool, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from packages.agents.models.domain.agent_dependencies import AgentDependencies
from packages.agents.adapters.pydantic_ai_tools import execute_tool_for_pydantic_ai
from packages.agents.tools.base import ToolPermission
from packages.agents.tools.registry import registry
from common.core.config import settings
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class PydanticAIRunner:
    """Runs agent conversations using PydanticAI framework."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.default_model
        self._prompts_dir = self._get_prompts_dir()

    def _get_prompts_dir(self) -> str:
        """Get the prompts directory path."""
        project_root = os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
        )
        return os.path.join(project_root, "prompts")

    @lru_cache(maxsize=1)
    def _load_system_prompt(self) -> str:
        """Load the agent system prompt from file."""
        try:
            filepath = os.path.join(self._prompts_dir, "agent_system.txt")
            with open(filepath, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("Agent system prompt file not found, using default")
            return (
                "You are a helpful assistant that can call tools to help users. "
                "When you need to use a tool to answer a question, call the appropriate function."
            )

    def _create_agent(self, permission: ToolPermission) -> Agent[AgentDependencies, str]:
        """Create a PydanticAI agent with tools for the given permission level."""
        # Create OpenAI-compatible model via OpenRouter
        provider = OpenAIProvider(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
        model = OpenAIModel(self.model_name, provider=provider)

        # Build tools from our registry
        tools = self._build_tools(permission)

        # Create agent with system prompt and tools
        agent: Agent[AgentDependencies, str] = Agent(
            model=model,
            system_prompt=self._load_system_prompt(),
            deps_type=AgentDependencies,
            tools=tools,
        )

        return agent

    def _build_tools(self, permission: ToolPermission) -> list[Tool[AgentDependencies]]:
        """Build PydanticAI Tool objects from our registry."""
        tools: list[Tool[AgentDependencies]] = []

        # Get all tool classes for this permission level
        tool_definitions = registry.get_tool_definitions(permission=permission)

        for definition in tool_definitions:
            tool_name = definition.name

            # Create the tool function that delegates to our ToolService
            def make_tool_func(name: str):
                async def tool_func(
                    ctx: RunContext[AgentDependencies], **kwargs: Any
                ) -> str:
                    return await execute_tool_for_pydantic_ai(ctx, name, kwargs)

                tool_func.__name__ = name
                return tool_func

            # Create PydanticAI Tool with custom schema
            tool = Tool.from_schema(
                function=make_tool_func(tool_name),
                name=tool_name,
                description=definition.description,
                json_schema=definition.parameters,
                takes_ctx=True,
            )
            tools.append(tool)

        return tools

    @trace_span
    async def run(
        self,
        user_message: str,
        deps: AgentDependencies,
        message_history: Optional[list[ModelMessage]] = None,
    ) -> tuple[str, list[ModelMessage]]:
        """Run the agent and return final response with updated history.

        Args:
            user_message: The user's message
            deps: Agent dependencies (user context, permissions)
            message_history: Previous conversation messages

        Returns:
            Tuple of (final response text, updated message history)
        """
        agent = self._create_agent(deps.permission_mode)

        result = await agent.run(
            user_message,
            deps=deps,
            message_history=message_history or [],
        )

        return result.data, result.all_messages()

    @trace_span
    async def run_stream(
        self,
        user_message: str,
        deps: AgentDependencies,
        message_history: Optional[list[ModelMessage]] = None,
        on_text_delta: Optional[Callable[[str], Awaitable[None]]] = None,
        on_tool_call: Optional[Callable[[str, dict], Awaitable[None]]] = None,
        on_tool_result: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ) -> tuple[str, list[ModelMessage]]:
        """Run the agent with streaming support.

        Args:
            user_message: The user's message
            deps: Agent dependencies
            message_history: Previous conversation messages
            on_text_delta: Callback for text chunks as they arrive
            on_tool_call: Callback when a tool is called (name, args)
            on_tool_result: Callback when a tool returns (name, result)

        Returns:
            Tuple of (final response text, updated message history)
        """
        agent = self._create_agent(deps.permission_mode)

        async with agent.run_stream(
            user_message,
            deps=deps,
            message_history=message_history or [],
        ) as result:
            # Stream text deltas if callback provided
            if on_text_delta:
                async for text in result.stream_text(delta=True):
                    await on_text_delta(text)

            # Get final result
            final_response = await result.get_data()

        return final_response, result.all_messages()


def get_pydantic_ai_runner(model_name: Optional[str] = None) -> PydanticAIRunner:
    """Factory function for PydanticAIRunner."""
    return PydanticAIRunner(model_name)

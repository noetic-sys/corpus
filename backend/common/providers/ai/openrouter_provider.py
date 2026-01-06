from typing import Optional, List, Dict, Any

from openai import AsyncOpenAI

from .interface import AIProviderInterface
from .models import Message, ChatCompletionMessageToolCall, Function, InputMessage
from common.core.config import settings
from common.core.otel_axiom_exporter import get_logger, trace_span

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(AIProviderInterface):
    """AI provider using OpenRouter's unified API."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the OpenRouter provider.

        Args:
            model_name: Model in OpenRouter format (e.g., 'anthropic/claude-3.5-sonnet').
                       If None, uses default from settings.
        """
        self.model_name = model_name or settings.default_model
        self.client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=settings.openrouter_api_key,
        )

    @trace_span
    async def send_message(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a message using OpenRouter and get a response."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            request_params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                request_params["max_tokens"] = max_tokens

            logger.info(f"Sending request to OpenRouter with model: {self.model_name}")

            response = await self.client.chat.completions.create(**request_params)

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error sending message to OpenRouter: {e}")
            logger.error(f"Request details - Model: {self.model_name}")
            raise Exception(f"Failed to get response from OpenRouter: {str(e)}")

    @trace_span
    async def send_messages(
        self,
        messages: List[InputMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Message:
        """Send a list of messages to OpenRouter with optional tools."""
        try:
            # Convert InputMessage objects to dict format
            message_dicts = [msg.model_dump(exclude_none=True) for msg in messages]

            request_params = {
                "model": self.model_name,
                "messages": message_dicts,
                "temperature": temperature,
            }

            if max_tokens:
                request_params["max_tokens"] = max_tokens

            if tools:
                request_params["tools"] = tools

            logger.info(
                f"Sending messages request to OpenRouter with model: {self.model_name}"
            )

            response = await self.client.chat.completions.create(**request_params)

            message_response = response.choices[0].message

            # Parse tool calls if present
            tool_calls = None
            if hasattr(message_response, "tool_calls") and message_response.tool_calls:
                tool_calls = []
                for tc in message_response.tool_calls:
                    tool_call = ChatCompletionMessageToolCall(
                        id=tc.id,
                        type=tc.type,
                        function=Function(
                            name=tc.function.name, arguments=tc.function.arguments
                        ),
                    )
                    tool_calls.append(tool_call)

            return Message(
                content=message_response.content,
                tool_calls=tool_calls,
                role="assistant",
            )

        except Exception as e:
            logger.error(f"Error sending messages to OpenRouter: {e}")
            logger.error(f"Request details - Model: {self.model_name}")
            raise Exception(f"Failed to get response from OpenRouter: {str(e)}")

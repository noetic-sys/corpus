from typing import Optional, List, Dict, Any
import aisuite as ai
import json
import asyncio
from abc import ABC, abstractmethod

from .interface import AIProviderInterface
from .models import Message, ChatCompletionMessageToolCall, Function, InputMessage
from common.providers.api_keys.interface import APIKeyRotationInterface
from common.meta.singleton import SingletonABCMeta
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class AISuiteProvider(AIProviderInterface, ABC, metaclass=SingletonABCMeta):
    """Base class for AI providers using aisuite unified interface."""

    def __init__(
        self, provider: str, model_name: str, rotator: APIKeyRotationInterface
    ):
        """
        Initialize the AI Suite provider.

        Args:
            provider: Provider name (e.g., 'openai', 'anthropic', 'google', 'xai')
            model_name: Model name (will be prefixed with provider)
            rotator: API key rotation provider
        """
        self.provider = provider
        self.model_name = model_name
        # Format: provider:model-name
        self.full_model_name = f"{provider}:{model_name}"
        self.rotator = rotator

    @abstractmethod
    def get_config_dict(self, rotated_key: str) -> Dict[str, Any]:
        """Get provider-specific configuration dictionary with rotated key."""
        pass

    async def send_message(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a message using aisuite and get a response."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            request_params = {
                "model": self.full_model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                request_params["max_tokens"] = max_tokens

            # Get rotated key and provider-specific configuration
            rotated_key = self.rotator.get_next_key()
            provider_configs = {self.provider: self.get_config_dict(rotated_key)}

            client = ai.Client(provider_configs=provider_configs)

            # Log the request for debugging
            logger.info(
                f"Sending request to {self.provider} with model: {self.full_model_name}"
            )
            logger.debug(f"Request params: {request_params}")

            # Run synchronous aisuite call in thread pool to avoid blocking event loop
            response = await asyncio.to_thread(
                client.chat.completions.create, **request_params
            )

            # Report success
            self.rotator.report_success(rotated_key)

            return response.choices[0].message.content.strip()

        except Exception as e:
            # Report failure
            self.rotator.report_failure(rotated_key)

            logger.error(f"Error sending message to {self.provider}: {e}")
            logger.error(
                f"Request details - Model: {self.full_model_name}, Provider: {self.provider}"
            )
            raise Exception(f"Failed to get response from {self.provider}: {str(e)}")

    async def send_messages(
        self,
        messages: List[InputMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Message:
        """Send a list of messages to the AI provider with optional tools."""
        try:
            # Convert InputMessage objects to dict format for aisuite
            message_dicts = [msg.model_dump(exclude_none=True) for msg in messages]

            request_params = {
                "model": self.full_model_name,
                "messages": message_dicts,
                "temperature": temperature,
            }

            if max_tokens:
                request_params["max_tokens"] = max_tokens

            if tools:
                request_params["tools"] = tools

            # Get rotated key and provider-specific configuration
            rotated_key = self.rotator.get_next_key()
            provider_configs = {self.provider: self.get_config_dict(rotated_key)}

            client = ai.Client(provider_configs=provider_configs)

            # Log the request for debugging
            logger.info(
                f"Sending messages request to {self.provider} with model: {self.full_model_name}"
            )
            logger.debug(f"Request params: {json.dumps(request_params, indent=2)}")

            # Run synchronous aisuite call in thread pool to avoid blocking event loop
            response = await asyncio.to_thread(
                client.chat.completions.create, **request_params
            )

            # Report success
            self.rotator.report_success(rotated_key)

            # Convert aisuite response to our Message format
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
            # Report failure
            self.rotator.report_failure(rotated_key)

            logger.error(f"Error sending messages to {self.provider}: {e}")
            logger.error(
                f"Request details - Model: {self.full_model_name}, Provider: {self.provider}"
            )
            raise Exception(f"Failed to get response from {self.provider}: {str(e)}")

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from deprecated import deprecated
from .models import Message, InputMessage


class AIProviderInterface(ABC):
    """Interface for AI providers to implement message-based communication."""

    @deprecated(reason="Use send_messages() instead for better caching optimization")
    @abstractmethod
    async def send_message(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a message to the AI provider and get a response.

        Args:
            system_prompt: The system prompt that sets the AI's behavior
            user_message: The user's message/question
            temperature: Controls randomness in the response (0.0 to 1.0)
            max_tokens: Maximum number of tokens in the response

        Returns:
            The AI provider's response as a string
        """
        pass

    @abstractmethod
    async def send_messages(
        self,
        messages: List[InputMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Message:
        """
        Send a list of structured messages to the AI provider with optional tools.
        Optimized for caching by separating cacheable content (documents, prompts)
        from non-cacheable content (questions).

        Args:
            messages: List of typed input messages for optimal caching
            tools: Optional list of tools in OpenAI function calling format
            temperature: Controls randomness in the response (0.0 to 1.0)
            max_tokens: Maximum number of tokens in the response

        Returns:
            The AI provider's response as a Message object
        """
        pass

from abc import ABC, abstractmethod
from typing import Callable, Dict, Any


class MessageQueueInterface(ABC):
    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def publish(
        self, queue: str, message: Dict[str, Any], exchange: str = ""
    ) -> bool:
        pass

    @abstractmethod
    async def publish_batch(
        self, queue: str, messages: list[Dict[str, Any]], exchange: str = ""
    ) -> int:
        """Publish multiple messages in a batch. Returns count of published messages."""
        pass

    @abstractmethod
    async def consume(
        self,
        queue: str,
        callback: Callable,
        auto_ack: bool = True,
        prefetch_count: int = 1,
    ) -> None:
        pass

    @abstractmethod
    async def declare_queue(
        self, queue: str, durable: bool = True, dlq_enabled: bool = True
    ) -> bool:
        pass

    @abstractmethod
    async def declare_exchange(
        self, exchange: str, exchange_type: str = "direct", durable: bool = True
    ) -> bool:
        pass

    @abstractmethod
    async def bind_queue(
        self, queue: str, exchange: str, routing_key: str = ""
    ) -> bool:
        pass

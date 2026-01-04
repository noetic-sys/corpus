from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic, Type
from pydantic import BaseModel
from uuid import uuid4

from common.providers.messaging.factory import get_message_queue
from common.providers.messaging.interface import MessageQueueInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


T = TypeVar("T", bound=BaseModel)


class BaseWorker(ABC, Generic[T]):
    """Base worker class for handling message queue processing."""

    def __init__(
        self,
        queue_name: str,
        worker_id: Optional[str] = None,
        message_class: Optional[Type[T]] = None,
        max_concurrent_messages: int = 1,
    ):
        self.queue_name = queue_name
        self.worker_id = worker_id or f"{queue_name}_worker_{uuid4()}"
        self.message_queue: Optional[MessageQueueInterface] = None
        self.running = False
        self.message_class = message_class
        self.max_concurrent_messages = max_concurrent_messages

    async def setup(self):
        """Initialize worker dependencies."""
        try:
            # Setup message queue
            self.message_queue = get_message_queue()
            await self.message_queue.connect()
            await self.message_queue.declare_queue(
                self.queue_name, durable=True, dlq_enabled=True
            )

            # Setup lock provider if this worker has one
            if hasattr(self, "lock_provider"):
                await self.lock_provider.connect()

            logger.info(f"Worker {self.worker_id} setup completed")

        except Exception as e:
            logger.error(f"Error setting up worker {self.worker_id}: {e}")
            raise

    async def cleanup(self):
        """Cleanup worker resources."""
        try:
            if self.message_queue:
                await self.message_queue.disconnect()

            # Cleanup lock provider if this worker has one
            if hasattr(self, "lock_provider"):
                await self.lock_provider.disconnect()

            logger.info(f"Worker {self.worker_id} cleanup completed")
        except Exception as e:
            logger.error(f"Error cleaning up worker {self.worker_id}: {e}")

    async def start(self):
        """Start the worker to consume messages."""
        if self.running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return

        self.running = True
        logger.info(f"Starting worker {self.worker_id} on queue {self.queue_name}")

        try:
            await self.setup()
            await self.message_queue.consume(
                self.queue_name,
                self._message_handler,
                auto_ack=False,
                prefetch_count=self.max_concurrent_messages,
            )
        except Exception as e:
            logger.error(f"Error in worker {self.worker_id}: {e}")
            raise
        finally:
            self.running = False
            await self.cleanup()

    async def stop(self):
        """Stop the worker."""
        self.running = False
        logger.info(f"Stopping worker {self.worker_id}")

    async def _message_handler(self, message: T):
        """Internal message handler that wraps the abstract process_message method."""
        logger.info(f"Worker {self.worker_id} received message: {message}")

        try:
            # Services handle their own sessions - no wrapper needed here
            if self.message_class:
                parsed_message = self.message_class(**message)
                await self.process_message(parsed_message)
            else:
                await self.process_message(message)

            logger.info(f"Worker {self.worker_id} successfully processed message")

        except Exception as e:
            logger.error(
                f"Error processing message in worker {self.worker_id}: {e}",
                exc_info=True,
            )
            raise

    @abstractmethod
    async def process_message(self, message: T):
        """Process a message from the queue. Must be implemented by subclasses."""
        pass

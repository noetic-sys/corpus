from .interface import MessageQueueInterface
from .rabbitmq_async import RabbitMQClient


def get_message_queue() -> MessageQueueInterface:
    """Get RabbitMQ client instance (async)."""
    return RabbitMQClient()

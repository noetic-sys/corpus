from temporalio.client import Client

from common.core.config import settings
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


async def get_temporal_client() -> Client:
    """Connect to Temporal (Cloud or self-hosted).

    Uses settings to determine connection params:
    - temporal_host: Server address
    - temporal_namespace: Namespace (required for Cloud)
    - temporal_api_key: API key (enables TLS, required for Cloud)
    """
    host = settings.temporal_host
    namespace = settings.temporal_namespace
    api_key = settings.temporal_api_key

    logger.info(f"Connecting to Temporal at {host} (namespace: {namespace})")

    if api_key:
        client = await Client.connect(
            host,
            namespace=namespace,
            api_key=api_key,
            tls=True,
        )
    else:
        client = await Client.connect(
            host,
            namespace=namespace,
        )

    logger.info("Connected to Temporal")
    return client

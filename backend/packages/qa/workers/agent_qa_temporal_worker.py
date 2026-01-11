from typing import Optional

from temporalio.client import Client
from temporalio.service import RetryConfig
from temporalio.worker import Worker

from common.core.otel_axiom_exporter import get_logger
from packages.qa.workflows import AgentQAWorkflow
from packages.qa.workflows.activities import (
    launch_agent_qa_activity,
    check_agent_qa_status_activity,
    extract_agent_qa_results_activity,
    cleanup_agent_qa_activity,
)

logger = get_logger(__name__)


class AgentQATemporalWorker:
    """Temporal worker for agent QA execution."""

    def __init__(
        self,
        temporal_host: str = "localhost:7233",
    ):
        self.temporal_host = temporal_host
        self.task_queue = "agent-qa-worker"
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.running = False

    async def connect(self):
        """Connect to Temporal server."""
        logger.info(f"Connecting to Temporal server at {self.temporal_host}")
        self.client = await Client.connect(
            self.temporal_host,
            retry_config=RetryConfig(
                initial_interval_millis=100,
                max_interval_millis=10_000,  # 10s max backoff
                multiplier=2.0,
                max_retries=30,  # Exit after ~5min of failures so K8s can restart
            ),
        )
        logger.info("Connected to Temporal server")

    async def create_worker(self):
        """Create Temporal worker with agent QA workflows and activities."""
        if not self.client:
            await self.connect()

        logger.info(f"Creating Temporal worker for task queue: {self.task_queue}")

        self.worker = Worker(
            self.client,
            task_queue=self.task_queue,
            workflows=[AgentQAWorkflow],
            activities=[
                launch_agent_qa_activity,
                check_agent_qa_status_activity,
                extract_agent_qa_results_activity,
                cleanup_agent_qa_activity,
            ],
        )

        logger.info(
            f"Temporal worker created successfully with 1 workflow and 4 activities"
        )

    async def start(self):
        """Start the Temporal worker."""
        if not self.worker:
            await self.create_worker()

        logger.info("Starting Temporal worker...")
        self.running = True

        try:
            await self.worker.run()
        except Exception as e:
            logger.error(f"Worker failed with error: {e}", exc_info=True)
            raise
        finally:
            self.running = False

    async def stop(self):
        """Stop the Temporal worker."""
        logger.info("Stopping Temporal worker...")
        self.running = False

        if self.worker:
            # Temporal worker will stop when the run() method exits
            pass

        if self.client:
            await self.client.close()

        logger.info("Temporal worker stopped")

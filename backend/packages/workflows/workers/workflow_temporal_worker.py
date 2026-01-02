import logging
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker

from packages.workflows.workflows import WorkflowExecutionWorkflow
from packages.workflows.workflows.activities import (
    launch_workflow_agent_activity,
    check_workflow_agent_status_activity,
    extract_workflow_results_activity,
    cleanup_workflow_agent_activity,
    update_execution_status_activity,
)


logger = logging.getLogger(__name__)


class WorkflowTemporalWorker:
    """Temporal worker for workflow execution."""

    def __init__(
        self,
        temporal_host: str = "localhost:7233",
    ):
        self.temporal_host = temporal_host
        self.task_queue = "workflow-execution-queue"
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.running = False

    async def connect(self):
        """Connect to Temporal server."""
        logger.info(f"Connecting to Temporal server at {self.temporal_host}")
        self.client = await Client.connect(self.temporal_host)
        logger.info("Connected to Temporal server")

    async def create_worker(self):
        """Create Temporal worker with workflow execution workflows and activities."""
        if not self.client:
            await self.connect()

        logger.info(f"Creating Temporal worker for task queue: {self.task_queue}")

        self.worker = Worker(
            self.client,
            task_queue=self.task_queue,
            workflows=[WorkflowExecutionWorkflow],
            activities=[
                launch_workflow_agent_activity,
                check_workflow_agent_status_activity,
                extract_workflow_results_activity,
                cleanup_workflow_agent_activity,
                update_execution_status_activity,
            ],
        )

        logger.info(
            f"Temporal worker created successfully with 1 workflow and 2 activities"
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

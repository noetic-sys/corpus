import argparse

from common.core.config import settings
from common.workers.launcher import WorkerLauncher
from packages.documents.workers.temporal_worker import TemporalWorker
from packages.documents.workflows import TaskQueueType


def setup_cli():
    """Setup CLI arguments and return parsed args with factory parameters."""
    parser = argparse.ArgumentParser(description="Temporal Document Extraction Worker")
    parser.add_argument(
        "--queue",
        type=str,
        choices=[
            TaskQueueType.DOCUMENT_ROUTING.value,
            TaskQueueType.PDF_PROCESSING.value,
            TaskQueueType.PAGE_CONVERSION.value,
            TaskQueueType.GENERIC_EXTRACTION.value,
            TaskQueueType.DOCUMENT_CHUNKING.value,
            "all",
        ],
        default=TaskQueueType.DOCUMENT_ROUTING.value,
        help=f"Task queue to process (default: {TaskQueueType.DOCUMENT_ROUTING.value})",
    )
    parser.add_argument(
        "--temporal-host",
        type=str,
        default=getattr(settings, "temporal_host", "localhost:7233"),
        help="Temporal server host:port (default: from settings or localhost:7233)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)",
    )

    args = parser.parse_args()

    # Return args and factory parameters
    factory_args = (args.temporal_host, args.queue)
    factory_kwargs = {}

    return args, factory_args, factory_kwargs


def main():
    """Main entry point with command-line argument support."""

    WorkerLauncher().run_with_cli(
        worker_factory=TemporalWorker,
        worker_name="Temporal Worker",
        setup_models=True,
        setup_logging=False,  # Temporal worker doesn't use the basic logging setup
        cli_setup_func=setup_cli,
    )


if __name__ == "__main__":
    main()

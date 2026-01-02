import argparse

from common.core.config import settings
from common.workers.launcher import WorkerLauncher
from packages.qa.workers.agent_qa_temporal_worker import AgentQATemporalWorker


def setup_cli():
    """Setup CLI arguments and return parsed args with factory parameters."""
    parser = argparse.ArgumentParser(description="Temporal Agent QA Worker")
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
    factory_args = (args.temporal_host,)
    factory_kwargs = {}

    return args, factory_args, factory_kwargs


def main():
    """Main entry point with command-line argument support."""

    WorkerLauncher().run_with_cli(
        worker_factory=AgentQATemporalWorker,
        worker_name="Agent QA Worker",
        setup_models=True,
        setup_logging=False,  # Temporal worker doesn't use the basic logging setup
        cli_setup_func=setup_cli,
    )


if __name__ == "__main__":
    main()

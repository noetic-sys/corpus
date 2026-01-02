"""
Common worker launcher utilities to reduce boilerplate code across workers.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, Any, Callable

from common.core.otel_axiom_exporter import _initialize_telemetry, get_logger


class WorkerLauncher:
    """Common worker launcher that handles boilerplate setup, signals, and lifecycle."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.worker_instance: Optional[Any] = None

    def _setup_logging(self):
        """Configure logging at module level."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,  # This ensures it overrides any existing configuration
        )

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle SIGINT (Ctrl+C) gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        if self.worker_instance:
            # Set running to False to break the consume loop
            self.worker_instance.running = False
        sys.exit(0)

    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def _run_worker_async(self, worker_instance: Any, worker_name: str):
        """Run worker with common lifecycle management."""
        self.worker_instance = worker_instance

        # Register signal handlers
        self._register_signal_handlers()

        try:
            self.logger.info(f"Starting {worker_name}...")
            await worker_instance.start()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down worker...")
        except Exception as e:
            self.logger.error(f"Worker failed with error: {e}", exc_info=True)
        finally:
            try:
                self.logger.info("Performing worker cleanup...")
                await worker_instance.stop()
                self.logger.info("Worker shutdown complete")
            except Exception as cleanup_error:
                self.logger.error(f"Error during cleanup: {cleanup_error}")

    def run(
        self,
        worker_factory: Callable,
        worker_name: str,
        setup_models: bool = False,
        setup_logging: bool = True,
        factory_args: tuple = (),
        factory_kwargs: dict = None,
    ):
        """
        Main entry point to run a worker.

        Args:
            worker_factory: Function/class that creates the worker instance
            worker_name: Human readable name for logging
            setup_models: Whether to register SQLAlchemy models (for temporal workers)
            setup_logging: Whether to setup logging configuration
            factory_args: Args to pass to worker factory
            factory_kwargs: Kwargs to pass to worker factory
        """
        if factory_kwargs is None:
            factory_kwargs = {}

        # Initialize telemetry
        _initialize_telemetry()

        # Setup models if needed (for temporal workers)
        # Setup logging if requested
        if setup_logging:
            self._setup_logging()

        self.logger.info(f"Configuring {worker_name}...")

        # Create worker instance
        worker_instance = worker_factory(*factory_args, **factory_kwargs)

        # Run worker
        try:
            asyncio.run(self._run_worker_async(worker_instance, worker_name))
        except KeyboardInterrupt:
            self.logger.info("Final keyboard interrupt caught, exiting...")
            sys.exit(0)

    def run_with_cli(
        self,
        worker_factory: Callable,
        worker_name: str,
        setup_models: bool = False,
        setup_logging: bool = True,
        cli_setup_func: Optional[Callable] = None,
    ):
        """
        Run worker with CLI argument parsing support.

        Args:
            worker_factory: Function/class that creates the worker instance
            worker_name: Human readable name for logging
            setup_models: Whether to register SQLAlchemy models
            setup_logging: Whether to setup logging configuration
            cli_setup_func: Function that sets up argument parser and returns (args, factory_args, factory_kwargs)
        """
        if cli_setup_func:
            args, factory_args, factory_kwargs = cli_setup_func()

            # Update logging level if provided in args
            if hasattr(args, "log_level"):
                logging.getLogger().setLevel(getattr(logging, args.log_level))
        else:
            factory_args, factory_kwargs = (), {}

        self.run(
            worker_factory=worker_factory,
            worker_name=worker_name,
            setup_models=setup_models,
            setup_logging=setup_logging,
            factory_args=factory_args,
            factory_kwargs=factory_kwargs,
        )

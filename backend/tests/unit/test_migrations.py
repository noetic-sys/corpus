import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from testcontainers.postgres import PostgresContainer


def test_migration_cycle():
    """Test that alembic migrations can upgrade to head and downgrade to base without errors."""

    with PostgresContainer("postgres:16") as postgres:
        # Get database connection details from testcontainer
        db_url = postgres.get_connection_url()
        parsed_url = urlparse(db_url)

        # Set environment variables for alembic to use testcontainer database
        env = os.environ.copy()
        env["DB_USER"] = parsed_url.username
        env["DB_PASSWORD"] = parsed_url.password
        env["DB_HOST"] = parsed_url.hostname
        env["DB_PORT"] = str(parsed_url.port)
        env["DB_NAME"] = parsed_url.path.lstrip("/")

        # Also set other required env vars to prevent config errors
        env["APP_NAME"] = "test"
        env["API_VERSION"] = "v1"
        env["DEBUG"] = "true"
        env["AWS_ACCESS_KEY_ID"] = "test"
        env["AWS_SECRET_ACCESS_KEY"] = "test"
        env["AWS_REGION"] = "us-east-1"
        env["S3_BUCKET_NAME"] = "test"

        # RabbitMQ
        env["RABBITMQ_HOST"] = "localhost"
        env["RABBITMQ_PORT"] = "5672"
        env["RABBITMQ_USERNAME"] = "test"
        env["RABBITMQ_PASSWORD"] = "test"
        env["RABBITMQ_VHOST"] = "/"

        # AI API Keys (required fields)
        env["OPENAI_API_KEYS"] = '["test-key"]'
        env["ANTHROPIC_API_KEYS"] = '["test-key"]'
        env["ANTHROPIC_API_KEY"] = "test-key"
        env["XAI_API_KEYS"] = '["test-key"]'
        env["GEMINI_API_KEYS"] = '["test-key"]'
        env["GEMINI_MODEL"] = "gemini-pro"

        # OpenTelemetry
        env["OTEL_SERVICE_NAME"] = "test"
        env["OTEL_SERVICE_VERSION"] = "test"

        # Axiom
        env["AXIOM_TOKEN"] = "test"
        env["AXIOM_DATASET"] = "test"

        # Vectorize and Datalab
        env["VECTORIZE_API_KEY"] = "test"
        env["VECTORIZE_ORGANIZATION_ID"] = "test"
        env["DATALAB_API_KEY"] = "test"

        # Exa Search
        env["EXA_API_KEY"] = "test"

        # Temporal
        env["TEMPORAL_HOST"] = "localhost:7233"
        env["TEMPORAL_TASK_QUEUE"] = "test"

        # Google Cloud
        env["GOOGLE_PROJECT_ID"] = "test"
        env["GOOGLE_REGION"] = "us-central1"

        # Auth0
        env["AUTH0_DOMAIN"] = "test.auth0.com"
        env["AUTH0_CLIENT_ID"] = "test"
        env["AUTH0_AUDIENCE"] = "test"

        # Get project root directory
        project_root = Path(__file__).parents[2]

        # Run alembic upgrade head
        upgrade_result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
        )

        # Assert upgrade succeeded
        assert (
            upgrade_result.returncode == 0
        ), f"Upgrade failed: {upgrade_result.stderr}"

        # Run alembic downgrade base
        downgrade_result = subprocess.run(
            ["alembic", "downgrade", "base"],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
        )

        # Assert downgrade succeeded
        assert (
            downgrade_result.returncode == 0
        ), f"Downgrade failed: {downgrade_result.stderr}"

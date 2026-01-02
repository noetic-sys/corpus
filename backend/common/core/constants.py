from enum import Enum


class Environment(str, Enum):
    """Environment profiles."""

    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageProvider(str, Enum):
    """Storage provider types."""

    S3 = "s3"
    GCS = "gcs"


class WorkflowExecutionMode(str, Enum):
    """Workflow execution modes."""

    DOCKER = "docker"
    K8S = "k8s"

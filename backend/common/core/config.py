from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.core.constants import Environment, StorageProvider, WorkflowExecutionMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Environment Profile
    environment: Environment = Environment.LOCAL

    # API Settings
    app_name: str
    api_version: str
    debug: bool

    # Database Components
    db_user: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str
    db_use_nullpool: bool = (
        False  # True for workers (sequential), False for API (concurrent)
    )
    db_pool_size: int = 10
    db_pool_overflow: int = 5

    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # AWS/S3
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    s3_bucket_name: str
    s3_endpoint_url: Optional[str] = None  # For LocalStack

    # RabbitMQ
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_username: str
    rabbitmq_password: str
    rabbitmq_vhost: str

    # Worker Concurrency Settings
    qa_worker_prefetch_count: int = 5  # How many QA jobs to process concurrently

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_url: Optional[str] = None  # For compatibility

    @property
    def redis_connection_url(self) -> str:
        """Construct Redis URL from components."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # OpenAI
    openai_api_keys: List[str]
    openai_model: str = "gpt-4o-mini"

    # Embeddings
    embedding_provider: str = "openai"  # openai or voyage
    embedding_model: Optional[str] = None  # Provider-specific model

    # Voyage AI (optional embedding provider)
    voyage_api_keys: Optional[List[str]] = None

    anthropic_api_keys: List[str]
    anthropic_api_key: str  # Single key for workflow agent execution
    anthropic_model: str = "claude-3-7-sonnet-20250219"

    xai_api_keys: List[str]
    xai_model: str = "grok-3"

    # OpenTelemetry
    otel_service_name: str
    otel_service_version: str

    # Axiom
    axiom_token: str
    axiom_dataset: str

    # Vectorize Iris
    vectorize_api_key: str
    vectorize_organization_id: str

    datalab_api_key: str

    # Exa Search
    exa_api_key: str

    # Temporal
    temporal_host: str
    temporal_task_queue: str

    # Google Gemini
    gemini_api_keys: List[str]
    gemini_model: str

    # Vertex ai
    google_project_id: str
    google_region: str
    google_application_credentials: Optional[str] = (
        None  # Optional - falls back to pod identity with Workload Identity
    )

    # AI Provider Selection
    default_ai_provider: str = "google"

    # PDF Processing
    pdf_page_split_size: int = 1

    # Document Search
    document_search_provider: str = "elasticsearch"
    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    elasticsearch_scheme: str = "http"

    @property
    def elasticsearch_url(self) -> str:
        """Construct Elasticsearch URL from components."""
        if self.elasticsearch_username and self.elasticsearch_password:
            return f"{self.elasticsearch_scheme}://{self.elasticsearch_username}:{self.elasticsearch_password}@{self.elasticsearch_host}:{self.elasticsearch_port}"
        else:
            return f"{self.elasticsearch_scheme}://{self.elasticsearch_host}:{self.elasticsearch_port}"

    # Okta SSO
    okta_issuer: str = ""
    okta_client_id: str = ""
    okta_audience: str = "api://default"

    # Firebase Auth (uses Workload Identity on GKE - no API keys needed)
    firebase_project_id: Optional[str] = None  # Falls back to google_project_id

    # Auth0 SSO (optional)
    auth0_domain: Optional[str] = None
    auth0_client_id: Optional[str] = None
    auth0_audience: Optional[str] = None

    # Workflow Execution
    gcp_project_id: Optional[str] = None  # GCP project ID for K8s image
    workflow_agent_image_tag: str = (
        "latest"  # Workflow agent image tag (set by deployment)
    )

    # Environment-aware properties
    @property
    def storage_provider(self) -> StorageProvider:
        """Auto-select storage provider based on environment."""
        return (
            StorageProvider.S3
            if self.environment == Environment.LOCAL
            else StorageProvider.GCS
        )

    @property
    def workflow_execution_mode(self) -> WorkflowExecutionMode:
        """Auto-select workflow execution mode based on environment."""
        return (
            WorkflowExecutionMode.DOCKER
            if self.environment == Environment.LOCAL
            else WorkflowExecutionMode.K8S
        )

    @property
    def api_endpoint(self) -> str:
        """Auto-select API endpoint based on environment."""
        if self.environment == Environment.LOCAL:
            return "http://backend:8000"
        return "http://corpus-api:8000"

    @property
    def cors_allowed_origins(self) -> List[str]:
        """Auto-select CORS origins based on environment."""
        if self.environment == Environment.LOCAL:
            return [
                "http://localhost:3000",
                "http://localhost:3001",
            ]
        return [
            "https://onecorpus.com",
            "https://api.onecorpus.com",
            "https://ws.onecorpus.com",
        ]

    # Document Chunking (always enabled - small docs become single chunk)
    chunk_target_size: int = 12000  # Target chunk size in characters (~3000 tokens)
    chunk_overlap_size: int = 800  # Overlap between chunks in characters (~200 tokens)

    # Billing - Stripe (payments)
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    # Stripe price IDs for subscription tiers
    stripe_price_id_starter: str = ""
    stripe_price_id_professional: str = ""
    stripe_price_id_business: str = ""
    stripe_price_id_enterprise: str = ""


settings = Settings()

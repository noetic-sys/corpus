# Shared pytest configuration and fixtures for all test types
import hashlib
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address
from unittest.mock import patch
from packages.matrices.models.domain.matrix_enums import EntityType, EntityRole
from packages.matrices.models.domain.matrix import MatrixCellStatus
from packages.matrices.models.domain.matrix_enums import CellType
from datetime import datetime, timezone, timedelta

# Create test limiter with no limits and in-memory storage
test_limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)

# Patch the limiter before importing the app so decorators use test limiter
with patch("common.providers.rate_limiter.limiter.limiter", test_limiter):
    from api.main import app

from common.db.session import get_db, get_db_readonly
from common.db.base import Base
from packages.agents.models.database.conversation import ConversationEntity
from packages.agents.models.database.message import MessageEntity
from packages.ai_model.models.database import AIProviderEntity, AIModelEntity
from packages.companies.models.database.company import CompanyEntity
from packages.users.models.database.user import UserEntity
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.matrices.models.database import MatrixTemplateVariableEntity
from packages.questions.models.database.question_template_variable import (
    QuestionTemplateVariableEntity,
)
from packages.questions.models.database.question_type import QuestionTypeEntity
from packages.workspaces.models.database.workspace import WorkspaceEntity
from packages.matrices.models.database.matrix import MatrixEntity, MatrixCellEntity
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetEntity,
    MatrixEntitySetMemberEntity,
    MatrixCellEntityReferenceEntity,
)
from packages.documents.models.database.document import (
    DocumentEntity,
)
from packages.qa.models.database.answer import AnswerEntity
from packages.qa.models.database.answer_set import AnswerSetEntity
from packages.qa.models.database.citation import CitationSetEntity
from packages.questions.models.database.question import QuestionEntity
from packages.auth.dependencies import get_current_active_user
from packages.workflows.models.database.workflow import (
    WorkflowEntity,
    WorkflowExecutionEntity,
)
from packages.workflows.models.database.input_file import WorkflowInputFile
from packages.workflows.models.database.execution_file import (
    WorkflowExecutionFile,
    ExecutionFileType,
)
from packages.billing.models.database.subscription import SubscriptionEntity
from packages.billing.models.database.usage import UsageEventEntity
from packages.billing.models.domain.enums import (
    SubscriptionStatus,
    SubscriptionTier,
    PaymentProvider,
    UsageEventType,
)
from packages.billing.models.domain.subscription import Subscription

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine and initialize schema."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_connection(test_engine):
    """Create test connection with outer transaction for rollback isolation."""
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        yield connection
        await trans.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_session_factory(test_connection):
    """Create session factory bound to test connection.

    Using join_transaction_mode="create_savepoint" so nested transaction()
    calls create savepoints instead of real nested transactions.
    """
    return async_sessionmaker(
        bind=test_connection,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


@pytest_asyncio.fixture(scope="function")
async def test_db(test_session_factory):
    """Create a test database session."""
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def patch_lazy_sessions(test_session_factory, monkeypatch):
    """
    Patch session factories to use test database.

    This allows real transaction() and get_session() to run with proper
    commit/rollback/ContextVar semantics while using the test database.
    """
    monkeypatch.setattr("common.db.scoped.AsyncSessionLocal", test_session_factory)
    monkeypatch.setattr(
        "common.db.scoped.AsyncSessionLocalReadonly", test_session_factory
    )


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession, test_user):
    """Create a test client."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    def override_get_current_active_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_readonly] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def sample_company(test_db: AsyncSession):
    """Create a sample company for testing."""
    company = CompanyEntity(name="test company", stripe_customer_id="cus_test123")
    test_db.add(company)
    await test_db.commit()
    await test_db.refresh(company)
    return company


@pytest_asyncio.fixture(scope="function")
async def test_user(sample_company, sso_user_entity):
    """Create a test authenticated user."""
    return AuthenticatedUser(
        user_id=sso_user_entity.id,
        # email="test@example.com",
        # full_name="Test User",
        company_id=sample_company.id,
        # is_active=True,
        # is_admin=False,
    )


@pytest_asyncio.fixture(scope="function")
async def sample_workspace(test_db: AsyncSession, sample_company):
    """Create a sample workspace for testing."""
    workspace = WorkspaceEntity(
        name="Test Workspace",
        description="A test workspace for organizing matrices",
        company_id=sample_company.id,
    )
    test_db.add(workspace)
    await test_db.commit()
    await test_db.refresh(workspace)
    return workspace


@pytest_asyncio.fixture(scope="function")
async def sample_matrix(test_db: AsyncSession, sample_workspace, sample_company):
    """Create a sample matrix for testing with entity sets."""
    matrix = MatrixEntity(
        name="Test Matrix",
        workspace_id=sample_workspace.id,
        company_id=sample_company.id,
        matrix_type="standard",
    )
    test_db.add(matrix)
    await test_db.commit()
    await test_db.refresh(matrix)

    # Create required entity sets for standard matrix
    document_entity_set = MatrixEntitySetEntity(
        matrix_id=matrix.id,
        company_id=sample_company.id,
        name="Documents",
        entity_type="document",
    )
    question_entity_set = MatrixEntitySetEntity(
        matrix_id=matrix.id,
        company_id=sample_company.id,
        name="Questions",
        entity_type="question",
    )
    test_db.add(document_entity_set)
    test_db.add(question_entity_set)
    await test_db.commit()

    return matrix


@pytest_asyncio.fixture(scope="function")
async def sample_document(test_db: AsyncSession, sample_company):
    """Create a sample document for testing."""
    document = DocumentEntity(
        filename="test.pdf",
        storage_key="test_storage_key",
        checksum="test_checksum_hash",
        content_type="application/pdf",
        file_size=1024,
        company_id=sample_company.id,
    )
    test_db.add(document)
    await test_db.commit()
    await test_db.refresh(document)
    return document


@pytest_asyncio.fixture(scope="function")
async def sample_question(test_db: AsyncSession, sample_matrix, sample_company):
    """Create a sample question for testing."""
    question = QuestionEntity(
        matrix_id=sample_matrix.id,
        question_text="What is the sample question?",
        question_type_id=1,  # SHORT_ANSWER
        company_id=sample_company.id,
    )
    test_db.add(question)
    await test_db.commit()
    await test_db.refresh(question)
    return question


@pytest_asyncio.fixture(scope="function")
async def sample_wired_matrix_cell(
    test_db: AsyncSession,
    sample_matrix,
    sample_company,
    sample_document,
    sample_question,
):
    """Create a sample matrix cell for testing with entity sets and references."""

    # Create entity sets for matrix
    doc_entity_set = MatrixEntitySetEntity(
        matrix_id=sample_matrix.id,
        name="Documents",
        entity_type=EntityType.DOCUMENT.value,
        company_id=sample_company.id,
    )
    question_entity_set = MatrixEntitySetEntity(
        matrix_id=sample_matrix.id,
        name="Questions",
        entity_type=EntityType.QUESTION.value,
        company_id=sample_company.id,
    )
    test_db.add(doc_entity_set)
    test_db.add(question_entity_set)
    await test_db.commit()
    await test_db.refresh(doc_entity_set)
    await test_db.refresh(question_entity_set)

    # Create entity set members
    doc_member = MatrixEntitySetMemberEntity(
        entity_set_id=doc_entity_set.id,
        entity_type=EntityType.DOCUMENT.value,
        entity_id=sample_document.id,
        member_order=0,
        company_id=sample_company.id,
    )
    question_member = MatrixEntitySetMemberEntity(
        entity_set_id=question_entity_set.id,
        entity_type=EntityType.QUESTION.value,
        entity_id=sample_question.id,
        member_order=0,
        company_id=sample_company.id,
    )
    test_db.add(doc_member)
    test_db.add(question_member)
    await test_db.commit()
    await test_db.refresh(doc_member)
    await test_db.refresh(question_member)

    # Create cell
    cell = MatrixCellEntity(
        matrix_id=sample_matrix.id,
        company_id=sample_company.id,
        cell_type="standard",
        status="pending",
        cell_signature=hashlib.md5(b"sample_wired_matrix_cell_fixture").hexdigest(),
    )
    test_db.add(cell)
    await test_db.commit()
    await test_db.refresh(cell)

    # Create entity references for cell
    doc_ref = MatrixCellEntityReferenceEntity(
        matrix_id=sample_matrix.id,
        matrix_cell_id=cell.id,
        entity_set_id=doc_entity_set.id,
        entity_set_member_id=doc_member.id,
        role=EntityRole.DOCUMENT.value,
        entity_order=0,
        company_id=sample_company.id,
    )
    question_ref = MatrixCellEntityReferenceEntity(
        matrix_id=sample_matrix.id,
        matrix_cell_id=cell.id,
        entity_set_id=question_entity_set.id,
        entity_set_member_id=question_member.id,
        role=EntityRole.QUESTION.value,
        entity_order=0,
        company_id=sample_company.id,
    )
    test_db.add(doc_ref)
    test_db.add(question_ref)
    await test_db.commit()

    return cell


@pytest_asyncio.fixture(scope="function")
async def sample_matrix_cell(
    test_db: AsyncSession,
    sample_matrix,
    sample_company,
    sample_document,
    sample_question,
):
    # Create cell
    cell = MatrixCellEntity(
        matrix_id=sample_matrix.id,
        company_id=sample_company.id,
        cell_type="standard",
        status="pending",
        cell_signature=hashlib.md5(b"sample_matrix_cell_fixture").hexdigest(),
    )
    test_db.add(cell)
    await test_db.commit()
    await test_db.refresh(cell)

    return cell


@pytest_asyncio.fixture(scope="function")
async def sample_answer_set(test_db: AsyncSession, sample_matrix_cell, sample_company):
    """Create a sample answer set for testing."""
    answer_set = AnswerSetEntity(
        matrix_cell_id=sample_matrix_cell.id,
        company_id=sample_company.id,
        question_type_id=1,  # SHORT_ANSWER
        answer_found=True,
    )
    test_db.add(answer_set)
    await test_db.commit()
    await test_db.refresh(answer_set)
    return answer_set


@pytest_asyncio.fixture(scope="function")
async def sample_answer(test_db: AsyncSession, sample_answer_set, sample_company):
    """Create a sample answer for testing."""
    answer = AnswerEntity(
        answer_set_id=sample_answer_set.id,
        company_id=sample_company.id,
        answer_data={"type": "text", "value": "Sample answer"},
    )
    test_db.add(answer)
    await test_db.commit()
    await test_db.refresh(answer)
    return answer


@pytest_asyncio.fixture(scope="function")
async def sample_citation_set(test_db: AsyncSession, sample_answer, sample_company):
    """Create a sample citation set for testing."""
    citation_set = CitationSetEntity(
        answer_id=sample_answer.id, company_id=sample_company.id
    )
    test_db.add(citation_set)
    await test_db.commit()
    await test_db.refresh(citation_set)
    return citation_set


@pytest_asyncio.fixture
async def sample_ai_provider(test_db: AsyncSession):
    """Create a sample AI provider."""
    provider = AIProviderEntity(name="openai", display_name="OpenAI", enabled=True)
    test_db.add(provider)
    await test_db.commit()
    await test_db.refresh(provider)
    return provider


@pytest_asyncio.fixture
async def disabled_ai_provider(test_db: AsyncSession):
    """Create a disabled AI provider."""
    provider = AIProviderEntity(
        name="disabled_provider", display_name="Disabled Provider", enabled=False
    )
    test_db.add(provider)
    await test_db.commit()
    await test_db.refresh(provider)
    return provider


@pytest_asyncio.fixture
async def sample_ai_model(test_db: AsyncSession, sample_ai_provider):
    """Create a sample AI model."""
    model = AIModelEntity(
        provider_id=sample_ai_provider.id,
        model_name="gpt-4",
        display_name="GPT-4",
        default_temperature=0.7,
        enabled=True,
    )
    test_db.add(model)
    await test_db.commit()
    await test_db.refresh(model)
    return model


@pytest_asyncio.fixture
async def disabled_ai_model(test_db: AsyncSession, sample_ai_provider):
    """Create a disabled AI model."""
    model = AIModelEntity(
        provider_id=sample_ai_provider.id,
        model_name="disabled-model",
        display_name="Disabled Model",
        default_temperature=0.7,
        enabled=False,
    )
    test_db.add(model)
    await test_db.commit()
    await test_db.refresh(model)
    return model


@pytest_asyncio.fixture
async def sample_conversation(test_db: AsyncSession, sample_ai_model, sample_company):
    """Create a sample conversation."""
    conversation = ConversationEntity(
        title="Test Conversation",
        company_id=sample_company.id,
        ai_model_id=sample_ai_model.id,
        extra_data={"test_key": "test_value"},
    )
    test_db.add(conversation)
    await test_db.commit()
    await test_db.refresh(conversation)
    return conversation


@pytest_asyncio.fixture
async def sample_message(test_db: AsyncSession, sample_conversation, sample_company):
    """Create a sample message."""
    message = MessageEntity(
        conversation_id=sample_conversation.id,
        company_id=sample_company.id,
        role="user",
        content="Hello, how are you?",
        sequence_number=1,
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)
    return message


@pytest_asyncio.fixture
async def sample_template_variable(
    test_db: AsyncSession, sample_matrix, sample_company
):
    """Create a sample template variable."""
    template_var = MatrixTemplateVariableEntity(
        matrix_id=sample_matrix.id,
        company_id=sample_company.id,
        template_string="company_name",
        value="Acme Corporation",
    )
    test_db.add(template_var)
    await test_db.commit()
    await test_db.refresh(template_var)
    return template_var


@pytest_asyncio.fixture
async def sample_association(
    test_db: AsyncSession, sample_question, sample_template_variable, sample_company
):
    """Create a sample question-template variable association."""
    association = QuestionTemplateVariableEntity(
        question_id=sample_question.id,
        company_id=sample_company.id,
        template_variable_id=sample_template_variable.id,
    )
    test_db.add(association)
    await test_db.commit()
    await test_db.refresh(association)
    return association


@pytest_asyncio.fixture
async def sample_user_entity(test_db: AsyncSession, sample_company):
    """Create a sample user entity."""
    user = UserEntity(
        email="test@example.com",
        full_name="Test User",
        company_id=sample_company.id,
        is_active=True,
        is_admin=False,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def sso_user_entity(test_db: AsyncSession, sample_company):
    """Create a sample SSO user entity."""
    user = UserEntity(
        email="sso@example.com",
        full_name="SSO User",
        company_id=sample_company.id,
        is_active=True,
        is_admin=False,
        sso_provider="auth0",
        sso_user_id="auth0|123456",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_company(test_db: AsyncSession):
    """Create a second company for testing."""
    company = CompanyEntity(name="Second Test Company", domain="second.com")
    test_db.add(company)
    await test_db.commit()
    await test_db.refresh(company)
    return company


@pytest_asyncio.fixture(scope="function")
async def second_user(second_company, test_db: AsyncSession):
    """Create a second test authenticated user for a different company."""
    user_entity = UserEntity(
        email="second@example.com",
        full_name="Second User",
        company_id=second_company.id,
        is_active=True,
        is_admin=False,
        sso_provider="auth0",
        sso_user_id="auth0|second123",
    )
    test_db.add(user_entity)
    await test_db.commit()
    await test_db.refresh(user_entity)

    return AuthenticatedUser(
        user_id=user_entity.id,
        company_id=second_company.id,
    )


@pytest_asyncio.fixture(scope="function")
async def sample_entity_set(test_db: AsyncSession, sample_matrix, sample_company):
    """Create a sample entity set for testing."""
    entity_set = MatrixEntitySetEntity(
        matrix_id=sample_matrix.id,
        company_id=sample_company.id,
        name="documents",
        entity_type="document",
    )
    test_db.add(entity_set)
    await test_db.commit()
    await test_db.refresh(entity_set)
    return entity_set


@pytest_asyncio.fixture(scope="function")
async def sample_question_entity_set(
    test_db: AsyncSession, sample_matrix, sample_company
):
    """Get the question entity set from sample_matrix (already created)."""
    result = await test_db.execute(
        select(MatrixEntitySetEntity).where(
            MatrixEntitySetEntity.matrix_id == sample_matrix.id,
            MatrixEntitySetEntity.entity_type == "question",
        )
    )
    return result.scalar_one()


@pytest_asyncio.fixture(scope="function")
async def sample_document_entity_set(
    test_db: AsyncSession, sample_matrix, sample_company
):
    """Get the document entity set from sample_matrix (already created)."""
    result = await test_db.execute(
        select(MatrixEntitySetEntity).where(
            MatrixEntitySetEntity.matrix_id == sample_matrix.id,
            MatrixEntitySetEntity.entity_type == "document",
        )
    )
    return result.scalar_one()


@pytest_asyncio.fixture(scope="function")
async def sample_entity_set_member(
    test_db: AsyncSession, sample_entity_set, sample_document, sample_company
):
    """Create a sample entity set member for testing."""
    member = MatrixEntitySetMemberEntity(
        entity_set_id=sample_entity_set.id,
        company_id=sample_company.id,
        entity_type="document",
        entity_id=sample_document.id,
        member_order=0,
    )
    test_db.add(member)
    await test_db.commit()
    await test_db.refresh(member)
    return member


@pytest_asyncio.fixture(scope="function")
async def sample_cell_entity_reference(
    test_db: AsyncSession,
    sample_matrix,
    sample_matrix_cell,
    sample_entity_set,
    sample_entity_set_member,
    sample_company,
):
    """Create a sample cell entity reference for testing."""
    reference = MatrixCellEntityReferenceEntity(
        matrix_id=sample_matrix.id,
        matrix_cell_id=sample_matrix_cell.id,
        entity_set_id=sample_entity_set.id,
        entity_set_member_id=sample_entity_set_member.id,
        company_id=sample_company.id,
        role="document",
        entity_order=0,
    )
    test_db.add(reference)
    await test_db.commit()
    await test_db.refresh(reference)
    return reference


@pytest_asyncio.fixture(scope="function")
async def sample_question_types(test_db: AsyncSession):
    """Create sample question types for testing."""
    question_types = [
        QuestionTypeEntity(
            id=1,
            name="SHORT_ANSWER",
            description="Brief text responses (≤200 characters)",
            validation_schema={"max_length": 200},
        ),
        QuestionTypeEntity(
            id=2,
            name="LONG_ANSWER",
            description="Extended text responses (>200 characters)",
            validation_schema={"min_length": 1},
        ),
        QuestionTypeEntity(
            id=3,
            name="DATE",
            description="Date values with format validation",
            validation_schema={"format": "date", "output_format": "ISO"},
        ),
        QuestionTypeEntity(
            id=4,
            name="CURRENCY",
            description="Monetary amounts with currency detection",
            validation_schema={"format": "currency", "detect_currency": True},
        ),
        QuestionTypeEntity(
            id=5,
            name="SINGLE_SELECT",
            description="Choose one option from predefined values",
            validation_schema={"type": "enum", "options": []},
        ),
    ]

    for qt in question_types:
        test_db.add(qt)

    await test_db.commit()
    for qt in question_types:
        await test_db.refresh(qt)

    return question_types


# Common test data for AI responses (now JSON-based)
AI_RESPONSE_SAMPLES = {
    "currency": {
        "valid": """{
            "items": [
                {
                    "amount": 1250.50,
                    "code": "USD",
                    "citations": []
                }
            ]
        }""",
        "multiple": """{
            "items": [
                {
                    "amount": 1250.50,
                    "code": "USD",
                    "citations": []
                },
                {
                    "amount": 1100.00,
                    "code": "EUR",
                    "citations": []
                }
            ]
        }""",
        "empty": """{"items": []}""",
        "with_citations": """{
            "items": [
                {
                    "amount": 1250.50,
                    "code": "USD",
                    "citations": [
                        {
                            "order": 1,
                            "quote_text": "The contract value is $1,250.50",
                            "document_id": 1
                        }
                    ]
                }
            ]
        }""",
    },
    "date": {
        "valid": """{
            "items": [
                {
                    "value": "2024-03-15",
                    "citations": []
                }
            ]
        }""",
        "multiple": """{
            "items": [
                {
                    "value": "2024-03-15",
                    "citations": []
                },
                {
                    "value": "2024-03-16",
                    "citations": []
                }
            ]
        }""",
        "empty": """{"items": []}""",
    },
    "select": {
        "single": """{
            "options": [
                {
                    "value": "Option A",
                    "citations": []
                }
            ]
        }""",
        "multiple": """{
            "options": [
                {
                    "value": "Option A",
                    "citations": []
                },
                {
                    "value": "Option B",
                    "citations": []
                },
                {
                    "value": "Option C",
                    "citations": []
                }
            ]
        }""",
        "empty": """{"options": []}""",
    },
    "text": {
        "valid": """{
            "items": [
                {
                    "value": "This is the answer text",
                    "citations": []
                }
            ]
        }""",
        "multiple": """{
            "items": [
                {
                    "value": "First answer",
                    "citations": []
                },
                {
                    "value": "Second answer",
                    "citations": []
                }
            ]
        }""",
        "empty": """{"items": []}""",
        "with_citations": """{
            "items": [
                {
                    "value": "This answer has citations [[cite:1]]",
                    "citations": [
                        {
                            "order": 1,
                            "quote_text": "This is the source text",
                            "document_id": 1
                        }
                    ]
                }
            ]
        }""",
    },
    "not_found": "<<ANSWER_NOT_FOUND>>",
}

# Sample option lists for select questions
SAMPLE_OPTIONS = [
    "Option A",
    "Option B",
    "Option C",
    "Option D",
    "Yes",
    "No",
    "Not Applicable",
]


# Workflow fixtures
@pytest_asyncio.fixture(scope="function")
async def sample_workflow(test_db: AsyncSession, sample_workspace, sample_company):
    """Create a sample workflow for testing."""
    workflow = WorkflowEntity(
        name="Test Workflow",
        description="A test workflow for automated reporting",
        company_id=sample_company.id,
        workspace_id=sample_workspace.id,
        trigger_type="manual",
        output_type="excel",
    )
    test_db.add(workflow)
    await test_db.commit()
    await test_db.refresh(workflow)
    return workflow


@pytest_asyncio.fixture(scope="function")
async def sample_workflow_execution(
    test_db: AsyncSession, sample_workflow, sample_company
):
    """Create a sample workflow execution for testing."""

    execution = WorkflowExecutionEntity(
        workflow_id=sample_workflow.id,
        company_id=sample_company.id,
        trigger_type="manual",
        started_at=datetime.now(timezone.utc),
        status="pending",
    )
    test_db.add(execution)
    await test_db.commit()
    await test_db.refresh(execution)
    return execution


@pytest_asyncio.fixture(scope="function")
async def sample_workflow_input_file(
    test_db: AsyncSession, sample_workflow, sample_company
):
    """Create a sample workflow input file for testing."""
    input_file = WorkflowInputFile(
        workflow_id=sample_workflow.id,
        company_id=sample_company.id,
        name="test_template.xlsx",
        description="Test Excel template",
        storage_path=f"workflows/{sample_workflow.id}/inputs/test_template.xlsx",
        file_size=2048,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        deleted=False,
    )
    test_db.add(input_file)
    await test_db.commit()
    await test_db.refresh(input_file)
    return input_file


@pytest_asyncio.fixture(scope="function")
async def sample_workflow_execution_file(
    test_db: AsyncSession, sample_workflow_execution, sample_company
):
    """Create a sample workflow execution file for testing."""
    execution_file = WorkflowExecutionFile(
        execution_id=sample_workflow_execution.id,
        company_id=sample_company.id,
        file_type=ExecutionFileType.OUTPUT.value,
        name="test_output.xlsx",
        storage_path=f"workflows/executions/{sample_workflow_execution.id}/outputs/test_output.xlsx",
        file_size=4096,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    test_db.add(execution_file)
    await test_db.commit()
    await test_db.refresh(execution_file)
    return execution_file


# Helper for creating test matrix cells with required cell_signature
def create_test_matrix_cell_entity(**kwargs):
    """Create a MatrixCellEntity for testing with all required fields.

    Provides sensible defaults including cell_signature which is required.
    Usage: create_test_matrix_cell_entity(matrix_id=1, company_id=1, status='completed')
    """
    # Compute test signature from params to ensure some uniqueness
    sig_str = f"{kwargs.get('matrix_id', 1)}_{kwargs.get('company_id', 1)}_{kwargs.get('status', 'pending')}"

    defaults = {
        "matrix_id": 1,
        "company_id": 1,
        "cell_type": CellType.STANDARD.value,
        "status": MatrixCellStatus.PENDING.value,
        "cell_signature": hashlib.md5(sig_str.encode()).hexdigest(),
    }
    defaults.update(kwargs)
    return MatrixCellEntity(**defaults)


# ============================================================================
# Billing Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def sample_subscription(test_db: AsyncSession, sample_company):
    """Create a sample active subscription for testing."""
    subscription_entity = SubscriptionEntity(
        company_id=sample_company.id,
        tier=SubscriptionTier.STARTER.value,
        status=SubscriptionStatus.ACTIVE.value,
        payment_provider=PaymentProvider.STRIPE.value,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        stripe_subscription_id="sub_test123",
    )
    test_db.add(subscription_entity)
    await test_db.commit()
    await test_db.refresh(subscription_entity)
    return Subscription.model_validate(subscription_entity)


@pytest_asyncio.fixture(scope="function")
async def suspended_subscription(test_db: AsyncSession, sample_company):
    """Create a suspended subscription for testing."""
    subscription_entity = SubscriptionEntity(
        company_id=sample_company.id,
        tier=SubscriptionTier.STARTER.value,
        status=SubscriptionStatus.SUSPENDED.value,
        payment_provider=PaymentProvider.STRIPE.value,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        suspended_at=datetime.now(timezone.utc),
    )
    test_db.add(subscription_entity)
    await test_db.commit()
    await test_db.refresh(subscription_entity)
    return Subscription.model_validate(subscription_entity)


@pytest_asyncio.fixture(scope="function")
async def sample_usage_event(test_db: AsyncSession, sample_company, sample_user_entity):
    """Create a sample usage event for testing."""
    usage_event = UsageEventEntity(
        company_id=sample_company.id,
        user_id=sample_user_entity.id,
        event_type=UsageEventType.CELL_OPERATION.value,
        event_metadata={"cell_id": 100, "operation": "create"},
    )
    test_db.add(usage_event)
    await test_db.commit()
    await test_db.refresh(usage_event)
    return usage_event

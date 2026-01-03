"""Unit tests for EntitySetMemberRepository."""

from uuid import uuid4
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from packages.documents.models.database import DocumentEntity
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetMemberEntity,
)
from packages.matrices.models.domain.matrix_enums import EntityType
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixEntitySetMemberCreateModel,
)


class TestEntitySetMemberRepository:
    """Unit tests for EntitySetMemberRepository."""

    @pytest.fixture
    async def member_repo(self, test_db):
        """Create an EntitySetMemberRepository instance."""
        return EntitySetMemberRepository()

    @pytest.fixture(autouse=True)
    def setup_span_mock(self):
        """Set up the span mock to work properly with async methods."""
        mock_span = MagicMock()
        mock_span.__aenter__ = AsyncMock(return_value=mock_span)
        mock_span.__aexit__ = AsyncMock(return_value=None)
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)

        with patch(
            "common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span",
            return_value=mock_span,
        ):
            yield

    @pytest.mark.asyncio
    async def test_get_by_entity_set_id(
        self, member_repo, test_db, sample_entity_set, sample_document, sample_company
    ):
        """Test getting all members of an entity set."""
        # Create members
        members = []
        for i in range(3):
            member = MatrixEntitySetMemberEntity(
                entity_set_id=sample_entity_set.id,
                company_id=sample_company.id,
                entity_type=EntityType.DOCUMENT.value,
                entity_id=sample_document.id,
                member_order=i,
            )
            members.append(member)

        test_db.add_all(members)
        await test_db.commit()

        # Get members
        result = await member_repo.get_by_entity_set_id(sample_entity_set.id)

        assert len(result) == 3
        # Check ordering
        assert result[0].member_order == 0
        assert result[1].member_order == 1
        assert result[2].member_order == 2

    @pytest.mark.asyncio
    async def test_get_member_by_entity_id(self, member_repo, sample_entity_set_member):
        """Test getting a specific member by entity_id."""
        result = await member_repo.get_member_by_entity_id(
            sample_entity_set_member.entity_set_id,
            sample_entity_set_member.entity_id,
            EntityType.DOCUMENT,
        )

        assert result is not None
        assert result.id == sample_entity_set_member.id
        assert result.entity_id == sample_entity_set_member.entity_id

    @pytest.mark.asyncio
    async def test_get_member_by_entity_id_not_found(
        self, member_repo, sample_entity_set
    ):
        """Test getting member that doesn't exist."""
        result = await member_repo.get_member_by_entity_id(
            sample_entity_set.id, 99999, EntityType.DOCUMENT
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add_member(
        self, member_repo, sample_entity_set, sample_document, sample_company
    ):
        """Test adding a new member to an entity set."""
        create_model = MatrixEntitySetMemberCreateModel(
            entity_set_id=sample_entity_set.id,
            company_id=sample_company.id,
            entity_type=EntityType.DOCUMENT,
            entity_id=sample_document.id,
            member_order=0,
        )

        result = await member_repo.add_member(create_model)

        assert result is not None
        assert result.entity_set_id == sample_entity_set.id
        assert result.entity_id == sample_document.id
        assert result.member_order == 0

    @pytest.mark.asyncio
    async def test_add_members_batch(
        self, member_repo, test_db, sample_entity_set, sample_company
    ):
        """Test adding multiple members in a batch."""
        # Create test documents

        documents = []
        for i in range(3):
            doc = DocumentEntity(
                filename=f"test{i}.pdf",
                storage_key=f"key{i}",
                checksum=str(uuid4()),
                company_id=sample_company.id,
            )
            documents.append(doc)

        test_db.add_all(documents)
        await test_db.commit()
        for doc in documents:
            await test_db.refresh(doc)

        # Create batch
        create_models = [
            MatrixEntitySetMemberCreateModel(
                entity_set_id=sample_entity_set.id,
                company_id=sample_company.id,
                entity_type=EntityType.DOCUMENT,
                entity_id=doc.id,
                member_order=i,
            )
            for i, doc in enumerate(documents)
        ]

        result = await member_repo.add_members_batch(create_models)

        assert len(result) == 3
        assert all(m.entity_set_id == sample_entity_set.id for m in result)

    @pytest.mark.asyncio
    async def test_get_member_id_mappings(
        self, member_repo, test_db, sample_entity_set, sample_company
    ):
        """Test getting entity_id -> member_id mappings."""
        # Create test documents and members

        doc_ids = []
        member_ids = []

        for i in range(3):
            doc = DocumentEntity(
                filename=f"test{i}.pdf",
                storage_key=f"key{i}",
                checksum=str(uuid4()),
                company_id=sample_company.id,
            )
            test_db.add(doc)
            await test_db.commit()
            await test_db.refresh(doc)
            doc_ids.append(doc.id)

            member = MatrixEntitySetMemberEntity(
                entity_set_id=sample_entity_set.id,
                company_id=sample_company.id,
                entity_type=EntityType.DOCUMENT.value,
                entity_id=doc.id,
                member_order=i,
            )
            test_db.add(member)
            await test_db.commit()
            await test_db.refresh(member)
            member_ids.append(member.id)

        # Get mappings
        mappings = await member_repo.get_member_id_mappings(sample_entity_set.id)

        assert len(mappings) == 3
        for doc_id, member_id in zip(doc_ids, member_ids):
            assert doc_id in mappings
            assert mappings[doc_id] == member_id

    @pytest.mark.asyncio
    async def test_get_by_member_ids(
        self, member_repo, test_db, sample_entity_set, sample_document, sample_company
    ):
        """Test getting multiple members by their member IDs."""
        # Create members
        members = []
        for i in range(3):
            member = MatrixEntitySetMemberEntity(
                entity_set_id=sample_entity_set.id,
                company_id=sample_company.id,
                entity_type=EntityType.DOCUMENT.value,
                entity_id=sample_document.id,
                member_order=i,
            )
            members.append(member)

        test_db.add_all(members)
        await test_db.commit()
        for m in members:
            await test_db.refresh(m)

        # Get by member IDs
        member_ids = [m.id for m in members]
        result = await member_repo.get_by_member_ids(member_ids)

        assert len(result) == 3
        assert all(r.id in member_ids for r in result)

    @pytest.mark.asyncio
    async def test_get_by_member_ids_empty_list(self, member_repo):
        """Test get_by_member_ids with empty list."""
        result = await member_repo.get_by_member_ids([])
        assert result == []

    @pytest.mark.asyncio
    async def test_company_id_filtering(
        self,
        member_repo,
        test_db,
        sample_entity_set,
        sample_document,
        sample_company,
        second_company,
    ):
        """Test that company_id filtering works correctly."""
        # Create member for first company
        member = MatrixEntitySetMemberEntity(
            entity_set_id=sample_entity_set.id,
            company_id=sample_company.id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=sample_document.id,
            member_order=0,
        )
        test_db.add(member)
        await test_db.commit()

        # Query with correct company_id
        result = await member_repo.get_by_entity_set_id(
            sample_entity_set.id, company_id=sample_company.id
        )
        assert len(result) == 1

        # Query with different company_id
        result = await member_repo.get_by_entity_set_id(
            sample_entity_set.id, company_id=second_company.id
        )
        assert len(result) == 0

import pytest
from sqlalchemy import select, update
from common.db.transaction_utils import transaction, transactional, TransactionMixin
from packages.matrices.models.database.matrix import MatrixCellEntity
from packages.matrices.models.domain.matrix_enums import MatrixCellStatus, CellType


class TestTransactionUtilsRealDB:
    """Real database tests for transaction utilities."""

    @pytest.mark.asyncio
    async def test_transaction_commits_changes(self, test_db):
        """Test that transaction properly commits changes to database."""

        cell_id = None
        # Create a cell within transaction using raw entity
        async with transaction(test_db):
            cell = MatrixCellEntity(
                matrix_id=1,
                company_id=1,
                cell_type=CellType.STANDARD.value,
                status=MatrixCellStatus.PENDING.value,
                cell_signature="test_sig_1",
            )
            test_db.add(cell)
            await test_db.flush()  # Get ID without committing
            cell_id = cell.id

        # Verify it was committed - query outside the transaction
        result = await test_db.execute(
            select(MatrixCellEntity).where(MatrixCellEntity.id == cell_id)
        )
        found_cell = result.scalar_one_or_none()
        assert found_cell is not None
        assert found_cell.matrix_id == 1
        assert found_cell.cell_type == CellType.STANDARD.value

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_exception(self, test_db):
        """Test that transaction rolls back on exception."""

        # Count initial cells
        initial_result = await test_db.execute(select(MatrixCellEntity))
        initial_count = len(initial_result.scalars().all())

        # Try to create a cell but raise exception
        with pytest.raises(ValueError):
            async with transaction(test_db):
                cell = MatrixCellEntity(
                    company_id=1,
                    matrix_id=1,
                    cell_type=CellType.STANDARD.value,
                    status=MatrixCellStatus.PENDING.value,
                    cell_signature="test_sig_2",
                )
                test_db.add(cell)
                raise ValueError("Simulated error")

        # Verify no cell was created due to rollback
        final_result = await test_db.execute(select(MatrixCellEntity))
        final_count = len(final_result.scalars().all())
        assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_nested_transaction_with_savepoint_rollback(self, test_db):
        """Test nested transactions where inner transaction rolls back but outer commits."""

        # Track created cells
        created_cell_id = None

        async with transaction(test_db):
            # Create first cell in outer transaction
            cell1 = MatrixCellEntity(
                matrix_id=1,
                company_id=1,
                cell_type=CellType.STANDARD.value,
                status=MatrixCellStatus.PENDING.value,
                cell_signature="test_sig_3",
            )
            test_db.add(cell1)
            await test_db.flush()
            created_cell_id = cell1.id

            # Inner transaction that will rollback
            try:
                async with transaction(test_db):
                    # Create second cell in nested transaction
                    cell2 = MatrixCellEntity(
                        matrix_id=1,
                        company_id=1,
                        cell_type=CellType.STANDARD.value,
                        status=MatrixCellStatus.PENDING.value,
                        cell_signature="test_sig_4",
                    )
                    test_db.add(cell2)
                    await test_db.flush()
                    # Force rollback of inner transaction
                    raise ValueError("Inner transaction error")
            except ValueError:
                pass  # Inner transaction rolled back

            # Outer transaction continues and commits

        # Verify first cell was committed but second was not
        result = await test_db.execute(
            select(MatrixCellEntity).where(MatrixCellEntity.id == created_cell_id)
        )
        cell1_exists = result.scalar_one_or_none()
        assert cell1_exists is not None

        # Verify only one cell exists with our matrix_id
        all_result = await test_db.execute(
            select(MatrixCellEntity).where(MatrixCellEntity.matrix_id == 1)
        )
        all_cells = all_result.scalars().all()
        assert len(all_cells) == 1
        assert all_cells[0].id == created_cell_id

    @pytest.mark.asyncio
    async def test_transactional_decorator_commits(self, test_db):
        """Test that @transactional decorator properly commits changes."""

        class TestService:
            def __init__(self, db_session):
                self.db_session = db_session

            @transactional
            async def create_cell(self, matrix_id):
                cell = MatrixCellEntity(
                    matrix_id=matrix_id,
                    company_id=1,
                    cell_type=CellType.STANDARD.value,
                    status=MatrixCellStatus.PENDING.value,
                    cell_signature="test_sig_5",
                )
                self.db_session.add(cell)
                await self.db_session.flush()
                return cell.id

        service = TestService(test_db)
        created_cell_id = await service.create_cell(1)

        # Verify it was committed
        result = await test_db.execute(
            select(MatrixCellEntity).where(MatrixCellEntity.id == created_cell_id)
        )
        found_cell = result.scalar_one_or_none()
        assert found_cell is not None
        assert found_cell.matrix_id == 1

    @pytest.mark.asyncio
    async def test_transactional_decorator_rollback(self, test_db):
        """Test that @transactional decorator rolls back on exception."""

        class TestService:
            def __init__(self, db_session):
                self.db_session = db_session

            @transactional
            async def create_cell_with_error(self):
                cell = MatrixCellEntity(
                    matrix_id=1,
                    company_id=1,
                    cell_type=CellType.STANDARD.value,
                    status=MatrixCellStatus.PENDING.value,
                    cell_signature="test_sig_6",
                )
                self.db_session.add(cell)
                await self.db_session.flush()
                raise ValueError("Simulated error")

        service = TestService(test_db)

        # Count initial cells
        initial_result = await test_db.execute(select(MatrixCellEntity))
        initial_count = len(initial_result.scalars().all())

        # Try to create cell but it should rollback
        with pytest.raises(ValueError):
            await service.create_cell_with_error()

        # Verify no new cells were created
        final_result = await test_db.execute(select(MatrixCellEntity))
        final_count = len(final_result.scalars().all())
        assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_transaction_mixin_works(self, test_db):
        """Test that TransactionMixin properly manages transactions."""

        class TestService(TransactionMixin):
            def __init__(self, db_session):
                self.db_session = db_session

            async def create_multiple_cells(self):
                created_ids = []
                async with self.transaction():
                    for i in range(3):
                        cell = MatrixCellEntity(
                            matrix_id=1,
                            company_id=1,
                            cell_type=CellType.STANDARD.value,
                            status=MatrixCellStatus.PENDING.value,
                            cell_signature=f"test_sig_7_{i}",
                        )
                        self.db_session.add(cell)
                        await self.db_session.flush()
                        created_ids.append(cell.id)
                return created_ids

        service = TestService(test_db)
        created_ids = await service.create_multiple_cells()

        # Verify all cells were created
        assert len(created_ids) == 3

        # Verify they're in the database
        for cell_id in created_ids:
            result = await test_db.execute(
                select(MatrixCellEntity).where(MatrixCellEntity.id == cell_id)
            )
            found = result.scalar_one_or_none()
            assert found is not None

    @pytest.mark.asyncio
    async def test_multiple_services_with_nested_transactions(self, test_db):
        """Test multiple services using nested transactions."""

        class ServiceA(TransactionMixin):
            def __init__(self, db_session):
                self.db_session = db_session

            @transactional
            async def create_and_call_b(self, service_b):
                # Create a cell in service A
                cell_a = MatrixCellEntity(
                    matrix_id=1,
                    company_id=1,
                    cell_type=CellType.STANDARD.value,
                    status=MatrixCellStatus.PENDING.value,
                    cell_signature="test_sig_8",
                )
                self.db_session.add(cell_a)
                await self.db_session.flush()

                # Call service B (will be nested transaction)
                cell_b_id = await service_b.create_cell()

                return cell_a.id, cell_b_id

        class ServiceB(TransactionMixin):
            def __init__(self, db_session):
                self.db_session = db_session

            @transactional
            async def create_cell(self):
                cell = MatrixCellEntity(
                    matrix_id=1,
                    company_id=1,
                    cell_type=CellType.CORRELATION.value,
                    status=MatrixCellStatus.PROCESSING.value,
                    cell_signature="test_sig_9",
                )
                self.db_session.add(cell)
                await self.db_session.flush()
                return cell.id

        service_a = ServiceA(test_db)
        service_b = ServiceB(test_db)

        cell_a_id, cell_b_id = await service_a.create_and_call_b(service_b)

        # Verify both cells were created
        result_a = await test_db.execute(
            select(MatrixCellEntity).where(MatrixCellEntity.id == cell_a_id)
        )
        result_b = await test_db.execute(
            select(MatrixCellEntity).where(MatrixCellEntity.id == cell_b_id)
        )

        found_a = result_a.scalar_one_or_none()
        found_b = result_b.scalar_one_or_none()

        assert found_a is not None
        assert found_b is not None
        assert found_a.status == MatrixCellStatus.PENDING.value
        assert found_b.status == MatrixCellStatus.PROCESSING.value

    @pytest.mark.asyncio
    async def test_nested_transaction_isolation(self, test_db):
        """Test that nested transaction failure doesn't affect outer transaction."""

        class TestService(TransactionMixin):
            def __init__(self, db_session):
                self.db_session = db_session

            async def create_with_nested_failure(self):
                created_cell_id = None

                async with self.transaction():
                    # Create cell in outer transaction
                    cell = MatrixCellEntity(
                        matrix_id=1,
                        company_id=1,
                        cell_type=CellType.STANDARD.value,
                        status=MatrixCellStatus.PENDING.value,
                        cell_signature="test_sig_10",
                    )
                    self.db_session.add(cell)
                    await self.db_session.flush()
                    created_cell_id = cell.id

                    # Try nested transaction that fails
                    try:
                        async with self.transaction():
                            # Update the cell
                            await self.db_session.execute(
                                update(MatrixCellEntity)
                                .where(MatrixCellEntity.id == created_cell_id)
                                .values(status=MatrixCellStatus.PROCESSING.value)
                            )
                            # Then fail
                            raise ValueError("Nested failure")
                    except ValueError:
                        pass  # Nested transaction rolled back

                    # Update in outer transaction should still work
                    await self.db_session.execute(
                        update(MatrixCellEntity)
                        .where(MatrixCellEntity.id == created_cell_id)
                        .values(status=MatrixCellStatus.COMPLETED.value)
                    )

                return created_cell_id

        service = TestService(test_db)
        cell_id = await service.create_with_nested_failure()

        # Verify cell was created with final status from outer transaction
        result = await test_db.execute(
            select(MatrixCellEntity).where(MatrixCellEntity.id == cell_id)
        )
        final_cell = result.scalar_one_or_none()
        assert final_cell is not None
        assert final_cell.status == MatrixCellStatus.COMPLETED.value

import pytest

from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork


class FakeSession:
    def __init__(self) -> None:
        self.statements = []
        self.rolled_back = False
        self.closed = False

    def execute(self, statement, params=None):
        self.statements.append(str(statement))

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_read_only_unit_of_work_owns_transaction() -> None:
    session = FakeSession()
    with ReadOnlyUnitOfWork(lambda: session) as unit_of_work:
        assert unit_of_work.sales is not None
        assert unit_of_work.channel_sales is not None
        assert unit_of_work.refunds is not None
        assert unit_of_work.inventory is not None
        assert unit_of_work.customers is not None
        assert unit_of_work.profit is not None

    assert session.statements == ["SET TRANSACTION READ ONLY"]
    assert session.rolled_back is True
    assert session.closed is True


def test_read_only_unit_of_work_rolls_back_after_failure() -> None:
    session = FakeSession()

    with pytest.raises(RuntimeError, match="expected failure"):
        with ReadOnlyUnitOfWork(lambda: session):
            raise RuntimeError("expected failure")

    assert session.rolled_back is True
    assert session.closed is True

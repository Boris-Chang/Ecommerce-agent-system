from pathlib import Path

import pytest
from sqlalchemy import text


pytestmark = [pytest.mark.integration, pytest.mark.data_quality]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUALITY_CHECK_ROOT = PROJECT_ROOT / "db" / "quality_checks"


@pytest.mark.parametrize(
    "sql_path",
    sorted(QUALITY_CHECK_ROOT.glob("*.sql")),
    ids=lambda path: path.stem,
)
def test_quality_check_has_no_violations(database_test_engine, sql_path: Path) -> None:
    with database_test_engine.connect() as connection:
        results = connection.execute(
            text(sql_path.read_text(encoding="utf-8"))
        ).mappings().all()

    assert results, f"{sql_path.name} returned no checks"
    failures = {
        row["check_id"]: row["violation_count"]
        for row in results
        if row["violation_count"] != 0
    }
    assert failures == {}

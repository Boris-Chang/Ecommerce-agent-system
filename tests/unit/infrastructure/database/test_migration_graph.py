from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_business_baseline_is_the_only_migration_head() -> None:
    config = Config(str(PROJECT_ROOT / "db" / "migrations" / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["20260721_0001"]
    baseline = scripts.get_revision("20260721_0001")
    assert baseline is not None
    assert baseline.down_revision is None

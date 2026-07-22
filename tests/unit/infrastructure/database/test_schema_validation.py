import json
from pathlib import Path

from infrastructure.database.schema_validation import (
    assert_contract,
    sha256_file,
    validate_ddl_baseline,
)


def test_ddl_baseline_validation_checks_tables_and_hash(tmp_path: Path) -> None:
    ddl_path = tmp_path / "baseline.sql"
    ddl_path.write_text(
        'CREATE SCHEMA "sales";\nCREATE TABLE "sales"."orders" (id TEXT);\n',
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source_sha256": sha256_file(ddl_path),
                "expected_business_schema_count": 1,
                "expected_business_table_count": 1,
                "business_schemas": {"sales": ["orders"]},
            }
        ),
        encoding="utf-8",
    )

    report = validate_ddl_baseline(ddl_path, manifest_path)

    assert report.matched is True
    assert report.actual_schema_count == 1
    assert report.actual_table_count == 1
    assert_contract(report)

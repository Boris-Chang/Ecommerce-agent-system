from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, text

from core.exceptions import DatabaseContractError
from infrastructure.database.engine import create_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "db" / "baseline_manifest.json"
CREATE_TABLE_RE = re.compile(
    r'^CREATE TABLE\s+"(?P<schema>[^"]+)"\."(?P<table>[^"]+)"',
    re.MULTILINE,
)


@dataclass(frozen=True)
class SchemaContractReport:
    matched: bool
    expected_schema_count: int
    expected_table_count: int
    actual_schema_count: int
    actual_table_count: int
    missing_tables: dict[str, list[str]]
    extra_tables: dict[str, list[str]]
    source_hash_matches: bool | None = None


def load_baseline_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def inspect_ddl_tables(path: Path, schemas: set[str]) -> dict[str, set[str]]:
    ddl = path.read_text(encoding="utf-8")
    result = {schema: set() for schema in schemas}
    for match in CREATE_TABLE_RE.finditer(ddl):
        schema = match.group("schema")
        if schema in result:
            result[schema].add(match.group("table"))
    return result


def inspect_live_tables(engine: Engine, schemas: set[str]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    with engine.connect() as connection:
        for schema in sorted(schemas):
            rows = connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = :schema
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                ),
                {"schema": schema},
            ).scalars()
            result[schema] = set(rows)
    return result


def compare_schema_contract(
    actual: dict[str, set[str]],
    manifest: dict,
    *,
    source_hash_matches: bool | None = None,
) -> SchemaContractReport:
    expected = {
        schema: set(tables)
        for schema, tables in manifest["business_schemas"].items()
    }
    missing = {
        schema: sorted(expected[schema] - actual.get(schema, set()))
        for schema in expected
        if expected[schema] - actual.get(schema, set())
    }
    extra = {
        schema: sorted(actual.get(schema, set()) - expected[schema])
        for schema in expected
        if actual.get(schema, set()) - expected[schema]
    }
    actual_table_count = sum(len(actual.get(schema, set())) for schema in expected)
    matched = not missing and not extra and source_hash_matches is not False
    return SchemaContractReport(
        matched=matched,
        expected_schema_count=manifest["expected_business_schema_count"],
        expected_table_count=manifest["expected_business_table_count"],
        actual_schema_count=sum(bool(actual.get(schema)) for schema in expected),
        actual_table_count=actual_table_count,
        missing_tables=missing,
        extra_tables=extra,
        source_hash_matches=source_hash_matches,
    )


def validate_ddl_baseline(
    ddl_path: Path,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> SchemaContractReport:
    manifest = load_baseline_manifest(manifest_path)
    schemas = set(manifest["business_schemas"])
    actual = inspect_ddl_tables(ddl_path, schemas)
    return compare_schema_contract(
        actual,
        manifest,
        source_hash_matches=(
            sha256_file(ddl_path) == manifest["source_sha256"].upper()
        ),
    )


def validate_live_database(
    engine: Engine,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> SchemaContractReport:
    manifest = load_baseline_manifest(manifest_path)
    schemas = set(manifest["business_schemas"])
    return compare_schema_contract(inspect_live_tables(engine, schemas), manifest)


def assert_contract(report: SchemaContractReport) -> None:
    if not report.matched:
        raise DatabaseContractError(
            "Database schema does not match the approved baseline: "
            f"missing={report.missing_tables}, extra={report.extra_tables}, "
            f"source_hash_matches={report.source_hash_matches}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the approved 12-schema PostgreSQL baseline without writes."
    )
    parser.add_argument("--ddl", type=Path, help="Validate a local SQL DDL file.")
    parser.add_argument(
        "--database",
        action="store_true",
        help="Validate the live DATABASE_URL using read-only queries.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
    )
    args = parser.parse_args()

    if not args.ddl and not args.database:
        parser.error("provide --ddl and/or --database")

    reports = []
    if args.ddl:
        reports.append(validate_ddl_baseline(args.ddl, args.manifest))
    if args.database:
        reports.append(validate_live_database(create_database_engine(), args.manifest))

    for report in reports:
        print(json.dumps(report.__dict__, ensure_ascii=False, indent=2))
        assert_contract(report)


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url

from core.exceptions import DatabaseConfigurationError, DatabaseContractError


BUSINESS_SCHEMAS = (
    "mdm",
    "catalog",
    "crm",
    "sales",
    "inventory",
    "procurement",
    "logistics",
    "finance",
    "marketing",
    "planning",
    "integration",
    "analytics",
)


@dataclass(frozen=True)
class SchemaDumpComparison:
    matched: bool
    reference_sha256: str
    database_sha256: str


def _pg_environment(url: URL) -> dict[str, str]:
    if url.get_backend_name() != "postgresql":
        raise DatabaseConfigurationError("Schema comparison requires PostgreSQL URLs.")
    if not url.host or not url.database or not url.username:
        raise DatabaseConfigurationError(
            "PostgreSQL URL must include host, database, and username."
        )

    environment = os.environ.copy()
    if url.password:
        environment["PGPASSWORD"] = url.password
    if sslmode := url.query.get("sslmode"):
        environment["PGSSLMODE"] = sslmode
    return environment


def dump_business_schema(database_url: str, pg_dump_path: str = "pg_dump") -> str:
    """Read a schema-only dump of the 12 business schemas without DB writes."""
    url = make_url(database_url)
    command = [
        pg_dump_path,
        "--schema-only",
        "--no-owner",
        "--no-privileges",
        "--host",
        url.host,
        "--port",
        str(url.port or 5432),
        "--username",
        url.username,
        "--dbname",
        url.database,
    ]
    for schema in BUSINESS_SCHEMAS:
        command.extend(["--schema", schema])

    completed = subprocess.run(
        command,
        env=_pg_environment(url),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "pg_dump schema inspection failed: " + completed.stderr.strip()
        )
    return completed.stdout


def canonicalize_schema_dump(value: str) -> str:
    """Remove pg_dump metadata that is unrelated to database structure."""
    lines = []
    for raw_line in value.replace("\r\n", "\n").splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("--"):
            continue
        if line.startswith("\\restrict") or line.startswith("\\unrestrict"):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def compare_database_schemas(
    reference_url: str,
    database_url: str,
    *,
    pg_dump_path: str = "pg_dump",
) -> SchemaDumpComparison:
    reference = canonicalize_schema_dump(
        dump_business_schema(reference_url, pg_dump_path)
    )
    database = canonicalize_schema_dump(
        dump_business_schema(database_url, pg_dump_path)
    )
    reference_hash = _sha256(reference)
    database_hash = _sha256(database)
    return SchemaDumpComparison(
        matched=reference_hash == database_hash,
        reference_sha256=reference_hash,
        database_sha256=database_hash,
    )


def main() -> None:
    load_dotenv()
    reference_url = os.getenv("DATABASE_REFERENCE_URL")
    database_url = os.getenv("DATABASE_URL")
    pg_dump_path = os.getenv("PG_DUMP_PATH", "pg_dump")

    if not reference_url or not database_url:
        raise SystemExit(
            "DATABASE_REFERENCE_URL and DATABASE_URL are required for exact comparison."
        )

    comparison = compare_database_schemas(
        reference_url,
        database_url,
        pg_dump_path=pg_dump_path,
    )
    print(
        f"matched={comparison.matched}\n"
        f"reference_sha256={comparison.reference_sha256}\n"
        f"database_sha256={comparison.database_sha256}"
    )
    if not comparison.matched:
        raise DatabaseContractError(
            "Live database structure differs from the approved reference database."
        )


if __name__ == "__main__":
    main()

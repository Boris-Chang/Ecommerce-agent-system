from infrastructure.database import schema_dump_validation as validation


def test_canonicalize_schema_dump_removes_volatile_metadata() -> None:
    first = """
-- Dumped from database version 17
\\restrict random-one
CREATE TABLE sales.orders (id text);
\\unrestrict random-one
"""
    second = """
-- Dumped by pg_dump version 17
\\restrict random-two
CREATE TABLE sales.orders (id text);
\\unrestrict random-two
"""

    assert validation.canonicalize_schema_dump(first) == (
        validation.canonicalize_schema_dump(second)
    )


def test_compare_database_schemas_uses_same_business_scope(monkeypatch) -> None:
    calls = []

    def fake_dump(url: str, path: str) -> str:
        calls.append((url, path))
        return "CREATE TABLE sales.orders (id text);\n"

    monkeypatch.setattr(validation, "dump_business_schema", fake_dump)

    comparison = validation.compare_database_schemas(
        "postgresql+psycopg://ref:secret@localhost/reference",
        "postgresql+psycopg://app:secret@localhost/live",
        pg_dump_path="pg_dump.exe",
    )

    assert comparison.matched is True
    assert calls == [
        (
            "postgresql+psycopg://ref:secret@localhost/reference",
            "pg_dump.exe",
        ),
        (
            "postgresql+psycopg://app:secret@localhost/live",
            "pg_dump.exe",
        ),
    ]

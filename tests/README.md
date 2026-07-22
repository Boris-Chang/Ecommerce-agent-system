# Test architecture

Tests are a peer engineering concern beside `src/` and `db/`; they are not a
production runtime layer. Agent-specific tests remain out of this restructuring.

## Test groups

- `unit/`: deterministic logic with no PostgreSQL, Shopify, or model calls.
- `integration/database/`: real SQL and Repository checks against an isolated
  PostgreSQL database.
- `contract/shopify/`: local, versioned Shopify payload fixtures and error mapping.
- `data_quality/`: pytest wrappers around read-only SQL in `db/quality_checks/`.
- `architecture/`: source dependency direction and transaction-ownership rules.
- `fixtures/`: sanitized external-interface samples.

The `analytics.v_*` objects are v0.2 snapshot tables, not SQL views.

## Commands

Fast, external-service-free checks:

```powershell
.\.venv\Scripts\python -m pytest -m "not integration and not shopify_live"
```

Database integration and deterministic data-quality checks require an isolated
database whose name ends in `_test`:

```powershell
$env:DATABASE_TEST_URL="postgresql+psycopg://coolcool_app_test:password@localhost:5432/coolcool_erp_test"
.\.venv\Scripts\python -m pytest -m integration
```

`DATABASE_TEST_ADMIN_URL` is reserved for future disposable-database provisioning
and migration tests. Current tests never use it and never stamp or upgrade a DB.

Mock contract tests do not prove that Shopify's live API has not changed. A
separate, explicitly selected `shopify_live` job should be added when a dedicated
read-only test store is available.

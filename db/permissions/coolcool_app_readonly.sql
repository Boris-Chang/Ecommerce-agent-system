-- Review and execute manually as a database administrator.
-- This script changes role privileges, never business data.
-- The agent schema is intentionally outside this implementation round.

\set ON_ERROR_STOP on

BEGIN;

ALTER ROLE coolcool_app SET default_transaction_read_only = on;
GRANT CONNECT ON DATABASE coolcool_erp TO coolcool_app;
REVOKE CREATE ON SCHEMA public FROM coolcool_app;

GRANT USAGE ON SCHEMA
    mdm,
    catalog,
    crm,
    sales,
    inventory,
    procurement,
    logistics,
    finance,
    marketing,
    planning,
    integration,
    analytics
TO coolcool_app;

GRANT SELECT ON ALL TABLES IN SCHEMA
    mdm,
    catalog,
    crm,
    sales,
    inventory,
    procurement,
    logistics,
    finance,
    marketing,
    planning,
    integration,
    analytics
TO coolcool_app;

COMMIT;

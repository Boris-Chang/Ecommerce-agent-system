# Bootstrap source

The approved candidate source is `coolcool_erp_v0.2_full.sql`, generated on
2026-07-20 with SHA-256:

`492F5B225319A721CFA35E3BF7932D7A7568837088E4B230469B67F4705D18AB`

The source contains 13 schemas and 81 tables. This implementation round covers
only the 12 business schemas and 77 business tables recorded in
`db/baseline_manifest.json`; the four `agent` tables are explicitly excluded.

The full SQL also contains seed data, so it is not copied into Alembic and must
not be executed against an existing database. Use the schema validation module
before stamping any database.

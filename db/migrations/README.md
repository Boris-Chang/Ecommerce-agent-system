# Database migrations

Alembic is rooted in `db/migrations/`. The initial revision is a no-op marker;
it does not create, alter, or seed the existing business schemas.

Before stamping an existing database:

1. Configure the read-only `DATABASE_URL`.
2. Run the live table contract validator:

   ```powershell
   .\.venv\Scripts\python -m infrastructure.database.schema_validation --database
   ```

3. Build a disposable reference database from the approved bootstrap SQL. Never
   load that SQL into the existing database.
4. Configure `DATABASE_REFERENCE_URL` with a read-only connection to the
   reference database, then run the exact schema-only comparison:

   ```powershell
   .\.venv\Scripts\python -m infrastructure.database.schema_dump_validation
   ```

5. Continue only when both validators report `matched: true`. The second gate
   compares canonical `pg_dump --schema-only` output for all 12 business schemas,
   including columns, constraints, indexes, sequences, functions, and comments.
6. Configure the privileged `DATABASE_MIGRATION_URL` separately.
7. Stamp the baseline manually:

   ```powershell
   .\.venv\Scripts\alembic -c db\migrations\alembic.ini stamp 20260721_0001
   ```

No stamp or migration command is run automatically by the application.

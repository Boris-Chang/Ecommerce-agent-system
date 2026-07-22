# SQL data-quality checks

This directory is the single source for reusable, read-only SQL data-quality
rules. Each query returns `check_id` and `violation_count`; zero means that the
rule passed.

`tests/data_quality/` executes these rules against an isolated PostgreSQL test
database and asserts deterministic results. Running the same SQL against a
development or production database is an operational monitoring concern and
must not be mixed into the default pytest job.

The current rules cover relationships that are clear in baseline v0.2. Business
formula checks for sales, refunds, inventory movement, currency conversion, and
profit are deferred until their semantic definitions are approved.

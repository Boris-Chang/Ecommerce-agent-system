# Database permissions

`coolcool_app_readonly.sql` is a DBA-reviewed template. It grants the application
account only `CONNECT`, schema `USAGE`, and table `SELECT` across the 12 business
schemas, and sets `default_transaction_read_only=on`.

The script has not been executed by this project. Future tables require matching
default privileges to be granted by each owning role; those owner-specific
commands are intentionally not guessed here.

`coolcool_app_sample_writer.sql` is a separate, opt-in grant for the controlled
sample-data writer. It does not grant DELETE, DDL, or unrestricted writes. The
normal Web engine and `ReadOnlyUnitOfWork` continue to force read-only
transactions; the seed runner must explicitly open a read-write session.

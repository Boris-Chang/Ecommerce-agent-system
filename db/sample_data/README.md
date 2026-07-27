# Targeted sample-data extensions

These scripts add explicitly labelled development samples to an existing
business database. They are not schema migrations and must not run under the
read-only `coolcool_app` role.

## Complete order chain through 2026-07-27

`seed_complete_order_chain_to_20260727.sql` copies the normal sales profile from
2026-06-15 through 2026-06-29 forward by 28 days. The shift preserves weekday,
channel, SKU, price and discount patterns while avoiding the known July 3
outlier.

The script:

- creates 116 orders and order lines covering 2026-07-13 through 2026-07-27;
- creates anonymized `.invalid` customers, identities and addresses;
- creates captured payments, payment transactions and discount allocations;
- creates inventory shipments for fulfilled orders and reservations for open
  orders, then updates inventory balances;
- adds 106 sales snapshot rows and refreshes affected customer-LTV and inventory
  cover snapshots;
- preserves the existing Shopify/Amazon mix;
- labels every new row `derived_sample_extension_20260727`;
- uses deterministic IDs and refuses to run when the batch already exists;
- rolls back unless order, line, unit, snapshot, customer and inventory checks
  pass.

Run with a dedicated maintenance connection:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" `
  "$env:DATABASE_SEED_URL" `
  -v ON_ERROR_STOP=1 `
  -f "db\sample_data\seed_complete_order_chain_to_20260727.sql"
```

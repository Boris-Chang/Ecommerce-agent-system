-- Minimum write privileges for the controlled sample-data writer.
--
-- Run as postgres (or the owning DBA role). The normal Web application still
-- opens read-only sessions and ReadOnlyUnitOfWork transactions.

GRANT INSERT, UPDATE ON TABLE
    crm.customers
TO coolcool_app;
GRANT INSERT ON TABLE
    crm.customer_identities,
    crm.customer_addresses,
    sales.orders,
    sales.order_lines,
    sales.order_discounts,
    sales.discount_allocations,
    sales.payments,
    sales.payment_transactions,
    inventory.inventory_movements,
    inventory.inventory_reservations
TO coolcool_app;

GRANT INSERT, UPDATE ON TABLE
    inventory.inventory_balances,
    analytics.v_sku_daily_sales,
    analytics.v_customer_ltv,
    analytics.v_inventory_cover
TO coolcool_app;

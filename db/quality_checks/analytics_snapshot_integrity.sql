-- The analytics.v_* objects are snapshot tables in baseline v0.2, not views.

SELECT
    'analytics.v_sku_daily_sales.sku_id' AS check_id,
    COUNT(*)::bigint AS violation_count
FROM analytics.v_sku_daily_sales AS snapshot
LEFT JOIN catalog.skus AS sku ON sku.sku_id = snapshot.sku_id
WHERE sku.sku_id IS NULL

UNION ALL

SELECT
    'analytics.v_inventory_cover.sku_id' AS check_id,
    COUNT(*)::bigint AS violation_count
FROM analytics.v_inventory_cover AS snapshot
LEFT JOIN catalog.skus AS sku ON sku.sku_id = snapshot.sku_id
WHERE sku.sku_id IS NULL

UNION ALL

SELECT
    'analytics.v_inventory_cover.warehouse_id' AS check_id,
    COUNT(*)::bigint AS violation_count
FROM analytics.v_inventory_cover AS snapshot
LEFT JOIN inventory.warehouses AS warehouse
    ON warehouse.warehouse_id = snapshot.warehouse_id
WHERE warehouse.warehouse_id IS NULL;

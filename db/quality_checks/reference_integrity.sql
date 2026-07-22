-- Read-only operational data-quality checks for relationships that are not yet
-- enforced with foreign keys. Every row returns the number of violations.

SELECT
    'sales.order_lines.order_id' AS check_id,
    COUNT(*)::bigint AS violation_count
FROM sales.order_lines AS child
LEFT JOIN sales.orders AS parent ON parent.order_id = child.order_id
WHERE child.order_id IS NOT NULL AND parent.order_id IS NULL

UNION ALL

SELECT
    'sales.order_lines.sku_id' AS check_id,
    COUNT(*)::bigint AS violation_count
FROM sales.order_lines AS child
LEFT JOIN catalog.skus AS parent ON parent.sku_id = child.sku_id
WHERE child.sku_id IS NOT NULL AND parent.sku_id IS NULL

UNION ALL

SELECT
    'sales.order_lines.listing_id' AS check_id,
    COUNT(*)::bigint AS violation_count
FROM sales.order_lines AS child
LEFT JOIN catalog.channel_listings AS parent
    ON parent.listing_id = child.listing_id
WHERE child.listing_id IS NOT NULL AND parent.listing_id IS NULL

UNION ALL

SELECT
    'catalog.channel_listings.sku_id' AS check_id,
    COUNT(*)::bigint AS violation_count
FROM catalog.channel_listings AS child
LEFT JOIN catalog.skus AS parent ON parent.sku_id = child.sku_id
WHERE child.sku_id IS NOT NULL AND parent.sku_id IS NULL

UNION ALL

SELECT
    'inventory.inventory_balances.sku_id' AS check_id,
    COUNT(*)::bigint AS violation_count
FROM inventory.inventory_balances AS child
LEFT JOIN catalog.skus AS parent ON parent.sku_id = child.sku_id
WHERE parent.sku_id IS NULL;

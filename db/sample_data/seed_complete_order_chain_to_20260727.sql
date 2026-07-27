-- Build a complete, internally consistent sample order chain through 2026-07-27.
--
-- The normal profile from 2026-06-15 through 2026-06-29 is shifted by
-- 28 days. Zero-unit rows and the known "null" SKU outlier are excluded.
--
-- Expected facts:
--   target dates: 2026-07-13 through 2026-07-27
--   orders:       116
--   order lines:  116
--   units:        136
--   sales rows:   106
--
-- Run only after coolcool_app_sample_writer.sql has been applied by the DBA.

\set ON_ERROR_STOP on

SET default_transaction_read_only = off;

BEGIN;
SET TRANSACTION READ WRITE;
SET CONSTRAINTS ALL DEFERRED;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sales.orders
        WHERE data_origin = 'derived_sample_extension_20260727'
    ) THEN
        RAISE EXCEPTION
            'sample batch derived_sample_extension_20260727 already exists';
    END IF;
END
$$;

CREATE TEMP TABLE seed_sales_profile ON COMMIT DROP AS
SELECT
    source.sales_date + 28 AS sales_date,
    source.sku_id,
    source.channel_account_id,
    LEAST(source.orders_count, source.units_sold) AS orders_count,
    source.units_sold,
    source.gross_sales,
    source.discount_amount,
    source.net_sales,
    source.currency_code
FROM analytics.v_sku_daily_sales AS source
WHERE source.sales_date BETWEEN DATE '2026-06-15' AND DATE '2026-06-29'
  AND source.sku_id <> 'null'
  AND source.units_sold > 0
  AND source.orders_count > 0;

DO $$
DECLARE
    profile_rows integer;
    profile_orders integer;
    profile_units integer;
BEGIN
    SELECT count(*), sum(orders_count), sum(units_sold)
    INTO profile_rows, profile_orders, profile_units
    FROM seed_sales_profile;

    IF (profile_rows, profile_orders, profile_units) <> (106, 116, 136) THEN
        RAISE EXCEPTION
            'unexpected source profile: rows %, orders %, units %',
            profile_rows,
            profile_orders,
            profile_units;
    END IF;
END
$$;

CREATE TEMP TABLE seed_order_parts ON COMMIT DROP AS
SELECT
    profile.*,
    part.order_sequence,
    (
        profile.units_sold / profile.orders_count
        + CASE
            WHEN part.order_sequence
                <= profile.units_sold % profile.orders_count
            THEN 1
            ELSE 0
          END
    )::integer AS quantity,
    format(
        'SMP-20260727-O-%s-%s-%s-%s',
        CASE
            WHEN profile.channel_account_id = 'CA_SHOPIFY_US'
            THEN 'SHP'
            ELSE 'AMZ'
        END,
        to_char(profile.sales_date, 'YYYYMMDD'),
        profile.sku_id,
        lpad(part.order_sequence::text, 2, '0')
    ) AS order_id
FROM seed_sales_profile AS profile
CROSS JOIN LATERAL generate_series(
    1,
    profile.orders_count
) AS part(order_sequence);

CREATE TEMP TABLE seed_orders ON COMMIT DROP AS
SELECT
    part.*,
    format(
        'SMP-20260727-C-%s-%s',
        CASE
            WHEN part.channel_account_id = 'CA_SHOPIFY_US'
            THEN 'SHP'
            ELSE 'AMZ'
        END,
        lpad(
            (
                1 + mod(
                    abs(hashtextextended(part.order_id, 20260727)),
                    CASE
                        WHEN part.channel_account_id = 'CA_SHOPIFY_US'
                        THEN 32
                        ELSE 16
                    END
                )
            )::text,
            2,
            '0'
        )
    ) AS customer_id,
    (
        part.sales_date::timestamp
        + time '10:00'
        + (
            mod(abs(hashtextextended(part.order_id, 17)), 600)
            * interval '1 minute'
        )
    ) AT TIME ZONE 'Asia/Shanghai' AS ordered_at,
    round(
        part.gross_sales * part.quantity / part.units_sold,
        2
    ) AS line_gross_amount,
    round(
        part.discount_amount * part.quantity / part.units_sold,
        2
    ) AS line_discount_amount
FROM seed_order_parts AS part;

ALTER TABLE seed_orders
ADD COLUMN line_net_amount numeric;

UPDATE seed_orders
SET line_net_amount = line_gross_amount - line_discount_amount;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM seed_orders AS sample
        LEFT JOIN catalog.channel_listings AS listing
          ON listing.channel_account_id = sample.channel_account_id
         AND listing.sku_id = sample.sku_id
        WHERE listing.listing_id IS NULL
    ) THEN
        RAISE EXCEPTION 'one or more sample SKUs lack channel listings';
    END IF;
END
$$;

INSERT INTO crm.customers (
    customer_id,
    customer_name,
    email_normalized,
    phone_normalized,
    first_order_at,
    last_order_at,
    lifetime_orders,
    lifetime_spend_usd,
    customer_status,
    created_at,
    data_origin
)
SELECT
    customer_id,
    'Sample Customer ' || right(customer_id, 6),
    lower(customer_id) || '@example.invalid',
    NULL,
    min(ordered_at),
    max(ordered_at),
    count(*),
    round(sum(line_net_amount), 2),
    'active',
    min(ordered_at) - interval '1 day',
    'derived_sample_extension_20260727'
FROM seed_orders
GROUP BY customer_id;

INSERT INTO crm.customer_identities (
    customer_identity_id,
    customer_id,
    channel_account_id,
    external_customer_id,
    email,
    identity_type,
    match_confidence,
    data_origin
)
SELECT
    replace(customer_id, '-C-', '-CI-'),
    customer_id,
    min(channel_account_id),
    'sample://' || customer_id,
    lower(customer_id) || '@example.invalid',
    CASE
        WHEN min(channel_account_id) = 'CA_SHOPIFY_US'
        THEN 'shopify_customer'
        ELSE 'amazon_buyer_alias'
    END,
    1,
    'derived_sample_extension_20260727'
FROM seed_orders
GROUP BY customer_id;

INSERT INTO crm.customer_addresses (
    address_id,
    customer_id,
    address_type,
    country_code,
    province,
    city,
    postal_code,
    address_line1,
    address_line2,
    is_default,
    data_origin
)
SELECT DISTINCT
    replace(customer_id, '-C-', '-A-'),
    customer_id,
    'shipping',
    'US',
    CASE mod(right(customer_id, 2)::integer, 4)
        WHEN 0 THEN 'CA'
        WHEN 1 THEN 'TX'
        WHEN 2 THEN 'WA'
        ELSE 'CO'
    END,
    CASE mod(right(customer_id, 2)::integer, 4)
        WHEN 0 THEN 'Los Angeles'
        WHEN 1 THEN 'Austin'
        WHEN 2 THEN 'Seattle'
        ELSE 'Denver'
    END,
    '00000',
    (100 + right(customer_id, 2)::integer)::text
        || ' Sample Data Way',
    NULL,
    true,
    'derived_sample_extension_20260727'
FROM seed_orders;

INSERT INTO sales.orders (
    order_id,
    channel_account_id,
    external_order_id,
    order_number,
    customer_id,
    order_currency,
    base_currency,
    exchange_rate,
    order_status,
    payment_status,
    fulfillment_status,
    ordered_at,
    cancelled_at,
    subtotal_amount,
    discount_amount,
    shipping_amount,
    tax_amount,
    refund_amount,
    total_amount,
    base_total_amount,
    ship_country,
    ship_region,
    ship_city,
    tags,
    data_origin
)
SELECT
    order_id,
    channel_account_id,
    'sample://' || order_id,
    'SAMPLE-' || right(order_id, 20),
    customer_id,
    currency_code,
    'USD',
    1,
    'confirmed',
    'paid',
    CASE
        WHEN sales_date >= DATE '2026-07-25'
        THEN 'unfulfilled'
        WHEN channel_account_id = 'CA_SHOPIFY_US'
        THEN 'fulfilled'
        WHEN sales_date >= DATE '2026-07-21'
        THEN 'shipped'
        ELSE 'delivered'
    END,
    ordered_at,
    NULL,
    line_gross_amount,
    line_discount_amount,
    0,
    0,
    0,
    line_net_amount,
    line_net_amount,
    'US',
    CASE mod(right(customer_id, 2)::integer, 4)
        WHEN 0 THEN 'CA'
        WHEN 1 THEN 'TX'
        WHEN 2 THEN 'WA'
        ELSE 'CO'
    END,
    CASE mod(right(customer_id, 2)::integer, 4)
        WHEN 0 THEN 'Los Angeles'
        WHEN 1 THEN 'Austin'
        WHEN 2 THEN 'Seattle'
        ELSE 'Denver'
    END,
    'sample,batch_20260727,do_not_sync_production',
    'derived_sample_extension_20260727'
FROM seed_orders;

INSERT INTO sales.order_lines (
    order_line_id,
    order_id,
    sku_id,
    listing_id,
    external_line_id,
    seller_sku,
    product_title,
    variant_title,
    quantity,
    unit_price,
    gross_amount,
    discount_amount,
    tax_amount,
    net_amount,
    data_origin
)
SELECT
    replace(sample.order_id, '-O-', '-OL-'),
    sample.order_id,
    sample.sku_id,
    listing.listing_id,
    'sample-line://' || sample.order_id,
    listing.seller_sku,
    listing.listing_title,
    variant.variant_title,
    sample.quantity,
    round(sample.line_gross_amount / sample.quantity, 2),
    sample.line_gross_amount,
    sample.line_discount_amount,
    0,
    sample.line_net_amount,
    'derived_sample_extension_20260727'
FROM seed_orders AS sample
JOIN catalog.channel_listings AS listing
  ON listing.channel_account_id = sample.channel_account_id
 AND listing.sku_id = sample.sku_id
JOIN catalog.skus AS sku
  ON sku.sku_id = sample.sku_id
LEFT JOIN catalog.product_variants AS variant
  ON variant.variant_id = sku.variant_id;

INSERT INTO sales.order_discounts (
    discount_id,
    order_id,
    discount_code,
    discount_type,
    discount_value,
    discount_amount,
    description,
    data_origin
)
SELECT
    replace(order_id, '-O-', '-D-'),
    order_id,
    'SAMPLE10',
    'fixed_amount',
    line_discount_amount,
    line_discount_amount,
    'Derived sample promotion',
    'derived_sample_extension_20260727'
FROM seed_orders
WHERE line_discount_amount > 0;

INSERT INTO sales.discount_allocations (
    discount_allocation_id,
    discount_id,
    order_line_id,
    allocated_amount,
    data_origin
)
SELECT
    replace(order_id, '-O-', '-DA-'),
    replace(order_id, '-O-', '-D-'),
    replace(order_id, '-O-', '-OL-'),
    line_discount_amount,
    'derived_sample_extension_20260727'
FROM seed_orders
WHERE line_discount_amount > 0;

INSERT INTO sales.payments (
    payment_id,
    order_id,
    payment_provider,
    payment_status,
    currency_code,
    authorized_amount,
    captured_amount,
    paid_at,
    data_origin
)
SELECT
    replace(order_id, '-O-', '-P-'),
    order_id,
    CASE
        WHEN channel_account_id = 'CA_SHOPIFY_US'
        THEN 'shopify_payments_sample'
        ELSE 'amazon_payments_sample'
    END,
    'paid',
    currency_code,
    line_net_amount,
    line_net_amount,
    ordered_at + interval '2 minutes',
    'derived_sample_extension_20260727'
FROM seed_orders;

INSERT INTO sales.payment_transactions (
    transaction_id,
    payment_id,
    transaction_type,
    external_transaction_id,
    amount,
    currency_code,
    transaction_at,
    status,
    data_origin
)
SELECT
    replace(order_id, '-O-', '-PT-'),
    replace(order_id, '-O-', '-P-'),
    'capture',
    'sample-transaction://' || order_id,
    line_net_amount,
    currency_code,
    ordered_at + interval '2 minutes',
    'succeeded',
    'derived_sample_extension_20260727'
FROM seed_orders;

CREATE TEMP TABLE seed_inventory_effect ON COMMIT DROP AS
SELECT
    sample.order_id,
    replace(sample.order_id, '-O-', '-OL-') AS order_line_id,
    sample.sku_id,
    CASE
        WHEN sample.channel_account_id = 'CA_AMAZON_US'
        THEN 'WH_AMZ_FBA'
        WHEN sample.sku_id = 'SKU0008'
        THEN 'WH_CN_FACTORY'
        ELSE 'WH_US_3PL'
    END AS warehouse_id,
    sample.quantity,
    sample.ordered_at,
    sample.sales_date >= DATE '2026-07-25' AS is_reserved
FROM seed_orders AS sample;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (
            SELECT
                warehouse_id,
                sku_id,
                sum(quantity) AS required_qty
            FROM seed_inventory_effect
            GROUP BY warehouse_id, sku_id
        ) AS required
        LEFT JOIN inventory.inventory_balances AS balance
          ON balance.warehouse_id = required.warehouse_id
         AND balance.sku_id = required.sku_id
        WHERE balance.sku_id IS NULL
           OR balance.available_qty < required.required_qty
    ) THEN
        RAISE EXCEPTION 'insufficient inventory for generated sample orders';
    END IF;
END
$$;

INSERT INTO inventory.inventory_movements (
    movement_id,
    sku_id,
    warehouse_id,
    movement_type,
    quantity_delta,
    reference_type,
    reference_id,
    occurred_at,
    created_at,
    data_origin
)
SELECT
    replace(order_id, '-O-', '-IM-'),
    sku_id,
    warehouse_id,
    'sales_shipment',
    -quantity,
    'sales_order',
    order_id,
    ordered_at + interval '1 day',
    ordered_at + interval '1 day',
    'derived_sample_extension_20260727'
FROM seed_inventory_effect
WHERE NOT is_reserved;

INSERT INTO inventory.inventory_reservations (
    reservation_id,
    order_line_id,
    warehouse_id,
    sku_id,
    reserved_qty,
    reservation_status,
    reserved_at,
    released_at,
    data_origin
)
SELECT
    replace(order_id, '-O-', '-IR-'),
    order_line_id,
    warehouse_id,
    sku_id,
    quantity,
    'active',
    ordered_at,
    NULL,
    'derived_sample_extension_20260727'
FROM seed_inventory_effect
WHERE is_reserved;

WITH effect AS (
    SELECT
        warehouse_id,
        sku_id,
        sum(quantity) FILTER (WHERE NOT is_reserved)::integer AS shipped_qty,
        sum(quantity) FILTER (WHERE is_reserved)::integer AS reserved_qty
    FROM seed_inventory_effect
    GROUP BY warehouse_id, sku_id
)
UPDATE inventory.inventory_balances AS balance
SET
    on_hand_qty = balance.on_hand_qty - coalesce(effect.shipped_qty, 0),
    reserved_qty = balance.reserved_qty + coalesce(effect.reserved_qty, 0),
    available_qty = (
        balance.available_qty
        - coalesce(effect.shipped_qty, 0)
        - coalesce(effect.reserved_qty, 0)
    ),
    updated_at = TIMESTAMPTZ '2026-07-27 23:59:00+08'
FROM effect
WHERE balance.warehouse_id = effect.warehouse_id
  AND balance.sku_id = effect.sku_id;

INSERT INTO analytics.v_sku_daily_sales (
    sales_date,
    sku_id,
    channel_account_id,
    orders_count,
    units_sold,
    gross_sales,
    discount_amount,
    net_sales,
    currency_code,
    data_origin
)
SELECT
    sales_date,
    sku_id,
    channel_account_id,
    count(DISTINCT order_id),
    sum(quantity),
    round(sum(line_gross_amount), 2),
    round(sum(line_discount_amount), 2),
    round(sum(line_net_amount), 2),
    min(currency_code),
    'derived_sample_extension_20260727'
FROM seed_orders
GROUP BY sales_date, sku_id, channel_account_id;

INSERT INTO analytics.v_customer_ltv (
    customer_id,
    first_order_at,
    last_order_at,
    order_count,
    net_revenue,
    estimated_contribution_profit,
    avg_order_value,
    repeat_customer,
    ltv_segment,
    currency_code,
    data_origin
)
SELECT
    customer_id,
    min(ordered_at),
    max(ordered_at),
    count(*),
    round(sum(line_net_amount), 2),
    round(sum(line_net_amount) * 0.35, 2),
    round(avg(line_net_amount), 2),
    count(*) > 1,
    CASE
        WHEN sum(line_net_amount) >= 200 THEN 'high'
        WHEN sum(line_net_amount) >= 80 THEN 'medium'
        ELSE 'low'
    END,
    'USD',
    'derived_sample_extension_20260727'
FROM seed_orders
GROUP BY customer_id;

WITH affected AS (
    SELECT DISTINCT warehouse_id, sku_id
    FROM seed_inventory_effect
)
UPDATE analytics.v_inventory_cover AS cover
SET
    available_qty = balance.available_qty,
    incoming_qty = balance.incoming_qty,
    inventory_cover_days = CASE
        WHEN cover.forecast_daily_units > 0
        THEN floor(
            (balance.available_qty + balance.incoming_qty)
            / cover.forecast_daily_units
        )::integer
        ELSE NULL
    END,
    stock_status = CASE
        WHEN cover.forecast_daily_units <= 0 THEN 'overstock'
        WHEN (
            (balance.available_qty + balance.incoming_qty)
            / cover.forecast_daily_units
        ) < 14 THEN 'replenish'
        WHEN (
            (balance.available_qty + balance.incoming_qty)
            / cover.forecast_daily_units
        ) > 90 THEN 'overstock'
        ELSE 'healthy'
    END,
    snapshot_at = TIMESTAMPTZ '2026-07-27 23:59:00+08',
    data_origin = 'derived_sample_extension_20260727'
FROM inventory.inventory_balances AS balance
JOIN affected
  ON affected.warehouse_id = balance.warehouse_id
 AND affected.sku_id = balance.sku_id
WHERE cover.warehouse_id = balance.warehouse_id
  AND cover.sku_id = balance.sku_id;

DO $$
DECLARE
    order_rows integer;
    line_rows integer;
    sold_units integer;
    snapshot_rows integer;
    customer_rows integer;
BEGIN
    SELECT count(*)
    INTO order_rows
    FROM sales.orders
    WHERE data_origin = 'derived_sample_extension_20260727';

    SELECT count(*), sum(quantity)
    INTO line_rows, sold_units
    FROM sales.order_lines
    WHERE data_origin = 'derived_sample_extension_20260727';

    SELECT count(*)
    INTO snapshot_rows
    FROM analytics.v_sku_daily_sales
    WHERE data_origin = 'derived_sample_extension_20260727';

    SELECT count(*)
    INTO customer_rows
    FROM crm.customers
    WHERE data_origin = 'derived_sample_extension_20260727';

    IF (order_rows, line_rows, sold_units, snapshot_rows)
        <> (116, 116, 136, 106)
    THEN
        RAISE EXCEPTION
            'validation failed: orders %, lines %, units %, snapshots %',
            order_rows,
            line_rows,
            sold_units,
            snapshot_rows;
    END IF;

    IF customer_rows < 20 THEN
        RAISE EXCEPTION
            'validation failed: expected at least 20 sample customers, found %',
            customer_rows;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM inventory.inventory_balances
        WHERE on_hand_qty < 0
           OR reserved_qty < 0
           OR blocked_qty < 0
           OR available_qty < 0
           OR incoming_qty < 0
    ) THEN
        RAISE EXCEPTION 'validation failed: negative inventory balance';
    END IF;
END
$$;

COMMIT;

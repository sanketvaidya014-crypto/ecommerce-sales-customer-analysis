-- Monthly revenue, orders, AOV and freight (delivered orders only)
-- Revenue comes from order_items only, so it is never duplicated by payment rows.
SELECT strftime('%Y-%m', o.order_purchase_timestamp)      AS month,
       COUNT(DISTINCT o.order_id)                          AS orders,
       ROUND(SUM(oi.price), 2)                             AS revenue,
       ROUND(SUM(oi.price) * 1.0 / COUNT(DISTINCT o.order_id), 2) AS aov,
       ROUND(SUM(oi.freight_value), 2)                     AS freight
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY 1;

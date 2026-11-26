-- Repeat-customer rate. Uses customer_unique_id (customer_id is new per order in Olist).
WITH cust AS (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS orders
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1
)
SELECT COUNT(*)                                             AS customers,
       SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END)          AS repeat_customers,
       ROUND(100.0 * SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_pct
FROM cust;

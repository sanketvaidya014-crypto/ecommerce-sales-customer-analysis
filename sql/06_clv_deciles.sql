-- Historical customer lifetime value, bucketed in spend deciles (1 = top 10% spenders)
WITH cust AS (
    SELECT c.customer_unique_id AS uid,
           COUNT(DISTINCT o.order_id) AS orders,
           SUM(oi.price)              AS spend
    FROM orders o
    JOIN customers c    ON c.customer_id = o.customer_id
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1
),
ranked AS (
    SELECT *, NTILE(10) OVER (ORDER BY spend DESC) AS decile FROM cust
)
SELECT decile,
       COUNT(*)                                   AS customers,
       ROUND(AVG(spend), 2)                       AS avg_clv,
       ROUND(SUM(spend), 2)                       AS total_spend,
       ROUND(100.0 * SUM(spend) / (SELECT SUM(spend) FROM cust), 2) AS revenue_share_pct
FROM ranked
GROUP BY decile
ORDER BY decile;

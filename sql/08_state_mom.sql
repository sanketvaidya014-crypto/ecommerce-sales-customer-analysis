-- Month-over-month revenue growth per state using LAG
WITH m AS (
    SELECT c.customer_state AS state,
           strftime('%Y-%m', o.order_purchase_timestamp) AS month,
           SUM(oi.price) AS revenue
    FROM orders o
    JOIN customers c    ON c.customer_id = o.customer_id
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1, 2
)
SELECT state, month, ROUND(revenue, 2) AS revenue,
       ROUND(100.0 * (revenue / LAG(revenue) OVER (PARTITION BY state ORDER BY month) - 1), 1) AS mom_growth_pct
FROM m
ORDER BY state, month;

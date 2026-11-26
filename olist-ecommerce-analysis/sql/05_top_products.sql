-- Top 3 products inside each category (RANK + PARTITION BY)
WITH prod AS (
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
           oi.product_id,
           COUNT(*)                 AS units,
           ROUND(SUM(oi.price), 2)  AS revenue
    FROM order_items oi
    JOIN orders o   ON o.order_id = oi.order_id AND o.order_status = 'delivered'
    JOIN products p ON p.product_id = oi.product_id
    LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
    GROUP BY 1, 2
),
ranked AS (
    SELECT *, RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS rk,
              SUM(revenue) OVER (PARTITION BY category) AS cat_revenue
    FROM prod
)
SELECT category, product_id, units, revenue, rk
FROM ranked
WHERE rk <= 3
ORDER BY cat_revenue DESC, category, rk
LIMIT 30;

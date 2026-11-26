-- Category performance with an explicit profitability PROXY (Olist has no cost data).
-- est_margin = ASSUMED 20% of item price. freight_pct flags freight-heavy categories.
WITH item_cat AS (
    SELECT oi.order_id, oi.price, oi.freight_value,
           COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category
    FROM order_items oi
    JOIN orders o   ON o.order_id = oi.order_id AND o.order_status = 'delivered'
    JOIN products p ON p.product_id = oi.product_id
    LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
),
review AS (
    SELECT order_id, AVG(review_score) AS score FROM order_reviews GROUP BY order_id
),
agg AS (
    SELECT ic.category,
           COUNT(DISTINCT ic.order_id)            AS orders,
           ROUND(SUM(ic.price), 2)                AS revenue,
           ROUND(SUM(ic.freight_value), 2)        AS freight,
           ROUND(100.0 * SUM(ic.freight_value) / SUM(ic.price), 1) AS freight_pct,
           ROUND(SUM(ic.price) * 0.20, 2)         AS est_margin,
           ROUND(AVG(r.score), 2)                 AS avg_review
    FROM item_cat ic
    LEFT JOIN review r ON r.order_id = ic.order_id
    GROUP BY 1
)
SELECT *,
       RANK() OVER (ORDER BY revenue DESC)                AS revenue_rank,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)   AS revenue_share_pct
FROM agg
ORDER BY revenue DESC;

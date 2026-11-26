-- Does a late FIRST delivery hurt review score and the chance of a repeat purchase?
WITH ord AS (
    SELECT o.order_id, c.customer_unique_id AS uid, o.order_purchase_timestamp AS ts,
           CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                THEN 'late' ELSE 'on_time' END AS delivery_status
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
),
rev AS (
    SELECT order_id, AVG(review_score) AS score FROM order_reviews GROUP BY order_id
),
numbered AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY uid ORDER BY ts) AS rn,
              COUNT(*)     OVER (PARTITION BY uid)             AS n_orders
    FROM ord
)
SELECT n.delivery_status,
       COUNT(*)                                                    AS first_orders,
       ROUND(AVG(r.score), 2)                                      AS avg_review,
       ROUND(100.0 * AVG(CASE WHEN n.n_orders > 1 THEN 1.0 ELSE 0 END), 2) AS repeat_pct
FROM numbered n
LEFT JOIN rev r ON r.order_id = n.order_id
WHERE n.rn = 1
GROUP BY 1;

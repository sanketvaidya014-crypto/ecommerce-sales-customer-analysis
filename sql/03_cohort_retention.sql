-- Monthly acquisition cohorts and retention (% of cohort active N months later)
WITH base AS (
    SELECT DISTINCT c.customer_unique_id AS uid,
           strftime('%Y-%m', o.order_purchase_timestamp) AS ym
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
),
cohorts AS (
    SELECT uid, MIN(ym) AS cohort FROM base GROUP BY uid
),
activity AS (
    SELECT co.cohort,
           (CAST(substr(b.ym, 1, 4) AS INT) * 12 + CAST(substr(b.ym, 6, 2) AS INT))
         - (CAST(substr(co.cohort, 1, 4) AS INT) * 12 + CAST(substr(co.cohort, 6, 2) AS INT)) AS month_number,
           COUNT(DISTINCT b.uid) AS customers
    FROM base b
    JOIN cohorts co ON co.uid = b.uid
    GROUP BY 1, 2
)
SELECT cohort, month_number, customers,
       ROUND(100.0 * customers /
             FIRST_VALUE(customers) OVER (PARTITION BY cohort ORDER BY month_number), 2) AS retention_pct
FROM activity
ORDER BY cohort, month_number;

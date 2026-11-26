-- Like-for-like growth: Jan-Aug 2017 vs Jan-Aug 2018 revenue by customer state
SELECT c.customer_state AS state,
       ROUND(COALESCE(SUM(CASE WHEN strftime('%Y', o.order_purchase_timestamp) = '2017' THEN oi.price END), 0), 2) AS rev_2017,
       ROUND(COALESCE(SUM(CASE WHEN strftime('%Y', o.order_purchase_timestamp) = '2018' THEN oi.price END), 0), 2) AS rev_2018,
       ROUND(100.0 * (
            SUM(CASE WHEN strftime('%Y', o.order_purchase_timestamp) = '2018' THEN oi.price END)
          / NULLIF(SUM(CASE WHEN strftime('%Y', o.order_purchase_timestamp) = '2017' THEN oi.price END), 0) - 1), 1) AS growth_pct
FROM orders o
JOIN customers c    ON c.customer_id = o.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND strftime('%m', o.order_purchase_timestamp) <= '08'
  AND strftime('%Y', o.order_purchase_timestamp) IN ('2017', '2018')
GROUP BY 1
ORDER BY rev_2018 DESC;

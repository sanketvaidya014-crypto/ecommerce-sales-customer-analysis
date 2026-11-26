# E-commerce Sales & Customer Analysis (Olist)

**Business question:** *Which customers repeat purchases, which products and categories are profitable, and where (city/state/category) is sales growing?*

An end-to-end analytics project: **SQL** (joins, CTEs, window functions) for the core analysis, **Python** (pandas, matplotlib, seaborn) for cleaning, feature engineering, RFM segmentation and a dashboard, ending in **5 data-backed business insights**.

## Dataset
[Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (~100k orders, 2016-2018). Put the 7 CSVs below in `data/raw/`:
`olist_orders_dataset`, `olist_customers_dataset`, `olist_order_items_dataset`, `olist_products_dataset`, `olist_order_payments_dataset`, `olist_order_reviews_dataset`, `product_category_name_translation`.

## Project structure
```
data/raw/          source CSVs (git-ignored)
sql/               9 analysis queries (SQLite; window functions need >= 3.25)
src/load_db.py     CSVs -> SQLite (data/olist.db) with indexes
src/analysis.py    runs the SQL, cleans data, builds charts + insights
src/make_sample_data.py   synthetic Olist-shaped data for testing ONLY
outputs/           dashboard.png, figures/, tables/*.csv, insights.md
```

## How to run
```bash
pip install -r requirements.txt
python src/load_db.py        # build the database
python src/analysis.py       # run SQL + Python, write outputs/
```
No Kaggle access yet? `python src/make_sample_data.py` generates synthetic data to test the pipeline. **Never report numbers from it as findings.**

## SQL analysis
| File | What it answers | Techniques |
|---|---|---|
| 01_monthly_revenue | Revenue, orders, AOV, freight per month | joins, aggregation |
| 02_repeat_rate | % customers with more than 1 order | CTE, conditional agg |
| 03_cohort_retention | Retention by acquisition month | CTEs, date maths, `FIRST_VALUE` |
| 04_category_performance | Revenue, freight %, est. margin, review per category | multi-join, `RANK`, share of total |
| 05_top_products | Top 3 products per category | `RANK() OVER (PARTITION BY)` |
| 06_clv_deciles | Historical CLV and revenue concentration | `NTILE(10)` |
| 07_state_growth | Like-for-like Jan-Aug 2017 vs 2018 growth by state | conditional agg, `NULLIF` |
| 08_state_mom | Month-over-month growth per state | `LAG` |
| 09_delivery_vs_loyalty | Late first delivery vs review and repeat rate | `ROW_NUMBER`, window counts |

## Python analysis
- **Cleaning:** parse timestamps, keep delivered orders, drop impossible delivery times, handle missing categories (`unknown`), aggregate items/reviews to order level *before* joining (prevents duplicated revenue).
- **Outliers:** price flagged with IQR and winsorised at the 99th percentile (kept, not dropped).
- **Features:** `delivery_days`, `delay_flag`, `freight_ratio`, `order_month`, RFM scores and segments.
- **Charts:** monthly revenue, top categories, cohort heatmap, state revenue, CLV deciles, delivery vs loyalty, combined into `outputs/dashboard.png`.

## Key methodology decisions (and why)
1. **`customer_unique_id`, not `customer_id`.** Olist issues a new `customer_id` per order; using it makes repeat rate look like 0%.
2. **Delivered orders only** for revenue, to avoid counting cancelled or unshipped orders.
3. **Profit is a proxy.** Olist has no cost data, so I use an *assumed* 20% margin plus freight % of price. Change `0.20` in `sql/04_category_performance.sql` to test sensitivity.
4. **Like-for-like growth** (Jan-Aug vs Jan-Aug) because 2018 data ends in August.

## Results
Run the pipeline, then see `outputs/insights.md` (numbers are generated from the data, not hand-typed) and `outputs/dashboard.png`. Paste the final insights here once you have run it on the real data.

## Limitations
- Observational data; late delivery and low repeat rate are correlated, not proven causal.
- Retention is measured over a short window (about 2 years); recent cohorts have had little time to return.
- Margin is assumed, so category profitability is directional only.

## Interview talking points
- "Repeat rate is very low, so I traced it to the `customer_id` vs `customer_unique_id` trap, then cohort-analysed retention."
- "I joined payments, items and reviews at the right grain to avoid revenue duplication."
- "With no cost data I defined a transparent profitability proxy and documented the assumption."
- "I connected operations (late delivery) to customer behaviour (reviews, repeat purchase) and recommended actions."

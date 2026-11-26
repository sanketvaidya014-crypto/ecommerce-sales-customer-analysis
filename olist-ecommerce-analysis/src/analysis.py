"""Run all SQL files, clean/engineer features in pandas, build charts + auto-generated insights.
Usage: python src/analysis.py   (after python src/load_db.py)"""
import pathlib
import sqlite3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB, SQL_DIR = ROOT / "data" / "olist.db", ROOT / "sql"
OUT = ROOT / "outputs"
FIG, TAB = OUT / "figures", OUT / "tables"
for d in (FIG, TAB):
    d.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="notebook")
PALETTE = "#2F5D8A"


def sql(con, name):
    df = pd.read_sql_query((SQL_DIR / name).read_text(), con)
    df.to_csv(TAB / (pathlib.Path(name).stem + ".csv"), index=False)
    return df


# ---------------------------------------------------------------- 1. cleaning + features
def build_order_frame(con):
    o = pd.read_sql_query(
        """SELECT o.order_id, c.customer_unique_id, c.customer_state,
                  o.order_purchase_timestamp AS purchase_ts,
                  o.order_delivered_customer_date AS delivered_ts,
                  o.order_estimated_delivery_date AS estimated_ts
           FROM orders o JOIN customers c ON c.customer_id = o.customer_id
           WHERE o.order_status = 'delivered'""", con,
        parse_dates=["purchase_ts", "delivered_ts", "estimated_ts"])
    items = pd.read_sql_query(
        "SELECT order_id, SUM(price) AS price, SUM(freight_value) AS freight FROM order_items GROUP BY order_id", con)
    rev = pd.read_sql_query(
        "SELECT order_id, AVG(review_score) AS review FROM order_reviews GROUP BY order_id", con)
    df = o.merge(items, on="order_id", how="inner").merge(rev, on="order_id", how="left")
    df = df.dropna(subset=["delivered_ts"]).drop_duplicates("order_id")

    df["order_month"] = df.purchase_ts.dt.to_period("M").astype(str)
    df["delivery_days"] = (df.delivered_ts - df.purchase_ts).dt.days
    df["delay_flag"] = (df.delivered_ts > df.estimated_ts).astype(int)
    df["freight_ratio"] = df.freight / df.price

    # outliers: flag with IQR, winsorise at the 99th percentile (kept, not dropped)
    q1, q3 = df.price.quantile([.25, .75])
    df["price_outlier"] = df.price > q3 + 1.5 * (q3 - q1)
    df["price_capped"] = df.price.clip(upper=df.price.quantile(.99))
    df = df[df.delivery_days.between(0, 120)]  # remove impossible delivery times
    return df


def rfm(df):
    snap = df.purchase_ts.max() + pd.Timedelta(days=1)
    g = df.groupby("customer_unique_id").agg(
        recency=("purchase_ts", lambda s: (snap - s.max()).days),
        frequency=("order_id", "nunique"), monetary=("price_capped", "sum"))
    g["R"] = pd.qcut(g.recency.rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    g["M"] = pd.qcut(g.monetary.rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    g["F"] = np.where(g.frequency > 1, 4, 1)
    g["segment"] = np.select(
        [(g.F == 4) & (g.M >= 3), g.F == 4, (g.R >= 3) & (g.M >= 3), g.R == 1],
        ["Loyal high-value", "Repeat", "New high-value", "Lapsed"], default="Other")
    return g


# ---------------------------------------------------------------- 2. charts
def ch_revenue(ax, d):
    m = d["monthly"]; m = m[m.orders >= 50]
    ax.plot(m.month, m.revenue / 1e3, color=PALETTE, marker="o", ms=3)
    ax.set(title="Monthly revenue (delivered orders)", ylabel="Revenue (thousand)")
    ax.set_xticks(range(0, len(m), 3)); ax.set_xticklabels(m.month.iloc[::3], rotation=45, ha="right")


def ch_category(ax, d):
    c = d["category"].head(10).iloc[::-1]
    ax.barh(c.category, c.revenue / 1e3, color=PALETTE)
    ax.set(title="Top 10 categories by revenue", xlabel="Revenue (thousand)")


def ch_cohort(ax, d):
    c = d["cohort"]
    p = c[(c.month_number >= 1) & (c.month_number <= 12)].pivot(index="cohort", columns="month_number", values="retention_pct")
    sizes = c[c.month_number == 0].set_index("cohort").customers
    p = p[sizes.reindex(p.index) >= 30]
    sns.heatmap(p, ax=ax, cmap="Blues", annot=len(p) <= 12, fmt=".1f", cbar_kws={"label": "% retained"})
    ax.set(title="Cohort retention (% active by month since 1st order)", xlabel="Months since first order", ylabel="")


def ch_state(ax, d):
    s = d["state"].head(10).iloc[::-1]
    ax.barh(s.state, s.rev_2018 / 1e3, color=PALETTE)
    ax.set(title="Revenue by customer state (Jan-Aug 2018)", xlabel="Revenue (thousand)")


def ch_clv(ax, d):
    c = d["clv"]
    ax.bar(c.decile.astype(str), c.revenue_share_pct, color=PALETTE)
    ax.set(title="Share of revenue by customer spend decile", xlabel="Decile (1 = top spenders)", ylabel="% of revenue")


def ch_delivery(ax, d):
    t = d["delivery"].set_index("delivery_status")
    bars = ax.bar(t.index, t.avg_review, color=["#C0504D" if i == "late" else PALETTE for i in t.index])
    for b, rp in zip(bars, t.repeat_pct):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + .05, f"repeat {rp:.1f}%", ha="center", fontsize=9)
    ax.set(title="First-delivery status vs review & repeat rate", ylabel="Avg review score", ylim=(0, 5.5))


CHARTS = [("monthly_revenue", ch_revenue), ("top_categories", ch_category), ("cohort_retention", ch_cohort),
          ("state_revenue", ch_state), ("clv_deciles", ch_clv), ("delivery_vs_loyalty", ch_delivery)]


# ---------------------------------------------------------------- 3. insights
def insights(d, df, seg):
    rep = d["repeat"].iloc[0]
    cat = d["category"]
    top5 = cat.head(5).revenue_share_pct.sum()
    big = cat[cat.revenue >= cat.revenue.median()]
    fr = big.sort_values("freight_pct", ascending=False).iloc[0]
    dl = d["delivery"].set_index("delivery_status")
    st = d["state"]
    sp = st.loc[st.state == "SP", "rev_2018"].sum() / st.rev_2018.sum() * 100
    base = st[st.rev_2017 >= st.rev_2017.median()].sort_values("growth_pct", ascending=False).iloc[0]
    top10 = d["clv"].loc[d["clv"].decile == 1, "revenue_share_pct"].iloc[0]
    L = ["# Business insights (auto-generated from the data currently loaded)\n"]
    L.append(f"1. **Retention is the weak spot.** Only {rep.repeat_pct:.2f}% of {int(rep.customers):,} customers "
             f"ordered more than once, so growth is almost entirely new-customer acquisition. "
             f"Action: post-purchase email/CRM and loyalty offers within 30-60 days.")
    L.append(f"2. **Revenue is concentrated.** The top 5 categories generate {top5:.1f}% of revenue, and the top spend decile "
             f"alone brings {top10:.1f}%. Action: protect inventory and seller quality in these categories.")
    L.append(f"3. **Freight erodes margin.** Among large categories, *{fr.category}* has freight at {fr.freight_pct:.1f}% of item "
             f"price (assumed margin 20%). Action: free-shipping thresholds or regional sellers for such categories.")
    if {"late", "on_time"} <= set(dl.index):
        L.append(f"4. **Delivery performance vs loyalty.** First orders delivered late average a {dl.loc['late','avg_review']:.2f} review "
                 f"vs {dl.loc['on_time','avg_review']:.2f} on time, and repeat rate is {dl.loc['late','repeat_pct']:.2f}% vs "
                 f"{dl.loc['on_time','repeat_pct']:.2f}%. Action: tighter delivery promises and carrier SLAs.")
    L.append(f"5. **Geography.** SP contributes {sp:.1f}% of Jan-Aug 2018 revenue, while *{base.state}* grew fastest among "
             f"sizeable states ({base.growth_pct:.1f}% vs 2017). Action: shift acquisition spend toward high-growth states.")
    seg_tbl = seg.groupby("segment").agg(customers=("monetary", "size"), avg_spend=("monetary", "mean")).round(2)
    L.append("\n## RFM segments\n\n" + seg_tbl.to_markdown())
    L.append("\n## Data-quality notes\n")
    L.append(f"- Delivered orders analysed: {len(df):,}; IQR price outliers flagged: {int(df.price_outlier.sum()):,} "
             f"({df.price_outlier.mean()*100:.1f}%), winsorised at the 99th percentile (kept, not dropped).")
    L.append("- 'Profit' is a proxy (assumed 20% margin; Olist has no cost data).")
    (OUT / "insights.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


def main():
    with sqlite3.connect(DB) as con:
        d = {"monthly": sql(con, "01_monthly_revenue.sql"), "repeat": sql(con, "02_repeat_rate.sql"),
             "cohort": sql(con, "03_cohort_retention.sql"), "category": sql(con, "04_category_performance.sql"),
             "products": sql(con, "05_top_products.sql"), "clv": sql(con, "06_clv_deciles.sql"),
             "state": sql(con, "07_state_growth.sql"), "mom": sql(con, "08_state_mom.sql"),
             "delivery": sql(con, "09_delivery_vs_loyalty.sql")}
        df = build_order_frame(con)
    seg = rfm(df)
    df.to_csv(TAB / "orders_clean.csv", index=False)
    seg.to_csv(TAB / "rfm_segments.csv")

    for name, fn in CHARTS:
        fig, ax = plt.subplots(figsize=(8, 4.5)); fn(ax, d); fig.tight_layout()
        fig.savefig(FIG / f"{name}.png", dpi=150); plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(20, 10))
    for ax, (_, fn) in zip(axes.ravel(), CHARTS):
        fn(ax, d)
    fig.suptitle("E-commerce Sales & Customer Analysis Dashboard", fontsize=18, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, .96]); fig.savefig(OUT / "dashboard.png", dpi=130); plt.close(fig)
    insights(d, df, seg)
    print(f"\nOutputs written to {OUT}")


if __name__ == "__main__":
    main()

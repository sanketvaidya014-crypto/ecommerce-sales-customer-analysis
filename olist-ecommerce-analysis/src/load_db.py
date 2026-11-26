"""Load the Olist CSVs from data/raw into a SQLite database (data/olist.db)."""
import pathlib
import sqlite3
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DB = ROOT / "data" / "raw", ROOT / "data" / "olist.db"

FILES = {
    "olist_orders_dataset.csv": "orders",
    "olist_customers_dataset.csv": "customers",
    "olist_order_items_dataset.csv": "order_items",
    "olist_products_dataset.csv": "products",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "product_category_name_translation.csv": "category_translation",
}
INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_orders_cust ON orders(customer_id)",
    "CREATE INDEX IF NOT EXISTS ix_items_order ON order_items(order_id)",
    "CREATE INDEX IF NOT EXISTS ix_items_prod ON order_items(product_id)",
    "CREATE INDEX IF NOT EXISTS ix_rev_order ON order_reviews(order_id)",
    "CREATE INDEX IF NOT EXISTS ix_pay_order ON order_payments(order_id)",
    "CREATE INDEX IF NOT EXISTS ix_cust_uid ON customers(customer_unique_id)",
]


def main() -> None:
    missing = [f for f in FILES if not (RAW / f).exists()]
    if missing:
        raise SystemExit(
            f"Missing files in {RAW}: {missing}\n"
            "Download Olist from Kaggle (olistbr/brazilian-ecommerce) or run "
            "`python src/make_sample_data.py` for a synthetic demo dataset."
        )
    if DB.exists():
        DB.unlink()
    with sqlite3.connect(DB) as con:
        for fname, table in FILES.items():
            df = pd.read_csv(RAW / fname)
            df.to_sql(table, con, index=False)
            print(f"{table:22s} {len(df):>8,} rows")
        for stmt in INDEXES:
            con.execute(stmt)
    print(f"\nDatabase ready: {DB}")


if __name__ == "__main__":
    main()

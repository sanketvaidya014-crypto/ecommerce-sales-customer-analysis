"""Generate a SYNTHETIC dataset with the Olist schema, to test the pipeline end to end.
Numbers produced from it are NOT real findings. Use the real Olist data for the analysis."""
import pathlib
import numpy as np
import pandas as pd

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
rng = np.random.default_rng(42)

STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "GO", "DF", "PE"]
S_P = [.42, .13, .12, .06, .06, .04, .04, .03, .03, .07]
CATS = [("cama_mesa_banho", "bed_bath_table", 90, .20), ("beleza_saude", "health_beauty", 130, .15),
        ("informatica_acessorios", "computers_accessories", 110, .17),
        ("moveis_decoracao", "furniture_decor", 85, .25), ("esporte_lazer", "sports_leisure", 100, .18),
        ("utilidades_domesticas", "housewares", 75, .22), ("relogios_presentes", "watches_gifts", 200, .10),
        ("telefonia", "telephony", 60, .30), ("moveis_escritorio", "office_furniture", 250, .35),
        ("brinquedos", "toys", 95, .20)]
START, END = pd.Timestamp("2017-01-01"), pd.Timestamp("2018-08-31")
N_CUST = 8000

days = (END - START).days
w = np.linspace(1, 6, days + 1); w /= w.sum()  # growing marketplace

# products
prods = pd.DataFrame({"product_id": [f"p{i:04d}" for i in range(400)]})
prods["cat_idx"] = rng.integers(0, len(CATS), len(prods))
prods["product_category_name"] = [CATS[i][0] for i in prods.cat_idx]
prods.loc[rng.choice(len(prods), 8, replace=False), "product_category_name"] = np.nan

# orders
rows = []
for i in range(N_CUST):
    uid = f"u{i:05d}"
    state = rng.choice(STATES, p=S_P)
    first = START + pd.Timedelta(days=int(rng.choice(days + 1, p=w)))
    ts = [first]
    if rng.random() < 0.04:
        for _ in range(rng.integers(1, 3)):
            nxt = ts[-1] + pd.Timedelta(days=int(rng.integers(30, 240)))
            if nxt <= END:
                ts.append(nxt)
    for t in ts:
        rows.append((uid, state, t + pd.Timedelta(minutes=int(rng.integers(0, 1440)))))
orders = pd.DataFrame(rows, columns=["uid", "state", "ts"]).reset_index(drop=True)
orders["order_id"] = [f"o{i:06d}" for i in range(len(orders))]
orders["customer_id"] = [f"c{i:06d}" for i in range(len(orders))]
orders["order_status"] = rng.choice(["delivered", "canceled", "shipped"], len(orders), p=[.97, .02, .01])
transit = rng.gamma(4, 3, len(orders)).round() + 3
est = rng.integers(14, 28, len(orders))
orders["order_purchase_timestamp"] = orders.ts
orders["order_approved_at"] = orders.ts + pd.Timedelta(hours=2)
orders["order_delivered_carrier_date"] = orders.ts + pd.Timedelta(days=2)
deliv = orders.ts + pd.to_timedelta(transit, unit="D")
orders["order_delivered_customer_date"] = deliv.where(orders.order_status == "delivered")
orders["order_estimated_delivery_date"] = orders.ts + pd.to_timedelta(est, unit="D")
late = (orders.order_delivered_customer_date > orders.order_estimated_delivery_date).fillna(False)

customers = orders[["customer_id", "uid", "state"]].rename(
    columns={"uid": "customer_unique_id", "state": "customer_state"})
customers["customer_zip_code_prefix"] = rng.integers(1000, 99999, len(customers))
customers["customer_city"] = "city_" + customers.customer_state

# items
it = []
for oid in orders.order_id:
    for k in range(1, rng.integers(1, 4) + 1):
        p = prods.iloc[rng.integers(0, len(prods))]
        _, _, mean, fr = CATS[p.cat_idx]
        price = float(np.round(rng.lognormal(np.log(mean), .6), 2))
        freight = float(np.round(price * fr * rng.uniform(.6, 1.4) + 8, 2))
        it.append((oid, k, p.product_id, f"s{rng.integers(0, 80):03d}", price, freight))
items = pd.DataFrame(it, columns=["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"])
items["shipping_limit_date"] = START

pay = items.groupby("order_id")[["price", "freight_value"]].sum().sum(axis=1).round(2).rename("payment_value").reset_index()
pay["payment_sequential"] = 1
pay["payment_type"] = rng.choice(["credit_card", "boleto", "voucher", "debit_card"], len(pay), p=[.74, .19, .04, .03])
pay["payment_installments"] = rng.integers(1, 10, len(pay))

late_by_order = dict(zip(orders.order_id, late))
score = [rng.choice([1, 2, 3, 4, 5], p=[.35, .25, .2, .12, .08] if late_by_order[o] else [.04, .03, .08, .25, .60])
         for o in orders.order_id]
reviews = pd.DataFrame({"review_id": [f"r{i:06d}" for i in range(len(orders))], "order_id": orders.order_id,
                        "review_score": score, "review_creation_date": orders.ts})

trans = pd.DataFrame([(c[0], c[1]) for c in CATS], columns=["product_category_name", "product_category_name_english"])
RAW.mkdir(parents=True, exist_ok=True)
cols = ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]
orders[cols].to_csv(RAW / "olist_orders_dataset.csv", index=False)
customers[["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"]] \
    .to_csv(RAW / "olist_customers_dataset.csv", index=False)
items.to_csv(RAW / "olist_order_items_dataset.csv", index=False)
prods[["product_id", "product_category_name"]].to_csv(RAW / "olist_products_dataset.csv", index=False)
pay.to_csv(RAW / "olist_order_payments_dataset.csv", index=False)
reviews.to_csv(RAW / "olist_order_reviews_dataset.csv", index=False)
trans.to_csv(RAW / "product_category_name_translation.csv", index=False)
print(f"Synthetic sample written to {RAW}: {len(orders):,} orders, {N_CUST:,} customers")

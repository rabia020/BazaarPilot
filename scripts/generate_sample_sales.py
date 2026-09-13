"""Generate a realistic 8-month kiryana/retail sales dataset for BazaarPilot demos."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data"
SEED = 42

PRODUCTS = [
    # High volume, critically low stock
    {"product": "Milk", "category": "Dairy", "unit_price": 180, "unit_cost": 145, "inventory": 12, "supplier": "Al-Fajr Dairy", "base_qty": 7.0, "trend": 0.02},
    # Low stock + steady demand
    {"product": "Cooking Oil", "category": "Grocery", "unit_price": 520, "unit_cost": 430, "inventory": 8, "supplier": "Pakistan Oil Mills", "base_qty": 3.2, "trend": 0.05},
    # Low-ish stock, slower sales
    {"product": "Rice", "category": "Grocery", "unit_price": 280, "unit_cost": 210, "inventory": 18, "supplier": "Punjab Grain Co", "base_qty": 2.1, "trend": 0.0},
    # High volume, thinner margin
    {"product": "Instant Noodles", "category": "Grocery", "unit_price": 60, "unit_cost": 42, "inventory": 140, "supplier": "City Foods", "base_qty": 14.0, "trend": 0.03},
    # Highly profitable
    {"product": "Premium Headphones", "category": "Electronics", "unit_price": 4500, "unit_cost": 2100, "inventory": 22, "supplier": "TechHub", "base_qty": 0.7, "trend": 0.04},
    # Highly profitable accessory
    {"product": "Smartphone Case", "category": "Electronics", "unit_price": 650, "unit_cost": 180, "inventory": 55, "supplier": "TechHub", "base_qty": 4.5, "trend": 0.01},
    # Rapidly increasing demand
    {"product": "Energy Drink", "category": "Beverages", "unit_price": 150, "unit_cost": 95, "inventory": 28, "supplier": "CoolBev Ltd", "base_qty": 3.0, "trend": 0.55},
    # Declining sales
    {"product": "Green Tea", "category": "Beverages", "unit_price": 220, "unit_cost": 140, "inventory": 90, "supplier": "Highland Tea", "base_qty": 5.0, "trend": -0.65},
    # High margin gift item
    {"product": "Basmati Gift Box", "category": "Grocery", "unit_price": 1800, "unit_cost": 900, "inventory": 16, "supplier": "Punjab Grain Co", "base_qty": 0.8, "trend": 0.08},
    # Healthy stock
    {"product": "Dish Soap", "category": "Household", "unit_price": 190, "unit_cost": 120, "inventory": 75, "supplier": "CleanHome", "base_qty": 2.4, "trend": 0.0},
    # Anomaly product (one extreme day)
    {"product": "Mineral Water", "category": "Beverages", "unit_price": 80, "unit_cost": 45, "inventory": 60, "supplier": "CoolBev Ltd", "base_qty": 6.0, "trend": 0.0},
]

REGIONS = ["Karachi", "Lahore", "Islamabad", "Faisalabad"]
CUSTOMER_TYPES = ["Retail", "Retail", "Retail", "Wholesale"]


def main() -> None:
    rng = np.random.default_rng(SEED)
    dates = pd.date_range("2026-01-01", "2026-08-31", freq="D")
    rows: list[dict] = []

    for day in dates:
        month = day.month
        day_index = (day - dates[0]).days
        total_days = max((dates[-1] - dates[0]).days, 1)
        progress = day_index / total_days

        for spec in PRODUCTS:
            # Weekends slightly busier for kiryana items
            weekend_boost = 1.25 if day.weekday() >= 5 else 1.0
            trend_mult = 1.0 + spec["trend"] * progress
            mean_qty = max(spec["base_qty"] * weekend_boost * trend_mult, 0.15)

            # August profit dip for Beverages (used later for "why did profit decrease?")
            august_penalty = 1.0
            extra_discount = 0.0
            if month == 8 and spec["category"] == "Beverages":
                august_penalty = 0.62
                extra_discount = 0.12

            n_tickets = 1
            if spec["base_qty"] >= 6:
                n_tickets = int(rng.integers(1, 4))

            for _ in range(n_tickets):
                qty = int(max(round(rng.normal(mean_qty * august_penalty, mean_qty * 0.18)), 0))
                if qty <= 0:
                    continue

                # Obvious anomaly: Mineral Water crash on 18 Jul 2026
                if spec["product"] == "Mineral Water" and day.strftime("%Y-%m-%d") == "2026-07-18":
                    qty = max(1, int(round(spec["base_qty"] * 0.52)))  # ~48% below typical ~6

                discount = float(np.clip(rng.normal(0.03, 0.02) + extra_discount, 0.0, 0.25))
                unit_price = spec["unit_price"]
                unit_cost = spec["unit_cost"]
                revenue = round(qty * unit_price * (1.0 - discount), 2)
                cost = round(qty * unit_cost, 2)
                profit = round(revenue - cost, 2)

                rows.append(
                    {
                        "date": day.strftime("%Y-%m-%d"),
                        "product": spec["product"],
                        "category": spec["category"],
                        "quantity": qty,
                        "unit_price": unit_price,
                        "unit_cost": unit_cost,
                        "discount": round(discount, 4),
                        "revenue": revenue,
                        "cost": cost,
                        "profit": profit,
                        "inventory": spec["inventory"],
                        "customer_type": rng.choice(CUSTOMER_TYPES),
                        "region": rng.choice(REGIONS),
                        "supplier": spec["supplier"],
                    }
                )

    df = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "sample_sales.csv"
    xlsx_path = OUT_DIR / "sample_sales.xlsx"
    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False)

    print(f"Wrote {len(df):,} rows to {csv_path}")
    print(f"Wrote {len(df):,} rows to {xlsx_path}")
    print("Products:", ", ".join(df["product"].unique()))
    print("Date range:", df["date"].min(), "->", df["date"].max())
    print("Total revenue:", round(df["revenue"].sum(), 2))
    print("Total profit:", round(df["profit"].sum(), 2))


if __name__ == "__main__":
    main()
    
from __future__ import annotations

import os
import argparse
import random
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List
from dotenv import load_dotenv
from app.db.engine import engine

from faker import Faker
from sqlalchemy import create_engine, text
load_dotenv()


def q(name: str, capital: bool) -> str:
    """Quote identifiers if using PascalCase schema."""
    return f'"{name}"' if capital else name


def bulk_insert(conn, table: str, columns: List[str], rows: List[Dict[str, Any]], capital: bool):
    if not rows:
        return
    cols_sql = ", ".join(q(c, capital) for c in columns)
    params_sql = ", ".join(f":{c}" for c in columns)
    sql = f"INSERT INTO {q(table, capital)} ({cols_sql}) VALUES ({params_sql})"
    conn.execute(text(sql), rows)


def truncate_all(conn, capital: bool):
    tables = [
        "asset_transactions",
        "sales_order_lines",
        "sales_orders",
        "purchase_order_lines",
        "purchase_orders",
        "bills",
        "assets",
        "items",
        "locations",
        "sites",
        "vendors",
        "customers",
    ]
    tables_sql = ", ".join(f"public.{q(t, capital)}" for t in tables)
    conn.execute(text(f"TRUNCATE {tables_sql} RESTART IDENTITY CASCADE;"))


def dt_between(fake: Faker, days_back: int = 365) -> datetime:
    return fake.date_time_between(start_date=f"-{days_back}d", end_date="now", tzinfo=timezone.utc)


def d_between(fake: Faker, days_back: int = 365) -> date:
    return fake.date_between(start_date=f"-{days_back}d", end_date="today")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="TRUNCATE all tables then seed")
    parser.add_argument("--capital-names", type=int, default=0, help="1 => PascalCase quoted, 0 => snake_case")
    parser.add_argument("--customers", type=int, default=300)
    parser.add_argument("--vendors", type=int, default=80)
    parser.add_argument("--sites", type=int, default=8)
    parser.add_argument("--locations-per-site", type=int, default=60)
    parser.add_argument("--items", type=int, default=800)
    parser.add_argument("--assets", type=int, default=600)
    parser.add_argument("--bills", type=int, default=500)
    parser.add_argument("--purchase-orders", type=int, default=350)
    parser.add_argument("--sales-orders", type=int, default=300)
    parser.add_argument("--max-lines", type=int, default=10)
    parser.add_argument("--asset-txns", type=int, default=1200)
    args = parser.parse_args()

    capital = bool(args.capital_names)
    db_url = os.getenv("database_url")
    if not db_url:
        raise SystemExit("Missing database_url env var")

    engine = create_engine(db_url, future=True)

    fake = Faker("en_US")
    Faker.seed(42)
    random.seed(42)

    now = datetime.now(timezone.utc)

    # -----------------------------
    # customers
    # -----------------------------
    customers: List[Dict[str, Any]] = []
    for i in range(1, args.customers + 1):
        customers.append({
            "customer_id": i,
            "customer_code": f"cust-{i:05d}",
            "customer_name": fake.name(),
            "email": fake.email(),
            "phone": fake.msisdn()[:15],
            "billing_address1": fake.street_address(),
            "billing_city": fake.city(),
            "billing_country": fake.country(),
            "created_at": dt_between(fake, 900),
            "updated_at": None,
            "is_active": random.random() > 0.05,
        })

    # -----------------------------
    # vendors
    # -----------------------------
    vendors: List[Dict[str, Any]] = []
    for i in range(1, args.vendors + 1):
        vendors.append({
            "vendor_id": i,
            "vendor_code": f"vend-{i:04d}",
            "vendor_name": fake.company(),
            "email": fake.company_email(),
            "phone": fake.msisdn()[:15],
            "address_line1": fake.street_address(),
            "city": fake.city(),
            "country": fake.country(),
            "created_at": dt_between(fake, 900),
            "updated_at": None,
            "is_active": random.random() > 0.03,
        })

    # -----------------------------
    # sites
    # -----------------------------
    sites: List[Dict[str, Any]] = []
    timezones = ["Africa/Cairo", "Europe/London", "Asia/Dubai", "Europe/Berlin", "America/New_York"]
    for i in range(1, args.sites + 1):
        sites.append({
            "site_id": i,
            "site_code": f"site-{i:03d}",
            "site_name": f"{fake.city()} main site",
            "address_line1": fake.street_address(),
            "city": fake.city(),
            "country": fake.country(),
            "time_zone": random.choice(timezones),
            "created_at": dt_between(fake, 900),
            "updated_at": None,
            "is_active": True,
        })

    # -----------------------------
    # locations (hierarchical)
    # -----------------------------
    locations: List[Dict[str, Any]] = []
    loc_id = 1
    for s in sites:
        site_id = s["site_id"]

        # Top-level warehouses (e.g., 3 per site)
        parents: List[int] = []
        for w in range(1, 4):
            locations.append({
                "location_id": loc_id,
                "site_id": site_id,
                "location_code": f"wh-{site_id:02d}-{w:02d}",
                "location_name": f"warehouse {w} - site {site_id}",
                "parent_location_id": None,
                "created_at": dt_between(fake, 900),
                "updated_at": None,
                "is_active": True,
            })
            parents.append(loc_id)
            loc_id += 1

        # Children bins/zones
        per_site_children = args.locations_per_site
        for n in range(1, per_site_children + 1):
            parent_id = random.choice(parents)
            locations.append({
                "location_id": loc_id,
                "site_id": site_id,
                "location_code": f"bin-{site_id:02d}-{n:03d}",
                "location_name": f"bin {n:03d} (site {site_id})",
                "parent_location_id": parent_id,
                "created_at": dt_between(fake, 900),
                "updated_at": None,
                "is_active": random.random() > 0.02,
            })
            loc_id += 1

    # -----------------------------
    # items
    # -----------------------------
    categories = ["electrical", "mechanical", "it", "office", "safety", "hvac", "plumbing"]
    uoms = ["ea", "box", "pack", "kg", "l", "m", "set"]
    items: List[Dict[str, Any]] = []
    for i in range(1, args.items + 1):
        items.append({
            "item_id": i,
            "item_code": f"item-{i:06d}",
            "item_name": f"{fake.word().title()} {fake.word().title()}",
            "category": random.choice(categories),
            "unit_of_measure": random.choice(uoms),
            "created_at": dt_between(fake, 900),
            "updated_at": None,
            "is_active": random.random() > 0.03,
        })

    # -----------------------------
    # assets
    # -----------------------------
    asset_statuses = ["active", "in_service", "maintenance", "retired"]
    assets: List[Dict[str, Any]] = []
    max_location_id = loc_id - 1
    for i in range(1, args.assets + 1):
        site_id = random.randint(1, args.sites)
        location_id = random.randint(1, max_location_id) if random.random() < 0.8 else None
        vendor_id = random.randint(1, args.vendors) if random.random() < 0.7 else None

        purchase_dt = fake.date_between(start_date="-1200d", end_date="today")
        cost = round(random.uniform(200.0, 20000.0), 2)

        assets.append({
            "asset_id": i,
            "asset_tag": f"ast-{i:06d}",
            "asset_name": f"{fake.word().title()} {random.choice(['pump','router','generator','laptop','valve','sensor'])}",
            "site_id": site_id,
            "location_id": location_id,
            "serial_number": fake.bothify(text="sn-##########"),
            "category": random.choice(categories),
            "status": random.choice(asset_statuses),
            "cost": cost,
            "purchase_date": purchase_dt,
            "vendor_id": vendor_id,
            "created_at": dt_between(fake, 1200),
            "updated_at": None,
        })

    # -----------------------------
    # bills
    # -----------------------------
    bill_status = ["open", "paid", "cancelled"]
    currencies = ["usd", "eur", "egp"]
    bills: List[Dict[str, Any]] = []
    bill_id = 1
    vendor_bill_counter = {v["vendor_id"]: 1 for v in vendors}

    for _ in range(args.bills):
        vendor_id = random.randint(1, args.vendors)
        seq = vendor_bill_counter[vendor_id]
        vendor_bill_counter[vendor_id] += 1

        bill_date = d_between(fake, 600)
        due_date = bill_date + timedelta(days=random.choice([15, 30, 45, 60]))
        total = round(random.uniform(100.0, 50000.0), 2)

        bills.append({
            "bill_id": bill_id,
            "vendor_id": vendor_id,
            "bill_number": f"bill-{vendor_id:03d}-{seq:05d}",
            "bill_date": bill_date,
            "due_date": due_date if random.random() < 0.9 else None,
            "total_amount": total,
            "currency": random.choice(currencies),
            "status": random.choices(bill_status, weights=[0.55, 0.4, 0.05])[0],
            "created_at": dt_between(fake, 600),
            "updated_at": None,
        })
        bill_id += 1

    # -----------------------------
    # purchase_orders + purchase_order_lines
    # -----------------------------
    po_status = ["open", "approved", "closed", "cancelled"]
    purchase_orders: List[Dict[str, Any]] = []
    purchase_order_lines: List[Dict[str, Any]] = []
    po_id = 1
    po_line_id = 1

    for n in range(1, args.purchase_orders + 1):
        vendor_id = random.randint(1, args.vendors)
        site_id = random.randint(1, args.sites) if random.random() < 0.8 else None
        po_date = d_between(fake, 600)
        status = random.choices(po_status, weights=[0.45, 0.25, 0.25, 0.05])[0]

        purchase_orders.append({
            "po_id": po_id,
            "po_number": f"po-{now.year}-{n:06d}",
            "vendor_id": vendor_id,
            "po_date": po_date,
            "status": status,
            "site_id": site_id,
            "created_at": dt_between(fake, 600),
            "updated_at": None,
        })

        lines_count = random.randint(1, args.max_lines)
        for ln in range(1, lines_count + 1):
            it = random.choice(items)
            qty = round(random.uniform(1, 500), 4)
            unit_price = round(random.uniform(1, 2500), 4)
            purchase_order_lines.append({
                "po_line_id": po_line_id,
                "po_id": po_id,
                "line_number": ln,
                "item_id": it["item_id"] if random.random() < 0.9 else None,
                "item_code": it["item_code"],
                "description": f"{it['item_name']} - {fake.sentence(nb_words=6)}" if random.random() < 0.6 else None,
                "quantity": qty,
                "unit_price": unit_price,
            })
            po_line_id += 1

        po_id += 1

    # -----------------------------
    # sales_orders + sales_order_lines
    # -----------------------------
    so_status = ["open", "confirmed", "delivered", "cancelled"]
    sales_orders: List[Dict[str, Any]] = []
    sales_order_lines: List[Dict[str, Any]] = []
    so_id = 1
    so_line_id = 1

    for n in range(1, args.sales_orders + 1):
        customer_id = random.randint(1, args.customers)
        site_id = random.randint(1, args.sites) if random.random() < 0.85 else None
        so_date = d_between(fake, 600)
        status = random.choices(so_status, weights=[0.5, 0.25, 0.2, 0.05])[0]

        sales_orders.append({
            "so_id": so_id,
            "so_number": f"so-{now.year}-{n:06d}",
            "customer_id": customer_id,
            "so_date": so_date,
            "status": status,
            "site_id": site_id,
            "created_at": dt_between(fake, 600),
            "updated_at": None,
        })

        lines_count = random.randint(1, args.max_lines)
        for ln in range(1, lines_count + 1):
            it = random.choice(items)
            qty = round(random.uniform(1, 300), 4)
            unit_price = round(random.uniform(1, 3000), 4)
            sales_order_lines.append({
                "so_line_id": so_line_id,
                "so_id": so_id,
                "line_number": ln,
                "item_id": it["item_id"] if random.random() < 0.9 else None,
                "item_code": it["item_code"],
                "description": f"{it['item_name']} - {fake.sentence(nb_words=6)}" if random.random() < 0.6 else None,
                "quantity": qty,
                "unit_price": unit_price,
            })
            so_line_id += 1

        so_id += 1

    # -----------------------------
    # asset_transactions
    # -----------------------------
    txn_types = ["move", "issue", "receive", "adjust", "inspection"]
    asset_txns: List[Dict[str, Any]] = []
    asset_txn_id = 1

    for _ in range(args.asset_txns):
        asset_id = random.randint(1, args.assets)
        from_loc = random.randint(1, max_location_id) if random.random() < 0.75 else None
        to_loc = random.randint(1, max_location_id) if random.random() < 0.75 else None

        asset_txns.append({
            "asset_txn_id": asset_txn_id,
            "asset_id": asset_id,
            "from_location_id": from_loc,
            "to_location_id": to_loc,
            "txn_type": random.choice(txn_types),
            "quantity": random.choice([1, 1, 1, 2, 3, 5, 10]),
            "txn_date": dt_between(fake, 600),
            "note": fake.sentence(nb_words=10) if random.random() < 0.7 else None,
        })
        asset_txn_id += 1

    # -----------------------------
    # Insert (transaction)
    # -----------------------------
    with engine.begin() as conn:
        if args.reset:
            truncate_all(conn, capital)

        bulk_insert(conn, "customers",
                    ["customer_id", "customer_code", "customer_name", "email", "phone",
                     "billing_address1", "billing_city", "billing_country",
                     "created_at", "updated_at", "is_active"],
                    customers, capital)

        bulk_insert(conn, "vendors",
                    ["vendor_id", "vendor_code", "vendor_name", "email", "phone",
                     "address_line1", "city", "country",
                     "created_at", "updated_at", "is_active"],
                    vendors, capital)

        bulk_insert(conn, "sites",
                    ["site_id", "site_code", "site_name", "address_line1", "city", "country",
                     "time_zone", "created_at", "updated_at", "is_active"],
                    sites, capital)

        bulk_insert(conn, "locations",
                    ["location_id", "site_id", "location_code", "location_name", "parent_location_id",
                     "created_at", "updated_at", "is_active"],
                    locations, capital)

        bulk_insert(conn, "items",
                    ["item_id", "item_code", "item_name", "category", "unit_of_measure",
                     "created_at", "updated_at", "is_active"],
                    items, capital)

        bulk_insert(conn, "assets",
                    ["asset_id", "asset_tag", "asset_name", "site_id", "location_id",
                     "serial_number", "category", "status", "cost", "purchase_date",
                     "vendor_id", "created_at", "updated_at"],
                    assets, capital)

        bulk_insert(conn, "bills",
                    ["bill_id", "vendor_id", "bill_number", "bill_date", "due_date",
                     "total_amount", "currency", "status", "created_at", "updated_at"],
                    bills, capital)

        bulk_insert(conn, "purchase_orders",
                    ["po_id", "po_number", "vendor_id", "po_date", "status", "site_id",
                     "created_at", "updated_at"],
                    purchase_orders, capital)

        bulk_insert(conn, "purchase_order_lines",
                    ["po_line_id", "po_id", "line_number", "item_id", "item_code",
                     "description", "quantity", "unit_price"],
                    purchase_order_lines, capital)

        bulk_insert(conn, "sales_orders",
                    ["so_id", "so_number", "customer_id", "so_date", "status", "site_id",
                     "created_at", "updated_at"],
                    sales_orders, capital)

        bulk_insert(conn, "sales_order_lines",
                    ["so_line_id", "so_id", "line_number", "item_id", "item_code",
                     "description", "quantity", "unit_price"],
                    sales_order_lines, capital)

        bulk_insert(conn, "asset_transactions",
                    ["asset_txn_id", "asset_id", "from_location_id", "to_location_id",
                     "txn_type", "quantity", "txn_date", "note"],
                    asset_txns, capital)

    print("✅ Seed completed!")
    print(f"customers={len(customers)}, vendors={len(vendors)}, sites={len(sites)}, "
          f"locations={len(locations)}, items={len(items)}, assets={len(assets)}, "
          f"bills={len(bills)}, pos={len(purchase_orders)}, po_lines={len(purchase_order_lines)}, "
          f"sos={len(sales_orders)}, so_lines={len(sales_order_lines)}, asset_txns={len(asset_txns)}")


if __name__ == "__main__":
    main()
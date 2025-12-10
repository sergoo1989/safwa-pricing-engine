import ast
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd

SKU_REGEX = re.compile(r"\(SKU:\s*([^\)]+)\)")
QTY_REGEX = re.compile(r"\(Qty:\s*(\d+)\)")


def load_orders(path: str = "data/salla_orders.csv", db_path: str = "data/salla_orders.db") -> pd.DataFrame:
    """Load orders from CSV (preferred) or SQLite fallback."""
    if os.path.exists(path):
        return pd.read_csv(path, low_memory=False)
    if os.path.exists(db_path):
        import sqlite3

        with sqlite3.connect(db_path) as conn:
            return pd.read_sql("SELECT * FROM salla_orders", conn)
    raise FileNotFoundError("لم يتم العثور على data/salla_orders.csv أو data/salla_orders.db")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize expected columns and trim whitespace."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    col_map = {
        "order_id": ["order_id", "id", "رقم الطلب"],
        "status": ["status", "حالة الطلب"],
        "city": ["city", "المدينة"],
        "sku": ["sku", "SKU", "items"],
        "payment": ["payment", "pay_method", "طريقة الدفع"],
        "date": ["order_date", "date", "تاريخ الطلب"],
    }
    resolved = {}
    for key, opts in col_map.items():
        for o in opts:
            if o in df.columns:
                resolved[key] = o
                break
    missing = [k for k in col_map if k not in resolved]
    if missing:
        raise ValueError(f"أعمدة مفقودة: {missing}")
    df = df.rename(columns={resolved[k]: k for k in resolved})
    return df


def parse_sku_cell(cell: str) -> List[Tuple[str, int]]:
    """Extract list of (sku_code, qty) from a cell containing list-like text."""
    if pd.isna(cell):
        return []
    text = str(cell)
    items: List[str]
    try:
        parsed = ast.literal_eval(text)
        items = parsed if isinstance(parsed, list) else [str(parsed)]
    except Exception:
        items = [text]
    result: List[Tuple[str, int]] = []
    for itm in items:
        sku_match = SKU_REGEX.search(str(itm))
        if not sku_match:
            continue
        sku_code = sku_match.group(1).strip()
        qty_match = QTY_REGEX.search(str(itm))
        qty = int(qty_match.group(1)) if qty_match else 1
        result.append((sku_code, qty))
    return result


def explode_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Explode orders to one row per SKU with quantity."""
    records = []
    for _, row in df.iterrows():
        skus = parse_sku_cell(row["sku"])
        for sku_code, qty in skus:
            records.append(
                {
                    "order_id": row["order_id"],
                    "status": str(row["status"]).strip().lower(),
                    "city": str(row["city"]).strip(),
                    "payment": str(row["payment"]).strip(),
                    "date": row["date"],
                    "sku_code": sku_code,
                    "qty": qty,
                }
            )
    return pd.DataFrame(records)


def compute_combos(df_orders: pd.DataFrame, min_items: int = 2, max_items: int = 5, top_n: int = 10) -> List[Dict]:
    """Compute frequent combinations (order-level)."""
    combos = Counter()
    for order_id, group in df_orders.groupby("order_id"):
        items = sorted(set(group["sku_code"]))
        if len(items) < min_items:
            continue
        for k in range(min_items, min(max_items, len(items)) + 1):
            # simple generation without heavy combinatorics for small k
            from itertools import combinations

            for combo in combinations(items, k):
                combos[frozenset(combo)] += 1
    top = combos.most_common(top_n)
    return [
        {"combo": list(c), "count": cnt}
        for c, cnt in top
    ]


def status_flags(status: str) -> str:
    s = status.strip().lower()
    if "ملغي" in s or "cancel" in s:
        return "canceled"
    if "مسترجع" in s or "return" in s:
        return "returned"
    return "delivered"


def summarize(df_orders: pd.DataFrame) -> Dict:
    df_orders = df_orders.copy()
    df_orders["status_flag"] = df_orders["status"].apply(status_flags)

    top_skus = (
        df_orders.groupby("sku_code")["qty"].sum().sort_values(ascending=False).head(10).reset_index()
    )

    payment_mix = (
        df_orders.groupby("payment")["order_id"].nunique().reset_index().rename(columns={"order_id": "orders"})
    )

    city_mix = (
        df_orders.groupby("city")["order_id"].nunique().sort_values(ascending=False).head(10).reset_index()
    )

    status_by_sku = (
        df_orders.groupby(["sku_code", "status_flag"])["order_id"].nunique().unstack(fill_value=0).reset_index()
    )

    combos = compute_combos(df_orders)

    summary = {
        "top_skus": top_skus.to_dict(orient="records"),
        "payment_mix": payment_mix.to_dict(orient="records"),
        "city_mix": city_mix.to_dict(orient="records"),
        "status_by_sku": status_by_sku.to_dict(orient="records"),
        "top_combos": combos,
    }
    return summary


def save_outputs(summary: Dict, output_dir: str = "data") -> None:
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "salla_orders_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    # save key tables as CSV for easy consumption
    def dump_csv(key: str, filename: str):
        if key in summary:
            pd.DataFrame(summary[key]).to_csv(os.path.join(output_dir, filename), index=False, encoding="utf-8-sig")

    dump_csv("top_skus", "salla_top_skus.csv")
    dump_csv("payment_mix", "salla_payment_mix.csv")
    dump_csv("city_mix", "salla_city_mix.csv")
    dump_csv("status_by_sku", "salla_status_by_sku.csv")
    dump_csv("top_combos", "salla_top_combos.csv")


def run_pipeline():
    orders_raw = load_orders()
    orders_norm = normalize_columns(orders_raw)
    orders_norm["date"] = pd.to_datetime(orders_norm["date"], errors="coerce")
    exploded = explode_orders(orders_norm)
    summary = summarize(exploded)
    save_outputs(summary)
    return summary


if __name__ == "__main__":
    result = run_pipeline()
    print(json.dumps(result, ensure_ascii=False, indent=2))

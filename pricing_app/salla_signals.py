import json
import os
from typing import Dict, Optional

import pandas as pd

DEFAULT_DATA_DIR = "data"
STATUS_FILE = "salla_status_by_sku.csv"
TOP_SKUS_FILE = "salla_top_skus.csv"
CITY_MIX_FILE = "salla_city_mix.csv"
TOP_COMBOS_FILE = "salla_top_combos.csv"


def _load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"لم يتم العثور على الملف: {path}")
    return pd.read_csv(path)


def _normalize_unit(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    min_v, max_v = series.min(), series.max()
    if max_v == min_v:
        return pd.Series(1.0, index=series.index)
    return (series - min_v) / (max_v - min_v)


def build_risk_table(status_df: pd.DataFrame, min_orders: int = 30, max_surcharge: float = 0.15) -> pd.DataFrame:
    required_cols = {"sku_code", "delivered", "canceled", "returned"}
    if not required_cols.issubset(status_df.columns):
        missing = required_cols - set(status_df.columns)
        raise ValueError(f"أعمدة مفقودة لحساب المخاطر: {missing}")

    df = status_df.copy()
    df["total_orders"] = df[["delivered", "canceled", "returned"]].sum(axis=1)
    df = df[df["total_orders"] >= min_orders]
    df["risk_pct"] = (df["canceled"] + df["returned"]) / df["total_orders"]
    df["risk_surcharge"] = (df["risk_pct"] * 0.5).clip(0, max_surcharge)
    df["risk_multiplier"] = 1 + df["risk_surcharge"]
    return df[["sku_code", "delivered", "canceled", "returned", "total_orders", "risk_pct", "risk_surcharge", "risk_multiplier"]]


def build_demand_tables(top_skus_df: pd.DataFrame, city_mix_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    # SKU demand
    if not {"sku_code", "qty"}.issubset(top_skus_df.columns):
        raise ValueError("يجب أن يحتوي top_skus_df على الأعمدة sku_code, qty")
    sku_df = top_skus_df.copy()
    sku_df["qty_norm"] = _normalize_unit(sku_df["qty"])
    sku_df["demand_factor"] = 0.9 + 0.4 * sku_df["qty_norm"]  # نطاق تقريبي 0.9 - 1.3

    # City demand
    city_df = city_mix_df.copy()
    if "orders" not in city_df.columns and "order_id" in city_df.columns:
        city_df = city_df.rename(columns={"order_id": "orders"})
    if not {"city", "orders"}.issubset(city_df.columns):
        raise ValueError("يجب أن يحتوي city_mix_df على الأعمدة city, orders أو order_id")

    city_df["orders_norm"] = _normalize_unit(city_df["orders"])
    city_df["geo_factor"] = 0.95 + 0.2 * city_df["orders_norm"]  # نطاق تقريبي 0.95 - 1.15

    return {"sku": sku_df[["sku_code", "qty", "demand_factor"]], "city": city_df[["city", "orders", "geo_factor"]]}


def build_combo_discounts(top_combos_df: pd.DataFrame, max_discount: float = 0.15) -> pd.DataFrame:
    if not {"combo", "count"}.issubset(top_combos_df.columns):
        raise ValueError("يجب أن يحتوي top_combos_df على الأعمدة combo, count")
    df = top_combos_df.copy()
    max_count = df["count"].max() or 1
    df["popularity_norm"] = df["count"] / max_count
    df["recommended_discount"] = (df["popularity_norm"] * max_discount).clip(0, max_discount)
    return df[["combo", "count", "recommended_discount"]]


def generate_pricing_signals(data_dir: str = DEFAULT_DATA_DIR, output_dir: Optional[str] = None) -> Dict:
    output_dir = output_dir or data_dir
    os.makedirs(output_dir, exist_ok=True)

    status_df = _load_csv(os.path.join(data_dir, STATUS_FILE))
    top_skus_df = _load_csv(os.path.join(data_dir, TOP_SKUS_FILE))
    city_mix_df = _load_csv(os.path.join(data_dir, CITY_MIX_FILE))
    top_combos_df = _load_csv(os.path.join(data_dir, TOP_COMBOS_FILE))

    risk_table = build_risk_table(status_df)
    demand_tables = build_demand_tables(top_skus_df, city_mix_df)
    combo_discounts = build_combo_discounts(top_combos_df)

    risk_path = os.path.join(output_dir, "salla_risk_factors.csv")
    sku_demand_path = os.path.join(output_dir, "salla_demand_factors.csv")
    city_demand_path = os.path.join(output_dir, "salla_city_factors.csv")
    combo_path = os.path.join(output_dir, "salla_combo_discounts.csv")
    risk_table.to_csv(risk_path, index=False)
    demand_tables["sku"].to_csv(sku_demand_path, index=False)
    demand_tables["city"].to_csv(city_demand_path, index=False)
    combo_discounts.to_csv(combo_path, index=False)

    summary = {
        "risk_table": risk_table.to_dict(orient="records"),
        "sku_demand": demand_tables["sku"].to_dict(orient="records"),
        "city_demand": demand_tables["city"].to_dict(orient="records"),
        "combo_discounts": combo_discounts.to_dict(orient="records"),
    }

    with open(os.path.join(output_dir, "salla_pricing_signals.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


def get_signals_for(
    sku_code: str,
    city: Optional[str] = None,
    data_dir: str = DEFAULT_DATA_DIR,
    default_risk_multiplier: float = 1.0,
    default_demand_factor: float = 1.0,
    default_geo_factor: float = 1.0,
) -> Dict:
    """
    إرجاع إشارات تسعير لسعر ديناميكي دون لمس الأكواد القديمة.
    - risk_multiplier: عامل يرفع السعر لتعويض الإلغاء/الاسترجاع.
    - demand_factor: عامل طلب خاص بالـ SKU.
    - geo_factor: عامل طلب خاص بالمدينة.
    - composite_multiplier: حاصل ضرب العوامل لتغذية أي معادلة تسعير.
    """

    def _safe_lookup(path: str, key_col: str, value_col: str, key: str, default: float) -> float:
        if not os.path.exists(path):
            return default
        df = pd.read_csv(path)
        row = df.loc[df[key_col] == key]
        if row.empty:
            return default
        return float(row.iloc[0][value_col])

    risk_multiplier = _safe_lookup(
        os.path.join(data_dir, "salla_risk_factors.csv"), "sku_code", "risk_multiplier", sku_code, default_risk_multiplier
    )
    demand_factor = _safe_lookup(
        os.path.join(data_dir, "salla_demand_factors.csv"), "sku_code", "demand_factor", sku_code, default_demand_factor
    )
    geo_factor = default_geo_factor
    if city:
        geo_factor = _safe_lookup(
            os.path.join(data_dir, "salla_city_factors.csv"), "city", "geo_factor", city, default_geo_factor
        )

    composite_multiplier = risk_multiplier * demand_factor * geo_factor

    return {
        "risk_multiplier": risk_multiplier,
        "demand_factor": demand_factor,
        "geo_factor": geo_factor,
        "composite_multiplier": composite_multiplier,
    }


if __name__ == "__main__":
    summary = generate_pricing_signals()
    print(json.dumps(summary, ensure_ascii=False, indent=2))

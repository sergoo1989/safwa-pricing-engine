"""
تحويل ملف طلبات سلة الخام إلى صيغة منظمة مع تفكيك المنتجات والبكجات
Salla Orders Normalizer - Explodes SKUs from raw format to normalized rows
"""

import pandas as pd
import ast
import re
from pathlib import Path


# ========= 1) إعداد أسماء الأعمدة بالعربي كما هي في ملف سلة =========
ORDER_ID_COL_AR = "رقم الطلب"
STATUS_COL_AR = "حالة الطلب"
CITY_COL_AR = "المدينة"
SKU_COL_AR = "SKU"
PAYMENT_COL_AR = "طريقة الدفع"
DATE_COL_AR = "تاريخ الطلب"


# ========= 2) دالة تفكيك خلية الـ SKU =========
# مثال نص للعنصر الواحد:
# (SKU: OLIVEOILE1000M)زيت زيتون بكر قطفة أولى 1لتر(Qty: 2)
sku_pattern = re.compile(r"\(SKU:\s*([^)]+)\)(.+?)\(Qty:\s*(\d+)\)")


def parse_sku_cell(cell_value):
    """
    ترجع قائمة عناصر:
    كل عنصر dict فيه: sku_code, sku_name, qty
    """
    if pd.isna(cell_value):
        return []

    text = str(cell_value).strip()
    items = []

    # محاولة أولى: تفسير النص كـ list بايثون زي ['...','...']
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            items = parsed
        else:
            items = [str(parsed)]
    except Exception:
        # لو فشلت، نرجع لفصلها يدويًا على الفواصل ,
        if text.startswith("[") and text.endswith("]"):
            inner = text[1:-1]
        else:
            inner = text
        items = [p.strip().strip("'").strip('"') for p in inner.split(",") if p.strip()]

    results = []
    for item in items:
        s = str(item).strip().strip("'").strip('"')
        m = sku_pattern.search(s)
        if m:
            code = m.group(1).strip()
            name = m.group(2).strip()
            qty = int(m.group(3))
        else:
            code = ""
            name = s
            qty = 1

        results.append({
            "sku_code": code,
            "sku_name": name,
            "qty": qty,
        })

    return results


# ========= 3) الدالة الرئيسية =========
def normalize_salla_orders(input_path: str, output_path: str = None):
    """
    تحويل ملف طلبات سلة الخام إلى صيغة منظمة
    
    Args:
        input_path: مسار ملف سلة الأصلي (xlsx أو csv)
        output_path: مسار الملف الناتج (اختياري، افتراضيًا salla_orders_normalized.xlsx)
    
    Returns:
        DataFrame: البيانات المنظمة
    """
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path.parent / "salla_orders_normalized.xlsx"
    else:
        output_path = Path(output_path)

    # قراءة الملف (يدعم xlsx أو csv)
    if input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    else:
        df = pd.read_excel(input_path)

    # توحيد أسماء الأعمدة إلى إنجليزي
    df = df.rename(columns={
        ORDER_ID_COL_AR: "order_id",
        STATUS_COL_AR: "status",
        CITY_COL_AR: "city",
        SKU_COL_AR: "sku_raw",
        PAYMENT_COL_AR: "payment_method",
        DATE_COL_AR: "order_date",
    })

    normalized_rows = []

    # تفجير كل طلب إلى صفوف حسب كل منتج/بكج
    for _, row in df.iterrows():
        sku_items = parse_sku_cell(row["sku_raw"])

        if not sku_items:
            normalized_rows.append({
                "order_id": row["order_id"],
                "order_date": row["order_date"],
                "status": row["status"],
                "city": row["city"],
                "payment_method": row["payment_method"],
                "sku_code": "",
                "sku_name": "",
                "qty": 0,
            })
            continue

        for item in sku_items:
            normalized_rows.append({
                "order_id": row["order_id"],
                "order_date": row["order_date"],
                "status": row["status"],
                "city": row["city"],
                "payment_method": row["payment_method"],
                "sku_code": item["sku_code"],
                "sku_name": item["sku_name"],
                "qty": item["qty"],
            })

    normalized_df = pd.DataFrame(normalized_rows)

    # حفظ الملف الناتج
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_df.to_excel(output_path, index=False)

    print(f"✅ تم إنشاء الملف: {output_path.resolve()}")
    print(f"📊 عدد الطلبات الأصلية: {len(df)}")
    print(f"📦 عدد الصفوف بعد التفكيك: {len(normalized_df)}")
    
    return normalized_df


def main():
    """
    استخدام من سطر الأوامر
    """
    # المسارات افتراضيًا من مجلد data
    import sys
    
    # تحديد المسار النسبي من جذر المشروع
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    
    # البحث عن ملف سلة الخام في المجلد
    input_files = list(data_dir.glob("salla_raw.*")) + list(data_dir.glob("salla_orders_raw.*"))
    
    if not input_files:
        print("❌ لم يتم العثور على ملف سلة خام في مجلد data/")
        print("💡 ضع ملف سلة باسم: salla_raw.xlsx أو salla_raw.csv")
        sys.exit(1)
    
    input_path = input_files[0]
    output_path = data_dir / "salla_orders.csv"
    
    print(f"📂 الملف المصدر: {input_path}")
    print(f"📂 الملف الناتج: {output_path}")
    
    normalize_salla_orders(str(input_path), str(output_path))


if __name__ == "__main__":
    main()

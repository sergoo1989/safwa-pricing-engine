import streamlit as st
import pandas as pd
from datetime import datetime
from pricing_app.data_loader import load_cost_data
from pricing_app.models import ChannelFees
from pricing_app.fees import extract_channel_fees_from_pl
from pricing_app.channels import load_channels, save_channels, ChannelFees as ChannelFeesData
from pricing_app.advanced_pricing import calculate_price_breakdown, create_pricing_table
from pricing_app.ui_components import UIComponents, ChartBuilder, TableFormatter
from pricing_app.utils import ExportManager, FormatHelper, ColorScheme, DateTimeHelper
from pricing_app.advanced_pricing_engine import AdvancedPricingEngine
from pricing_app.salla_signals import get_signals_for
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import zipfile
import io
import sqlite3

# Page Configuration
st.set_page_config(
    page_title="محرك تسعير صفوة - Professional",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "محرك تسعير صفوة الاحترافي"
    }
)

# تحسين التخزين المؤقت
if 'cache_ttl' not in st.session_state:
    st.session_state.cache_ttl = 3600  # ساعة واحدة

# Professional CSS Styling
st.markdown(
    """
<style>
    /* RTL Support */
    [data-testid="stSidebar"] {
        direction: rtl;
    }
    
    /* Modern Background */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
    }
    
    /* Enhanced Metrics */
    [data-testid="stMetric"] {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #1E88E5;
    }
    
    /* Professional Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(30, 136, 229, 0.3);
    }
    
    /* Enhanced Sidebar */
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #1E88E5 0%, #1565C0 100%);
    }
    
    [data-testid="stSidebar"] .stButton>button {
        color: white !important;
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    [data-testid="stSidebar"] .stButton>button:hover {
        background: rgba(255,255,255,0.2);
        border-color: rgba(255,255,255,0.3);
    }
    
    /* Beautiful Headers */
    h1, h2, h3 {
        color: #1a1a1a;
        font-weight: 700;
    }
    
    h1 {
        background: linear-gradient(90deg, #1E88E5 0%, #1976D2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Enhanced Tables */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* Info Boxes */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
    }
    
    /* Success Messages */
    .stSuccess {
        background-color: #E8F5E9;
        border-left-color: #43A047;
    }
    
    /* Warning Messages */
    .stWarning {
        background-color: #FFF3E0;
        border-left-color: #FB8C00;
    }
    
    /* Error Messages */
    .stError {
        background-color: #FFEBEE;
        border-left-color: #E53935;
    }
    
    /* Info Messages */
    .stInfo {
        background-color: #E1F5FE;
        border-left-color: #29B6F6;
    }
</style>
""",
    unsafe_allow_html=True,
)
# ========== دوال محسّنة للأداء ==========

@st.cache_data(ttl=3600, show_spinner=False)
def load_salla_orders_cached(file_path):
    """تحميل طلبات سلة مع تخزين مؤقت"""
    if os.path.exists(file_path):
        return pd.read_csv(file_path, low_memory=False)
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def load_pricing_data_cached(products_file, packages_file):
    """تحميل بيانات التسعير مع تخزين مؤقت"""
    products_df = None
    packages_df = None
    
    if os.path.exists(products_file):
        products_df = pd.read_csv(products_file, low_memory=False)
    if os.path.exists(packages_file):
        packages_df = pd.read_csv(packages_file, low_memory=False)
    
    return products_df, packages_df

@st.cache_data(ttl=3600, show_spinner=False)  
def process_salla_data_lite(orders_df, filters):
    """معالجة خفيفة لبيانات سلة بدون تحليلات ثقيلة"""
    if orders_df is None:
        return None
    
    df = orders_df.copy()
    
    # تطبيق الفلاتر
    if filters.get('year') != "الكل":
        df = df[df['year'] == filters['year']]
    if filters.get('month') != "الكل":
        df = df[df['month'] == filters['month']]
    if filters.get('status') != "الكل":
        df = df[df['status'] == filters['status']]
    if filters.get('city') != "الكل":
        df = df[df['city'] == filters['city']]
    if filters.get('payment') != "الكل":
        df = df[df['payment_method'] == filters['payment']]
    
    return df

# Initialize session state for page navigation
if "page" not in st.session_state:
    st.session_state.page = "main"

# Professional Header - نسخة مبسطة
st.markdown(
    """
<div style="text-align: center; padding: 15px; background: linear-gradient(90deg, #1E88E5 0%, #1976D2 100%); border-radius: 10px; margin-bottom: 20px;">
    <h1 style="color: white; margin: 0; font-size: 2em;">💎 محرك تسعير صفوة</h1>
    <p style="color: #E3F2FD; margin: 5px 0 0 0;">Safwa Pricing Engine</p>
</div>
""",
    unsafe_allow_html=True,
)


# Load data
@st.cache_data
def load_all_data():
    materials, product_recipes, products_summary, package_compositions, packages_summary = load_cost_data("data")
    return materials, product_recipes, products_summary, package_compositions, packages_summary


try:
    materials, product_recipes, products_summary, package_compositions, packages_summary = load_all_data()
except Exception as e:
    st.error(f"❌ خطأ في تحميل البيانات: {e}")
    st.info("""
    📝 **ملفات البيانات المطلوبة في مجلد `data`:**
    - `raw_materials_template.csv` (المواد الخام)
    - `products_template.csv` (المنتجات)
    - `packages_template.csv` (البكجات)
    
    💡 **كيفية الحل:**
    1. انتقل إلى صفحة "رفع الملفات" من القائمة الجانبية
    2. قم برفع الملفات المطلوبة
    3. أو قم بإنشاء ملفات جديدة فارغة
    """)
    
    # محاولة إنشاء ملفات فارغة كحل مؤقت
    import os
    os.makedirs("data", exist_ok=True)
    
    if st.button("🔧 إنشاء ملفات بيانات فارغة"):
        import pandas as pd
        
        # إنشاء ملف المواد الخام
        pd.DataFrame({
            'Material_Name': [],
            'Material_SKU': [],
            'Category': [],
            'Purchase_UoM': [],
            'Cost_Price': []
        }).to_csv('data/raw_materials_template.csv', index=False)
        
        # إنشاء ملف المنتجات
        pd.DataFrame({
            'Product_Name': [],
            'Product_SKU': [],
            'Material_SKU': [],
            'Quantity': []
        }).to_csv('data/products_template.csv', index=False)
        
        # إنشاء ملف البكجات
        pd.DataFrame({
            'Package_Name': [],
            'Package_SKU': [],
            'Item_SKU': [],
            'Quantity': []
        }).to_csv('data/packages_template.csv', index=False)
        
        st.success("✅ تم إنشاء الملفات الفارغة! يرجى إعادة تحميل الصفحة.")
        st.rerun()
    
    st.stop()

# Initialize advanced pricing engine
pricing_engine = AdvancedPricingEngine()

# Sidebar Navigation
with st.sidebar:
    st.markdown("### القائمة الرئيسية")

    # Navigation buttons - vertical layout
    if st.button("📤 رفع الملفات", help="رفع الملفات", key="btn_upload", width="stretch"):
        st.session_state.page = "upload"

    if st.button("💰 تكلفة البضاعة", help="تكلفة البضاعة", key="btn_cogs", width="stretch"):
        st.session_state.page = "cogs"

    if st.button("⚙️ المنصات", help="إعدادات المنصات", key="btn_settings", width="stretch"):
        st.session_state.page = "settings"

    if st.button(
        "💵 تسعير منتج/بكج فردي", help="التسعير للمنتج أو البكج الفردي", key="btn_pricing", width="stretch"
    ):
        st.session_state.page = "pricing"

    if st.button("📊 تسعير منصة كاملة", help="تسعير منصة كاملة", key="btn_profit_margins", width="stretch"):
        st.session_state.page = "profit_margins"
    
    if st.button("🎁 بكجات جديدة", help="إنشاء بكج مخصص جديد", key="btn_custom_package", width="stretch"):
        st.session_state.page = "custom_package"

    if st.button("🗂️ السجلات المحفوظة", help="عرض وتحميل السجلات المحفوظة", key="btn_history", width="stretch"):
        st.session_state.page = "history"

    if st.button("📦 تحليل سلة", help="مخاطر/طلب/مدن/كمبو من بيانات سلة", key="btn_salla_analysis", width="stretch"):
        st.session_state.page = "salla_analysis"
    
    st.markdown("---")
    st.markdown("### 📊 التحليل المالي")
    
    if st.button("💹 تحليل الربحية", help="تحليل الأرباح والخسائر", key="btn_profitability", width="stretch"):
        st.session_state.page = "profitability"
    
    if st.button("🔍 مراجعة التسعير", help="مقارنة الأسعار المتوقعة بالفعلية", key="btn_pricing_review", width="stretch"):
        st.session_state.page = "pricing_review"
    
    if st.button("📈 Dashboard المالي", help="مؤشرات الأداء المالي", key="btn_financial_dashboard", width="stretch"):
        st.session_state.page = "financial_dashboard"
    
    if st.button("🎯 تحليل P&L للقنوات", help="تحليل موحد + تنبيهات + حوكمة خصم", key="btn_pl_insights", width="stretch"):
        st.session_state.page = "pl_channel_insights"
    if st.button("🧠 تسعير معتمد على P&L", help="حاسبة سعر/سعر أرضي/سقف خصم", key="btn_smart_pricing_pl", width="stretch"):
        st.session_state.page = "smart_pricing_pl"


# Page: Upload Files
if st.session_state.page == "upload":
    st.header("رفع الملفات")
    st.markdown("---")

    # Clear data button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ مسح جميع البيانات", type="secondary", width="stretch"):
            # Confirm deletion
            if "confirm_delete" not in st.session_state:
                st.session_state.confirm_delete = True
                st.rerun()

    # Show confirmation dialog
    if st.session_state.get("confirm_delete", False):
        st.warning("⚠️ هل أنت متأكد من حذف جميع البيانات؟ هذا الإجراء لا يمكن التراجع عنه!")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ نعم، حذف الكل"):
                try:
                    data_files = [
                        "data/raw_materials_template.csv",
                        "data/products_template.csv",
                        "data/packages_template.csv",
                        "data/pricing_history_test.csv",
                        "data/profit_loss.csv",
                    ]
                    deleted_files = []

                    for file in data_files:
                        if os.path.exists(file):
                            os.remove(file)
                            deleted_files.append(file)

                    if deleted_files:
                        st.success(f"✅ تم حذف {len(deleted_files)} ملف بنجاح")
                        st.cache_data.clear()
                        st.session_state.confirm_delete = False
                        st.rerun()
                    else:
                        st.info("لا توجد ملفات للحذف")
                        st.session_state.confirm_delete = False
                except Exception as e:
                    st.error(f"خطأ في حذف البيانات: {e}")
                    st.session_state.confirm_delete = False

        with col2:
            if st.button("❌ لا، إلغاء"):
                st.session_state.confirm_delete = False
                st.rerun()

    st.markdown("---")

    tab_materials, tab_products, tab_packages, tab_pl, tab_salla = st.tabs([
        "المواد الخام", "المنتجات", "البكجات", "الأرباح والخسائر", "طلبات سلة"
    ])

    # Tab 1: Materials
    with tab_materials:
        st.subheader("رفع المواد الخام")
        st.info("صيغة الملف: CSV أو Excel (.xlsx)")

        raw_materials_file = st.file_uploader("اختر ملف المواد الخام", type=["csv", "xlsx"], key="upload_raw_materials")

        if raw_materials_file is not None:
            try:
                if raw_materials_file.name.endswith(".csv"):
                    df = pd.read_csv(raw_materials_file)
                else:
                    df = pd.read_excel(raw_materials_file)

                st.success(f"تم تحميل الملف بنجاح ({len(df)} صف)")
                st.dataframe(df, width="stretch")

                if st.button("حفظ المواد الخام"):
                    try:
                        df.to_csv("data/raw_materials_template.csv", index=False, encoding="utf-8-sig")
                        st.success("تم حفظ المواد الخام في data/raw_materials_template.csv")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"خطأ في الحفظ: {e}")
            except Exception as e:
                st.error(f"خطأ في تحميل الملف: {e}")

        st.markdown("---")
        st.subheader("متطلبات الملف:")
        st.code(
            """material_sku
material_name
category
unit
cost_per_unit"""
        )

    # Tab 2: Products
    with tab_products:
        st.subheader("رفع المنتجات")
        st.info("صيغة الملف: CSV أو Excel (.xlsx)")

        products_file = st.file_uploader("اختر ملف المنتجات", type=["csv", "xlsx"], key="upload_products")

        if products_file is not None:
            try:
                if products_file.name.endswith(".csv"):
                    df = pd.read_csv(products_file)
                else:
                    df = pd.read_excel(products_file)

                st.success(f"تم تحميل الملف بنجاح ({len(df)} صف)")
                st.dataframe(df, width="stretch")

                if st.button("حفظ المنتجات"):
                    try:
                        df.to_csv("data/products_template.csv", index=False, encoding="utf-8-sig")
                        st.success("تم حفظ المنتجات في data/products_template.csv")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"خطأ في الحفظ: {e}")
            except Exception as e:
                st.error(f"خطأ في تحميل الملف: {e}")

        st.markdown("---")
        st.subheader("متطلبات الملف:")
        st.code(
            """product_sku
product_name
material_code
quantity"""
        )

    # Tab 3: Packages
    with tab_packages:
        st.subheader("رفع البكجات")
        st.info("صيغة الملف: CSV أو Excel (.xlsx)")

        packages_file = st.file_uploader("اختر ملف البكجات", type=["csv", "xlsx"], key="upload_packages")

        if packages_file is not None:
            try:
                if packages_file.name.endswith(".csv"):
                    df = pd.read_csv(packages_file)
                else:
                    df = pd.read_excel(packages_file)

                st.success(f"تم تحميل الملف بنجاح ({len(df)} صف)")
                st.dataframe(df, width="stretch")

                if st.button("حفظ البكجات"):
                    try:
                        df.to_csv("data/packages_template.csv", index=False, encoding="utf-8-sig")
                        st.success("تم حفظ البكجات في data/packages_template.csv")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"خطأ في الحفظ: {e}")
            except Exception as e:
                st.error(f"خطأ في تحميل الملف: {e}")

        st.markdown("---")
        st.subheader("متطلبات الملف:")
        st.code(
            """package_sku
package_name
product_sku
quantity"""
        )

    # Tab 4: P&L (Profit and Loss)
    with tab_pl:
        st.subheader("رفع ملف الأرباح والخسائر (P&L)")
        st.info("صيغة الملف: CSV أو Excel (.xlsx)")

        st.markdown(
            """
        **📋 متطلبات الملف:**
        - Years (السنة)
        - date (الشهر)
        - Account Level 1 (نوع الحساب)
        - Account Level 2 (تفاصيل الحساب)
        - Cost Center (مركز التكلفة/القناة)
        - Account Level 3 (تفاصيل إضافية)
        - net_amount (المبلغ)
        """
        )

        pl_file = st.file_uploader("اختر ملف الأرباح والخسائر", type=["csv", "xlsx"], key="upload_pl")

        if pl_file is not None:
            try:
                if pl_file.name.endswith(".csv"):
                    df = pd.read_csv(pl_file)
                else:
                    df = pd.read_excel(pl_file)

                df.columns = df.columns.str.strip()

                st.success(f"✅ تم تحميل الملف بنجاح ({len(df):,} صف)")

                st.markdown("##### عينة من البيانات:")
                st.dataframe(df.head(10), use_container_width=True)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if "Years" in df.columns:
                        st.metric("السنوات", df["Years"].nunique())
                with col2:
                    if "Account Level 1" in df.columns:
                        st.metric("أنواع الحسابات", df["Account Level 1"].nunique())
                with col3:
                    if "Cost Center" in df.columns:
                        st.metric("مراكز التكلفة", df["Cost Center"].nunique())
                with col4:
                    if "net_amount" in df.columns or " net_amount " in df.columns:
                        amount_col = "net_amount" if "net_amount" in df.columns else " net_amount "
                        df[amount_col] = df[amount_col].astype(str).str.replace(",", "").astype(float)
                        total = df[amount_col].sum()
                        st.metric("الإجمالي", f"{total:,.2f} SAR")

                if st.button("💾 حفظ ملف الأرباح والخسائر", type="primary", use_container_width=True):
                    try:
                        if "net_amount" in df.columns:
                            df["net_amount"] = df["net_amount"].astype(str).str.replace(",", "").astype(float)
                        elif " net_amount " in df.columns:
                            df[" net_amount "] = df[" net_amount "].astype(str).str.replace(",", "").astype(float)

                        df.to_csv("data/profit_loss.csv", index=False, encoding="utf-8-sig")
                        st.success("✅ تم حفظ ملف الأرباح والخسائر في data/profit_loss.csv")
                        st.session_state.pl_uploaded = True
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ خطأ في الحفظ: {e}")

            except Exception as e:
                st.error(f"❌ خطأ في تحميل الملف: {e}")
                st.info("تأكد من أن الملف يحتوي على الأعمدة المطلوبة")

    # Tab 5: طلبات سلة (ملف كبير)
    with tab_salla:
        st.subheader("رفع ملف طلبات سلة (كبير الحجم)")
        st.info(
            "الملف قد يكون كبير جداً؛ سيتم عرض عينة فقط للتأكد، ثم حفظ الملف كاملاً في data/salla_orders.csv"
        )

        salla_file = st.file_uploader(
            "اختر ملف الطلبات (CSV/Excel/ZIP)", type=["csv", "xlsx", "zip", "gz"], key="upload_salla_orders"
        )

        if salla_file is not None:
            try:
                # دعم الملفات المضغوطة لتقليل الحجم
                filename = salla_file.name.lower()

                def read_any(file_like, name):
                    if name.endswith(".csv"):
                        return pd.read_csv(file_like, low_memory=False)
                    if name.endswith(".xlsx"):
                        return pd.read_excel(file_like)
                    if name.endswith(".gz"):
                        return pd.read_csv(file_like, compression="gzip", low_memory=False)
                    raise ValueError("صيغة غير مدعومة")

                if filename.endswith(".zip"):
                    with zipfile.ZipFile(salla_file) as zf:
                        members = [m for m in zf.namelist() if not m.endswith("/")]
                        if not members:
                            raise ValueError("الملف المضغوط فارغ")
                        target = members[0]
                        with zf.open(target) as f:
                            df_orders = read_any(f, target)
                else:
                    df_orders = read_any(salla_file, filename)

                df_orders.columns = df_orders.columns.str.strip()

                st.success(f"✅ تم تحميل الملف بنجاح ({len(df_orders):,} صف)")

                # عرض عينة صغيرة فقط لتجنب البطء
                st.markdown("##### عينة (أول 10 صفوف):")
                st.dataframe(df_orders.head(10), use_container_width=True)

                # اكتشاف الأعمدة المحتملة
                col_map = {
                    "order_id": ["رقم الطلب", "order_id", "id"],
                    "status": ["حالة الطلب", "status"],
                    "city": ["المدينة", "city"],
                    "sku": ["SKU", "sku", "items"],
                    "payment": ["طريقة الدفع", "payment", "pay_method"],
                    "date": ["تاريخ الطلب", "order_date", "date"],
                }

                resolved = {}
                for key, options in col_map.items():
                    found = [c for c in df_orders.columns if c in options]
                    if found:
                        resolved[key] = found[0]

                # ملخص سريع إذا توفرت الأعمدة الرئيسية
                cols = resolved
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("عدد الطلبات", f"{len(df_orders):,}")
                if "status" in cols:
                    with c2:
                        st.metric("عدد الحالات", df_orders[cols["status"]].nunique())
                if "city" in cols:
                    with c3:
                        st.metric("عدد المدن", df_orders[cols["city"]].nunique())
                if "date" in cols:
                    try:
                        dates = pd.to_datetime(df_orders[cols["date"]], errors="coerce")
                        with c4:
                            st.metric("المدى الزمني", f"{dates.min().date()} → {dates.max().date()}")
                    except Exception:
                        pass

                if st.button("💾 حفظ ملف طلبات سلة", type="primary", use_container_width=True):
                    try:
                        os.makedirs("data", exist_ok=True)
                        csv_path = "data/salla_orders.csv"
                        db_path = "data/salla_orders.db"

                        # حفظ CSV
                        df_orders.to_csv(csv_path, index=False, encoding="utf-8-sig")

                        # حفظ في SQLite لسهولة الاستعلام لاحقاً
                        with sqlite3.connect(db_path) as conn:
                            df_orders.to_sql("salla_orders", conn, if_exists="replace", index=False)

                        st.success(
                            "✅ تم حفظ ملف الطلبات في data/salla_orders.csv وفي قاعدة بيانات SQLite: data/salla_orders.db (جدول salla_orders)"
                        )
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ خطأ في الحفظ: {e}")

            except Exception as e:
                st.error(f"❌ خطأ في تحميل الملف: {e}")
                st.info("تأكد من أن الملف بصيغة CSV أو Excel، وقد يكون حجمه كبيراً")

        st.markdown("---")
        st.subheader("بدون رفع عبر المتصفح (ملف موجود على السيرفر)")
        st.caption("إذا كان الرفع يعطي 413، ضع الملف يدوياً في مجلد data ثم حمّله من هنا.")

        os.makedirs("data", exist_ok=True)
        existing_files = [f for f in os.listdir("data") if f.startswith("salla_orders") and not f.endswith(".db")]
        if existing_files:
            selected = st.selectbox("اختر ملفاً موجوداً في data/", existing_files, key="existing_salla_file")
            if st.button("تحميل الملف الموجود", type="primary"):
                try:
                    path = os.path.join("data", selected)
                    name = selected.lower()

                    def read_any(file_path, name):
                        if name.endswith(".csv"):
                            return pd.read_csv(file_path, low_memory=False)
                        if name.endswith(".xlsx"):
                            return pd.read_excel(file_path)
                        if name.endswith(".gz"):
                            return pd.read_csv(file_path, compression="gzip", low_memory=False)
                        if name.endswith(".zip"):
                            with zipfile.ZipFile(file_path) as zf:
                                members = [m for m in zf.namelist() if not m.endswith("/")]
                                if not members:
                                    raise ValueError("الملف المضغوط فارغ")
                                target = members[0]
                                with zf.open(target) as f:
                                    if target.endswith(".csv"):
                                        return pd.read_csv(f, low_memory=False)
                                    if target.endswith(".xlsx"):
                                        return pd.read_excel(f)
                                    if target.endswith(".gz"):
                                        return pd.read_csv(f, compression="gzip", low_memory=False)
                                    raise ValueError("صيغة داخلية غير مدعومة")
                        raise ValueError("صيغة غير مدعومة")

                    df_orders = read_any(path, name)
                    st.success(f"✅ تم تحميل الملف الموجود ({len(df_orders):,} صف)")
                    st.dataframe(df_orders.head(10), use_container_width=True)

                    # حفظ في CSV و SQLite لتوحيد المسارات
                    csv_path = "data/salla_orders.csv"
                    db_path = "data/salla_orders.db"
                    df_orders.to_csv(csv_path, index=False, encoding="utf-8-sig")
                    with sqlite3.connect(db_path) as conn:
                        df_orders.to_sql("salla_orders", conn, if_exists="replace", index=False)

                    st.success("✅ تم حفظ الملف إلى data/salla_orders.csv وقاعدة البيانات data/salla_orders.db (جدول salla_orders)")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ خطأ في قراءة الملف الموجود: {e}")
        else:
            st.info("ضع الملف يدوياً في مجلد data ثم حدّث الصفحة لاختياره من القائمة.")

# Page: COGS (Cost of Goods Sold)
elif st.session_state.page == "cogs":
    st.header("تكلفة البضاعة (COGS)")
    st.markdown("---")

    # Validation checks
    st.subheader("التحقق من صحة البيانات")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("إجمالي المواد الخام", len(materials))

    with col2:
        st.metric("إجمالي المنتجات", len(product_recipes))

    with col3:
        st.metric("إجمالي البكجات", len(package_compositions))

    st.markdown("---")

    # Validation: Check Products have Materials
    st.subheader("التحقق من المنتجات")

    products_warnings = []
    for product_sku, materials_dict in product_recipes.items():
        if not materials_dict:
            products_warnings.append(f"المنتج {product_sku} بدون مواد خام")
        else:
            missing_materials = []
            for material_code in materials_dict.keys():
                if material_code not in materials:
                    missing_materials.append(material_code)

            if missing_materials:
                products_warnings.append(f"المنتج {product_sku} يحتاج مواد غير موجودة: {', '.join(missing_materials)}")

    if products_warnings:
        st.warning(f"وجدنا {len(products_warnings)} تحذيرات في المنتجات:")
        for warning in products_warnings:
            st.write(warning)
    else:
        st.success("جميع المنتجات لديها مواد خام موجودة")

    st.markdown("---")

    # Validation: Check Packages have Products
    st.subheader("التحقق من البكجات")

    packages_warnings = []
    product_skus = list(product_recipes.keys())
    package_skus = list(package_compositions.keys())
    material_skus = list(materials.keys())

    for package_sku, components_dict in package_compositions.items():
        if not components_dict:
            packages_warnings.append(f"الباقة {package_sku} بدون مكونات")
        else:
            missing_components = []
            for component_sku in components_dict.keys():
                # Check if component exists as product, package, or material
                if (
                    component_sku not in product_skus
                    and component_sku not in package_skus
                    and component_sku not in material_skus
                ):
                    missing_components.append(component_sku)

            if missing_components:
                packages_warnings.append(
                    f"الباقة {package_sku} تحتوي على مكونات غير موجودة: {', '.join(missing_components)}"
                )

    if packages_warnings:
        st.warning(f"وجدنا {len(packages_warnings)} تحذيرات في البكجات:")
        for warning in packages_warnings:
            st.write(warning)
    else:
        st.success("جميع البكجات لديها مكونات موجودة")

    st.markdown("---")

    # COGS Calculation Table
    st.subheader("جدول حساب تكلفة البضاعة")

    cogs_data = []

    # Helper function to calculate cost of any component (material, product, or package)
    def calculate_component_cost(sku, component_type="product"):
        """Calculate cost of a component based on its type"""
        if component_type == "material" and sku in materials:
            return materials[sku].cost_per_unit
        elif component_type == "product" and sku in product_recipes:
            # Sum all materials in this product
            total = 0
            for material_code, mat_qty in product_recipes[sku].items():
                if material_code in materials:
                    total += materials[material_code].cost_per_unit * mat_qty
            return total
        elif component_type == "package" and sku in package_compositions:
            # Recursively calculate package cost
            total = 0
            for comp_sku, comp_qty in package_compositions[sku].items():
                # Determine type: check if it's a product, package, or material
                if comp_sku in product_recipes:
                    comp_cost = calculate_component_cost(comp_sku, "product")
                elif comp_sku in package_compositions:
                    comp_cost = calculate_component_cost(comp_sku, "package")
                elif comp_sku in materials:
                    comp_cost = calculate_component_cost(comp_sku, "material")
                else:
                    comp_cost = 0
                total += comp_cost * comp_qty
            return total
        return 0

    # Product COGS
    st.write("**تكلفة المنتجات:**")
    for product_sku, materials_dict in product_recipes.items():
        product_name = products_summary[products_summary["Product_SKU"] == product_sku]["Product_Name"].values
        product_name = product_name[0] if len(product_name) > 0 else product_sku

        total_cost = 0
        details = []

        for material_code, quantity in materials_dict.items():
            if material_code in materials:
                material = materials[material_code]
                cost = material.cost_per_unit * quantity
                total_cost += cost
                details.append(f"{material_code}: {quantity} x {material.cost_per_unit:.2f} = {cost:.2f}")

        cogs_data.append(
            {
                "النوع": "منتج",
                "SKU": product_sku,
                "الاسم": product_name,
                "التكلفة": total_cost,
                "التفاصيل": " | ".join(details) if details else "بدون مواد",
            }
        )

    # Package COGS
    st.write("**تكلفة البكجات:**")
    for package_sku, components_dict in package_compositions.items():
        package_name = packages_summary[packages_summary["Package_SKU"] == package_sku]["Package_Name"].values
        package_name = package_name[0] if len(package_name) > 0 else package_sku

        total_cost = 0
        details = []

        for component_sku, quantity in components_dict.items():
            # Determine component type and calculate its cost
            if component_sku in product_recipes:
                # It's a product
                comp_cost = calculate_component_cost(component_sku, "product")
                comp_type = "منتج"
            elif component_sku in package_compositions:
                # It's a package
                comp_cost = calculate_component_cost(component_sku, "package")
                comp_type = "بكج"
            elif component_sku in materials:
                # It's a material
                comp_cost = calculate_component_cost(component_sku, "material")
                comp_type = "مادة"
            else:
                comp_cost = 0
                comp_type = "غير معروف"

            cost = comp_cost * quantity
            total_cost += cost
            details.append(f"{component_sku} ({comp_type}): {quantity} x {comp_cost:.2f} = {cost:.2f}")

        cogs_data.append(
            {
                "النوع": "بكج",
                "SKU": package_sku,
                "الاسم": package_name,
                "التكلفة": total_cost,
                "التفاصيل": " | ".join(details) if details else "بدون مكونات",
            }
        )

    cogs_df = pd.DataFrame(cogs_data)
    if cogs_df.empty:
        # Ensure expected columns exist to avoid KeyError when data is missing
        cogs_df = pd.DataFrame(columns=["النوع", "SKU", "الاسم", "التكلفة", "التفاصيل"])

    # Separate dataframes for products and packages
    products_cogs_df = cogs_df[cogs_df["النوع"] == "منتج"].copy()
    packages_cogs_df = cogs_df[cogs_df["النوع"] == "بكج"].copy()

    # Products Table
    st.write("**جدول تكلفة المنتجات:**")
    if len(products_cogs_df) > 0:
        # Filter and Export for Products
        col_filter, col_export = st.columns([3, 1])
        with col_filter:
            products_search = st.text_input(
                "🔍 بحث في المنتجات (SKU أو الاسم)", key="products_search", placeholder="ابحث..."
            )
        with col_export:
            st.download_button(
                "📥 تصدير المنتجات",
                data=products_cogs_df[["SKU", "الاسم", "التكلفة", "التفاصيل"]].to_csv(
                    index=False, encoding="utf-8-sig"
                ),
                file_name="products_cogs.csv",
                mime="text/csv",
                width="stretch",
            )

        # Apply filter
        filtered_products = products_cogs_df
        if products_search:
            filtered_products = products_cogs_df[
                products_cogs_df["SKU"].str.contains(products_search, case=False, na=False)
                | products_cogs_df["الاسم"].str.contains(products_search, case=False, na=False)
            ]

        st.dataframe(
            filtered_products[["SKU", "الاسم", "التكلفة", "التفاصيل"]].style.format({"التكلفة": "{:.2f} SAR"}),
            width="stretch",
        )
        st.caption(f"عرض {len(filtered_products)} من {len(products_cogs_df)} منتج")
    else:
        st.info("لا توجد منتجات")

    st.markdown("---")

    # Packages Table
    st.write("**جدول تكلفة البكجات:**")
    if len(packages_cogs_df) > 0:
        # Filter and Export for Packages
        col_filter_pkg, col_export_pkg = st.columns([3, 1])
        with col_filter_pkg:
            packages_search = st.text_input(
                "🔍 بحث في البكجات (SKU أو الاسم)", key="packages_search", placeholder="ابحث..."
            )
        with col_export_pkg:
            st.download_button(
                "📥 تصدير البكجات",
                data=packages_cogs_df[["SKU", "الاسم", "التكلفة", "التفاصيل"]].to_csv(
                    index=False, encoding="utf-8-sig"
                ),
                file_name="packages_cogs.csv",
                mime="text/csv",
                width="stretch",
            )

        # Apply filter
        filtered_packages = packages_cogs_df
        if packages_search:
            filtered_packages = packages_cogs_df[
                packages_cogs_df["SKU"].str.contains(packages_search, case=False, na=False)
                | packages_cogs_df["الاسم"].str.contains(packages_search, case=False, na=False)
            ]

        st.dataframe(
            filtered_packages[["SKU", "الاسم", "التكلفة", "التفاصيل"]].style.format({"التكلفة": "{:.2f} SAR"}),
            width="stretch",
        )
        st.caption(f"عرض {len(filtered_packages)} من {len(packages_cogs_df)} بكج")
    else:
        st.info("لا توجد بكجات")

    # Summary Statistics
    st.subheader("إحصائيات التكاليف")

    col1, col2, col3, col4 = st.columns(4)

    products_cogs = products_cogs_df["التكلفة"]
    packages_cogs = packages_cogs_df["التكلفة"]

    with col1:
        st.metric("متوسط تكلفة المنتج", f"{products_cogs.mean():.2f} SAR")

    with col2:
        st.metric("أعلى تكلفة منتج", f"{products_cogs.max():.2f} SAR" if len(products_cogs) > 0 else "لا يوجد")

    with col3:
        st.metric("متوسط تكلفة الباقة", f"{packages_cogs.mean():.2f} SAR")

    with col4:
        st.metric("أعلى تكلفة باقة", f"{packages_cogs.max():.2f} SAR" if len(packages_cogs) > 0 else "لا يوجد")

    # Visualization - Separate charts for products and packages
    st.markdown("---")
    st.subheader("رسم بياني - تكاليف المنتجات")

    if len(products_cogs_df) > 0:
        fig_products = px.bar(
            products_cogs_df,
            x="SKU",
            y="التكلفة",
            title="تكلفة المنتجات (COGS)",
            labels={"التكلفة": "التكلفة (SAR)", "SKU": "رمز المنتج"},
            color="التكلفة",
            color_continuous_scale="Blues",
            text="التكلفة",
        )
        fig_products.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_products.update_layout(xaxis_tickangle=-45, height=500, hovermode="x unified", showlegend=False)
        st.plotly_chart(fig_products, width="stretch")
    else:
        st.info("لا توجد منتجات")

    st.markdown("---")
    st.subheader("رسم بياني - تكاليف البكجات")

    if len(packages_cogs_df) > 0:
        fig_packages = px.bar(
            packages_cogs_df,
            x="SKU",
            y="التكلفة",
            title="تكلفة البكجات (COGS)",
            labels={"التكلفة": "التكلفة (SAR)", "SKU": "رمز الباقة"},
            color="التكلفة",
            color_continuous_scale="Greens",
            text="التكلفة",
        )
        fig_packages.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_packages.update_layout(xaxis_tickangle=-45, height=500, hovermode="x unified", showlegend=False)
        st.plotly_chart(fig_packages, width="stretch")
    else:
        st.info("لا توجد بكجات")

    st.markdown("---")

    # Summary charts - Distribution
    st.subheader("الرسوم البيانية الملخصة")

    col_summary1, col_summary2, col_summary3 = st.columns(3)

    # Chart 1: Distribution by Type
    with col_summary1:
        st.write("**توزيع التكاليف حسب النوع**")
        type_summary = cogs_df.groupby("النوع")["التكلفة"].sum().reset_index()
        fig_pie = px.pie(
            type_summary,
            values="التكلفة",
            names="النوع",
            title="نسبة التكاليف",
            color_discrete_map={"منتج": "#1f77b4", "بكج": "#2ca02c"},
            labels={"التكلفة": "التكلفة (SAR)"},
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, width="stretch")

    # Chart 2: Top 10 Items
    with col_summary2:
        st.write("**أعلى 10 عناصر تكلفة**")
        # Ensure numeric dtype for cost to avoid errors when data is empty or mixed
        cogs_df["التكلفة"] = pd.to_numeric(cogs_df["التكلفة"], errors="coerce").fillna(0)
        top_items = cogs_df.nlargest(10, "التكلفة")[["SKU", "النوع", "التكلفة"]].copy()
        fig_top = px.bar(
            top_items,
            y="SKU",
            x="التكلفة",
            orientation="h",
            color="النوع",
            title="أعلى العناصر تكلفة",
            labels={"التكلفة": "التكلفة (SAR)", "SKU": "رمز العنصر"},
            color_discrete_map={"منتج": "#1f77b4", "بكج": "#2ca02c"},
            text="التكلفة",
        )
        fig_top.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_top.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_top, width="stretch")

    # Chart 3: Statistics Summary
    with col_summary3:
        st.write("**إحصائيات ملخصة**")

        # Create summary statistics dataframe
        stats_data = {
            "البيان": [
                "إجمالي المنتجات",
                "إجمالي البكجات",
                "إجمالي التكاليف",
                "متوسط تكلفة المنتج",
                "متوسط تكلفة الباقة",
                "أعلى منتج تكلفة",
                "أعلى بكجة تكلفة",
            ],
            "القيمة": [
                f"{len(products_cogs_df)}",
                f"{len(packages_cogs_df)}",
                f"{cogs_df['التكلفة'].sum():.2f} SAR",
                f"{products_cogs.mean():.2f} SAR" if len(products_cogs) > 0 else "0",
                f"{packages_cogs.mean():.2f} SAR" if len(packages_cogs) > 0 else "0",
                f"{products_cogs.max():.2f} SAR" if len(products_cogs) > 0 else "0",
                f"{packages_cogs.max():.2f} SAR" if len(packages_cogs) > 0 else "0",
            ],
        }
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, width="stretch", hide_index=True)

# Page: Settings
elif st.session_state.page == "settings":
    st.header("إعدادات القنوات والتسعير")
    st.markdown("---")

    # Load existing channels
    channels_file = "data/channels.json"
    channels = load_channels(channels_file)

    # Tab 1: Manage Channels
    # Tab 2: Channel Pricing
    tab_manage = st.tabs(["إدارة القنوات"])[0]

    # ===== Tab 1: Manage Channels =====
    with tab_manage:
        st.subheader("إدارة قنوات البيع")

        # Display existing channels
        if channels:
            st.write(f"**القنوات المحفوظة ({len(channels)}):**")
            col1, col2 = st.columns(2)

            with col1:
                existing_channels = list(channels.keys())
                selected_channel = st.selectbox("اختر قناة للتعديل", ["إضافة جديدة"] + existing_channels)

            with col2:
                if selected_channel != "إضافة جديدة":
                    if st.button("حذف القناة"):
                        del channels[selected_channel]
                        save_channels(channels, channels_file)
                        st.success(f"تم حذف القناة: {selected_channel}")
                        st.rerun()
        else:
            selected_channel = "إضافة جديدة"
            st.info("لا توجد قنوات محفوظة حالياً")

        st.markdown("---")

        # Add/Edit Channel Form
        if selected_channel == "إضافة جديدة":
            st.write("**إضافة قناة جديدة:**")
            channel_name = st.text_input("اسم القناة", placeholder="مثال: سلة، شمسة، أمازون السعودية")
        else:
            st.write(f"**تعديل القناة: {selected_channel}**")
            channel_name = selected_channel

        st.markdown("**رسوم القناة:**")
        col1, col2 = st.columns(2)

        with col1:
            # Get current values if editing
            if selected_channel != "إضافة جديدة" and selected_channel in channels:
                current = channels[selected_channel]
                default_platform = current.platform_pct * 100
                default_marketing = current.marketing_pct * 100
                default_opex = current.opex_pct * 100
            else:
                default_platform = 3.0
                default_marketing = 28.0
                default_opex = 4.0

            platform_pct = (
                st.number_input("رسوم المنصات %", min_value=0.0, max_value=20.0, value=default_platform, step=0.1) / 100
            )
            marketing_pct = (
                st.number_input("نسبة التسويق %", min_value=0.0, max_value=50.0, value=default_marketing, step=0.1)
                / 100
            )
            opex_pct = (
                st.number_input("نسبة التشغيل %", min_value=0.0, max_value=20.0, value=default_opex, step=0.1) / 100
            )

        with col2:
            if selected_channel != "إضافة جديدة" and selected_channel in channels:
                current = channels[selected_channel]
                default_shipping = current.shipping_fixed
                default_prep = current.preparation_fee
                default_threshold = current.free_shipping_threshold
            else:
                default_shipping = 20.0
                default_prep = 5.0
                default_threshold = 0.0

            shipping_fixed = st.number_input(
                "رسوم الشحن الثابتة (SAR)", min_value=0.0, value=default_shipping, step=0.01
            )
            preparation_fee = st.number_input("رسوم التحضير (SAR)", min_value=0.0, value=default_prep, step=0.01)
            free_threshold = st.number_input(
                "الحد الأدنى للشحن والتجهيز مجاني (SAR)",
                min_value=0.0,
                value=default_threshold,
                step=0.01,
                help="إذا كان السعر قبل الخصم ≥ هذا الحد، يكون الشحن والتجهيز مجاني",
            )

        st.markdown("---")

        # ===== Custom Fees Management =====
        st.subheader("إدارة الرسوم الإضافية المخصصة")

        custom_fees = {}
        if selected_channel != "إضافة جديدة" and selected_channel in channels:
            current = channels[selected_channel]
            custom_fees = current.custom_fees if hasattr(current, "custom_fees") else {}

        col1, col2, col3 = st.columns(3)
        with col1:
            fee_name = st.text_input("اسم الرسم الجديد", placeholder="مثال: رسم معالجة", key="fee_name_input")
        with col2:
            fee_amount = st.number_input("المبلغ أو النسبة", min_value=0.0, step=0.01, key="fee_amount_input")
        with col3:
            fee_type = st.selectbox("نوع الرسم", ["نسبة %", "مبلغ ثابت SAR"], key="fee_type_select")

        if st.button("➕ إضافة رسم جديد", type="secondary", width="stretch", key="add_fee_btn"):
            if fee_name.strip():
                fee_type_key = "percentage" if fee_type == "نسبة %" else "fixed"
                if fee_type_key == "percentage":
                    custom_fees[fee_name] = {"name": fee_name, "amount": fee_amount / 100, "fee_type": fee_type_key}
                else:
                    custom_fees[fee_name] = {"name": fee_name, "amount": fee_amount, "fee_type": fee_type_key}
                
                # حفظ الرسوم مباشرة في القناة المحفوظة
                if selected_channel != "إضافة جديدة" and selected_channel in channels:
                    channels[selected_channel].custom_fees = custom_fees
                    save_channels(channels, channels_file)
                    st.success(f"✅ تم إضافة وحفظ الرسم: {fee_name}")
                    st.rerun()
                else:
                    st.success(f"تم إضافة الرسم: {fee_name}")

        # Display existing custom fees
        if custom_fees:
            st.write("**الرسوم المضافة:**")
            for fee_key, fee_data in list(custom_fees.items()):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.write(f"**{fee_data['name']}**")
                with col2:
                    if fee_data["fee_type"] == "percentage":
                        st.write(f"{fee_data['amount']*100:.1f}%")
                    else:
                        st.write(f"{fee_data['amount']:.2f} SAR")
                with col3:
                    st.write("نسبة" if fee_data["fee_type"] == "percentage" else "مبلغ ثابت")
                with col4:
                    if st.button("حذف", key=f"delete_fee_{fee_key}"):
                        del custom_fees[fee_key]
                        # حفظ التعديل مباشرة
                        if selected_channel != "إضافة جديدة" and selected_channel in channels:
                            channels[selected_channel].custom_fees = custom_fees
                            save_channels(channels, channels_file)
                        st.rerun()

        st.markdown("---")

        if st.button("💾 حفظ القناة", type="primary", width="stretch"):
            if channel_name.strip():
                new_channel = ChannelFeesData(
                    platform_pct=platform_pct,
                    marketing_pct=marketing_pct,
                    opex_pct=opex_pct,
                    vat_rate=0.15,  # Default VAT 15%
                    discount_rate=0.10,  # Default discount 10%
                    shipping_fixed=shipping_fixed,
                    preparation_fee=preparation_fee,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                )
                channels[channel_name] = new_channel
                save_channels(channels, channels_file)
                st.success(f"تم حفظ القناة: {channel_name}")
                st.rerun()
            else:
                st.error("يجب إدخال اسم القناة")

        # Display all channels
        st.markdown("---")
        st.subheader("جميع القنوات المحفوظة")
        if channels:
            for ch_name, ch_fees in channels.items():
                with st.expander(f"📱 {ch_name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("رسوم المنصات", f"{ch_fees.platform_pct*100:.1f}%")
                        st.metric("نسبة التسويق", f"{ch_fees.marketing_pct*100:.1f}%")
                        st.metric("نسبة التشغيل", f"{ch_fees.opex_pct*100:.1f}%")
                    with col2:
                        st.metric("رسوم الشحن", f"{ch_fees.shipping_fixed:.2f} SAR")
                        st.metric("رسوم التحضير", f"{ch_fees.preparation_fee:.2f} SAR")
                        st.metric(
                            "الحد الأدنى للشحن مجاني",
                            (
                                f"{ch_fees.free_shipping_threshold:.2f} SAR"
                                if ch_fees.free_shipping_threshold > 0
                                else "معطل"
                            ),
                        )

                    # Display custom fees if any
                    if hasattr(ch_fees, "custom_fees") and ch_fees.custom_fees:
                        st.write("**الرسوم الإضافية:**")
                        for fee_key, fee_data in ch_fees.custom_fees.items():
                            if fee_data["fee_type"] == "percentage":
                                st.write(f"• {fee_data['name']}: {fee_data['amount']*100:.1f}%")
                            else:
                                st.write(f"• {fee_data['name']}: {fee_data['amount']:.2f} SAR")

# Page: Info
elif st.session_state.page == "info":
    st.header("📊 تحليل هوامش الربح")
    st.markdown("---")

    # التحقق من وجود جدول تسعير محفوظ
    if "last_pricing_breakdown" not in st.session_state:
        st.info(
            "⚠️ لم يتم حساب التسعير بعد. اذهب إلى تبويب '💵 شاشة تسعير المنتجات والبكجات' أولاً، اختر منتج أو بكج، واضغط على زر 'حساب السعر الكامل'."
        )
        st.stop()

    breakdown = st.session_state.get("last_pricing_breakdown", {})
    meta = st.session_state.get("last_pricing_meta", {})

    # عرض ملخص العملية
    st.markdown("### ملخص آخر عملية تسعير")
    if meta:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("SKU المنتج", meta.get("sku", "N/A"))
        with col2:
            st.metric("نوع المنتج", meta.get("sku_type", "N/A"))
        with col3:
            st.metric("المنصة", meta.get("platform", "N/A"))
        with col4:
            st.metric("السعر المدخل", f"{meta.get('base_price', 0):.2f} SAR")

    st.markdown("---")

    # عرض الملخص الرئيسي
    if breakdown:
        st.markdown("### الملخص المالي")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("سعر البيع", f"{breakdown.get('sale_price', 0):.2f} SAR")
        with col2:
            st.metric("الربح", f"{breakdown.get('profit', 0):.2f} SAR")
        with col3:
            st.metric("هامش الربح %", f"{breakdown.get('margin_pct', 0)*100:.1f}%")
        with col4:
            st.metric("نقطة التعادل", f"{breakdown.get('breakeven_price', 0):.2f} SAR")

        st.markdown("---")

        # رسم بياني لتوزيع التكاليف
        st.markdown("### توزيع التكاليف والرسوم")

        costs = {
            "تكلفة البضاعة": breakdown.get("cogs", 0),
            "مصاريف إدارية": breakdown.get("admin_fee", 0),
            "مصاريف تسويق": breakdown.get("marketing_fee", 0),
            "شحن": breakdown.get("shipping_fee", 0),
            "تحضير": breakdown.get("preparation_fee", 0),
        }

        # إضافة الرسوم المخصصة
        custom_fees = breakdown.get("custom_fees", {})
        if custom_fees:
            for fee_name, fee_amount in custom_fees.items():
                if fee_amount > 0:
                    costs[fee_name] = fee_amount

        costs_df = pd.DataFrame(list(costs.items()), columns=["النوع", "المبلغ"])
        costs_df = costs_df[costs_df["المبلغ"] > 0]

        fig_costs = px.pie(costs_df, values="المبلغ", names="النوع", title="توزيع التكاليف والرسوم")
        st.plotly_chart(fig_costs, width="stretch")

        st.markdown("---")

        # رسم بياني لتكوين السعر
        st.markdown("### تكوين السعر النهائي")

        price_elements = {
            "COGS": breakdown.get("cogs", 0),
            "الرسوم": breakdown.get("total_costs_fees", 0)
            - breakdown.get("cogs", 0)
            - breakdown.get("shipping_fee", 0)
            - breakdown.get("preparation_fee", 0),
            "الربح": breakdown.get("profit", 0),
        }
        price_df = pd.DataFrame(list(price_elements.items()), columns=["العنصر", "المبلغ"])

        fig_price = px.bar(
            price_df,
            x="العنصر",
            y="المبلغ",
            title="تكوين السعر",
            text="المبلغ",
            color="العنصر",
            color_discrete_map={"COGS": "#1f77b4", "الرسوم": "#ff7f0e", "الربح": "#2ca02c"},
        )
        fig_price.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(fig_price, width="stretch")

# Main Page
elif st.session_state.page == "main":
    # Professional Dashboard Header
    st.markdown(
        """
    <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: #1E88E5; margin: 0;">🏠 لوحة التحكم الرئيسية</h2>
        <p style="color: #666; margin: 10px 0 0 0;">نظرة شاملة على نظام التسعير</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Key Metrics Row with Beautiful Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            """
        <div style="background: linear-gradient(135deg, #1E88E515 0%, #1E88E505 100%); 
                    border-left: 4px solid #1E88E5; border-radius: 10px; padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <p style="color: #666; font-size: 0.85em; margin: 0;">إجمالي المواد الخام</p>
            <p style="color: #1E88E5; font-size: 2.5em; margin: 10px 0; font-weight: bold;">{}</p>
            <p style="color: #999; font-size: 0.8em; margin: 0;">🧱 مادة خام متوفرة</p>
        </div>
        """.format(
                len(materials)
            ),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div style="background: linear-gradient(135deg, #43A04715 0%, #43A04705 100%); 
                    border-left: 4px solid #43A047; border-radius: 10px; padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <p style="color: #666; font-size: 0.85em; margin: 0;">إجمالي المنتجات</p>
            <p style="color: #43A047; font-size: 2.5em; margin: 10px 0; font-weight: bold;">{}</p>
            <p style="color: #999; font-size: 0.8em; margin: 0;">📦 منتج جاهز</p>
        </div>
        """.format(
                len(product_recipes)
            ),
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        <div style="background: linear-gradient(135deg, #FB8C0015 0%, #FB8C0005 100%); 
                    border-left: 4px solid #FB8C00; border-radius: 10px; padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <p style="color: #666; font-size: 0.85em; margin: 0;">إجمالي البكجات</p>
            <p style="color: #FB8C00; font-size: 2.5em; margin: 10px 0; font-weight: bold;">{}</p>
            <p style="color: #999; font-size: 0.8em; margin: 0;">🎁 باقة متكاملة</p>
        </div>
        """.format(
                len(package_compositions)
            ),
            unsafe_allow_html=True,
        )

    with col4:
        # Count pricing history
        history_file = "data/pricing_history.csv"
        if os.path.exists(history_file):
            try:
                history_df = pd.read_csv(history_file, encoding="utf-8-sig")
                pricing_count = len(history_df)
            except:
                pricing_count = 0
        else:
            pricing_count = 0

        st.markdown(
            """
        <div style="background: linear-gradient(135deg, #E5393515 0%, #E5393505 100%); 
                    border-left: 4px solid #E53935; border-radius: 10px; padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <p style="color: #666; font-size: 0.85em; margin: 0;">سجلات التسعير</p>
            <p style="color: #E53935; font-size: 2.5em; margin: 10px 0; font-weight: bold;">{}</p>
            <p style="color: #999; font-size: 0.8em; margin: 0;">📝 سجل محفوظ</p>
        </div>
        """.format(
                pricing_count
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick Actions
    st.markdown(
        """
    <div style="background: white; border-radius: 10px; padding: 20px; margin: 20px 0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h3 style="color: #1E88E5; margin: 0 0 15px 0;">⚡ الإجراءات السريعة</h3>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🚀 تسعير سريع", width="stretch", type="primary"):
            st.session_state.page = "pricing"
            st.rerun()

    with col2:
        if st.button("💰 تكلفة البضاعة", width="stretch"):
            st.session_state.page = "cogs"
            st.rerun()

    with col3:
        if st.button("⚙️ إعدادات المنصات", width="stretch"):
            st.session_state.page = "settings"
            st.rerun()

    with col4:
        if st.button("📊 تسعير شامل", width="stretch"):
            st.session_state.page = "profit_margins"
            st.rerun()

    # Recent Activity & Charts
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
            """
        <div style="background: white; border-radius: 10px; padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <h3 style="color: #1E88E5; margin: 0 0 15px 0;">🕐 النشاط الأخير</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if os.path.exists(history_file) and pricing_count > 0:
            try:
                recent_df = history_df.tail(5)[["التاريخ", "اسم المنتج/البكج", "سعر البيع", "الربح"]].copy()
                recent_df["سعر البيع"] = recent_df["سعر البيع"].apply(lambda x: f"{x:.2f} SAR")
                recent_df["الربح"] = recent_df["الربح"].apply(lambda x: f"{x:.2f} SAR")
                st.dataframe(recent_df, width="stretch", hide_index=True)
            except:
                st.info("لا توجد سجلات تسعير حالياً")
        else:
            st.info("لا توجد سجلات تسعير حالياً. ابدأ بتسعير منتج!")

    with col2:
        st.markdown(
            """
        <div style="background: white; border-radius: 10px; padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <h3 style="color: #1E88E5; margin: 0 0 15px 0;">📊 توزيع البيانات</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if len(product_recipes) > 0 or len(package_compositions) > 0:
            data = pd.DataFrame(
                {"النوع": ["منتجات", "بكجات"], "العدد": [len(product_recipes), len(package_compositions)]}
            )
            fig = px.pie(data, values="العدد", names="النوع", color_discrete_sequence=["#1E88E5", "#43A047"], hole=0.4)
            fig.update_layout(height=300, showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("لا توجد بيانات لعرضها. ابدأ برفع ملفات المواد والمنتجات!")

    # Getting Started Guide
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
    <div style="background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%); 
                border-radius: 10px; padding: 25px; margin: 20px 0;
                border-left: 4px solid #1E88E5;">
        <h3 style="color: #1565C0; margin: 0 0 15px 0;">📘 دليل البدء السريع</h3>
        <ol style="color: #424242; line-height: 1.8; margin: 0;">
            <li><strong>رفع الملفات</strong> - قم برفع ملفات المواد الخام والمنتجات والبكجات</li>
            <li><strong>إعداد المنصات</strong> - أضف قنوات البيع وحدد الرسوم والنسب</li>
            <li><strong>حساب التكاليف</strong> - تحقق من تكلفة البضاعة (COGS)</li>
            <li><strong>التسعير</strong> - احسب الأسعار المثلى لمنتجاتك</li>
            <li><strong>التحليل</strong> - راقب الأرباح والهوامش</li>
        </ol>
    </div>
    """,
        unsafe_allow_html=True,
    )

# Page: Advanced Pricing
elif st.session_state.page == "pricing":
    st.header("💵 تسعير منتج/بكج فردي")
    st.markdown("حساب التكلفة الكاملة وتحليل هوامش الربح لمنتج أو بكج واحد")
    st.markdown("---")

    # Load channels
    channels_file = "data/channels.json"
    channels = load_channels(channels_file)

    if not channels:
        st.error("⚠️ لا توجد قنوات محفوظة! يجب إضافة قناة أولاً من صفحة الإعدادات")
    else:
        # Load all data to get products and packages
        materials, product_recipes, products_df, package_compositions, packages_df = load_cost_data("data")

        UIComponents.render_section_header(
            "تسعير احترافي لمنتج/بكج واحد",
            "اختر الاستراتيجية، أعد ضبط الرسوم التسويقية، واحصل على توصية سعرية مدعومة بحساسيات",
            "💡",
        )

        # Helper function to calculate cost of any component
        def calculate_component_cost(sku, component_type="product"):
            if component_type == "material" and sku in materials:
                return materials[sku].cost_per_unit
            if component_type == "product" and sku in product_recipes:
                total = 0
                for material_code, mat_qty in product_recipes[sku].items():
                    if material_code in materials:
                        total += materials[material_code].cost_per_unit * mat_qty
                return total
            if component_type == "package" and sku in package_compositions:
                total = 0
                for comp_sku, comp_qty in package_compositions[sku].items():
                    if comp_sku in materials:
                        total += materials[comp_sku].cost_per_unit * comp_qty
                    elif comp_sku in product_recipes:
                        total += calculate_component_cost(comp_sku, "product") * comp_qty
                    elif comp_sku in package_compositions:
                        total += calculate_component_cost(comp_sku, "package") * comp_qty
                return total
            return 0.0

        # Build selector options (unique)
        sku_options = []
        sku_to_name = {}
        sku_to_type = {}
        sku_to_cogs = {}

        def add_item(option, sku, name, item_type, cogs_val):
            sku_options.append(option)
            sku_to_name[option] = name
            sku_to_type[option] = item_type
            sku_to_cogs[option] = cogs_val

        if not products_df.empty:
            for _, row in products_df.iterrows():
                sku = row["Product_SKU"]
                name = row["Product_Name"]
                option = f"{name} - {sku}"
                add_item(option, sku, name, "منتج", calculate_component_cost(sku, "product"))

        if not packages_df.empty:
            for _, row in packages_df.iterrows():
                sku = row["Package_SKU"]
                name = row["Package_Name"]
                option = f"{name} - {sku}"
                add_item(option, sku, name, "باقة", calculate_component_cost(sku, "package"))

        # === Inputs ===
        col_left, col_mid, col_right = st.columns([1.2, 1, 1.1])

        with col_left:
            selected_channel = st.selectbox(
                "📍 قناة البيع", list(channels.keys()), help="اختر القناة لتطبيق رسومها وعتباتها"
            )

            # المدن من إشارات سلة (اختياري)
            city_options = ["(بدون مدينة)"]
            try:
                city_df = pd.read_csv("data/salla_city_factors.csv")
                cities = sorted(city_df["city"].dropna().unique().tolist())
                if cities:
                    city_options += cities
            except Exception:
                pass

            selected_city = st.selectbox("🗺️ المدينة (اختياري)", city_options)
            selected_city = None if selected_city == "(بدون مدينة)" else selected_city

            search_term = st.text_input("🔎 بحث بالاسم أو SKU", placeholder="اكتب للبحث السريع")
            filtered_sku_options = (
                [opt for opt in sku_options if search_term.lower() in opt.lower()] if search_term else sku_options
            )
            if filtered_sku_options:
                selected_sku_option = st.selectbox("📦 المنتج/البكج", filtered_sku_options)
                sku_input = selected_sku_option.split(" - ")[-1]
                item_type = sku_to_type.get(selected_sku_option, "منتج")
                default_cogs = sku_to_cogs.get(selected_sku_option, 0.0)
                item_name = sku_to_name.get(selected_sku_option, sku_input)
            else:
                st.warning("لا توجد نتائج مطابقة للبحث")
                selected_sku_option = ""
                sku_input = ""
                item_type = "منتج"
                default_cogs = 0.0
                item_name = ""

            cogs = st.number_input("💰 تكلفة البضاعة (COGS)", min_value=0.0, step=0.01, value=default_cogs)

            # اختيارات استبعاد رسوم معينة لهذا السيناريو
            skip_shipping = st.checkbox("🚚 بدون رسوم شحن", value=False, help="استبعد الشحن لهذا السيناريو فقط")
            skip_preparation = st.checkbox("🧰 بدون رسوم تجهيز", value=False, help="استبعد رسوم التجهيز/التعبئة")
            skip_marketing = st.checkbox("📢 بدون رسوم تسويق", value=False, help="استبعد نسبة التسويق من الحساب")

        with col_mid:
            strategy_presets = {
                "اختراق السوق": {"margin": 10.0, "discount": 5.0},
                "توازن ربحي": {"margin": 18.0, "discount": 3.0},
                "تميز/بريميم": {"margin": 25.0, "discount": 0.0},
                "تصفية": {"margin": 8.0, "discount": 10.0},
            }
            strategy_descriptions = {
                "اختراق السوق": "تسعير هجومي لزيادة الحصة بسرعة بهامش أقل وخصم لجذب العملاء.",
                "توازن ربحي": "مزيج متوازن بين هامش جيد ونمو مستدام مع خصم محدود.",
                "تميز/بريميم": "تركيز على القيمة والعلامة؛ هامش أعلى وخصم شبه معدوم.",
                "تصفية": "تصريف المخزون بسرعة مع خصم أكبر مع الحفاظ على هامش أمان.",
            }

            strategy = st.selectbox(
                "🎯 الإستراتيجية السعرية",
                list(strategy_presets.keys()),
                index=list(strategy_presets.keys()).index("توازن ربحي"),
                format_func=lambda k: f"{k} — {strategy_descriptions.get(k, '')}",
            )
            preset_margin = strategy_presets[strategy]["margin"]
            preset_discount = strategy_presets[strategy]["discount"]

            target_margin_pct = st.number_input(
                "هامش الربح المستهدف (%)", min_value=0.0, max_value=40.0, value=preset_margin, step=0.5
            )
            discount_pct = st.number_input(
                "الخصم الممنوح (%)", min_value=0.0, max_value=50.0, value=preset_discount, step=0.5
            )

            apply_salla_signals = st.checkbox(
                "تفعيل إشارات طلبات سلة في التسعير",
                value=False,
                help="يضرب السعر في عوامل المخاطر/الطلب/الجغرافيا من بيانات سلة",
            )

        with col_right:
            marketing_boost = st.number_input(
                "رفع ميزانية التسويق % إضافية",
                min_value=0.0,
                max_value=5.0,
                value=0.0,
                step=0.25,
                help="يضاف إلى نسبة التسويق للقناة لهذا السيناريو",
            )
            ops_buffer = st.number_input(
                "احتياط تشغيلي (SAR)", min_value=0.0, value=0.0, step=0.5, help="هوامش أمان لعمليات التعبئة والتغليف"
            )
            competitor_price = st.number_input(
                "سعر منافس (اختياري)",
                min_value=0.0,
                value=0.0,
                step=0.5,
                help="أدخل سعر المنافس شامل الضريبة قبل الخصم",
            )

        target_margin = target_margin_pct / 100
        discount_rate = discount_pct / 100

        st.markdown("---")

        # Auto-recalculate when channel changes if already calculated
        if "last_calculated_channel" not in st.session_state:
            st.session_state["last_calculated_channel"] = None

        channel_changed = (
            st.session_state["last_calculated_channel"] is not None
            and st.session_state["last_calculated_channel"] != selected_channel
        )

        col_btn = st.columns([1, 2, 1])[1]
        with col_btn:
            run_pricing = st.button("🚀 احسب التسعير الاحترافي", type="primary", width="stretch")

        if run_pricing or channel_changed:
            if not sku_input:
                st.error("اختر منتجاً أو بكجاً أولاً")
                st.stop()
            if cogs <= 0:
                st.error("أدخل تكلفة صالحة")
                st.stop()

            ch = channels[selected_channel]
            shipping = 0.0 if skip_shipping else ch.shipping_fixed
            preparation = 0.0 if skip_preparation else ch.preparation_fee
            vat_rate = ch.vat_rate
            free_threshold = getattr(ch, "free_shipping_threshold", 0)
            custom_fees = getattr(ch, "custom_fees", {}) or {}

            marketing_effective = 0.0 if skip_marketing else (ch.marketing_pct + (marketing_boost / 100))

            channel_dict = {
                "opex_pct": ch.opex_pct,
                "marketing_pct": marketing_effective,
                "platform_pct": ch.platform_pct,
                "vat_rate": vat_rate,
                "discount_rate": discount_rate,
            }

            total_pct = (
                channel_dict["opex_pct"]
                + channel_dict["marketing_pct"]
                + channel_dict["platform_pct"]
            )
            fixed_costs = cogs + shipping + preparation + ops_buffer
            denominator = 1 - total_pct - target_margin

            if denominator <= 0:
                st.error("الهامش المطلوب غير ممكن مع نسب الرسوم الحالية. خفّض الهامش أو الرسوم أو زد السعر.")
                st.stop()

            # حساب السعر المباشر من المعادلة لتحقيق الهامش المستهدف
            def solve_price_for_margin(target_margin_val: float):
                """حساب السعر المباشر الذي يحقق الهامش المستهدف"""
                # المعادلة: السعر الصافي = (COGS + رسوم ثابتة) / (1 - النسب - الهامش)
                net_price = fixed_costs / (1 - total_pct - target_margin_val)
                
                # السعر شامل الضريبة بعد الخصم
                price_with_vat_after_discount = net_price * (1 + vat_rate)
                
                # السعر شامل الضريبة قبل الخصم
                price_before_discount = price_with_vat_after_discount / (1 - discount_rate)
                
                # احسب التفصيل الكامل مع تمرير الهامش المستهدف
                bd = calculate_price_breakdown(
                    cogs=cogs,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=price_before_discount,
                    target_margin=target_margin_val,
                )
                
                return price_before_discount, bd

            price_list_before_discount, breakdown = solve_price_for_margin(target_margin)

            # استخدام النتيجة المحسوبة مباشرة بدون تعديل الهامش
            display_price_with_vat = price_list_before_discount
            display_breakdown = breakdown
            signals_details = None
            signals_multiplier = 1.0

            if apply_salla_signals:
                try:
                    signals_details = get_signals_for(sku_input, city=selected_city)
                    signals_multiplier = float(signals_details.get("composite_multiplier", 1.0))
                    display_price_with_vat = price_list_before_discount * signals_multiplier
                    display_breakdown = calculate_price_breakdown(
                        cogs=cogs,
                        channel_fees=channel_dict,
                        shipping=shipping,
                        preparation=preparation,
                        discount_rate=discount_rate,
                        vat_rate=vat_rate,
                        free_shipping_threshold=free_threshold,
                        custom_fees=custom_fees,
                        price_with_vat=display_price_with_vat,
                    )
                except Exception as e:
                    st.warning(f"تعذر تطبيق إشارات سلة: {e}")

            UIComponents.render_section_header("نتيجة الإستراتيجية", "سعر موصى به مع تفكيك مالي", "📊")
            colm1, colm2, colm3, colm4 = st.columns(4)
            with colm1:
                st.metric("سعر البيع شامل الضريبة قبل الخصم", f"{display_price_with_vat:.2f} SAR")
            with colm2:
                st.metric(
                    "سعر بعد الخصم",
                    f"{display_breakdown['price_after_discount']:.2f} SAR",
                    help="السعر النهائي المتوقع بعد الخصم",
                )
            with colm3:
                st.metric(
                    "صافي الربح",
                    f"{display_breakdown['profit']:.2f} SAR",
                    delta=f"{display_breakdown['margin_pct']*100:.1f}%",
                )
            with colm4:
                st.metric("هامش صافي الربح", f"{display_breakdown['margin_pct']*100:.1f}%")

            if signals_details:
                UIComponents.render_info_box(
                    (
                        "تم تطبيق إشارات طلبات سلة"
                        f" — عامل مركب: {signals_details['composite_multiplier']:.3f}"
                        f" (مخاطر {signals_details['risk_multiplier']:.3f} × طلب {signals_details['demand_factor']:.3f}"
                        f" × جغرافيا {signals_details['geo_factor']:.3f})"
                        f" — السعر قبل الإشارات: {price_list_before_discount:.2f} SAR"
                    ),
                    "info",
                )

            st.markdown("### 💡 توصية الاستراتيجية")
            rec_notes = {
                "اختراق السوق": "تسعير هجومي لزيادة الحصة مع خصم محسوب.",
                "توازن ربحي": "مزيج متوازن بين الهامش والنمو.",
                "تميز/بريميم": "تركيز على القيمة المضافة مع خصم محدود.",
                "تصفية": "تسريع التصريف مع بقاء هامش آمن.",
            }
            UIComponents.render_info_box(f"النهج: {rec_notes.get(strategy, '')}", "info")

            st.markdown("---")
            st.subheader("جدول حساب التكلفة والربح")

            # Display product info at top
            st.markdown(f"**SKU:** `{sku_input.strip()}` | **المنتج:** {item_name}")
            st.markdown("---")

            # Build table matching the exact format in the example
            # Get percentages from channel
            platform_pct = channel_dict.get("platform_pct", 0) * 100
            marketing_pct = channel_dict.get("marketing_pct", 0) * 100
            opex_pct = channel_dict.get("opex_pct", 0) * 100
            discount_pct_display = discount_pct * 100

            rows = [
                ("الجزء 1: الأسعار", None),
                ("سعر البيع شامل الضريبة قبل الخصم", display_breakdown["sale_price"]),
                (f"الخصم {discount_pct_display:.0f}%", display_breakdown["discount_amount"]),
                ("سعر البيع شامل الضريبة بعد الخصم", display_breakdown["price_after_discount"]),
                ("سعر البيع غير شامل الضريبة بعد الخصم", display_breakdown["net_price"]),
                (None, None),
                ("الجزء 2: تكلفة البضاعة", None),
                ("تكلفة البضاعة (من صفحة تكلفة البضاعة)", display_breakdown["cogs"]),
                (None, None),
                ("الجزء 3: رسوم المنصة والقناة المختارة", None),
                ("القناة المختارة", selected_channel),
            ]

            # Build active fees summary for display
            active_fees = []
            if platform_pct > 0:
                active_fees.append(f"منصة {platform_pct:.2f}%")
            if marketing_pct > 0:
                active_fees.append(f"تسويق {marketing_pct:.2f}%")
            if opex_pct > 0:
                active_fees.append(f"تشغيل {opex_pct:.2f}%")

            if active_fees:
                rows.append(("القيم المحفوظة للقناة", " / ".join(active_fees)))

            rows.append(("إعدادات القنوات والتسعير من صفحة المنصات", None))

            # Add fee rows only if they have values > 0
            fee_counter = 6
            if platform_pct > 0 and display_breakdown["platform_fee"] > 0:
                rows.append((f"رسوم المنصة {platform_pct:.0f}%", display_breakdown["platform_fee"]))
                fee_counter += 1
            if marketing_pct > 0 and display_breakdown["marketing_fee"] > 0:
                rows.append((f"نسبة التسويق {marketing_pct:.0f}%", display_breakdown["marketing_fee"]))
                fee_counter += 1
            if opex_pct > 0 and display_breakdown["admin_fee"] > 0:
                rows.append((f"نسبة التشغيل {opex_pct:.0f}%", display_breakdown["admin_fee"]))
                fee_counter += 1
            if shipping > 0 and display_breakdown["shipping_fee"] > 0:
                rows.append((f"رسوم الشحن {shipping:.0f}", display_breakdown["shipping_fee"]))
                fee_counter += 1
            if preparation > 0 and display_breakdown["preparation_fee"] > 0:
                rows.append((f"رسوم التحضير {preparation:.0f}", display_breakdown["preparation_fee"]))
                fee_counter += 1
            
            # إضافة الرسوم الإضافية المخصصة
            if display_breakdown.get("custom_fees") and display_breakdown["custom_fees_total"] > 0:
                for fee_name, fee_amount in display_breakdown["custom_fees"].items():
                    if fee_amount > 0:
                        rows.append((f"{fee_name}", fee_amount))
                        fee_counter += 1

            rows.extend(
                [
                    (None, None),
                    ("إجمالي تكلفة البضاعة ورسوم المنصات", display_breakdown["total_costs_fees"]),
                    (None, None),
                    ("الجزء 4: الربح", None),
                    (
                        "الربح = سعر البيع غير شامل الضريبة بعد الخصم - إجمالي تكلفة البضاعة ورسوم المنصات",
                        display_breakdown["profit"],
                    ),
                    ("هامش الربح %", display_breakdown["margin_pct"] * 100),
                ]
            )

            cost_df = pd.DataFrame(rows, columns=["البند", "القيمة (SAR)"])

            # Format the display with improved styling
            def format_row(row):
                if row["البند"] is None:
                    return ["background-color: #ffffff; border: none"] * len(row)
                if "الجزء" in str(row["البند"]):
                    return [
                        "background-color: #1e88e5; color: white; font-weight: bold; font-size: 16px; padding: 12px"
                    ] * len(row)
                elif "إجمالي تكلفة البضاعة ورسوم المنصات" in str(row["البند"]):
                    return ["background-color: #fff3cd; font-weight: bold; border-top: 2px solid #856404"] * len(row)
                elif "القناة المختارة" in str(row["البند"]) or "القيم المحفوظة" in str(row["البند"]):
                    return ["background-color: #e3f2fd; font-style: italic"] * len(row)
                elif "إعدادات القنوات" in str(row["البند"]):
                    return ["background-color: #f5f5f5; font-size: 11px; color: #666"] * len(row)
                elif "الربح =" in str(row["البند"]) or "هامش الربح" in str(row["البند"]):
                    return ["background-color: #d4edda; font-weight: bold; color: #155724"] * len(row)
                return [""] * len(row)

            styled_cost = (
                cost_df.style.apply(format_row, axis=1)
                .format({"القيمة (SAR)": lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else ""})
                .set_properties(**{"text-align": "right", "padding": "10px", "border": "1px solid #e0e0e0"})
                .set_table_styles(
                    [
                        {
                            "selector": "th",
                            "props": [
                                ("background-color", "#1e88e5"),
                                ("color", "white"),
                                ("font-weight", "bold"),
                                ("text-align", "center"),
                                ("padding", "12px"),
                                ("font-size", "14px"),
                            ],
                        },
                        {"selector": "td", "props": [("border", "1px solid #e0e0e0")]},
                        {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                    ]
                )
            )

            st.dataframe(styled_cost, width="stretch", hide_index=True, height=900)

            # Sensitivity analysis using advanced engine (جداول مبسطة)
            sens = pricing_engine.perform_sensitivity_analysis(
                base_cogs=cogs,
                base_price=breakdown["price_after_discount"],
                channel_fees=channel_dict,
                shipping=shipping,
                preparation=preparation,
            )

            st.markdown("---")
            st.subheader("حساسية بسيطة يمكن التصرف عليها")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.markdown("##### تغير التكلفة ±20%")
                df_cogs_sens = pd.DataFrame(sens["cogs_sensitivity"])
                df_cogs_sens.rename(
                    columns={"change_pct": "التغير %", "cogs": "تكلفة البضاعة", "profit": "الربح", "margin": "هامش %"},
                    inplace=True,
                )
                df_cogs_sens["هامش %"] = df_cogs_sens["هامش %"].round(2)
                df_cogs_sens["الربح"] = df_cogs_sens["الربح"].round(2)

                # تطبيق تنسيق محسّن
                def format_sensitivity_row(row):
                    if row["التغير %"] == "0%":
                        return ["background-color: #fff3cd; font-weight: bold"] * len(row)
                    elif row["التغير %"] in ["-20%", "-10%"]:
                        return ["background-color: #f8d7da"] * len(row)
                    elif row["التغير %"] in ["+10%", "+20%"]:
                        return ["background-color: #d1ecf1"] * len(row)
                    return [""] * len(row)

                styled_cogs = (
                    df_cogs_sens[["التغير %", "تكلفة البضاعة", "الربح", "هامش %"]]
                    .style.apply(format_sensitivity_row, axis=1)
                    .format({"تكلفة البضاعة": "{:.2f}", "الربح": "{:.2f}", "هامش %": "{:.2f}"})
                    .set_table_styles(
                        [
                            {
                                "selector": "th",
                                "props": [
                                    ("background-color", "#1e88e5"),
                                    ("color", "white"),
                                    ("font-weight", "bold"),
                                    ("text-align", "center"),
                                    ("padding", "10px"),
                                ],
                            },
                            {
                                "selector": "td",
                                "props": [("text-align", "right"), ("padding", "8px"), ("border", "1px solid #ddd")],
                            },
                            {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                        ]
                    )
                )
                st.dataframe(styled_cogs, width="stretch", hide_index=True, height=280)

            with col_s2:
                st.markdown("##### تغير السعر ±20%")
                df_price_sens = pd.DataFrame(sens["price_sensitivity"])
                df_price_sens.rename(
                    columns={"change_pct": "التغير %", "price": "السعر", "profit": "الربح", "margin": "هامش %"},
                    inplace=True,
                )
                df_price_sens["هامش %"] = df_price_sens["هامش %"].round(2)
                df_price_sens["الربح"] = df_price_sens["الربح"].round(2)

                # تطبيق تنسيق محسّن
                def format_sensitivity_row(row):
                    if row["التغير %"] == "0%":
                        return ["background-color: #fff3cd; font-weight: bold"] * len(row)
                    elif row["التغير %"] in ["-20%", "-10%"]:
                        return ["background-color: #f8d7da"] * len(row)
                    elif row["التغير %"] in ["+10%", "+20%"]:
                        return ["background-color: #d1ecf1"] * len(row)
                    return [""] * len(row)

                styled_price = (
                    df_price_sens[["التغير %", "السعر", "الربح", "هامش %"]]
                    .style.apply(format_sensitivity_row, axis=1)
                    .format({"السعر": "{:.2f}", "الربح": "{:.2f}", "هامش %": "{:.2f}"})
                    .set_table_styles(
                        [
                            {
                                "selector": "th",
                                "props": [
                                    ("background-color", "#1e88e5"),
                                    ("color", "white"),
                                    ("font-weight", "bold"),
                                    ("text-align", "center"),
                                    ("padding", "10px"),
                                ],
                            },
                            {
                                "selector": "td",
                                "props": [("text-align", "right"), ("padding", "8px"), ("border", "1px solid #ddd")],
                            },
                            {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                        ]
                    )
                )
                st.dataframe(styled_price, width="stretch", hide_index=True, height=280)

            # Positioning vs competitor with side-by-side detailed tables
            if competitor_price > 0:
                our_price_after_discount = breakdown["price_after_discount"]
                competitor_list_price = competitor_price  # إدخال المستخدم هو السعر شامل الضريبة قبل الخصم
                competitor_breakdown = calculate_price_breakdown(
                    cogs=cogs,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=competitor_list_price,
                )

                comp_price_after_discount = competitor_breakdown["price_after_discount"]
                positioning = (
                    "أعلى من السوق"
                    if our_price_after_discount > comp_price_after_discount * 1.05
                    else "ضمن السوق" if our_price_after_discount >= comp_price_after_discount * 0.95 else "أقل من السوق"
                )
                UIComponents.render_info_box(
                    f"مقارنة السعر بعد الخصم بالمنافس: {positioning} (بعد خصم منافس {comp_price_after_discount:.2f} SAR)",
                    "warning",
                )

                # عرض شروط المنصة المختارة
                st.info(f"📋 **شروط المنصة المختارة ({selected_channel}):**\n"
                       f"- حد الشحن المجاني: {free_threshold} ريال\n"
                       f"- رسوم الشحن: {shipping} ريال\n"
                       f"- رسوم التحضير: {preparation} ريال\n"
                       f"- القاعدة: إذا السعر > {free_threshold} → شحن مدفوع | إذا ≤ {free_threshold} → شحن مجاني")
                
                # عرض قرار الشحن لسعرنا
                our_list_price = price_list_before_discount
                if free_threshold > 0 and our_list_price <= free_threshold:
                    st.success(f"✅ السعر بدون رسوم ({our_list_price:.2f}) ≤ الحد ({free_threshold}) → شحن مجاني (0), تحضير مجاني (0)")
                elif free_threshold > 0:
                    st.success(f"✅ السعر بدون رسوم ({our_list_price:.2f}) > الحد ({free_threshold}) → شحن مدفوع ({shipping}), تحضير مدفوع ({preparation})")
                else:
                    st.success(f"✅ لا يوجد حد للشحن المجاني → شحن مدفوع ({shipping}), تحضير مدفوع ({preparation})")

                st.markdown("### مقارنة سعرنا مع المنافس (تفصيل كامل مثل ورقة الحساب)")

                def build_detail_rows(bd: dict, rate_map: dict, list_price: float) -> pd.DataFrame:
                    custom_total = bd.get("custom_fees_total", 0)
                    rows = [
                        ("الجزء الأول: التسعير", None, None),
                        ("سعر البيع شامل الضريبة قبل الخصم", list_price, ""),
                        ("نسبة الخصم", bd["discount_rate"] * 100, "%"),
                        ("مبلغ الخصم", bd["discount_amount"], ""),
                        ("سعر البيع شامل الضريبة بعد الخصم", bd["price_after_discount"], ""),
                        ("سعر البيع غير الضريبة بعد الخصم", bd["net_price"], ""),
                        ("الجزء الثاني: تكلفة البضاعة المباعة", None, None),
                        ("تكلفة البضاعة للوحدة", bd["cogs"], ""),
                        ("الجزء الثالث: رسوم المنصة", None, None),
                        ("التحضير", bd["preparation_fee"], ""),
                        ("الشحن", bd["shipping_fee"], ""),
                    ]

                    # إضافة الرسوم فقط إذا كانت أكبر من صفر
                    if bd["admin_fee"] > 0:
                        rows.append(("المصاريف الإدارية", bd["admin_fee"], f"{rate_map['admin']*100:.1f}%"))
                    if bd["marketing_fee"] > 0:
                        rows.append(("مصاريف التسويق", bd["marketing_fee"], f"{rate_map['marketing']*100:.1f}%"))
                    if bd["platform_fee"] > 0:
                        rows.append(("رسوم المنصات", bd["platform_fee"], f"{rate_map['platform']*100:.1f}%"))
                    if custom_total > 0:
                        rows.append(("رسوم مخصصة", custom_total, ""))

                    rows.extend(
                        [
                            ("إجمالي التكلفة والرسوم", bd["total_costs_fees"], ""),
                            ("الجزء الرابع: صافي الربح", None, None),
                            ("الربح", bd["profit"], ""),
                            ("هامش الربح %", bd["margin_pct"] * 100, "%"),
                        ]
                    )

                    df = pd.DataFrame(rows, columns=["البند", "القيمة", "ملاحظة"])

                    # تطبيق تنسيق محسّن
                    def format_comparison_row(row):
                        label = row["البند"]
                        if label and label.startswith("الجزء"):
                            return [
                                "background-color: #1e88e5; color: white; font-weight: bold; font-size: 16px"
                            ] * len(row)
                        elif label == "إجمالي التكلفة والرسوم":
                            return [
                                "background-color: #fff3cd; border-top: 2px solid #856404; font-weight: bold"
                            ] * len(row)
                        elif label in ["الربح", "هامش الربح %"]:
                            return ["background-color: #d4edda; color: #155724; font-weight: bold"] * len(row)
                        return [""] * len(row)

                    styled = (
                        df.style.apply(format_comparison_row, axis=1)
                        .format(
                            {
                                "القيمة": lambda x: (
                                    f"{x:.2f}" if isinstance(x, (int, float)) else ("—" if x is None else str(x))
                                ),
                                "ملاحظة": lambda x: "" if x is None else str(x),
                            }
                        )
                        .set_table_styles(
                            [
                                {
                                    "selector": "th",
                                    "props": [
                                        ("background-color", "#1e88e5"),
                                        ("color", "white"),
                                        ("font-weight", "bold"),
                                        ("text-align", "center"),
                                        ("padding", "10px"),
                                    ],
                                },
                                {
                                    "selector": "td",
                                    "props": [
                                        ("text-align", "right"),
                                        ("padding", "8px"),
                                        ("border", "1px solid #ddd"),
                                    ],
                                },
                                {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                            ]
                        )
                    )

                    return styled

                rate_map = {
                    "admin": channel_dict.get("opex_pct", 0),
                    "marketing": channel_dict.get("marketing_pct", 0),
                    "platform": channel_dict.get("platform_pct", 0),
                }

                # حساب سعر التعادل (هامش ربح 0%)
                breakeven_breakdown = calculate_price_breakdown(
                    cogs=cogs,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=breakdown["breakeven_price"],
                )

                col_cmp1, col_cmp2, col_cmp3 = st.columns(3)
                table_height = 820
                with col_cmp1:
                    st.markdown("**سعرنا**")
                    styled_ours = build_detail_rows(breakdown, rate_map, price_list_before_discount)
                    st.dataframe(styled_ours, width="stretch", hide_index=True, height=table_height)
                with col_cmp2:
                    st.markdown("**سعر المنافس**")
                    styled_comp = build_detail_rows(competitor_breakdown, rate_map, competitor_list_price)
                    st.dataframe(styled_comp, width="stretch", hide_index=True, height=table_height)
                with col_cmp3:
                    st.markdown("**سعر التعادل (0% ربح)**")
                    styled_breakeven = build_detail_rows(breakeven_breakdown, rate_map, breakdown["breakeven_price"])
                    st.dataframe(styled_breakeven, width="stretch", hide_index=True, height=table_height)

            st.markdown("---")
            st.subheader("حفظ التسعير")
            
            # حفظ النتائج في session_state للاحتفاظ بها
            if "current_pricing_result" not in st.session_state:
                st.session_state["current_pricing_result"] = None
            
            # تخزين النتيجة الحالية
            st.session_state["current_pricing_result"] = {
                "التاريخ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "اسم المنتج/البكج": item_name,
                "SKU": sku_input.strip(),
                "النوع": item_type,
                "المنصة": selected_channel,
                "التكلفة": cogs,
                "سعر القائمة": price_list_before_discount,
                "سعر بعد الخصم": breakdown["price_after_discount"],
                "الربح": breakdown["profit"],
                "هامش الربح %": breakdown["margin_pct"] * 100,
                "رسوم الشحن": breakdown["shipping_fee"],
                "رسوم التحضير": breakdown["preparation_fee"],
                "رسوم إدارية": breakdown["admin_fee"],
                "رسوم تسويق": breakdown["marketing_fee"],
                "رسوم المنصة": breakdown["platform_fee"],
                "نسبة الخصم": discount_pct,
                "صافي السعر": breakdown["net_price"],
                "إجمالي التكاليف": breakdown["total_costs_fees"],
                "نقطة التعادل": breakdown["breakeven_price"],
                "استراتيجية": strategy,
            }
            
            if st.button("💾 حفظ النتيجة", type="primary", width="stretch", key="save_pricing_btn_pro"):
                pass  # سيتم معالجة الحفظ خارج هذا الشرط

        # معالجة الحفظ خارج شرط run_pricing لتجنب إعادة التحميل
        if "current_pricing_result" in st.session_state and st.session_state.get("current_pricing_result"):
            # فحص إذا تم الضغط على زر الحفظ
            if st.session_state.get("save_pricing_btn_pro"):
                try:
                    import os

                    data_dir = os.path.join(os.path.dirname(__file__), "data")
                    os.makedirs(data_dir, exist_ok=True)

                    pricing_record = st.session_state["current_pricing_result"]

                    history_file = os.path.join(data_dir, "pricing_history.csv")

                    if os.path.exists(history_file):
                        history_df = pd.read_csv(history_file, encoding="utf-8-sig")
                        history_df = pd.concat([history_df, pd.DataFrame([pricing_record])], ignore_index=True)
                    else:
                        history_df = pd.DataFrame([pricing_record])

                    history_df.to_csv(history_file, index=False, encoding="utf-8-sig")

                    # Verify file was written
                    if os.path.exists(history_file):
                        st.success(f"✅ تم الحفظ بنجاح في: {history_file}")
                        st.info(f"📊 إجمالي السجلات: {len(history_df)}")
                    else:
                        st.error("❌ فشل في الحفظ - الملف غير موجود!")

                    st.session_state["saved_history_preview"] = history_df.copy()

                except Exception as e:
                    import traceback

                    st.error(f"❌ خطأ في الحفظ: {e}")
                    st.code(traceback.format_exc())
        
        # حفظ البيانات الوصفية للحساب الأخير
        if run_pricing or channel_changed:
            st.session_state["last_pricing_breakdown"] = breakdown
            st.session_state["last_pricing_meta"] = {
                "sku": sku_input.strip(),
                "sku_type": item_type,
                "platform": selected_channel,
                "base_price": price_list_before_discount,
                "discount_pct": discount_pct,
                "cogs": cogs,
            }
            st.session_state["last_calculated_channel"] = selected_channel

# Page: Custom Package Builder
elif st.session_state.page == "custom_package":
    st.header("🎁 إنشاء بكج مخصص جديد")
    st.markdown("قم بتجميع منتجات وبكجات مع بعضها لإنشاء بكج جديد واحسب تكلفته وهامش ربحه")
    st.markdown("---")

    # Load channels
    channels_file = "data/channels.json"
    channels = load_channels(channels_file)

    if not channels:
        st.error("⚠️ لا توجد قنوات محفوظة! يجب إضافة قناة أولاً من صفحة الإعدادات")
    else:
        # Load all data
        materials, product_recipes, products_df, package_compositions, packages_df = load_cost_data("data")

        UIComponents.render_section_header(
            "بناء بكج مخصص",
            "اختر عدة منتجات أو بكجات وحدد كمياتها لإنشاء بكج جديد",
            "🎁",
        )

        # Helper function to calculate cost
        def calculate_component_cost(sku, component_type="product"):
            if component_type == "material" and sku in materials:
                return materials[sku].cost_per_unit
            if component_type == "product" and sku in product_recipes:
                total = 0
                for material_code, mat_qty in product_recipes[sku].items():
                    if material_code in materials:
                        total += materials[material_code].cost_per_unit * mat_qty
                return total
            if component_type == "package" and sku in package_compositions:
                total = 0
                for comp_sku, comp_qty in package_compositions[sku].items():
                    if comp_sku in materials:
                        total += materials[comp_sku].cost_per_unit * comp_qty
                    elif comp_sku in product_recipes:
                        total += calculate_component_cost(comp_sku, "product") * comp_qty
                    elif comp_sku in package_compositions:
                        total += calculate_component_cost(comp_sku, "package") * comp_qty
                return total
            return 0.0

        # Build selector options
        all_items = {}
        item_types = {}
        
        # Add products from product_recipes
        for sku in product_recipes.keys():
            # Try to get name from products_df
            name = None
            if not products_df.empty and "Product_SKU" in products_df.columns:
                product_row = products_df[products_df["Product_SKU"] == sku]
                if not product_row.empty and "Product_Name" in product_row.columns:
                    name_value = product_row.iloc[0]["Product_Name"]
                    if pd.notna(name_value) and str(name_value).strip():
                        name = str(name_value).strip()
            
            # Use SKU as fallback if no name found
            if not name:
                name = f"منتج {sku}"
            
            all_items[f"{sku} - {name}"] = sku
            item_types[sku] = "منتج"
        
        # Add packages from package_compositions
        for sku in package_compositions.keys():
            # Try to get name from packages_df
            name = None
            if not packages_df.empty and "Package_SKU" in packages_df.columns:
                package_row = packages_df[packages_df["Package_SKU"] == sku]
                if not package_row.empty and "Package_Name" in package_row.columns:
                    name_value = package_row.iloc[0]["Package_Name"]
                    if pd.notna(name_value) and str(name_value).strip():
                        name = str(name_value).strip()
            
            # Use SKU as fallback if no name found
            if not name:
                name = f"بكج {sku}"
            
            all_items[f"{sku} - {name}"] = sku
            item_types[sku] = "بكج"

        if not all_items:
            st.warning("⚠️ لا توجد منتجات أو بكجات متاحة. قم برفع الملفات من صفحة 'رفع الملفات' أولاً.")
            st.info("💡 تأكد من رفع ملفات المنتجات والبكجات من القائمة الجانبية.")
            st.stop()

        # Initialize package components and rows in session state
        if "package_rows" not in st.session_state:
            st.session_state.package_rows = [{"id": 0}]  # Start with one empty row
        if "package_components" not in st.session_state:
            st.session_state.package_components = []
        if "show_pricing" not in st.session_state:
            st.session_state.show_pricing = False

        st.markdown("### 📦 بناء البكج المخصص")
        
        # Search box
        search_term = st.text_input(
            "🔍 بحث عن منتج أو بكج",
            placeholder="ابحث بالاسم أو SKU...",
            key="component_search"
        )
        
        # Filter items based on search
        filtered_items = {}
        if search_term:
            search_lower = search_term.lower()
            for display_name, sku in all_items.items():
                if search_lower in display_name.lower():
                    filtered_items[display_name] = sku
        else:
            filtered_items = all_items
        
        if not filtered_items and search_term:
            st.warning(f"⚠️ لم يتم العثور على نتائج للبحث: {search_term}")
        
        st.markdown("#### اختر المكونات")
        st.markdown("أضف عدة منتجات/بكجات بكميات مختلفة، ثم اضغط **تجميع** للانتقال للتسعير")
        
        # Display rows dynamically
        for idx, row in enumerate(st.session_state.package_rows):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 0.5])
            
            with col1:
                selected_item = st.selectbox(
                    "اختر منتج أو بكج",
                    options=[""] + list(filtered_items.keys()) if filtered_items else [""],
                    key=f"item_selector_{row['id']}",
                    label_visibility="collapsed"
                )
            
            with col2:
                quantity = st.number_input(
                    "الكمية",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"item_quantity_{row['id']}",
                    label_visibility="collapsed"
                )
            
            with col3:
                if idx == len(st.session_state.package_rows) - 1:
                    # Last row: show "Add another" button
                    if st.button("➕ إضافة عنصر آخر", type="primary", key=f"add_row_{row['id']}", use_container_width=True):
                        # Add new empty row
                        new_id = max([r['id'] for r in st.session_state.package_rows]) + 1
                        st.session_state.package_rows.append({"id": new_id})
                        st.rerun()
                else:
                    st.markdown("<div style='height: 38px'></div>", unsafe_allow_html=True)
            
            with col4:
                if len(st.session_state.package_rows) > 1:
                    # Show delete button for all rows except if only one row exists
                    if st.button("🗑️", key=f"delete_row_{row['id']}", help="حذف هذا السطر", use_container_width=True):
                        st.session_state.package_rows = [r for r in st.session_state.package_rows if r['id'] != row['id']]
                        st.rerun()
        
        st.markdown("---")
        
        # Aggregate button
        col_center = st.columns([1, 2, 1])[1]
        with col_center:
            if st.button("📦 تجميع البكج وحساب التسعير", type="primary", use_container_width=True):
                # Collect all selected items
                st.session_state.package_components = []
                
                for row in st.session_state.package_rows:
                    row_id = row['id']
                    # Get values from session state (streamlit stores widget values there)
                    item_key = f"item_selector_{row_id}"
                    qty_key = f"item_quantity_{row_id}"
                    
                    # Access widget values
                    if item_key in st.session_state and st.session_state[item_key]:
                        selected_item = st.session_state[item_key]
                        quantity = st.session_state[qty_key]
                        
                        if selected_item and selected_item in filtered_items:
                            sku = filtered_items[selected_item]
                            component_type = item_types[sku]
                            cost = calculate_component_cost(
                                sku, 
                                "product" if component_type == "منتج" else "package"
                            )
                            
                            st.session_state.package_components.append({
                                "sku": sku,
                                "name": selected_item,
                                "type": component_type,
                                "quantity": quantity,
                                "unit_cost": cost,
                                "total_cost": cost * quantity
                            })
                
                if st.session_state.package_components:
                    st.session_state.show_pricing = True
                    st.rerun()
                else:
                    st.error("⚠️ يجب اختيار منتج واحد على الأقل!")
        
        # Show assembled package if exists
        if st.session_state.show_pricing and st.session_state.package_components:
            st.markdown("---")
            st.markdown("#### 🧾 البكج المُجمّع")
            
            # Show SKU and Name separately
            display_data = []
            for idx, comp in enumerate(st.session_state.package_components):
                display_data.append({
                    "#": idx + 1,
                    "SKU": comp["sku"],
                    "الاسم": comp["name"].split(" - ", 1)[1] if " - " in comp["name"] else comp["name"],
                    "النوع": comp["type"],
                    "الكمية": comp["quantity"],
                    "تكلفة الوحدة": f"{comp['unit_cost']:.2f}",
                    "التكلفة الإجمالية": f"{comp['total_cost']:.2f}"
                })
            
            display_df = pd.DataFrame(display_data)
            
            # Show table
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                height=min(400, (len(display_data) + 1) * 35 + 38)
            )
            
            # Recalculate total
            components_df = pd.DataFrame(st.session_state.package_components)
            total_package_cost = components_df["total_cost"].sum()
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col2:
                st.metric("💰 إجمالي تكلفة البكج", f"{total_package_cost:.2f} SAR", 
                         help=f"مجموع {len(st.session_state.package_components)} مكونات")
            with col3:
                if st.button("🔄 إعادة التصميم", type="secondary", use_container_width=True):
                    st.session_state.show_pricing = False
                    st.session_state.package_components = []
                    st.session_state.package_rows = [{"id": 0}]
                    st.rerun()
            
            st.markdown("---")
            
            # Pricing section
            st.markdown("### 💵 حساب التسعير")
            
            col1, col2 = st.columns(2)
            with col1:
                package_name = st.text_input(
                    "اسم البكج الجديد",
                    value="بكج مخصص",
                    key="custom_package_name"
                )
            
            with col2:
                selected_channel = st.selectbox(
                    "🏪 اختر المنصة/القناة",
                    options=list(channels.keys()),
                    key="custom_pkg_channel"
                )

            # Strategy and pricing parameters
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                strategy = st.selectbox(
                    "الاستراتيجية",
                    ["اختراق السوق", "توازن ربحي", "تميز/بريميم", "تصفية"],
                    key="custom_pkg_strategy"
                )
            
            with col2:
                target_margin_input = st.number_input(
                    "هامش الربح المستهدف %",
                    min_value=0,
                    max_value=50,
                    value=9,
                    step=1,
                    key="custom_pkg_margin"
                )
                target_margin = target_margin_input / 100
            
            with col3:
                marketing_boost = st.number_input(
                    "زيادة تسويق إضافية %",
                    min_value=0,
                    max_value=20,
                    value=0,
                    step=1,
                    key="custom_pkg_marketing"
                )
            
            with col4:
                discount_pct_input = st.number_input(
                    "نسبة الخصم %",
                    min_value=0,
                    max_value=50,
                    value=10,
                    step=1,
                    key="custom_pkg_discount"
                )
                discount_pct = discount_pct_input / 100

            # Competitor price
            competitor_price = st.number_input(
                "سعر المنافس (اختياري)",
                min_value=0.0,
                value=0.0,
                step=1.0,
                key="custom_pkg_competitor"
            )

            # Calculate button
            col_btn = st.columns([1, 2, 1])[1]
            with col_btn:
                run_pricing = st.button(
                    "🚀 احسب تسعير البكج المخصص",
                    type="primary",
                    width="stretch",
                    key="custom_pkg_calc"
                )

            if run_pricing:
                ch = channels[selected_channel]
                shipping = ch.shipping_fixed
                preparation = ch.preparation_fee
                vat_rate = ch.vat_rate
                free_threshold = getattr(ch, "free_shipping_threshold", 0)
                custom_fees = getattr(ch, "custom_fees", {}) or {}

                # عرض شروط المنصة المختارة
                st.info(f"📋 **شروط المنصة المختارة ({selected_channel}):**\n"
                       f"- حد الشحن المجاني: {free_threshold} ريال\n"
                       f"- رسوم الشحن: {shipping} ريال\n"
                       f"- رسوم التحضير: {preparation} ريال\n"
                       f"- القاعدة: إذا السعر > {free_threshold} → شحن مدفوع | إذا ≤ {free_threshold} → شحن مجاني")

                channel_dict = {
                    "opex_pct": ch.opex_pct,
                    "marketing_pct": ch.marketing_pct + (marketing_boost / 100),
                    "platform_pct": ch.platform_pct,
                    "vat_rate": vat_rate,
                    "discount_rate": discount_pct,
                }

                # حساب نسبة ورسوم مخصصة إن وجدت
                custom_pct = 0.0
                custom_fixed = 0.0
                custom_fees_dict = {}
                if custom_fees:
                    for fee_name, fee_data in custom_fees.items():
                        if fee_data.get("fee_type") == "percentage":
                            custom_pct += fee_data.get("amount", 0)
                        else:
                            custom_fixed += fee_data.get("amount", 0)

                admin_pct = channel_dict["opex_pct"]
                marketing_pct = channel_dict["marketing_pct"]
                platform_pct = channel_dict["platform_pct"]
                
                total_pct = admin_pct + marketing_pct + platform_pct + custom_pct
                denom = 1 - total_pct - target_margin

                if denom <= 0 or (1 - discount_pct) <= 0:
                    st.error("الهامش المطلوب غير ممكن مع نسب الرسوم الحالية. خفّض الهامش أو الرسوم أو الخصم.")
                    st.stop()

                # السيناريو 1: حساب السعر بدون رسوم شحن/تحضير (لو كان الشحن مجاني)
                fixed_costs_without_fees = total_package_cost + custom_fixed
                net_without_fees = fixed_costs_without_fees / denom
                price_after_vat_without_fees = net_without_fees * (1 + vat_rate)
                list_price_without_fees = price_after_vat_without_fees / (1 - discount_pct)
                
                # السيناريو 2: حساب السعر مع رسوم شحن/تحضير (لو كان الشحن مدفوع)
                fixed_costs_with_fees = total_package_cost + shipping + preparation + custom_fixed
                net_with_fees = fixed_costs_with_fees / denom
                price_after_vat_with_fees = net_with_fees * (1 + vat_rate)
                list_price_with_fees = price_after_vat_with_fees / (1 - discount_pct)
                
                # قرار: هل الشحن مجاني أم مدفوع؟
                # إذا السعر بدون رسوم ≤ الحد → استخدم السعر بدون رسوم (شحن مجاني)
                # إذا السعر بدون رسوم > الحد → استخدم السعر مع رسوم (شحن مدفوع)
                if free_threshold > 0 and list_price_without_fees <= free_threshold:
                    # الشحن مجاني لأن السعر ≤ الحد
                    actual_shipping = 0
                    actual_preparation = 0
                    fixed_costs = fixed_costs_without_fees
                    net_price = net_without_fees
                    price_after_discount = price_after_vat_without_fees
                    list_price = list_price_without_fees
                    st.success(f"✅ السعر بدون رسوم ({list_price_without_fees:.2f}) ≤ الحد ({free_threshold}) → شحن مجاني (0), تحضير مجاني (0)")
                else:
                    # الشحن مدفوع لأن السعر > الحد (أو لا يوجد حد)
                    actual_shipping = shipping
                    actual_preparation = preparation
                    fixed_costs = fixed_costs_with_fees
                    net_price = net_with_fees
                    price_after_discount = price_after_vat_with_fees
                    list_price = list_price_with_fees
                    if free_threshold > 0:
                        st.success(f"✅ السعر بدون رسوم ({list_price_without_fees:.2f}) > الحد ({free_threshold}) → شحن مدفوع ({actual_shipping}), تحضير مدفوع ({actual_preparation})")
                    else:
                        st.success(f"✅ لا يوجد حد للشحن المجاني → شحن مدفوع ({actual_shipping}), تحضير مدفوع ({actual_preparation})")
                
                # استخدام القيم المحسوبة
                # B (discount amount) = A * discount_rate
                discount_amount = list_price * discount_pct
                
                # الرسوم المحسوبة من السعر الصافي
                admin_fee = net_price * admin_pct
                marketing_fee = net_price * marketing_pct
                platform_fee = net_price * platform_pct
                
                # حساب الرسوم المخصصة
                custom_fees_total = custom_fixed
                if custom_fees:
                    for fee_name, fee_data in custom_fees.items():
                        if fee_data.get("fee_type") == "percentage":
                            fee_amount = net_price * fee_data.get("amount", 0)
                        else:
                            fee_amount = fee_data.get("amount", 0)
                        custom_fees_dict[fee_name] = fee_amount
                        if fee_data.get("fee_type") == "percentage":
                            custom_fees_total += fee_amount
                
                total_costs_fees = total_package_cost + actual_shipping + actual_preparation + admin_fee + marketing_fee + platform_fee + custom_fees_total
                profit = net_price - total_costs_fees
                margin_pct = target_margin  # الهامش المستهدف بالضبط
                
                # بناء breakdown يدوياً
                breakdown = {
                    "sale_price": list_price,
                    "discount_amount": discount_amount,
                    "discount_rate": discount_pct,
                    "price_after_discount": price_after_discount,
                    "vat_rate": vat_rate,
                    "net_price": net_price,
                    "custom_fees": custom_fees_dict,
                    "custom_fees_total": custom_fees_total,
                    "cogs": total_package_cost,
                    "preparation_fee": actual_preparation,
                    "shipping_fee": actual_shipping,
                    "admin_fee": admin_fee,
                    "marketing_fee": marketing_fee,
                    "platform_fee": platform_fee,
                    "total_costs_fees": total_costs_fees,
                    "profit": profit,
                    "margin_pct": margin_pct,
                    "breakeven_price": (fixed_costs / (1 - total_pct)) * (1 + vat_rate) / (1 - discount_pct) if (1 - total_pct) > 0 else 0,
                }

                # Display results
                UIComponents.render_section_header("نتيجة التسعير", "سعر موصى به للبكج المخصص", "📊")
                
                colm1, colm2, colm3, colm4 = st.columns(4)
                with colm1:
                    st.metric("سعر البيع شامل الضريبة قبل الخصم", f"{list_price:.2f} SAR")
                with colm2:
                    st.metric("سعر بعد الخصم", f"{breakdown['price_after_discount']:.2f} SAR")
                with colm3:
                    st.metric("صافي الربح", f"{breakdown['profit']:.2f} SAR")
                with colm4:
                    st.metric("هامش الربح", f"{breakdown['margin_pct']*100:.1f}%")

                # Detailed comparison tables (سعرنا / المنافس / التعادل)
                def build_detail_rows(bd: dict, rate_map: dict, list_price: float) -> pd.DataFrame:
                    custom_total = bd.get("custom_fees_total", 0)
                    rows = [
                        ("الجزء الأول: التسعير", None, None),
                        ("سعر البيع شامل الضريبة قبل الخصم", list_price, None),
                        ("نسبة الخصم", bd.get("discount_rate", 0) * 100, "%"),
                        ("مبلغ الخصم", bd.get("discount_amount", 0), None),
                        ("سعر البيع شامل الضريبة بعد الخصم", bd.get("price_after_discount", 0), None),
                        ("سعر البيع غير الضريبة بعد الخصم", bd.get("net_price", 0), None),
                        ("الجزء الثاني: تكلفة البضاعة المباعة", None, None),
                        ("تكلفة البضاعة للوحدة", bd.get("cogs", 0), None),
                        ("الجزء الثالث: رسوم المنصة", None, None),
                        ("التحضير", bd.get("preparation_fee", 0), None),
                        ("الشحن", bd.get("shipping_fee", 0), None),
                    ]

                    if bd.get("admin_fee", 0) > 0:
                        rows.append(("المصاريف الإدارية", bd.get("admin_fee", 0), f"{rate_map['admin']*100:.1f}%"))
                    if bd.get("marketing_fee", 0) > 0:
                        rows.append(("مصاريف التسويق", bd.get("marketing_fee", 0), f"{rate_map['marketing']*100:.1f}%"))
                    if bd.get("platform_fee", 0) > 0:
                        rows.append(("رسوم المنصات", bd.get("platform_fee", 0), f"{rate_map['platform']*100:.1f}%"))
                    if custom_total > 0:
                        rows.append(("رسوم مخصصة", custom_total, None))

                    rows.extend(
                        [
                            ("إجمالي التكلفة والرسوم", bd.get("total_costs_fees", 0), None),
                            ("الجزء الرابع: صافي الربح", None, None),
                            ("الربح", bd.get("profit", 0), None),
                            ("هامش الربح %", bd.get("margin_pct", 0) * 100, "%"),
                        ]
                    )

                    df = pd.DataFrame(rows, columns=["البند", "القيمة", "ملاحظة"])

                    def format_comparison_row(row):
                        label = row["البند"]
                        if label and label.startswith("الجزء"):
                            return ["background-color: #1e88e5; color: white; font-weight: bold"] * len(row)
                        if label == "إجمالي التكلفة والرسوم":
                            return ["background-color: #fff3cd; font-weight: bold"] * len(row)
                        if label in ["الربح", "هامش الربح %"]:
                            return ["background-color: #d4edda; font-weight: bold"] * len(row)
                        return [""] * len(row)

                    styled = (
                        df.style.apply(format_comparison_row, axis=1)
                        .format(
                            {
                                "القيمة": lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else ("" if x is None else x),
                                "ملاحظة": lambda x: "" if x is None else x,
                            }
                        )
                        .set_table_styles(
                            [
                                {
                                    "selector": "th",
                                    "props": [
                                        ("background-color", "#1e88e5"),
                                        ("color", "white"),
                                        ("font-weight", "bold"),
                                        ("text-align", "center"),
                                        ("padding", "8px"),
                                    ],
                                },
                                {
                                    "selector": "td",
                                    "props": [("text-align", "right"), ("padding", "6px"), ("border", "1px solid #ddd")],
                                },
                                {"selector": "", "props": [("border-collapse", "collapse"), ("width", "100%")]},
                            ]
                        )
                    )

                    return styled

                # Build rate map once
                rate_map = {
                    "admin": channel_dict.get("opex_pct", 0),
                    "marketing": channel_dict.get("marketing_pct", 0),
                    "platform": channel_dict.get("platform_pct", 0),
                }

                # Breakeven breakdown (Goal Seek: margin = 0%)
                breakeven_margin = 0.0
                
                # حساب أولي لسعر التعادل لفحص الحد الأدنى للشحن (نفترض مجاني)
                temp_breakeven_denom = 1 - total_pct - breakeven_margin
                if temp_breakeven_denom <= 0 or (1 - discount_pct) <= 0:
                    breakeven_shipping = 0
                    breakeven_preparation = 0
                else:
                    temp_breakeven_fixed = total_package_cost + 0 + 0 + custom_fixed
                    temp_breakeven_net = temp_breakeven_fixed / temp_breakeven_denom
                    temp_breakeven_after_discount = temp_breakeven_net * (1 + vat_rate)
                    temp_breakeven_list = temp_breakeven_after_discount / (1 - discount_pct)
                    
                    # فحص: إذا السعر ≤ الحد → شحن مجاني، إذا > الحد → احسب رسوم
                    if free_threshold > 0 and temp_breakeven_list <= free_threshold:
                        breakeven_shipping = 0
                        breakeven_preparation = 0
                    else:
                        breakeven_shipping = shipping
                        breakeven_preparation = preparation
                
                # إعادة الحساب بالرسوم الفعلية
                breakeven_fixed_costs = total_package_cost + breakeven_shipping + breakeven_preparation + custom_fixed
                breakeven_denom = 1 - total_pct - breakeven_margin
                
                if breakeven_denom <= 0 or (1 - discount_pct) <= 0:
                    breakeven_net = 0
                    breakeven_price_after_discount = 0
                    breakeven_list_price = 0
                    breakeven_discount = 0
                    breakeven_admin = 0
                    breakeven_marketing = 0
                    breakeven_platform = 0
                    breakeven_profit = 0
                else:
                    breakeven_net = breakeven_fixed_costs / breakeven_denom
                    breakeven_price_after_discount = breakeven_net * (1 + vat_rate)
                    breakeven_list_price = breakeven_price_after_discount / (1 - discount_pct)
                    breakeven_discount = breakeven_list_price * discount_pct
                    breakeven_admin = breakeven_net * admin_pct
                    breakeven_marketing = breakeven_net * marketing_pct
                    breakeven_platform = breakeven_net * platform_pct
                    breakeven_profit = breakeven_net - (total_package_cost + breakeven_shipping + breakeven_preparation + breakeven_admin + breakeven_marketing + breakeven_platform + custom_fees_total)
                
                breakeven_breakdown = {
                    "sale_price": breakeven_list_price,
                    "discount_amount": breakeven_discount,
                    "discount_rate": discount_pct,
                    "price_after_discount": breakeven_price_after_discount,
                    "vat_rate": vat_rate,
                    "net_price": breakeven_net,
                    "custom_fees": custom_fees_dict,
                    "custom_fees_total": custom_fees_total,
                    "cogs": total_package_cost,
                    "preparation_fee": breakeven_preparation,
                    "shipping_fee": breakeven_shipping,
                    "admin_fee": breakeven_admin,
                    "marketing_fee": breakeven_marketing,
                    "platform_fee": breakeven_platform,
                    "total_costs_fees": total_package_cost + breakeven_shipping + breakeven_preparation + breakeven_admin + breakeven_marketing + breakeven_platform + custom_fees_total,
                    "profit": breakeven_profit,
                    "margin_pct": breakeven_margin,
                }

                # Competitor breakdown (if provided)
                competitor_breakdown = None
                if competitor_price and competitor_price > 0:
                    # حساب عكسي من السعر المدخل
                    comp_list_price = competitor_price
                    comp_discount = comp_list_price * discount_pct
                    comp_after_discount = comp_list_price - comp_discount
                    comp_net = comp_after_discount / (1 + vat_rate)
                    
                    # فحص: إذا السعر ≤ الحد → شحن مجاني، إذا > الحد → احسب رسوم
                    if free_threshold > 0 and comp_list_price <= free_threshold:
                        comp_shipping = 0
                        comp_preparation = 0
                    else:
                        comp_shipping = shipping
                        comp_preparation = preparation
                    
                    comp_admin = comp_net * admin_pct
                    comp_marketing = comp_net * marketing_pct
                    comp_platform = comp_net * platform_pct
                    
                    comp_custom_total = custom_fixed
                    comp_custom_dict = {}
                    if custom_fees:
                        for fee_name, fee_data in custom_fees.items():
                            if fee_data.get("fee_type") == "percentage":
                                fee_amt = comp_net * fee_data.get("amount", 0)
                                comp_custom_total += fee_amt
                            else:
                                fee_amt = fee_data.get("amount", 0)
                            comp_custom_dict[fee_name] = fee_amt
                    
                    comp_total_costs = total_package_cost + comp_shipping + comp_preparation + comp_admin + comp_marketing + comp_platform + comp_custom_total
                    comp_profit = comp_net - comp_total_costs
                    comp_margin = (comp_profit / comp_net) if comp_net > 0 else 0
                    
                    competitor_breakdown = {
                        "sale_price": comp_list_price,
                        "discount_amount": comp_discount,
                        "discount_rate": discount_pct,
                        "price_after_discount": comp_after_discount,
                        "vat_rate": vat_rate,
                        "net_price": comp_net,
                        "custom_fees": comp_custom_dict,
                        "custom_fees_total": comp_custom_total,
                        "cogs": total_package_cost,
                        "preparation_fee": comp_preparation,
                        "shipping_fee": comp_shipping,
                        "admin_fee": comp_admin,
                        "marketing_fee": comp_marketing,
                        "platform_fee": comp_platform,
                        "total_costs_fees": comp_total_costs,
                        "profit": comp_profit,
                        "margin_pct": comp_margin,
                    }

                st.markdown("### مقارنة سعرنا مع المنافس (تفصيل كامل مثل ورقة الحساب)")
                col_cmp1, col_cmp2, col_cmp3 = st.columns(3)
                table_height = 820
                with col_cmp1:
                    st.markdown("**سعرنا**")
                    styled_ours = build_detail_rows(breakdown, rate_map, list_price)
                    st.dataframe(styled_ours, width="stretch", hide_index=True, height=table_height)
                with col_cmp2:
                    st.markdown("**سعر المنافس**")
                    if competitor_breakdown:
                        styled_comp = build_detail_rows(competitor_breakdown, rate_map, competitor_price)
                        st.dataframe(styled_comp, width="stretch", hide_index=True, height=table_height)
                    else:
                        st.info("أدخل سعر المنافس لعرض الجدول")
                with col_cmp3:
                    st.markdown("**سعر التعادل (0% ربح)**")
                    styled_breakeven = build_detail_rows(breakeven_breakdown, rate_map, breakeven_list_price)
                    st.dataframe(styled_breakeven, width="stretch", hide_index=True, height=table_height)

                # Components breakdown
                st.markdown("---")
                st.markdown("### 📋 مكونات البكج")
                st.dataframe(display_df, width="stretch", hide_index=True, height=300)
                
                # Save option
                st.markdown("---")
                if st.button("💾 حفظ البكج المخصص", type="primary", width="stretch"):
                    try:
                        import os
                        
                        data_dir = os.path.join(os.path.dirname(__file__), "data")
                        os.makedirs(data_dir, exist_ok=True)

                        pricing_record = {
                            "التاريخ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "اسم المنتج/البكج": package_name,
                            "SKU": "CUSTOM_PKG",
                            "النوع": "بكج مخصص",
                            "المنصة": selected_channel,
                            "التكلفة": total_package_cost,
                            "سعر القائمة": list_price,
                            "سعر بعد الخصم": breakdown["price_after_discount"],
                            "الربح": breakdown["profit"],
                            "هامش الربح %": breakdown["margin_pct"] * 100,
                            "المكونات": " + ".join([f"{c['name']} (x{c['quantity']})" for c in st.session_state.package_components]),
                        }

                        history_file = os.path.join(data_dir, "pricing_history.csv")

                        if os.path.exists(history_file):
                            history_df = pd.read_csv(history_file, encoding="utf-8-sig")
                            history_df = pd.concat([history_df, pd.DataFrame([pricing_record])], ignore_index=True)
                        else:
                            history_df = pd.DataFrame([pricing_record])

                        history_df.to_csv(history_file, index=False, encoding="utf-8-sig")
                        st.success("✅ تم حفظ البكج المخصص بنجاح!")
                        
                    except Exception as e:
                        st.error(f"❌ خطأ في الحفظ: {e}")
        
        else:
            st.info("💡 ابدأ بإضافة المنتجات/البكجات أعلاه، ثم اضغط **تجميع** لحساب التسعير")

elif st.session_state.page == "profit_margins":
    UIComponents.render_section_header("📊 تسعير منصة كاملة", "نسخة احترافية شاملة مع مؤشرات ورؤى فورية", "🚀")
    UIComponents.render_info_box(
        "احسب أسعار جميع المنتجات والبكجات دفعة واحدة مع لوحات بصرية، تنبيهات ذكية، وتصدير فوري.", "info"
    )

    # Load channels
    channels_file = "data/channels.json"
    channels_data = load_channels(channels_file)
    if not channels_data:
        st.warning("لا توجد قنوات محفوظة. يرجى إضافة قناة من صفحة الإعدادات أولاً.")
        st.stop()

    # Quick stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        UIComponents.render_metric_card(
            "عدد المنتجات", str(len(product_recipes)), "جاهزة للتسعير", "📦", ColorScheme.PRIMARY
        )
    with col2:
        UIComponents.render_metric_card(
            "عدد البكجات", str(len(package_compositions)), "محتوى مركب", "🎁", ColorScheme.SUCCESS
        )
    with col3:
        total_items = len(product_recipes) + len(package_compositions)
        UIComponents.render_metric_card("إجمالي العناصر", str(total_items), "منتج + بكج", "🧮", ColorScheme.WARNING)
    with col4:
        UIComponents.render_metric_card(
            "آخر تحديث للبيانات", DateTimeHelper.get_date_string(), "من ملفات البيانات", "⏱️", ColorScheme.INFO
        )

    st.markdown("---")

    # Configuration
    st.subheader("⚙️ إعدادات التسعير الجماعي")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        selected_channel = st.selectbox(
            "القناة / المنصة",
            options=list(channels_data.keys()),
            key="pm_channel",
            help="حدد القناة لتطبيق رسومها الافتراضية",
        )

    with col2:
        target_margin_pct = st.number_input(
            "هامش الربح المستهدف (%)", min_value=0.0, max_value=50.0, value=18.0, step=0.5, key="pm_margin"
        )

    with col3:
        discount_pct = st.number_input(
            "نسبة الخصم للعميل (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.5, key="pm_discount"
        )

    target_margin = target_margin_pct / 100
    discount_rate = discount_pct / 100
    channel = channels_data[selected_channel]

    # Set default values (no filtering)
    item_filter = ["منتج", "بكج"]
    min_cogs = 0.0
    max_cogs = 0.0

    st.caption("يتم تطبيق الخصم على السعر النهائي للعميل، بينما يبقى الهامش المستهدف بعد الخصم.")

    # Auto-recalculate when channel changes
    if "last_pm_channel" not in st.session_state:
        st.session_state["last_pm_channel"] = None
    
    channel_changed = (
        st.session_state["last_pm_channel"] is not None 
        and st.session_state["last_pm_channel"] != selected_channel
    )

    col_btn_left, col_btn_center, col_btn_right = st.columns([1, 2, 1])
    with col_btn_center:
        run_pricing = st.button("🚀 تشغيل المحرك الاحترافي", type="primary", width="stretch")

    if run_pricing or channel_changed:
        st.markdown("---")
        UIComponents.render_section_header("نتائج التسعير الجماعي", "حساب شامل لكل منتج وبكج", "📑")

        # Helper: calculate component cost
        def calculate_component_cost(sku, component_type):
            if component_type == "material" and sku in materials:
                return materials[sku].cost_per_unit
            if component_type == "product" and sku in product_recipes:
                total = 0
                for material_code, mat_qty in product_recipes[sku].items():
                    if material_code in materials:
                        total += materials[material_code].cost_per_unit * mat_qty
                return total
            if component_type == "package" and sku in package_compositions:
                total = 0
                for comp_sku, comp_qty in package_compositions[sku].items():
                    if comp_sku in materials:
                        total += materials[comp_sku].cost_per_unit * comp_qty
                    elif comp_sku in product_recipes:
                        total += calculate_component_cost(comp_sku, "product") * comp_qty
                    elif comp_sku in package_compositions:
                        total += calculate_component_cost(comp_sku, "package") * comp_qty
                return total
            return 0.0

        # Build items list
        all_items = []
        for _, row in products_summary.iterrows():
            all_items.append(
                {
                    "sku": row["Product_SKU"],
                    "name": row.get("Product_Name", row["Product_SKU"]),
                    "type": "منتج",
                    "cogs": calculate_component_cost(row["Product_SKU"], "product"),
                }
            )

        for _, row in packages_summary.iterrows():
            all_items.append(
                {
                    "sku": row["Package_SKU"],
                    "name": row.get("Package_Name", row["Package_SKU"]),
                    "type": "بكج",
                    "cogs": calculate_component_cost(row["Package_SKU"], "package"),
                }
            )

        # Apply filters
        filtered_items = [item for item in all_items if item["type"] in item_filter]
        if min_cogs > 0:
            filtered_items = [item for item in filtered_items if item["cogs"] >= min_cogs]
        if max_cogs > 0:
            filtered_items = [item for item in filtered_items if item["cogs"] <= max_cogs]

        if not filtered_items:
            st.warning("لا توجد عناصر مطابقة للمعايير المحددة")
            st.stop()

        # Pricing calculations
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        results = []

        shipping = channel.shipping_fixed
        preparation = channel.preparation_fee
        vat_rate = channel.vat_rate
        custom_fees = channel.custom_fees if hasattr(channel, "custom_fees") else {}
        free_shipping_threshold = channel.free_shipping_threshold if hasattr(channel, "free_shipping_threshold") else 0

        # إعداد قاموس الرسوم
        channel_dict = {
            "platform_pct": channel.platform_pct,
            "marketing_pct": channel.marketing_pct,
            "opex_pct": channel.opex_pct,
            "vat_rate": vat_rate,
        }

        # Binary Search Function (نفس الطريقة من صفحة التسعير الفردي)
        def solve_price_for_margin(cogs_val, target_margin_val):
            """استخدام Binary Search للوصول للسعر الذي يحقق الهامش المستهدف بدقة"""
            low = cogs_val * 1.1
            high = cogs_val * 10
            best_price = high
            best_bd = None

            tolerance = 0.0001
            for iteration in range(100):
                mid = (low + high) / 2
                bd = calculate_price_breakdown(
                    cogs=cogs_val,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=vat_rate,
                    free_shipping_threshold=free_shipping_threshold,
                    custom_fees=custom_fees,
                    price_with_vat=mid,
                )

                margin_diff = bd["margin_pct"] - target_margin_val

                if abs(margin_diff) < tolerance:
                    return mid, bd

                if margin_diff < 0:
                    low = mid
                else:
                    high = mid

                best_price = mid
                best_bd = bd

            return best_price, best_bd

        for idx, item in enumerate(filtered_items):
            status_placeholder.text(f"جاري تسعير {item['sku']} ({idx + 1}/{len(filtered_items)})")

            cogs_val = item["cogs"]

            # استخدام Binary Search للحصول على السعر الدقيق
            try:
                price_with_vat, breakdown = solve_price_for_margin(cogs_val, target_margin)

                # حساب السعر قبل الخصم
                price_before_discount = (
                    price_with_vat / (1 - discount_rate) if discount_rate > 0 else price_with_vat
                )

                # توليد تنبيهات
                alerts = []
                if breakdown["margin_pct"] < 0:
                    alerts.append("⛔ تحذير: السعر الحالي يحقق خسارة!")
                elif breakdown["margin_pct"] < 0.05:
                    alerts.append("⚠️ تحذير: هامش الربح أقل من الحد الأدنى المقبول (5.0%)")
                elif breakdown["margin_pct"] < 0.15:
                    alerts.append("💡 ملاحظة: هامش الربح أقل من الموصى به (15.0%)")
                elif breakdown["margin_pct"] >= 0.25:
                    alerts.append(f"✅ ممتاز: هامش ربح ممتاز ({breakdown['margin_pct']*100:.1f}%)")

                alerts_text = " | ".join(alerts) if alerts else "جيد"

                # حساب ROI
                roi = (breakdown["profit"] / breakdown["total_costs_fees"]) * 100 if breakdown["total_costs_fees"] > 0 else 0

                results.append(
                    {
                        "SKU": item["sku"],
                        "الاسم": item["name"],
                        "النوع": item["type"],
                        "الحالة": "تم التسعير",
                        "التكلفة": breakdown["cogs"],
                        "رسوم الشحن": breakdown["shipping_fee"],
                        "رسوم التحضير": breakdown["preparation_fee"],
                        "رسوم إدارية": breakdown["admin_fee"],
                        "رسوم تسويق": breakdown["marketing_fee"],
                        "رسوم المنصة": breakdown["platform_fee"],
                        "رسوم إضافية مخصصة": breakdown.get("custom_fees_total", 0),
                        "إجمالي الرسوم": breakdown["total_costs_fees"] - breakdown["cogs"],
                        "سعر قبل الخصم": price_before_discount,
                        "السعر النهائي بعد الخصم": breakdown["price_after_discount"],
                        "الربح": breakdown["profit"],
                        "هامش الربح %": breakdown["margin_pct"] * 100,
                        "ROI %": roi,
                        "نقطة التعادل": breakdown["breakeven_price"],
                        "الهامش الآمن %": ((breakdown["price_after_discount"] - breakdown["breakeven_price"]) / breakdown["breakeven_price"] * 100) if breakdown["breakeven_price"] > 0 else 0,
                        "توصية السعر": price_with_vat,
                        "تنبيهات": alerts_text,
                    }
                )
            except Exception as e:
                # في حالة فشل الحساب
                results.append(
                    {
                        "SKU": item["sku"],
                        "الاسم": item["name"],
                        "النوع": item["type"],
                        "الحالة": "غير قابل للتحقيق",
                        "التكلفة": cogs_val,
                        "رسوم الشحن": 0.0,
                        "رسوم التحضير": 0.0,
                        "رسوم إدارية": 0.0,
                        "رسوم تسويق": 0.0,
                        "رسوم المنصة": 0.0,
                        "إجمالي الرسوم": 0.0,
                        "سعر قبل الخصم": 0.0,
                        "السعر النهائي بعد الخصم": 0.0,
                        "الربح": 0.0,
                        "هامش الربح %": 0.0,
                        "ROI %": 0.0,
                        "نقطة التعادل": 0.0,
                        "الهامش الآمن %": 0.0,
                        "توصية السعر": 0.0,
                        "تنبيهات": f"خطأ في الحساب: {str(e)}",
                    }
                )


            progress_bar.progress((idx + 1) / len(filtered_items))

        status_placeholder.empty()
        progress_bar.empty()

        if not results:
            st.warning("لا توجد نتائج للعرض")
            st.stop()

        df_results = pd.DataFrame(results)
        priced_df = df_results[df_results["الحالة"] == "تم التسعير"]

        if priced_df.empty:
            st.warning("لم يتم تسعير أي عنصر بسبب حدود الهامش أو الفلاتر")
            st.stop()

        # Save results to session state
        st.session_state["priced_results"] = priced_df
        st.session_state["last_pm_channel"] = selected_channel
        st.session_state["last_pm_target_margin"] = target_margin_pct
        
        st.success("✅ تم التسعير بنجاح! استخدم الفلاتر أدناه للبحث والتصفية.")

    # Display results if available (outside the if block to allow filtering)
    if "priced_results" in st.session_state and st.session_state["priced_results"] is not None:
        priced_df = st.session_state["priced_results"]
        # Retrieve saved target margin for display
        saved_target_margin = st.session_state.get("last_pm_target_margin", target_margin_pct)
        
        st.markdown("---")
        
        # Summary metrics
        st.markdown("### 💡 لقطات سريعة")
        col1, col2, col3, col4 = st.columns(4)

        avg_margin = priced_df["هامش الربح %"].mean()
        total_revenue = priced_df["السعر النهائي بعد الخصم"].sum()
        profitable = len(priced_df[priced_df["الربح"] > 0])
        loss_items = len(priced_df[priced_df["الربح"] <= 0])

        with col1:
            UIComponents.render_metric_card(
                "متوسط الهامش",
                FormatHelper.format_percentage(avg_margin, 1),
                f"هدفك {saved_target_margin:.0f}%",
                "📈",
                ColorScheme.SUCCESS,
            )
        with col2:
            UIComponents.render_metric_card(
                "إجمالي الإيراد المتوقع",
                FormatHelper.format_currency(total_revenue),
                "بعد الخصم",
                "💰",
                ColorScheme.PRIMARY,
            )
        with col3:
            UIComponents.render_metric_card("منتجات رابحة", str(profitable), "عناصر تحقق ربح", "✅", ColorScheme.INFO)
        with col4:
            UIComponents.render_metric_card(
                "منتجات بحاجة مراجعة", str(loss_items), "هامش منخفض أو خسارة", "⚠️", ColorScheme.WARNING
            )

        st.markdown("---")

        # رسوم بيانية تفاعلية للنتائج
        st.markdown("### 📊 تحليل بصري للنتائج")
        
        tab1, tab2, tab3, tab4 = st.tabs(["💰 توزيع الأرباح", "📈 هوامش الربح", "💵 التسعير", "📉 التكاليف"])
        
        with tab1:
            st.markdown("#### توزيع الأرباح حسب المنتجات")
            # رسم بياني شريطي للأرباح
            top_n = min(15, len(priced_df))
            top_profit_df = priced_df.nlargest(top_n, "الربح")[["الاسم", "الربح", "هامش الربح %"]].copy()
            
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Bar(
                x=top_profit_df["الاسم"],
                y=top_profit_df["الربح"],
                marker_color=top_profit_df["الربح"].apply(
                    lambda x: '#2ecc71' if x > 0 else '#e74c3c'
                ),
                text=top_profit_df["الربح"].round(2),
                textposition='outside',
                name='الربح',
                hovertemplate='<b>%{x}</b><br>الربح: %{y:.2f} SAR<br>الهامش: %{customdata:.1f}%<extra></extra>',
                customdata=top_profit_df["هامش الربح %"]
            ))
            
            fig_profit.update_layout(
                title=f"أعلى {top_n} منتجات من حيث الربح",
                xaxis_title="المنتج",
                yaxis_title="الربح (SAR)",
                height=500,
                showlegend=False,
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig_profit, width="stretch")
            
        with tab2:
            st.markdown("#### هوامش الربح % لجميع المنتجات")
            # رسم بياني دائري لتوزيع الهوامش
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # توزيع فئات الهامش
                margin_categories = pd.cut(
                    priced_df["هامش الربح %"],
                    bins=[-float('inf'), 0, 10, 20, float('inf')],
                    labels=['خسارة (<0%)', 'منخفض (0-10%)', 'جيد (10-20%)', 'ممتاز (≥20%)']
                )
                margin_dist = margin_categories.value_counts()
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=margin_dist.index,
                    values=margin_dist.values,
                    hole=0.4,
                    marker=dict(colors=['#e74c3c', '#f39c12', '#3498db', '#2ecc71']),
                    textinfo='label+percent',
                    hovertemplate='<b>%{label}</b><br>العدد: %{value}<br>النسبة: %{percent}<extra></extra>'
                )])
                
                fig_pie.update_layout(
                    title="توزيع فئات الهامش",
                    height=400,
                    showlegend=True,
                )
                st.plotly_chart(fig_pie, width="stretch")
            
            with col_chart2:
                # رسم بياني شريطي لهوامش الربح
                sorted_df = priced_df.sort_values("هامش الربح %", ascending=False).head(15)
                
                fig_margin = go.Figure()
                fig_margin.add_trace(go.Bar(
                    x=sorted_df["الاسم"],
                    y=sorted_df["هامش الربح %"],
                    marker_color=sorted_df["هامش الربح %"].apply(
                        lambda x: '#2ecc71' if x >= 20 else '#3498db' if x >= 10 else '#f39c12' if x >= 0 else '#e74c3c'
                    ),
                    text=sorted_df["هامش الربح %"].round(1).astype(str) + '%',
                    textposition='outside',
                    name='هامش الربح %',
                    hovertemplate='<b>%{x}</b><br>الهامش: %{y:.1f}%<extra></extra>'
                ))
                
                fig_margin.update_layout(
                    title="أعلى هوامش ربح",
                    xaxis_title="المنتج",
                    yaxis_title="هامش الربح %",
                    height=400,
                    showlegend=False,
                )
                st.plotly_chart(fig_margin, width="stretch")
        
        with tab3:
            st.markdown("#### مقارنة الأسعار")
            # مقارنة السعر قبل وبعد الخصم
            comparison_df = priced_df.head(15)[["الاسم", "سعر قبل الخصم", "السعر النهائي بعد الخصم"]].copy()
            
            fig_price = go.Figure()
            fig_price.add_trace(go.Bar(
                name='سعر قبل الخصم',
                x=comparison_df["الاسم"],
                y=comparison_df["سعر قبل الخصم"],
                marker_color='#3498db',
                text=comparison_df["سعر قبل الخصم"].round(2),
                textposition='outside',
            ))
            fig_price.add_trace(go.Bar(
                name='السعر النهائي',
                x=comparison_df["الاسم"],
                y=comparison_df["السعر النهائي بعد الخصم"],
                marker_color='#2ecc71',
                text=comparison_df["السعر النهائي بعد الخصم"].round(2),
                textposition='outside',
            ))
            
            fig_price.update_layout(
                title="مقارنة الأسعار (قبل وبعد الخصم)",
                xaxis_title="المنتج",
                yaxis_title="السعر (SAR)",
                barmode='group',
                height=500,
                hovermode='x unified',
            )
            st.plotly_chart(fig_price, width="stretch")
        
        with tab4:
            st.markdown("#### تحليل التكاليف")
            # رسم بياني مكدس للتكاليف
            cost_analysis_df = priced_df.head(10)[
                ["الاسم", "التكلفة", "رسوم الشحن", "رسوم التحضير", "رسوم إدارية", "رسوم تسويق", "رسوم المنصة"]
            ].copy()
            
            fig_cost = go.Figure()
            
            fig_cost.add_trace(go.Bar(
                name='التكلفة الأساسية',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["التكلفة"],
                marker_color='#34495e'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم الشحن',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم الشحن"],
                marker_color='#9b59b6'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم التحضير',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم التحضير"],
                marker_color='#e67e22'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم إدارية',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم إدارية"],
                marker_color='#e74c3c'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم تسويق',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم تسويق"],
                marker_color='#f39c12'
            ))
            fig_cost.add_trace(go.Bar(
                name='رسوم المنصة',
                x=cost_analysis_df["الاسم"],
                y=cost_analysis_df["رسوم المنصة"],
                marker_color='#16a085'
            ))
            
            fig_cost.update_layout(
                title="تفصيل التكاليف والرسوم (أول 10 منتجات)",
                xaxis_title="المنتج",
                yaxis_title="المبلغ (SAR)",
                barmode='stack',
                height=500,
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            st.plotly_chart(fig_cost, width="stretch")

        st.markdown("---")

        # Data table with all columns in one table (like individual pricing page but as columns)
        st.markdown("### 📋 جدول التسعير التفصيلي")
        
        # Search and filter section
        col_search, col_filter1, col_filter2 = st.columns([2, 1, 1])
        
        with col_search:
            search_term = st.text_input("🔍 بحث بالاسم أو SKU", placeholder="ابحث...", key="search_pricing_table")
        
        with col_filter1:
            filter_type = st.multiselect(
                "فلتر حسب النوع",
                options=["منتج", "بكج"],
                default=["منتج", "بكج"],
                key="filter_type_pricing"
            )
        
        with col_filter2:
            filter_margin = st.selectbox(
                "فلتر حسب الهامش",
                options=["الكل", "ممتاز (≥20%)", "جيد (10-20%)", "منخفض (<10%)", "خسارة (<0%)"],
                key="filter_margin_pricing"
            )
        
        # Apply filters
        filtered_df = priced_df.copy()
        
        # Search filter
        if search_term:
            filtered_df = filtered_df[
                filtered_df["SKU"].str.contains(search_term, case=False, na=False) |
                filtered_df["الاسم"].str.contains(search_term, case=False, na=False)
            ]
        
        # Type filter
        if filter_type:
            filtered_df = filtered_df[filtered_df["النوع"].isin(filter_type)]
        
        # Margin filter
        if filter_margin == "ممتاز (≥20%)":
            filtered_df = filtered_df[filtered_df["هامش الربح %"] >= 20]
        elif filter_margin == "جيد (10-20%)":
            filtered_df = filtered_df[(filtered_df["هامش الربح %"] >= 10) & (filtered_df["هامش الربح %"] < 20)]
        elif filter_margin == "منخفض (<10%)":
            filtered_df = filtered_df[(filtered_df["هامش الربح %"] >= 0) & (filtered_df["هامش الربح %"] < 10)]
        elif filter_margin == "خسارة (<0%)":
            filtered_df = filtered_df[filtered_df["هامش الربح %"] < 0]
        
        st.info(f"📊 عرض {len(filtered_df)} من أصل {len(priced_df)} منتج/بكج")
        
        display_cols = [
            "SKU",
            "الاسم",
            "النوع",
            # الجزء الأول: التسعير
            "سعر قبل الخصم",
            "السعر النهائي بعد الخصم",
            # الجزء الثاني: تكلفة البضاعة المباعة
            "التكلفة",
            # الجزء الثالث: رسوم المنصة
            "رسوم الشحن",
            "رسوم التحضير",
            "رسوم إدارية",
            "رسوم تسويق",
            "رسوم المنصة",
            "رسوم إضافية مخصصة",
            "إجمالي الرسوم",
            # الجزء الرابع: صافي الربح
            "الربح",
            "هامش الربح %",
            "ROI %",
            "نقطة التعادل",
            "الهامش الآمن %",
            "تنبيهات",
        ]
        
        # تصفية الأعمدة الموجودة فقط
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        
        styled_table = TableFormatter.style_dataframe(
            filtered_df[available_cols], highlight_cols=["الربح", "هامش الربح %"], precision=2
        )
        st.dataframe(styled_table, width="stretch", hide_index=True, height=600)

        st.markdown("#### 📥 تنزيل النتائج")
        export_col1, export_col2 = st.columns(2)
        
        # Use saved values for filename
        saved_channel = st.session_state.get("last_pm_channel", selected_channel)
        
        with export_col1:
            csv_bytes = ExportManager.export_to_csv(priced_df, "pricing_results.csv")
            st.download_button(
                "تنزيل CSV",
                data=csv_bytes,
                file_name=f"pricing_results_{saved_channel}_{saved_target_margin}pct.csv",
                mime="text/csv",
                width="stretch",
            )
        with export_col2:
            excel_bytes = ExportManager.export_to_excel(priced_df, "pricing_results.xlsx", sheet_name="results")
            st.download_button(
                "تنزيل Excel",
                data=excel_bytes,
                file_name=f"pricing_results_{saved_channel}_{saved_target_margin}pct.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )

# Page: Saved History
elif st.session_state.page == "history":
    st.header("🗂️ السجلات المحفوظة")
    st.markdown("عرض وتحميل كل نتائج التسعير المحفوظة")

    import os

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    history_file = os.path.join(data_dir, "pricing_history.csv")

    hist_df = None

    # Try to load from file first
    if os.path.exists(history_file):
        try:
            hist_df = pd.read_csv(history_file, encoding="utf-8-sig")
            st.success(f"✅ تم تحميل {len(hist_df)} سجلات من الملف")
        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")

    # Fallback to session state
    if hist_df is None or hist_df.empty:
        if "saved_history_preview" in st.session_state:
            hist_df = st.session_state["saved_history_preview"]
            st.info(f"📋 عرض {len(hist_df)} سجلات من الذاكرة المؤقتة")

    if hist_df is not None and not hist_df.empty:
        st.download_button(
            "⬇️ تحميل السجلات CSV",
            data=hist_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="pricing_history.csv",
            mime="text/csv",
            width="stretch",
        )
        st.dataframe(hist_df, width="stretch", hide_index=True)
    else:
        st.info("لا توجد سجلات محفوظة بعد. احفظ نتيجة تسعير أولاً من صفحة التسعير.")
        st.caption(f"📁 مسار الملف المتوقع: {history_file}")


# Page: Profitability Analysis
elif st.session_state.page == "profitability":
    st.header("💹 تحليل الربحية")
    st.markdown("تحليل شامل للأرباح والخسائر من البيانات المالية")
    st.markdown("---")
    
    # Check if P&L file exists
    pl_file_path = "data/profit_loss.csv"
    if not os.path.exists(pl_file_path):
        st.warning("⚠️ لم يتم رفع ملف الأرباح والخسائر بعد!")
        st.info("📤 قم برفع الملف من صفحة 'رفع الملفات' → تاب 'الأرباح والخسائر'")
        
        if st.button("🔄 الذهاب لصفحة رفع الملفات", type="primary"):
            st.session_state.page = "upload"
            st.rerun()
        st.stop()
    
    # Load P&L data
    try:
        pl_df = pd.read_csv(pl_file_path, encoding="utf-8-sig")
        pl_df.columns = pl_df.columns.str.strip()
        
        # Clean amount column
        amount_col = 'net_amount' if 'net_amount' in pl_df.columns else ' net_amount '
        pl_df[amount_col] = pl_df[amount_col].astype(str).str.replace(',', '').astype(float)
        
        st.success(f"✅ تم تحميل {len(pl_df):,} سجل مالي")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            if 'Years' in pl_df.columns:
                years = ['الكل'] + sorted(pl_df['Years'].unique().tolist())
                selected_year = st.selectbox("السنة", years)
                if selected_year != 'الكل':
                    pl_df = pl_df[pl_df['Years'] == selected_year]
        
        with col2:
            if 'date' in pl_df.columns:
                months = ['الكل'] + sorted(pl_df['date'].unique().tolist())
                selected_month = st.selectbox("الشهر", months)
                if selected_month != 'الكل':
                    pl_df = pl_df[pl_df['date'] == selected_month]
        
        with col3:
            if 'Cost Center' in pl_df.columns:
                cost_centers = ['الكل'] + sorted(pl_df['Cost Center'].dropna().unique().tolist())
                selected_cc = st.selectbox("القناة/مركز التكلفة", cost_centers)
                if selected_cc != 'الكل':
                    pl_df = pl_df[pl_df['Cost Center'] == selected_cc]
        
        st.markdown("---")
        
        # Calculate key metrics
        income_df = pl_df[pl_df['Account Level 1'] == 'income']
        cogs_df = pl_df[pl_df['Account Level 1'] == 'cost_of_goods_sold']
        expense_df = pl_df[pl_df['Account Level 1'] == 'expense']
        other_income_df = pl_df[pl_df['Account Level 1'] == 'other_income']
        other_expense_df = pl_df[pl_df['Account Level 1'] == 'other_expense']
        
        total_income = income_df[amount_col].sum()
        total_cogs = cogs_df[amount_col].sum()
        total_expenses = expense_df[amount_col].sum()
        total_other_income = other_income_df[amount_col].sum()
        total_other_expense = other_expense_df[amount_col].sum()
        
        gross_profit = total_income - total_cogs
        operating_profit = gross_profit - total_expenses
        net_profit = operating_profit + total_other_income - total_other_expense
        
        gross_margin = (gross_profit / total_income * 100) if total_income > 0 else 0
        net_margin = (net_profit / total_income * 100) if total_income > 0 else 0
        
        # Display Key Metrics
        st.subheader("📊 المؤشرات الرئيسية")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("إجمالي الإيرادات", f"{total_income:,.0f} SAR", 
                     help="مجموع جميع الإيرادات")
        with col2:
            st.metric("تكلفة البضاعة", f"{total_cogs:,.0f} SAR",
                     delta=f"{(total_cogs/total_income*100):.1f}%" if total_income > 0 else "0%",
                     delta_color="inverse")
        with col3:
            st.metric("الربح الإجمالي", f"{gross_profit:,.0f} SAR",
                     delta=f"{gross_margin:.1f}%")
        with col4:
            st.metric("المصاريف التشغيلية", f"{total_expenses:,.0f} SAR",
                     delta=f"{(total_expenses/total_income*100):.1f}%" if total_income > 0 else "0%",
                     delta_color="inverse")
        with col5:
            st.metric("صافي الربح", f"{net_profit:,.0f} SAR",
                     delta=f"{net_margin:.1f}%",
                     delta_color="normal" if net_profit >= 0 else "inverse")
        
        st.markdown("---")
        
        # Charts
        tab1, tab2, tab3, tab4 = st.tabs(["📈 الإيرادات والتكاليف", "🎯 توزيع المصاريف", "📊 الاتجاهات الشهرية", "🏪 تحليل القنوات"])
        
        with tab1:
            # Revenue vs Costs breakdown
            breakdown_data = pd.DataFrame({
                'الفئة': ['الإيرادات', 'تكلفة البضاعة', 'المصاريف التشغيلية', 'إيرادات أخرى', 'مصاريف أخرى'],
                'المبلغ': [total_income, -total_cogs, -total_expenses, total_other_income, -total_other_expense],
                'النوع': ['إيجابي', 'سلبي', 'سلبي', 'إيجابي', 'سلبي']
            })
            
            fig = px.bar(breakdown_data, x='الفئة', y='المبلغ', color='النوع',
                        color_discrete_map={'إيجابي': '#10b981', 'سلبي': '#ef4444'},
                        title="توزيع الإيرادات والمصاريف")
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="المبلغ (SAR)")
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Expense breakdown
            if not expense_df.empty and 'Account Level 2' in expense_df.columns:
                exp_by_type = expense_df.groupby('Account Level 2')[amount_col].sum().sort_values(ascending=False)
                
                fig = px.pie(values=exp_by_type.values, names=exp_by_type.index,
                            title="توزيع المصاريف حسب النوع")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(pd.DataFrame({
                    'نوع المصروف': exp_by_type.index,
                    'المبلغ (SAR)': exp_by_type.values,
                    'النسبة %': (exp_by_type.values / total_expenses * 100).round(2)
                }), use_container_width=True, hide_index=True)
        
        with tab3:
            # Monthly trends
            if 'date' in pl_df.columns:
                monthly_data = pl_df.groupby(['date', 'Account Level 1'])[amount_col].sum().reset_index()
                monthly_pivot = monthly_data.pivot(index='date', columns='Account Level 1', values=amount_col).fillna(0)
                
                if 'income' in monthly_pivot.columns:
                    monthly_pivot['صافي الربح'] = (
                        monthly_pivot.get('income', 0) - 
                        monthly_pivot.get('cost_of_goods_sold', 0) - 
                        monthly_pivot.get('expense', 0) +
                        monthly_pivot.get('other_income', 0) -
                        monthly_pivot.get('other_expense', 0)
                    )
                    
                    fig = go.Figure()
                    if 'income' in monthly_pivot.columns:
                        fig.add_trace(go.Scatter(x=monthly_pivot.index, y=monthly_pivot['income'],
                                                name='الإيرادات', line=dict(color='#10b981', width=3)))
                    if 'cost_of_goods_sold' in monthly_pivot.columns:
                        fig.add_trace(go.Scatter(x=monthly_pivot.index, y=monthly_pivot['cost_of_goods_sold'],
                                                name='تكلفة البضاعة', line=dict(color='#f59e0b', width=2)))
                    fig.add_trace(go.Scatter(x=monthly_pivot.index, y=monthly_pivot['صافي الربح'],
                                            name='صافي الربح', line=dict(color='#3b82f6', width=3, dash='dash')))
                    
                    fig.update_layout(title="الاتجاهات الشهرية", xaxis_title="الشهر", yaxis_title="المبلغ (SAR)",
                                     hovermode='x unified')
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            # Channel analysis
            if 'Cost Center' in pl_df.columns:
                channel_data = pl_df.groupby(['Cost Center', 'Account Level 1'])[amount_col].sum().reset_index()
                channel_pivot = channel_data.pivot(index='Cost Center', columns='Account Level 1', values=amount_col).fillna(0)
                
                channel_pivot['الإيرادات'] = channel_pivot.get('income', 0)
                channel_pivot['التكاليف'] = channel_pivot.get('cost_of_goods_sold', 0)
                channel_pivot['الربح الإجمالي'] = channel_pivot['الإيرادات'] - channel_pivot['التكاليف']
                channel_pivot['هامش الربح %'] = (channel_pivot['الربح الإجمالي'] / channel_pivot['الإيرادات'] * 100).round(2)
                
                display_cols = ['الإيرادات', 'التكاليف', 'الربح الإجمالي', 'هامش الربح %']
                st.dataframe(channel_pivot[display_cols].sort_values('الإيرادات', ascending=False),
                           use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")


# Page: Pricing Review
elif st.session_state.page == "salla_analysis":
    st.header("📦 تحليل طلبات سلة")
    st.markdown("تحليل تفصيلي للطلبات")
    
    # قراءة ملف الطلبات المفكك باستخدام التخزين المؤقت
    exploded_file = "data/salla_orders_exploded.csv"
    orders_file = "data/salla_orders.csv"
    sample_file = "data/salla_orders_sample.csv"
    
    # أولوية للملف المفكك، ثم الملف الكامل، ثم الـ sample
    if os.path.exists(exploded_file):
        orders_file = exploded_file
    elif os.path.exists(orders_file):
        orders_file = orders_file
    elif os.path.exists(sample_file):
        orders_file = sample_file
    elif not os.path.exists(orders_file):
        st.warning("⚠️ ملف الطلبات غير موجود!")
        st.stop()

    # استخدام التخزين المؤقت لتسريع التحميل
    with st.spinner("جاري تحميل البيانات..."):
        orders_df = load_salla_orders_cached(orders_file)
    
    if orders_df is None:
        st.error("❌ فشل تحميل البيانات")
        st.stop()

    try:
        # توحيد أسماء الأعمدة للإنجليزية
        column_mapping = {
            'رقم الطلب': 'order_id',
            'حالة الطلب': 'status',
            'المدينة': 'city',
            'SKU': 'sku_raw',
            'طريقة الدفع': 'payment_method',
            'تاريخ الطلب': 'order_date'
        }
        
        # تطبيق التحويل إذا كانت الأعمدة بالعربي
        if 'رقم الطلب' in orders_df.columns:
            orders_df = orders_df.rename(columns=column_mapping)
        
        # تحويل التاريخ
        orders_df['order_date'] = pd.to_datetime(orders_df['order_date'], errors='coerce', dayfirst=True)
        
        # تفكيك SKU إذا لزم الأمر
        if 'sku_raw' in orders_df.columns and 'sku_code' not in orders_df.columns:
            with st.spinner("🔄 جاري تفكيك المنتجات والبكجات..."):
                from pricing_app.salla_normalizer import parse_sku_cell
                
                normalized_rows = []
                total_rows = len(orders_df)
                progress_bar = st.progress(0)
                
                for idx, row in orders_df.iterrows():
                    if idx % 100 == 0:
                        progress_bar.progress(min(idx / total_rows, 1.0))
                    
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
                
                progress_bar.progress(1.0)
                orders_df = pd.DataFrame(normalized_rows)
                orders_df['order_date'] = pd.to_datetime(orders_df['order_date'], errors='coerce')
                
                # حفظ النتيجة المفككة
                orders_df.to_csv("data/salla_orders_exploded.csv", index=False)
                st.success(f"✅ تم التفكيك! {len(orders_df):,} صف من {total_rows:,} طلب")
                progress_bar.empty()
        
        # استخراج السنة والشهر
        orders_df['year'] = orders_df['order_date'].dt.year
        orders_df['month'] = orders_df['order_date'].dt.month
        orders_df['year_month'] = orders_df['order_date'].dt.to_period('M').astype(str)
        
    except Exception as e:
        st.error(f"❌ خطأ في قراءة الملف: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

    # ========== الفلاتر أعلى الصفحة ==========
    st.markdown("### 🔍 فلاتر التحليل")
    
    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
    
    # فلتر السنة
    with col_f1:
        years = sorted(orders_df['year'].dropna().unique().astype(int))
        selected_year = st.selectbox("📅 السنة", ["الكل"] + years, key="salla_year_filter")
    
    # فلتر الشهر
    with col_f2:
        months_ar = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
            5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
            9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }
        months = sorted(orders_df['month'].dropna().unique().astype(int))
        month_options = ["الكل"] + [f"{months_ar.get(m, m)} ({m})" for m in months]
        selected_month = st.selectbox("📆 الشهر", month_options, key="salla_month_filter")
    
    # فلتر حالة الطلب
    with col_f3:
        statuses = ["الكل"] + sorted(orders_df['status'].dropna().unique().tolist())
        selected_status = st.selectbox("📋 حالة الطلب", statuses, key="salla_status_filter")
    
    # فلتر المدينة
    with col_f4:
        cities = ["الكل"] + sorted(orders_df['city'].dropna().unique().tolist())
        selected_city = st.selectbox("🏙️ المدينة", cities, key="salla_city_filter")
    
    # فلتر طريقة الدفع
    with col_f5:
        payments = ["الكل"] + sorted(orders_df['payment_method'].dropna().unique().tolist())
        selected_payment = st.selectbox("💳 طريقة الدفع", payments, key="salla_payment_filter")
    
    # تطبيق الفلاتر
    filtered_df = orders_df.copy()
    
    if selected_year != "الكل":
        filtered_df = filtered_df[filtered_df['year'] == selected_year]
    
    if selected_month != "الكل":
        month_num = int(selected_month.split("(")[1].split(")")[0])
        filtered_df = filtered_df[filtered_df['month'] == month_num]
    
    if selected_status != "الكل":
        filtered_df = filtered_df[filtered_df['status'] == selected_status]
    
    if selected_city != "الكل":
        filtered_df = filtered_df[filtered_df['city'] == selected_city]
    
    if selected_payment != "الكل":
        filtered_df = filtered_df[filtered_df['payment_method'] == selected_payment]
    
    # زر لتوليد التحليلات وحفظها
    if st.button("🔄 تحديث وحفظ جميع التحليلات", type="primary"):
        with st.spinner("جاري توليد التحليلات..."):
            try:
                from pricing_app.salla_insights import SallaInsights
                # تحديد الملف المتاح
                if os.path.exists("data/salla_orders_exploded.csv"):
                    data_file = "data/salla_orders_exploded.csv"
                elif os.path.exists("data/salla_orders.csv"):
                    data_file = "data/salla_orders.csv"
                else:
                    data_file = "data/salla_orders_sample.csv"
                analyzer = SallaInsights(data_file)
                analyzer.load_pricing_data()
                analyzer.save_insights()
                st.success("✅ تم حفظ جميع التحليلات في مجلد data/")
                st.rerun()
            except Exception as e:
                st.error(f"خطأ: {e}")
    
    st.markdown("---")
    
    # ========== المقاييس الرئيسية ==========
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 إجمالي الطلبات", f"{filtered_df['order_id'].nunique():,}")
    with col2:
        if 'sku_code' in filtered_df.columns:
            st.metric("🛍️ إجمالي المنتجات", f"{filtered_df['sku_code'].nunique():,}")
        else:
            st.metric("🛍️ إجمالي المنتجات", "N/A")
    with col3:
        if 'qty' in filtered_df.columns:
            st.metric("📊 إجمالي الكمية", f"{int(filtered_df['qty'].sum()):,}")
        else:
            st.metric("📊 إجمالي الكمية", "N/A")
    with col4:
        st.metric("📋 عدد الصفوف", f"{len(filtered_df):,}")
    
    # التحقق من أن البيانات مفككة
    if 'sku_code' not in filtered_df.columns or 'qty' not in filtered_df.columns:
        st.error("❌ البيانات غير مفككة! يجب أن تحتوي على أعمدة: sku_code, sku_name, qty")
        st.info("💡 استخدم `python pricing_app/salla_normalizer.py` لتفكيك الملف الخام")
        st.stop()

    st.markdown("---")

    # ========== أكثر المنتجات/البكجات مبيعًا ==========
    st.subheader("🏆 أكثر المنتجات والبكجات مبيعًا")
    
    # حساب الكميات حسب SKU
    sku_sales = filtered_df.groupby(['sku_code', 'sku_name'])['qty'].sum().reset_index()
    sku_sales = sku_sales.sort_values('qty', ascending=False)
    sku_sales.columns = ['كود المنتج', 'اسم المنتج', 'الكمية المباعة']
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**🥇 أعلى 10 منتجات/بكجات**")
        st.dataframe(sku_sales.head(10), hide_index=True, use_container_width=True)
    
    with col_b:
        st.markdown("**📊 الكميات المباعة (الكل)**")
        st.dataframe(sku_sales, hide_index=True, use_container_width=True, height=400)

    st.markdown("---")

    # ========== المبيعات حسب المدينة ==========
    st.subheader("🗺️ المبيعات حسب المدينة")
    
    city_sales = filtered_df.groupby('city').agg({
        'order_id': 'nunique',
        'qty': 'sum',
        'sku_code': 'nunique'
    }).reset_index()
    city_sales.columns = ['المدينة', 'عدد الطلبات', 'الكمية الإجمالية', 'عدد المنتجات']
    city_sales = city_sales.sort_values('الكمية الإجمالية', ascending=False)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(city_sales, hide_index=True, use_container_width=True)
    
    with col2:
        # أكثر منتج مبيع في كل مدينة
        st.markdown("**🏆 أكثر منتج مبيعًا لكل مدينة**")
        top_per_city = filtered_df.groupby(['city', 'sku_code', 'sku_name'])['qty'].sum().reset_index()
        top_per_city = top_per_city.sort_values(['city', 'qty'], ascending=[True, False])
        top_per_city = top_per_city.groupby('city').first().reset_index()
        top_per_city.columns = ['المدينة', 'كود المنتج', 'اسم المنتج', 'الكمية']
        st.dataframe(top_per_city, hide_index=True, use_container_width=True)

    st.markdown("---")

    # ========== المبيعات حسب طريقة الدفع ==========
    st.subheader("💳 المبيعات حسب طريقة الدفع")
    
    payment_sales = filtered_df.groupby('payment_method').agg({
        'order_id': 'nunique',
        'qty': 'sum',
        'sku_code': 'nunique'
    }).reset_index()
    payment_sales.columns = ['طريقة الدفع', 'عدد الطلبات', 'الكمية الإجمالية', 'عدد المنتجات']
    payment_sales = payment_sales.sort_values('الكمية الإجمالية', ascending=False)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(payment_sales, hide_index=True, use_container_width=True)
    
    with col2:
        # أكثر منتج مبيع لكل طريقة دفع
        st.markdown("**🏆 أكثر منتج مبيعًا لكل طريقة دفع**")
        top_per_payment = filtered_df.groupby(['payment_method', 'sku_code', 'sku_name'])['qty'].sum().reset_index()
        top_per_payment = top_per_payment.sort_values(['payment_method', 'qty'], ascending=[True, False])
        top_per_payment = top_per_payment.groupby('payment_method').first().reset_index()
        top_per_payment.columns = ['طريقة الدفع', 'كود المنتج', 'اسم المنتج', 'الكمية']
        st.dataframe(top_per_payment, hide_index=True, use_container_width=True)

    st.markdown("---")

    # ========== المبيعات حسب الحالة ==========
    st.subheader("📋 المبيعات حسب حالة الطلب")
    
    status_sales = filtered_df.groupby('status').agg({
        'order_id': 'nunique',
        'qty': 'sum',
        'sku_code': 'nunique'
    }).reset_index()
    status_sales.columns = ['حالة الطلب', 'عدد الطلبات', 'الكمية الإجمالية', 'عدد المنتجات']
    status_sales = status_sales.sort_values('الكمية الإجمالية', ascending=False)
    
    st.dataframe(status_sales, hide_index=True, use_container_width=True)

    st.markdown("---")
    
    # ========== التحليلات الذكية ==========
    st.header("🧠 التحليلات الذكية")
    
    # تحميل كسول - فقط عند الحاجة
    if st.checkbox("⚡ تحميل التحليلات المتقدمة", value=False, help="قد يستغرق بعض الوقت"):
        try:
            from pricing_app.salla_insights import SallaInsights
            
            with st.spinner("جاري تحميل التحليلات..."):
                # تحميل المحلل
                analyzer = SallaInsights(orders_file)
                analyzer.load_pricing_data()
            
            # تبويبات التحليلات
            tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🔍 VLOOKUP - المطابقة",
                "💰 التكاليف والأرباح",
                "📅 التوصيات الموسمية", 
                "🤝 المنتجات المترابطة",
                "📦 بكجات مقترحة",
                "🏙️ توصيات حسب المدينة"
            ])
            
            with tab0:
                st.subheader("🔍 مطابقة SKU بين سلة وملفات التسعير")
                
                missing, found, summary = analyzer.get_missing_skus()
                
                if summary:
                    # ملخص سريع
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("إجمالي SKU في سلة", f"{summary['total_salla_skus']:,}")
                    with col2:
                        st.metric("✅ موجود في التسعير", f"{summary['found_in_pricing']:,}")
                    with col3:
                        st.metric("❌ مفقود من التسعير", f"{summary['missing_from_pricing']:,}")
                    with col4:
                        st.metric("نسبة التغطية", f"{summary['coverage_percentage']:.1f}%")
                    
                    st.markdown("---")
                    
                    # التفاصيل
                    col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown("### ❌ مفقودة من ملفات التسعير")
                    st.markdown(f"**{len(missing)} صنف مفقود**")
                    
                    if len(missing) > 0:
                        # إحصائيات المفقودات
                        total_missing_qty = missing['الكمية المباعة'].sum()
                        total_missing_orders = missing['عدد الطلبات'].sum()
                        
                        st.error(f"""
                        ⚠️ **تأثير المفقودات:**
                        - الكمية المباعة: {total_missing_qty:,} وحدة
                        - عدد الطلبات: {total_missing_orders:,} طلب
                        - يجب إضافة هذه الأصناف لملفات التسعير لحساب التكلفة!
                        """)
                        
                        # الجدول
                        st.dataframe(
                            missing[['SKU', 'اسم الصنف', 'الكمية المباعة', 'عدد الطلبات']],
                            hide_index=True,
                            use_container_width=True,
                            height=500
                        )
                        
                        # تنزيل
                        csv_missing = missing.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            "⬇️ تحميل قائمة المفقودات",
                            csv_missing,
                            "salla_missing_skus.csv",
                            "text/csv"
                        )
                    else:
                        st.success("✅ جميع المنتجات موجودة في ملفات التسعير!")
                
                with col_b:
                    st.markdown("### ✅ موجودة في ملفات التسعير")
                    st.markdown(f"**{len(found)} صنف موجود**")
                    
                    if len(found) > 0:
                        # توزيع حسب النوع
                        type_dist = found['النوع'].value_counts()
                        
                        st.info(f"""
                        **التوزيع:**
                        - منتجات: {type_dist.get('منتج', 0):,}
                        - بكجات: {type_dist.get('بكج', 0):,}
                        """)
                        
                        # الجدول
                        st.dataframe(
                            found[['SKU', 'اسم الصنف', 'النوع', 'الكمية المباعة', 'عدد الطلبات']],
                            hide_index=True,
                            use_container_width=True,
                            height=500
                        )
                        
                        # تنزيل
                        csv_found = found.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            "⬇️ تحميل قائمة الموجودات",
                            csv_found,
                            "salla_found_skus.csv",
                            "text/csv"
                        )
                
                st.markdown("---")
                st.markdown("### 📊 تحليل المفقودات حسب الأهمية")
                
                if len(missing) > 0:
                    top_missing = missing.head(20)
                    
                    st.warning("**أكثر 20 صنف مفقود حسب الكمية المباعة:**")
                    st.dataframe(
                        top_missing[['SKU', 'اسم الصنف', 'الكمية المباعة', 'عدد الطلبات']],
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    st.markdown("**💡 توصية:** ابدأ بإضافة هذه الأصناف أولاً لأنها الأكثر مبيعًا")
                else:
                    st.info("لا توجد بيانات متاحة للتحليل")
            
            with tab1:
                st.subheader("💰 تحليل التكاليف")
                
                sales_with_cost = analyzer.calculate_cogs_for_sales()
                if sales_with_cost is not None:
                    # تطبيق الفلاتر
                    if selected_year != "الكل":
                        sales_with_cost = sales_with_cost[sales_with_cost['year'] == selected_year]
                    if selected_month != "الكل":
                        month_num = int(selected_month.split("(")[1].split(")")[0])
                        sales_with_cost = sales_with_cost[sales_with_cost['month'] == month_num]
                    if selected_city != "الكل":
                        sales_with_cost = sales_with_cost[sales_with_cost['city'] == selected_city]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_cogs = sales_with_cost['total_cogs'].sum()
                        st.metric("إجمالي تكلفة البضاعة", f"{total_cogs:,.2f} ريال")
                    with col2:
                        found = sales_with_cost['found_in_pricing'].sum()
                        total = len(sales_with_cost)
                        coverage = (found / total * 100) if total > 0 else 0
                        st.metric("نسبة التغطية", f"{coverage:.1f}%")
                    with col3:
                        products = sales_with_cost[sales_with_cost['item_type'] == 'product']['sku_code'].nunique()
                        packages = sales_with_cost[sales_with_cost['item_type'] == 'package']['sku_code'].nunique()
                        st.metric("منتجات / بكجات", f"{products} / {packages}")
                    
                    st.markdown("**التفاصيل:**")
                    cost_summary = sales_with_cost.groupby(['sku_code', 'sku_name', 'item_type']).agg({
                        'qty': 'sum',
                        'unit_cogs': 'first',
                        'total_cogs': 'sum',
                        'found_in_pricing': 'first'
                    }).reset_index()
                    cost_summary.columns = ['SKU', 'اسم المنتج', 'النوع', 'الكمية', 'التكلفة/وحدة', 'التكلفة الإجمالية', 'موجود في التسعير']
                    cost_summary = cost_summary.sort_values('التكلفة الإجمالية', ascending=False)
                    
                    st.dataframe(cost_summary, hide_index=True, use_container_width=True, height=400)
                else:
                    st.info("لا توجد بيانات طلبات متاحة")
            
            with tab2:
                st.subheader("📅 أفضل المنتجات لكل شهر")
                
                seasonal = analyzer.get_seasonal_recommendations()
                if seasonal is not None:
                    st.dataframe(seasonal, hide_index=True, use_container_width=True)
                    
                    st.markdown("**💡 التوصية:**")
                    st.info("استخدم هذه البيانات لتخطيط المخزون والحملات التسويقية الموسمية")
                else:
                    st.info("لا توجد بيانات كافية للتحليل الموسمي")
            
            with tab3:
                st.subheader("🤝 المنتجات التي تُباع معًا")
                
                associations = analyzer.find_product_associations(min_support=2)
                if associations is not None and len(associations) > 0:
                    st.dataframe(associations.head(20), hide_index=True, use_container_width=True)
                    
                    st.markdown("**💡 التوصية:**")
                    st.info("استخدم هذه الأزواج لإنشاء عروض \"اشتري مع\" أو خصومات على البكجات")
                else:
                    st.info("لا توجد ارتباطات قوية بين المنتجات")
            
            with tab4:
                st.subheader("📦 بكجات مقترحة بناءً على أنماط الشراء")
                
                bundles = analyzer.suggest_bundles(min_frequency=2, min_qty=3)
                if bundles is not None and len(bundles) > 0:
                    st.dataframe(bundles, hide_index=True, use_container_width=True)
                    
                    st.markdown("**💡 كيفية الاستخدام:**")
                    st.success("""
                    1. اختر البكجات ذات قوة الارتباط العالية
                    2. احسب تكلفة البكج من مجموع تكاليف المنتجات
                    3. قدم خصم 5-15% لتشجيع الشراء
                    4. أضف البكج الجديد في صفحة التسعير
                    """)
                else:
                    st.info("لا توجد بكجات مقترحة - جرب تقليل الحد الأدنى للتكرار")
            
            with tab5:
                st.subheader("🏙️ توصيات خاصة بالمدن")
                
                city_recs = analyzer.get_city_recommendations(top_n=5)
                if city_recs is not None:
                    # عرض حسب المدينة
                    cities_list = city_recs['city'].unique()
                    selected_city_analysis = st.selectbox("اختر المدينة", cities_list, key="city_analysis")
                    
                    city_data = city_recs[city_recs['city'] == selected_city_analysis]
                    city_data = city_data[['sku_code', 'sku_name', 'qty']]
                    city_data.columns = ['SKU', 'اسم المنتج', 'الكمية المباعة']
                    
                    st.dataframe(city_data, hide_index=True, use_container_width=True)
                    
                    # بكجات مقترحة للمدينة
                    st.markdown(f"**بكجات مقترحة لـ {selected_city_analysis}:**")
                    city_bundles = analyzer.get_city_specific_bundles(selected_city_analysis, min_support=1)
                    
                    if city_bundles is not None and len(city_bundles) > 0:
                        st.dataframe(city_bundles.head(10), hide_index=True, use_container_width=True)
                    else:
                        st.info("لا توجد بكجات مقترحة لهذه المدينة")
                else:
                    st.info("لا توجد بيانات مدن متاحة")
        
        except Exception as e:
            st.error(f"❌ خطأ في التحليلات الذكية: {e}")
            import traceback
            st.code(traceback.format_exc())

    st.markdown("---")

    # ========== إشارات سلة (إن وجدت) ==========
    st.subheader("🎯 إشارات التسعير من سلة")
    
    data_dir = "data"
    files_needed = {
        "risk": os.path.join(data_dir, "salla_risk_factors.csv"),
        "sku": os.path.join(data_dir, "salla_demand_factors.csv"),
        "city": os.path.join(data_dir, "salla_city_factors.csv"),
        "combo": os.path.join(data_dir, "salla_combo_discounts.csv"),
    }

    missing = [name for name, path in files_needed.items() if not os.path.exists(path)]
    if missing:
        st.info(
            "ℹ️ لم يتم توليد إشارات سلة بعد. شغّل `python -m pricing_app.salla_signals` لتوليد المعاملات."
        )
    else:
        try:
            risk_df = pd.read_csv(files_needed["risk"])
            sku_df = pd.read_csv(files_needed["sku"])
            city_df = pd.read_csv(files_needed["city"])
            combo_df = pd.read_csv(files_needed["combo"])
            
            tab1, tab2, tab3, tab4 = st.tabs(["⚠️ المخاطر", "🔥 الطلب", "🗺️ جغرافي", "🤝 كومبو"])
            
            with tab1:
                st.dataframe(risk_df.sort_values("risk_multiplier", ascending=False).head(10), 
                           hide_index=True, use_container_width=True)
            
            with tab2:
                st.dataframe(sku_df.sort_values("demand_factor", ascending=False).head(10), 
                           hide_index=True, use_container_width=True)
            
            with tab3:
                st.dataframe(city_df.sort_values("geo_factor", ascending=False).head(10), 
                           hide_index=True, use_container_width=True)
            
            with tab4:
                st.dataframe(combo_df.sort_values("recommended_discount", ascending=False).head(10), 
                           hide_index=True, use_container_width=True)
                
        except Exception as e:
            st.warning(f"تعذر قراءة ملفات الإشارات: {e}")

elif st.session_state.page == "pricing_review":
    st.header("🔍 مراجعة التسعير")
    st.markdown("مقارنة الأسعار المتوقعة بالإيرادات الفعلية")
    st.markdown("---")
    
    # Check files exist
    pl_file_path = "data/profit_loss.csv"
    history_file = "data/pricing_history.csv"
    
    if not os.path.exists(pl_file_path):
        st.warning("⚠️ لم يتم رفع ملف الأرباح والخسائر!")
        if st.button("🔄 الذهاب لرفع الملف"):
            st.session_state.page = "upload"
            st.rerun()
        st.stop()
    
    if not os.path.exists(history_file):
        st.info("📝 لا توجد سجلات تسعير محفوظة للمقارنة")
        st.stop()
    
    try:
        # Load data
        pl_df = pd.read_csv(pl_file_path, encoding="utf-8-sig")
        pl_df.columns = pl_df.columns.str.strip()
        amount_col = 'net_amount' if 'net_amount' in pl_df.columns else ' net_amount '
        pl_df[amount_col] = pl_df[amount_col].astype(str).str.replace(',', '').astype(float)
        
        pricing_df = pd.read_csv(history_file, encoding="utf-8-sig")
        
        st.success(f"✅ تم تحميل البيانات بنجاح")
        
        # Get actual revenues by channel
        income_df = pl_df[pl_df['Account Level 1'] == 'income']
        
        if 'Cost Center' in income_df.columns:
            actual_by_channel = income_df.groupby('Cost Center')[amount_col].sum()
            
            st.subheader("📊 مقارنة الإيرادات: المتوقع vs الفعلي")
            
            # Get expected from pricing history
            if 'المنصة' in pricing_df.columns and 'سعر بعد الخصم' in pricing_df.columns:
                expected_by_channel = pricing_df.groupby('المنصة')['سعر بعد الخصم'].sum()
                
                comparison_data = pd.DataFrame({
                    'القناة': actual_by_channel.index,
                    'الإيراد الفعلي': actual_by_channel.values,
                    'السعر المتوقع': [expected_by_channel.get(ch, 0) for ch in actual_by_channel.index],
                })
                
                comparison_data['الفرق'] = comparison_data['الإيراد الفعلي'] - comparison_data['السعر المتوقع']
                comparison_data['نسبة الفرق %'] = (comparison_data['الفرق'] / comparison_data['السعر المتوقع'] * 100).round(2)
                
                st.dataframe(comparison_data, use_container_width=True, hide_index=True)
                
                # Chart
                fig = go.Figure()
                fig.add_trace(go.Bar(name='الإيراد الفعلي', x=comparison_data['القناة'], 
                                    y=comparison_data['الإيراد الفعلي'], marker_color='#10b981'))
                fig.add_trace(go.Bar(name='السعر المتوقع', x=comparison_data['القناة'], 
                                    y=comparison_data['السعر المتوقع'], marker_color='#3b82f6'))
                
                fig.update_layout(title="مقارنة الإيرادات حسب القناة", barmode='group',
                                 xaxis_title="القناة", yaxis_title="المبلغ (SAR)")
                st.plotly_chart(fig, use_container_width=True)
        
        # Recommendations
        st.markdown("---")
        st.subheader("💡 التوصيات")
        
        if 'الفرق' in comparison_data.columns:
            underperforming = comparison_data[comparison_data['الفرق'] < 0]
            overperforming = comparison_data[comparison_data['الفرق'] > 0]
            
            col1, col2 = st.columns(2)
            with col1:
                if not underperforming.empty:
                    st.warning("⚠️ **قنوات أقل من المتوقع:**")
                    for _, row in underperforming.iterrows():
                        st.write(f"- {row['القناة']}: فرق {row['الفرق']:,.0f} SAR ({row['نسبة الفرق %']:.1f}%)")
                        st.caption("→ راجع استراتيجية التسعير والخصومات")
            
            with col2:
                if not overperforming.empty:
                    st.success("✅ **قنوات أعلى من المتوقع:**")
                    for _, row in overperforming.iterrows():
                        st.write(f"- {row['القناة']}: زيادة {row['الفرق']:,.0f} SAR (+{row['نسبة الفرق %']:.1f}%)")
                        st.caption("→ فرصة لزيادة الأسعار تدريجياً")
        
    except Exception as e:
        st.error(f"❌ خطأ: {e}")


# Page: Financial Dashboard
elif st.session_state.page == "financial_dashboard":
    st.header("📈 Dashboard المالي")
    st.markdown("مؤشرات الأداء المالي الرئيسية (KPIs)")
    st.markdown("---")
    
    pl_file_path = "data/profit_loss.csv"
    if not os.path.exists(pl_file_path):
        st.warning("⚠️ لم يتم رفع ملف الأرباح والخسائر!")
        if st.button("🔄 الذهاب لرفع الملف"):
            st.session_state.page = "upload"
            st.rerun()
        st.stop()
    
    try:
        pl_df = pd.read_csv(pl_file_path, encoding="utf-8-sig")
        pl_df.columns = pl_df.columns.str.strip()
        amount_col = 'net_amount' if 'net_amount' in pl_df.columns else ' net_amount '
        pl_df[amount_col] = pl_df[amount_col].astype(str).str.replace(',', '').astype(float)
        
        # Period selector
        col1, col2 = st.columns(2)
        with col1:
            if 'Years' in pl_df.columns:
                years = sorted(pl_df['Years'].unique().tolist())
                selected_year = st.selectbox("اختر السنة", years, index=len(years)-1 if years else 0)
                pl_df = pl_df[pl_df['Years'] == selected_year]
        
        # Calculate comprehensive KPIs
        income = pl_df[pl_df['Account Level 1'] == 'income'][amount_col].sum()
        cogs = pl_df[pl_df['Account Level 1'] == 'cost_of_goods_sold'][amount_col].sum()
        expenses = pl_df[pl_df['Account Level 1'] == 'expense'][amount_col].sum()
        other_income = pl_df[pl_df['Account Level 1'] == 'other_income'][amount_col].sum()
        other_expense = pl_df[pl_df['Account Level 1'] == 'other_expense'][amount_col].sum()
        
        gross_profit = income - cogs
        operating_profit = gross_profit - expenses
        net_profit = operating_profit + other_income - other_expense
        
        gross_margin = (gross_profit / income * 100) if income > 0 else 0
        operating_margin = (operating_profit / income * 100) if income > 0 else 0
        net_margin = (net_profit / income * 100) if income > 0 else 0
        
        # Display KPI Cards
        st.subheader(f"📊 المؤشرات الرئيسية - {selected_year}")
        
        # Row 1: Revenue metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 إجمالي الإيرادات", f"{income:,.0f} SAR")
        with col2:
            st.metric("📦 تكلفة البضاعة", f"{cogs:,.0f} SAR",
                     delta=f"-{(cogs/income*100):.1f}%",
                     delta_color="inverse")
        with col3:
            st.metric("💵 الربح الإجمالي", f"{gross_profit:,.0f} SAR",
                     delta=f"{gross_margin:.1f}%")
        with col4:
            st.metric("🎯 هامش الربح الإجمالي", f"{gross_margin:.1f}%")
        
        # Row 2: Profitability metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("⚙️ المصاريف التشغيلية", f"{expenses:,.0f} SAR",
                     delta=f"-{(expenses/income*100):.1f}%",
                     delta_color="inverse")
        with col2:
            st.metric("📊 الربح التشغيلي", f"{operating_profit:,.0f} SAR",
                     delta=f"{operating_margin:.1f}%")
        with col3:
            st.metric("✨ صافي الربح", f"{net_profit:,.0f} SAR",
                     delta=f"{net_margin:.1f}%",
                     delta_color="normal" if net_profit >= 0 else "inverse")
        with col4:
            st.metric("🎯 هامش صافي الربح", f"{net_margin:.1f}%",
                     delta_color="normal" if net_margin >= 0 else "inverse")
        
        st.markdown("---")
        
        # Profitability Waterfall
        st.subheader("📊 شلال الربحية")
        
        waterfall_data = {
            'المرحلة': ['الإيرادات', 'تكلفة البضاعة', 'الربح الإجمالي', 
                       'المصاريف التشغيلية', 'الربح التشغيلي',
                       'إيرادات أخرى', 'مصاريف أخرى', 'صافي الربح'],
            'المبلغ': [income, -cogs, gross_profit, -expenses, operating_profit,
                      other_income, -other_expense, net_profit],
            'النوع': ['إجمالي', 'نقص', 'إجمالي', 'نقص', 'إجمالي', 'زيادة', 'نقص', 'إجمالي']
        }
        
        fig = go.Figure(go.Waterfall(
            name="الربحية",
            orientation="v",
            measure=["relative", "relative", "total", "relative", "total", "relative", "relative", "total"],
            x=waterfall_data['المرحلة'],
            y=waterfall_data['المبلغ'],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#10b981"}},
            decreasing={"marker": {"color": "#ef4444"}},
            totals={"marker": {"color": "#3b82f6"}}
        ))
        
        fig.update_layout(title="تدفق الربحية من الإيرادات إلى صافي الربح",
                         xaxis_title="", yaxis_title="المبلغ (SAR)",
                         height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Monthly performance trend
        if 'date' in pl_df.columns:
            st.markdown("---")
            st.subheader("📈 الأداء الشهري")
            
            monthly = pl_df.groupby(['date', 'Account Level 1'])[amount_col].sum().reset_index()
            monthly_pivot = monthly.pivot(index='date', columns='Account Level 1', values=amount_col).fillna(0)
            
            monthly_pivot['الربح الإجمالي'] = monthly_pivot.get('income', 0) - monthly_pivot.get('cost_of_goods_sold', 0)
            monthly_pivot['صافي الربح'] = (
                monthly_pivot.get('income', 0) - 
                monthly_pivot.get('cost_of_goods_sold', 0) - 
                monthly_pivot.get('expense', 0) +
                monthly_pivot.get('other_income', 0) -
                monthly_pivot.get('other_expense', 0)
            )
            monthly_pivot['هامش الربح %'] = (monthly_pivot['صافي الربح'] / monthly_pivot.get('income', 1) * 100).round(2)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Bar(name='الإيرادات', x=monthly_pivot.index, 
                                    y=monthly_pivot.get('income', 0), marker_color='#10b981'))
                fig.add_trace(go.Scatter(name='صافي الربح', x=monthly_pivot.index,
                                        y=monthly_pivot['صافي الربح'], 
                                        line=dict(color='#3b82f6', width=3), yaxis='y2'))
                
                fig.update_layout(
                    title="الإيرادات وصافي الربح الشهري",
                    xaxis_title="الشهر",
                    yaxis=dict(title="الإيرادات (SAR)"),
                    yaxis2=dict(title="صافي الربح (SAR)", overlaying='y', side='right'),
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.metric("متوسط الإيرادات الشهرية", 
                         f"{monthly_pivot.get('income', 0).mean():,.0f} SAR")
                st.metric("متوسط صافي الربح الشهري",
                         f"{monthly_pivot['صافي الربح'].mean():,.0f} SAR")
                st.metric("متوسط هامش الربح",
                         f"{monthly_pivot['هامش الربح %'].mean():.1f}%")
        
    except Exception as e:
        st.error(f"❌ خطأ في تحميل البيانات: {e}")


# Page: P&L Channel Insights (consolidated)
elif st.session_state.page == "pl_channel_insights":
    st.header("🎯 تحليل P&L للقنوات (موحد)")
    st.markdown("تجميع التحليل + التنبيهات + حوكمة الخصم في صفحة واحدة")
    st.markdown("---")

    from pricing_app.pl_analyzer import PLAnalyzer, get_smart_channel_fees

    pl_file_path = "data/profit_loss.csv"
    if not os.path.exists(pl_file_path):
        st.warning("⚠️ لم يتم رفع ملف الأرباح والخسائر بعد!")
        if st.button("🔄 الذهاب لرفع الملف", type="primary"):
            st.session_state.page = "upload"
            st.rerun()
        st.stop()

    analyzer = PLAnalyzer(pl_file_path)
    if not analyzer.load_data():
        st.error("❌ فشل تحميل بيانات P&L")
        st.stop()

    selected_year = None
    if 'Years' in analyzer.df.columns:
        years = sorted(analyzer.df['Years'].unique().tolist())
        if years:
            selected_year = st.selectbox("📅 اختر السنة", years, index=len(years)-1)

    channels_file = "data/channels.json"
    channels = load_channels(channels_file)

    # Section A: إجمالي المصاريف
    st.subheader("📊 توزيع المصاريف على مستوى الشركة")
    overall_breakdown = analyzer.get_overall_expense_breakdown(selected_year)
    if overall_breakdown:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("💰 إجمالي الإيرادات", f"{overall_breakdown['total_revenue']:,.0f} SAR")
        col2.metric("📢 مصاريف التسويق", f"{overall_breakdown['marketing_total']:,.0f} SAR", delta=f"{overall_breakdown['marketing_pct']:.1f}%")
        col3.metric("🏢 المصاريف الإدارية", f"{overall_breakdown['admin_total']:,.0f} SAR", delta=f"{overall_breakdown['admin_pct']:.1f}%")
        col4.metric("💳 رسوم المنصات", f"{overall_breakdown['platform_total']:,.0f} SAR", delta=f"{overall_breakdown['platform_pct']:.1f}%")
        col5.metric("⚙️ مصاريف أخرى", f"{overall_breakdown['other_opex_total']:,.0f} SAR", delta=f"{overall_breakdown['other_opex_pct']:.1f}%")

    st.markdown("---")

    # Section B: جدول القنوات + تنزيل
    st.subheader("🏪 مقارنة القنوات")
    channels_analysis = analyzer.get_all_channels_analysis(selected_year)
    if not channels_analysis:
        st.warning("⚠️ لا توجد بيانات قنوات متاحة")
    else:
        comparison_data = []
        for ch, a in channels_analysis.items():
            comparison_data.append({
                'القناة': ch,
                'الإيراد (SAR)': f"{a.total_revenue:,.0f}",
                'نسبة الإيراد %': f"{a.revenue_share_pct:.1f}",
                'COGS %': f"{a.cogs_pct*100:.1f}",
                'تسويق %': f"{a.marketing_pct*100:.1f}",
                'منصة %': f"{a.platform_pct*100:.1f}",
                'إدارية/تشغيلية %': f"{(a.admin_pct + a.other_opex_pct)*100:.1f}",
                'هامش إجمالي %': f"{a.gross_margin_pct:.1f}",
                'هامش صافي %': f"{a.net_margin_pct:.1f}",
            })
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        csv = comparison_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 تحميل التحليل (CSV)", data=csv, file_name="channel_pl_insights.csv", mime="text/csv")

    st.markdown("---")

    # Section C: حوكمة الخصم/السعر الأرضي (جداول مختصرة)
    st.subheader("🛡️ حوكمة الخصم والسعر الأرضي")
    default_cogs = st.number_input("COGS افتراضي", min_value=0.0, value=50.0, step=1.0, key="gov_cogs")
    default_price = st.number_input("سعر قائمة افتراضي (شامل الضريبة قبل الخصم)", min_value=0.0, value=150.0, step=1.0, key="gov_price")
    safety_margin = st.slider("هامش أمان أدنى %", 0, 20, 5, key="gov_safety") / 100

    governance_rows = []
    for ch_name, cfg in channels.items():
        fees = get_smart_channel_fees(ch_name, selected_year, fallback_defaults=True)
        var_pct = fees.get("platform_pct",0)+fees.get("marketing_pct",0)+fees.get("opex_pct",0)
        vat_rate = cfg.vat_rate
        shipping = cfg.shipping_fixed
        preparation = cfg.preparation_fee
        discount_rate = cfg.discount_rate
        fixed_costs = default_cogs + shipping + preparation

        floor_net = fixed_costs/(1-var_pct) if (1-var_pct)>0 else 0
        floor_price = (floor_net*(1+vat_rate))/(1-discount_rate) if (1-discount_rate)>0 else 0

        safe_net = fixed_costs/(1-var_pct-safety_margin) if (1-var_pct-safety_margin)>0 else None
        safe_price = (safe_net*(1+vat_rate))/(1-discount_rate) if (safe_net and (1-discount_rate)>0) else 0

        net_from_price = default_price/(1+vat_rate) if default_price>0 else None
        max_discount_pct = None
        if net_from_price and (1-var_pct-safety_margin)>0:
            needed_net = fixed_costs/(1-var_pct-safety_margin)
            max_discount_pct = 1 - needed_net/net_from_price
            max_discount_pct = max(0, min(max_discount_pct, 0.9))

        governance_rows.append({
            "القناة": ch_name,
            "منصة %": fees.get("platform_pct",0)*100,
            "تسويق %": fees.get("marketing_pct",0)*100,
            "تشغيل/إدارية %": fees.get("opex_pct",0)*100,
            "السعر الأرضي": floor_price,
            "سعر آمن": safe_price,
            "سقف خصم آمن %": max_discount_pct*100 if max_discount_pct is not None else None,
        })

    if governance_rows:
        gov_df = pd.DataFrame(governance_rows)
        st.dataframe(gov_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Section D: تنبيهات الانحراف
    st.subheader("🚦 تنبيهات الانحراف عن الإعدادات")
    threshold_marketing = st.slider("عتبة تنبيه التسويق (نقطة مئوية)", 0, 10, 5, key="var_mkt")
    threshold_platform = st.slider("عتبة تنبيه المنصة (نقطة مئوية)", 0, 5, 2, key="var_plat")
    threshold_opex = st.slider("عتبة تنبيه التشغيل/الإدارية (نقطة مئوية)", 0, 10, 3, key="var_opex")

    var_rows = []
    for ch_name, cfg in channels.items():
        fees = get_smart_channel_fees(ch_name, selected_year, fallback_defaults=False)
        if not fees:
            continue
        delta_m = (fees['marketing_pct'] - cfg.marketing_pct)*100
        delta_p = (fees['platform_pct'] - cfg.platform_pct)*100
        delta_o = (fees['opex_pct'] - cfg.opex_pct)*100
        alert = (abs(delta_m)>=threshold_marketing or abs(delta_p)>=threshold_platform or abs(delta_o)>=threshold_opex)
        var_rows.append({
            "القناة": ch_name,
            "تسويق حالي %": cfg.marketing_pct*100,
            "تسويق فعلي %": fees['marketing_pct']*100,
            "فرق تسويق": delta_m,
            "منصة حالي %": cfg.platform_pct*100,
            "منصة فعلي %": fees['platform_pct']*100,
            "فرق منصة": delta_p,
            "تشغيل/إدارية حالي %": cfg.opex_pct*100,
            "تشغيل/إدارية فعلي %": fees['opex_pct']*100,
            "فرق تشغيل": delta_o,
            "تنبيه": "⚠️" if alert else "✅",
        })

    if var_rows:
        var_df = pd.DataFrame(var_rows)
        st.dataframe(var_df, use_container_width=True, hide_index=True)
        alerts = [r for r in var_rows if r['تنبيه']=="⚠️"]
        if alerts:
            st.warning(f"هناك {len(alerts)} قناة تحتاج مراجعة")
        else:
            st.success("لا توجد انحرافات تتجاوز العتبات المحددة")
    else:
        st.info("لا توجد بيانات كافية لعرض الانحرافات")

# Page: Smart Pricing (P&L-driven) - isolated
elif st.session_state.page == "smart_pricing_pl":
        st.header("🧠 تسعير ذكي معتمد على P&L (صفحة جديدة مستقلة)")
        st.markdown("يحسب السعر والسعر الأرضي وسقف الخصم بناءً على نسب التكاليف الفعلية من الأرباح والخسائر دون لمس الصفحات الأصلية")
        st.markdown("---")

        from pricing_app.pl_analyzer import get_smart_channel_fees

        pl_file_path = "data/profit_loss.csv"
        if not os.path.exists(pl_file_path):
            st.warning("⚠️ لم يتم رفع ملف الأرباح والخسائر بعد!")
            if st.button("🔄 الذهاب لرفع الملف"):
                st.session_state.page = "upload"
                st.rerun()
            st.stop()

        channels_file = "data/channels.json"
        channels = load_channels(channels_file)
        channel_names = list(channels.keys()) if channels else []

        col1, col2 = st.columns(2)
        with col1:
            selected_channel = st.selectbox("🏪 اختر القناة", options=channel_names or ["لا توجد قنوات"])
        with col2:
            selected_year = st.text_input("📅 السنة (اختياري)", value="")
            selected_year = selected_year.strip() or None

        col1, col2, col3 = st.columns(3)
        with col1:
            cogs = st.number_input("تكلفة البضاعة للوحدة (COGS)", min_value=0.0, value=50.0, step=1.0)
        with col2:
            target_margin_pct = st.number_input("هامش الربح المستهدف %", min_value=0.0, max_value=50.0, value=10.0, step=0.5)
        with col3:
            discount_pct_input = st.number_input("نسبة الخصم المدخلة %", min_value=0.0, max_value=80.0, value=10.0, step=1.0)

        list_price_input = st.number_input("سعر القائمة شامل الضريبة قبل الخصم (اختياري)", min_value=0.0, value=0.0, step=1.0)

        fees = get_smart_channel_fees(selected_channel, selected_year, fallback_defaults=True)

        if not fees:
            st.error("لم يتم العثور على نسب للقناة")
            st.stop()

        platform_pct = fees.get("platform_pct", 0)
        marketing_pct = fees.get("marketing_pct", 0)
        opex_pct = fees.get("opex_pct", 0)

        st.info("النسب الفعلية المستخدمة من P&L")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("رسوم المنصة %", f"{platform_pct*100:.2f}%")
        with col2:
            st.metric("مصاريف التسويق %", f"{marketing_pct*100:.2f}%")
        with col3:
            st.metric("مصاريف تشغيل/إدارية %", f"{opex_pct*100:.2f}%")

        if selected_channel in channels:
            cfg = channels[selected_channel]
            st.caption("مقارنة سريعة مع الإعدادات الحالية (دون تعديل)")
            comp_df = pd.DataFrame({
                "البند": ["رسوم المنصة", "التسويق", "التشغيل/الإدارية"],
                "الموجود": [cfg.platform_pct*100, cfg.marketing_pct*100, cfg.opex_pct*100],
                "الفعلي (P&L)": [platform_pct*100, marketing_pct*100, opex_pct*100],
                "الفرق (ن.ف)": [
                    (platform_pct - cfg.platform_pct)*100,
                    (marketing_pct - cfg.marketing_pct)*100,
                    (opex_pct - cfg.opex_pct)*100,
                ],
            })
            st.dataframe(comp_df, hide_index=True, use_container_width=True)

        vat_rate = getattr(channels.get(selected_channel, None), "vat_rate", 0.15) if channels else 0.15
        shipping = getattr(channels.get(selected_channel, None), "shipping_fixed", 0.0) if channels else 0.0
        preparation = getattr(channels.get(selected_channel, None), "preparation_fee", 0.0) if channels else 0.0
        discount_rate = discount_pct_input / 100
        target_margin = target_margin_pct / 100

        var_pct = platform_pct + marketing_pct + opex_pct
        fixed_costs = cogs + shipping + preparation

        if var_pct >= 1:
            st.error("مجموع النسب المتغيرة ≥ 100% - لا يمكن الحساب")
            st.stop()

        net_required_floor = fixed_costs / (1 - var_pct)
        floor_price_before_discount = (net_required_floor * (1 + vat_rate)) / (1 - discount_rate)

        net_required_target = fixed_costs / (1 - var_pct - target_margin) if (1 - var_pct - target_margin) > 0 else None
        target_price_before_discount = None
        if net_required_target:
            target_price_before_discount = (net_required_target * (1 + vat_rate)) / (1 - discount_rate)

        min_margin_safe = st.slider("هامش أمان للخصم %", min_value=0, max_value=20, value=5, step=1) / 100
        if 1 - var_pct - min_margin_safe <= 0:
            max_discount_pct = 0
        else:
            needed_net = fixed_costs / (1 - var_pct - min_margin_safe)
            if list_price_input > 0:
                net_from_price = list_price_input / (1 + vat_rate)
                max_discount_pct = 1 - (needed_net / net_from_price)
                max_discount_pct = max(0, min(max_discount_pct, 0.9))
            else:
                max_discount_pct = None

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("السعر الأرضي (لا خسارة)", f"{floor_price_before_discount:.2f} SAR")
        with col2:
            if target_price_before_discount:
                st.metric("سعر يحقق الهامش المستهدف", f"{target_price_before_discount:.2f} SAR")
        with col3:
            if max_discount_pct is not None:
                st.metric("سقف الخصم الآمن", f"{max_discount_pct*100:.1f}%")
            else:
                st.metric("سقف الخصم الآمن", "—", help="ادخل سعر القائمة لحساب سقف الخصم")

        if list_price_input > 0:
            net_price = list_price_input * (1 - discount_rate) / (1 + vat_rate)
            profit = net_price - fixed_costs - net_price * var_pct
            margin_now = profit / net_price if net_price > 0 else 0
            st.info(f"الهامش عند السعر المدخل = {margin_now*100:.2f}% | الربح = {profit:.2f} SAR")


# Page: Discount Governance - isolated
elif st.session_state.page == "discount_governance":
        st.header("🛡️ حوكمة الخصم والسعر الأرضي (صفحة جديدة مستقلة)")
        st.markdown("جدول يلخص السعر الأرضي وسقف الخصم لكل قناة بناءً على نسب P&L")
        st.markdown("---")

        from pricing_app.pl_analyzer import get_smart_channel_fees, PLAnalyzer

        pl_file_path = "data/profit_loss.csv"
        if not os.path.exists(pl_file_path):
            st.warning("⚠️ لم يتم رفع ملف الأرباح والخسائر بعد!")
            st.stop()

        analyzer = PLAnalyzer(pl_file_path)
        if not analyzer.load_data():
            st.error("فشل تحميل بيانات P&L")
            st.stop()

        selected_year = None
        if 'Years' in analyzer.df.columns:
            years = sorted(analyzer.df['Years'].unique().tolist())
            if years:
                selected_year = st.selectbox("📅 اختر السنة", years, index=len(years)-1)

        channels_file = "data/channels.json"
        channels = load_channels(channels_file)
        channel_names = list(channels.keys()) if channels else []

        default_cogs = st.number_input("COGS افتراضي (للجدول)", min_value=0.0, value=50.0, step=1.0)
        default_price = st.number_input("سعر قائمة افتراضي (شامل الضريبة قبل الخصم)", min_value=0.0, value=150.0, step=1.0)
        safety_margin = st.slider("هامش أمان أدنى %", min_value=0, max_value=20, value=5, step=1) / 100

        table_rows = []
        for ch_name in channel_names:
            fees = get_smart_channel_fees(ch_name, selected_year, fallback_defaults=True)
            platform_pct = fees.get("platform_pct", 0)
            marketing_pct = fees.get("marketing_pct", 0)
            opex_pct = fees.get("opex_pct", 0)
            var_pct = platform_pct + marketing_pct + opex_pct

            ch_cfg = channels[ch_name]
            vat_rate = ch_cfg.vat_rate
            shipping = ch_cfg.shipping_fixed
            preparation = ch_cfg.preparation_fee
            discount_rate = ch_cfg.discount_rate

            cogs = default_cogs
            fixed_costs = cogs + shipping + preparation

            floor_net = fixed_costs / (1 - var_pct) if (1 - var_pct) > 0 else 0
            floor_price = (floor_net * (1 + vat_rate)) / (1 - discount_rate) if (1 - discount_rate) > 0 else 0

            safe_net = fixed_costs / (1 - var_pct - safety_margin) if (1 - var_pct - safety_margin) > 0 else None
            safe_price = (safe_net * (1 + vat_rate)) / (1 - discount_rate) if (safe_net and (1 - discount_rate) > 0) else None

            net_from_price = default_price / (1 + vat_rate) if default_price > 0 else None
            max_discount_pct = None
            if net_from_price and (1 - var_pct - safety_margin) > 0:
                needed_net = fixed_costs / (1 - var_pct - safety_margin)
                max_discount_pct = 1 - needed_net / net_from_price
                max_discount_pct = max(0, min(max_discount_pct, 0.9))

            table_rows.append({
                "القناة": ch_name,
                "رسوم المنصة %": platform_pct*100,
                "التسويق %": marketing_pct*100,
                "التشغيل/الإدارية %": opex_pct*100,
                "السعر الأرضي (SAR)": floor_price,
                "سعر آمن لهامش الأمان (SAR)": safe_price if safe_price else 0,
                "سقف الخصم الآمن %": max_discount_pct*100 if max_discount_pct is not None else None,
            })

        if table_rows:
            df = pd.DataFrame(table_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📥 تحميل الجدول CSV", data=csv, file_name="discount_governance.csv", mime="text/csv")
        else:
            st.warning("لا توجد قنوات لعرضها")


# Page: Variance Alerts - isolated
elif st.session_state.page == "variance_alerts":
        st.header("🚦 تنبيهات الانحراف بين الواقع والإعدادات (صفحة جديدة مستقلة)")
        st.markdown("تقارن نسب الرسوم الفعلية من P&L مع الإعدادات الحالية دون تعديل الصفحات الأصلية")
        st.markdown("---")

        from pricing_app.pl_analyzer import PLAnalyzer, get_smart_channel_fees

        pl_file_path = "data/profit_loss.csv"
        channels_file = "data/channels.json"
        channels = load_channels(channels_file)

        if not os.path.exists(pl_file_path):
            st.warning("⚠️ لم يتم رفع ملف الأرباح والخسائر بعد!")
            st.stop()

        analyzer = PLAnalyzer(pl_file_path)
        if not analyzer.load_data():
            st.error("فشل تحميل بيانات P&L")
            st.stop()

        selected_year = None
        if 'Years' in analyzer.df.columns:
            years = sorted(analyzer.df['Years'].unique().tolist())
            if years:
                selected_year = st.selectbox("📅 اختر السنة", years, index=len(years)-1)

        threshold_marketing = st.slider("عتبة تنبيه التسويق (نقطة مئوية)", 0, 10, 5)
        threshold_platform = st.slider("عتبة تنبيه المنصة (نقطة مئوية)", 0, 5, 2)
        threshold_opex = st.slider("عتبة تنبيه التشغيل/الإدارية (نقطة مئوية)", 0, 10, 3)

        rows = []
        for ch_name, cfg in channels.items():
            fees = get_smart_channel_fees(ch_name, selected_year, fallback_defaults=False)
            if not fees:
                continue
            delta_marketing = (fees['marketing_pct'] - cfg.marketing_pct) * 100
            delta_platform = (fees['platform_pct'] - cfg.platform_pct) * 100
            delta_opex = (fees['opex_pct'] - cfg.opex_pct) * 100

            alert = (
                abs(delta_marketing) >= threshold_marketing or
                abs(delta_platform) >= threshold_platform or
                abs(delta_opex) >= threshold_opex
            )

            rows.append({
                "القناة": ch_name,
                "التسويق الحالي %": cfg.marketing_pct*100,
                "التسويق الفعلي %": fees['marketing_pct']*100,
                "فرق تسويق": delta_marketing,
                "رسوم المنصة الحالية %": cfg.platform_pct*100,
                "رسوم المنصة الفعلية %": fees['platform_pct']*100,
                "فرق منصة": delta_platform,
                "تشغيل/إدارية الحالية %": cfg.opex_pct*100,
                "تشغيل/إدارية الفعلية %": fees['opex_pct']*100,
                "فرق تشغيل": delta_opex,
                "تنبيه": "⚠️" if alert else "✅",
            })

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            alerts = [r for r in rows if r["تنبيه"] == "⚠️"]
            if alerts:
                st.warning(f"هناك {len(alerts)} قناة تحتاج مراجعة")
            else:
                st.success("لا توجد انحرافات تتجاوز العتبات المحددة")
        else:
            st.info("لا توجد بيانات كافية لعرض الانحرافات")


# Footer
st.markdown("---")
st.markdown(
    """
<div style='text-align: center'>
    <p>محرك تسعير صفوة - Safwa Pricing Engine v1.0</p>
    <p>نظام محاسبي متقدم لحساب COGS والتسعير الامثل</p>
</div>
""",
    unsafe_allow_html=True,
)

"""
وحدة التحليلات الذكية لطلبات سلة
Salla Insights - Smart Analytics & Recommendations
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json

from pricing_app.data_loader import load_cost_data


class SallaInsights:
    """محلل ذكي لبيانات سلة مع ربطها بمنتجات التسعير"""
    
    def __init__(self, orders_file="data/salla_orders_exploded.csv"):
        """
        تحميل بيانات الطلبات المفككة
        """
        self.orders_df = None
        self.products_df = None
        self.packages_df = None
        self.raw_materials_df = None
        self.materials = None
        self.product_recipes = None
        self.package_compositions = None
        self._product_cost_cache = {}
        self._package_cost_cache = {}
        
        if Path(orders_file).exists():
            self.orders_df = pd.read_csv(orders_file)
            
            # التحقق من وجود عمود order_date
            if 'order_date' in self.orders_df.columns:
                self.orders_df['order_date'] = pd.to_datetime(self.orders_df['order_date'], errors='coerce')
                self.orders_df['year'] = self.orders_df['order_date'].dt.year
                self.orders_df['month'] = self.orders_df['order_date'].dt.month
            elif 'تاريخ الطلب' in self.orders_df.columns:
                # إذا كان العمود بالعربي
                self.orders_df['order_date'] = pd.to_datetime(self.orders_df['تاريخ الطلب'], errors='coerce')
                self.orders_df['year'] = self.orders_df['order_date'].dt.year
                self.orders_df['month'] = self.orders_df['order_date'].dt.month
            else:
                # لا يوجد عمود تاريخ، نضيف أعمدة فارغة
                self.orders_df['order_date'] = pd.NaT
                self.orders_df['year'] = None
                self.orders_df['month'] = None
    
    def load_pricing_data(self, products_file="data/products_template.csv", 
                         packages_file="data/packages_template.csv",
                         raw_materials_file="data/raw_materials_template.csv"):
        """تحميل بيانات التسعير"""
        # تحميل بيانات التكلفة (مواد، وصفات منتجات، مكونات بكجات)
        data_dir = str(Path(products_file).parent)
        self.materials, self.product_recipes, products_summary, self.package_compositions, packages_summary = load_cost_data(data_dir)

        # تجهيز DataFrames مع أعمدة COGS المطلوبة من بقية الكود
        def _calc_cost_for_product(prod_sku: str, seen=None) -> float:
            """حساب تكلفة منتج من مكوناته مع دعم التكرار المتداخل."""
            if prod_sku in self._product_cost_cache:
                return self._product_cost_cache[prod_sku]
            seen = seen or set()
            if prod_sku in seen:
                return 0.0
            seen.add(prod_sku)
            recipe = (self.product_recipes or {}).get(prod_sku, {})
            total = 0.0
            for comp_sku, qty in recipe.items():
                if comp_sku in self.materials:
                    total += self.materials[comp_sku].cost_per_unit * qty
                elif comp_sku in (self.product_recipes or {}):
                    total += _calc_cost_for_product(comp_sku, seen) * qty
                elif comp_sku in (self.package_compositions or {}):
                    total += _calc_cost_for_package(comp_sku, seen) * qty
            self._product_cost_cache[prod_sku] = total
            return total

        def _calc_cost_for_package(pkg_sku: str, seen=None) -> float:
            if pkg_sku in self._package_cost_cache:
                return self._package_cost_cache[pkg_sku]
            seen = seen or set()
            if pkg_sku in seen:
                return 0.0
            seen.add(pkg_sku)
            comps = (self.package_compositions or {}).get(pkg_sku, {})
            total = 0.0
            for comp_sku, qty in comps.items():
                if comp_sku in self.materials:
                    total += self.materials[comp_sku].cost_per_unit * qty
                elif comp_sku in (self.product_recipes or {}):
                    total += _calc_cost_for_product(comp_sku, seen) * qty
                elif comp_sku in (self.package_compositions or {}):
                    total += _calc_cost_for_package(comp_sku, seen) * qty
            self._package_cost_cache[pkg_sku] = total
            return total

        # بناء جداول مع COGS
        product_rows = []
        for _, row in products_summary.iterrows():
            sku = row["Product_SKU"]
            cost = _calc_cost_for_product(sku)
            product_rows.append({"Product_Name": row["Product_Name"], "SKU": sku, "COGS": cost})
        self.products_df = pd.DataFrame(product_rows)

        package_rows = []
        for _, row in packages_summary.iterrows():
            sku = row["Package_SKU"]
            cost = _calc_cost_for_package(sku)
            package_rows.append({"Package_Name": row["Package_Name"], "SKU": sku, "Total_COGS": cost})
        self.packages_df = pd.DataFrame(package_rows)
        
        # تحميل المواد الخام للرجوع إليها لاحقاً إذا احتجناها
        if Path(raw_materials_file).exists():
            self.raw_materials_df = pd.read_csv(raw_materials_file)

        # محاولة تحميل COGS مباشر من ملف سلة المفكك إذا كان متوفراً (تغطية للـ SKU غير الموجودة في ملفات التسعير)
        salla_cogs_file = Path(data_dir) / "salla_sales_with_cogs.csv"
        if salla_cogs_file.exists():
            try:
                salla_cogs_df = pd.read_csv(salla_cogs_file, usecols=["sku_code", "unit_cogs"], low_memory=False)
                salla_cogs_df = salla_cogs_df.dropna(subset=["sku_code", "unit_cogs"])
                salla_cogs_df = salla_cogs_df.groupby("sku_code").first().reset_index()
                salla_cogs_df.columns = ["SKU", "COGS"]
                # دمج: نضيف أي SKU غير موجود بالفعل
                if not salla_cogs_df.empty:
                    existing_skus = set(self.products_df["SKU"].unique()) if self.products_df is not None else set()
                    extra_rows = salla_cogs_df[~salla_cogs_df["SKU"].isin(existing_skus)].copy()
                    extra_rows["Product_Name"] = extra_rows["SKU"]
                    self.products_df = pd.concat([self.products_df, extra_rows], ignore_index=True)
            except Exception:
                # في حالة أي خطأ نتجاهل ونكمل بالبيانات المتاحة
                pass
    
    def get_missing_skus(self):
        """
        تحليل VLOOKUP - المنتجات/البكجات الموجودة في سلة ومفقودة من التسعير
        """
        if self.orders_df is None:
            return None, None, None
        
        # جميع SKU من ملف سلة (فريدة)
        salla_skus = self.orders_df[['sku_code', 'sku_name']].drop_duplicates()
        salla_skus = salla_skus[salla_skus['sku_code'] != '']  # إزالة الفارغة
        
        # SKU من المنتجات
        products_skus = set()
        if self.products_df is not None and 'SKU' in self.products_df.columns:
            products_skus = set(self.products_df['SKU'].dropna().unique())
        
        # SKU من البكجات
        packages_skus = set()
        if self.packages_df is not None and 'SKU' in self.packages_df.columns:
            packages_skus = set(self.packages_df['SKU'].dropna().unique())
        
        # جميع SKU من التسعير (منتجات + بكجات)
        all_pricing_skus = products_skus.union(packages_skus)
        
        # تصنيف كل SKU من سلة
        results = []
        for _, row in salla_skus.iterrows():
            sku = row['sku_code']
            name = row['sku_name']
            
            # حساب الكمية المباعة
            qty_sold = self.orders_df[self.orders_df['sku_code'] == sku]['qty'].sum()
            orders_count = self.orders_df[self.orders_df['sku_code'] == sku]['order_id'].nunique()
            
            # التصنيف
            if sku in products_skus:
                status = "✅ موجود في المنتجات"
                item_type = "منتج"
            elif sku in packages_skus:
                status = "✅ موجود في البكجات"
                item_type = "بكج"
            else:
                status = "❌ مفقود"
                item_type = "غير معروف"
            
            results.append({
                'SKU': sku,
                'اسم الصنف': name,
                'النوع': item_type,
                'الحالة': status,
                'الكمية المباعة': int(qty_sold),
                'عدد الطلبات': int(orders_count),
                'موجود في التسعير': sku in all_pricing_skus
            })
        
        results_df = pd.DataFrame(results)
        
        # المفقودة من المنتجات
        missing_products = results_df[
            (results_df['موجود في التسعير'] == False) & 
            (results_df['الكمية المباعة'] > 0)
        ].copy()
        missing_products = missing_products.sort_values('الكمية المباعة', ascending=False)
        
        # الموجودة
        found_items = results_df[results_df['موجود في التسعير'] == True].copy()
        found_items = found_items.sort_values('الكمية المباعة', ascending=False)
        
        # ملخص
        summary = {
            'total_salla_skus': len(salla_skus),
            'found_in_pricing': len(found_items),
            'missing_from_pricing': len(missing_products),
            'coverage_percentage': (len(found_items) / len(salla_skus) * 100) if len(salla_skus) > 0 else 0,
            'total_products_in_pricing': len(products_skus),
            'total_packages_in_pricing': len(packages_skus),
        }
        
        return missing_products, found_items, summary
    
    def calculate_cogs_for_sales(self):
        """
        حساب تكلفة البضاعة المباعة (COGS) لكل منتج/بكج من سلة
        بناءً على بيانات التسعير
        """
        if self.orders_df is None:
            return None
        
        # ربط مع المنتجات
        sales_with_cost = self.orders_df.copy()
        sales_with_cost['item_type'] = 'unknown'
        sales_with_cost['unit_cogs'] = 0.0
        sales_with_cost['total_cogs'] = 0.0
        sales_with_cost['found_in_pricing'] = False
        
        # البحث في المنتجات
        if self.products_df is not None and 'SKU' in self.products_df.columns:
            product_map = self.products_df.set_index('SKU')['COGS'].to_dict()
            
            for idx, row in sales_with_cost.iterrows():
                sku = row['sku_code']
                if sku in product_map:
                    sales_with_cost.at[idx, 'item_type'] = 'product'
                    sales_with_cost.at[idx, 'unit_cogs'] = product_map[sku]
                    sales_with_cost.at[idx, 'total_cogs'] = product_map[sku] * row['qty']
                    sales_with_cost.at[idx, 'found_in_pricing'] = True
        
        # البحث في البكجات
        if self.packages_df is not None and 'SKU' in self.packages_df.columns:
            package_map = self.packages_df.set_index('SKU')['Total_COGS'].to_dict()
            
            for idx, row in sales_with_cost.iterrows():
                if not sales_with_cost.at[idx, 'found_in_pricing']:
                    sku = row['sku_code']
                    if sku in package_map:
                        sales_with_cost.at[idx, 'item_type'] = 'package'
                        sales_with_cost.at[idx, 'unit_cogs'] = package_map[sku]
                        sales_with_cost.at[idx, 'total_cogs'] = package_map[sku] * row['qty']
                        sales_with_cost.at[idx, 'found_in_pricing'] = True
        
        return sales_with_cost
    
    def get_monthly_top_products(self, year=None, month=None, top_n=10):
        """
        أفضل المنتجات/البكجات لشهر معين
        """
        if self.orders_df is None:
            return None
        
        df = self.orders_df.copy()
        
        if year:
            df = df[df['year'] == year]
        if month:
            df = df[df['month'] == month]
        
        # تجميع حسب المنتج
        top_products = df.groupby(['sku_code', 'sku_name']).agg({
            'qty': 'sum',
            'order_id': 'nunique'
        }).reset_index()
        
        top_products.columns = ['SKU', 'اسم المنتج', 'الكمية المباعة', 'عدد الطلبات']
        top_products = top_products.sort_values('الكمية المباعة', ascending=False).head(top_n)
        
        return top_products
    
    def get_seasonal_recommendations(self, df=None, top_n_per_month: int = 3):
        """
        توصيات موسمية - أفضل المنتجات لكل شهر (يحترم الفلاتر إذا تم تمرير DataFrame مخصص)
        """
        data = df if df is not None else self.orders_df
        if data is None or data.empty:
            return None

        # تأكد من وجود أعمدة السنة/الشهر
        if 'month' not in data.columns and 'order_date' in data.columns:
            data = data.copy()
            data['month'] = pd.to_datetime(data['order_date'], errors='coerce').dt.month
        if 'year' not in data.columns and 'order_date' in data.columns:
            data = data.copy()
            data['year'] = pd.to_datetime(data['order_date'], errors='coerce').dt.year

        monthly_sales = data.groupby(['year', 'month', 'sku_code', 'sku_name'])['qty'].sum().reset_index()
        monthly_sales = monthly_sales.dropna(subset=['month'])

        # أفضل N منتجات لكل شهر (ولكل سنة في حال تعدد السنوات)
        monthly_sales = monthly_sales.sort_values(['year', 'month', 'qty'], ascending=[False, True, False])
        best_per_month = monthly_sales.groupby(['year', 'month']).head(max(1, top_n_per_month)).reset_index(drop=True)

        months_ar = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
            5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
            9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }

        best_per_month['الشهر'] = best_per_month['month'].map(months_ar)
        best_per_month = best_per_month[['year', 'الشهر', 'sku_code', 'sku_name', 'qty']]
        best_per_month.columns = ['السنة', 'الشهر', 'SKU', 'اسم المنتج', 'الكمية']

        return best_per_month
    
    def get_city_recommendations(self, top_n=5):
        """
        توصيات البكجات/المنتجات لكل مدينة
        """
        if self.orders_df is None:
            return None
        
        city_sales = self.orders_df.groupby(['city', 'sku_code', 'sku_name'])['qty'].sum().reset_index()
        
        # أفضل منتجات لكل مدينة
        top_per_city = city_sales.sort_values(['city', 'qty'], ascending=[True, False])
        top_per_city = top_per_city.groupby('city').head(top_n).reset_index(drop=True)
        
        return top_per_city
    
    def find_product_associations(self, min_support=2):
        """
        اكتشاف المنتجات التي تُباع معًا (Market Basket Analysis)
        """
        if self.orders_df is None:
            return None
        
        # تجميع المنتجات حسب الطلب
        order_products = self.orders_df.groupby('order_id')['sku_code'].apply(list).reset_index()
        
        # حساب الأزواج
        associations = defaultdict(int)
        
        for products in order_products['sku_code']:
            if len(products) < 2:
                continue
            
            # كل الأزواج الممكنة
            for i in range(len(products)):
                for j in range(i + 1, len(products)):
                    pair = tuple(sorted([products[i], products[j]]))
                    associations[pair] += 1
        
        # تحويل لـ DataFrame
        assoc_list = []
        for (prod1, prod2), count in associations.items():
            if count >= min_support:
                # الحصول على الأسماء
                name1 = self.orders_df[self.orders_df['sku_code'] == prod1]['sku_name'].iloc[0] if len(self.orders_df[self.orders_df['sku_code'] == prod1]) > 0 else prod1
                name2 = self.orders_df[self.orders_df['sku_code'] == prod2]['sku_name'].iloc[0] if len(self.orders_df[self.orders_df['sku_code'] == prod2]) > 0 else prod2
                
                assoc_list.append({
                    'المنتج الأول': prod1,
                    'اسم الأول': name1,
                    'المنتج الثاني': prod2,
                    'اسم الثاني': name2,
                    'عدد مرات الشراء معًا': count
                })
        
        assoc_df = pd.DataFrame(assoc_list, columns=['المنتج الأول', 'اسم الأول', 'المنتج الثاني', 'اسم الثاني', 'عدد مرات الشراء معًا'])
        if assoc_df.empty:
            return assoc_df

        assoc_df = assoc_df.sort_values('عدد مرات الشراء معًا', ascending=False)
        return assoc_df
    
    def suggest_bundles(self, min_frequency=3, min_qty=5):
        """
        اقتراح بكجات جديدة بناءً على أنماط الشراء
        """
        associations = self.find_product_associations(min_support=min_frequency)
        
        if associations is None or len(associations) == 0:
            return None
        
        # فلترة حسب الكمية المباعة
        suggestions = []
        
        for _, row in associations.iterrows():
            sku1 = row['المنتج الأول']
            sku2 = row['المنتج الثاني']
            
            # حساب الكميات المباعة لكل منتج
            qty1 = self.orders_df[self.orders_df['sku_code'] == sku1]['qty'].sum()
            qty2 = self.orders_df[self.orders_df['sku_code'] == sku2]['qty'].sum()
            
            if qty1 >= min_qty and qty2 >= min_qty:
                suggestions.append({
                    'البكج المقترح': f"{sku1} + {sku2}",
                    'المنتج الأول': row['اسم الأول'],
                    'المنتج الثاني': row['اسم الثاني'],
                    'تكرار الشراء معًا': row['عدد مرات الشراء معًا'],
                    'كمية الأول': int(qty1),
                    'كمية الثاني': int(qty2),
                    'قوة الارتباط': row['عدد مرات الشراء معًا'] / min(qty1, qty2)
                })
        
        suggestions_df = pd.DataFrame(suggestions)
        if len(suggestions_df) > 0:
            suggestions_df = suggestions_df.sort_values('قوة الارتباط', ascending=False)
        
        return suggestions_df
    
    def get_city_specific_bundles(self, city, min_support=2):
        """
        اقتراح بكجات خاصة بمدينة معينة
        """
        if self.orders_df is None:
            return None
        
        city_orders = self.orders_df[self.orders_df['city'] == city]
        
        # حفظ البيانات الأصلية
        original_orders = self.orders_df
        
        # استخدام بيانات المدينة فقط
        self.orders_df = city_orders
        
        # اقتراح البكجات
        bundles = self.suggest_bundles(min_frequency=min_support)
        
        # استرجاع البيانات الأصلية
        self.orders_df = original_orders
        
        return bundles
    
    def generate_summary_report(self):
        """
        تقرير شامل بكل التحليلات
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_orders': int(self.orders_df['order_id'].nunique()) if self.orders_df is not None else 0,
            'total_items_sold': int(self.orders_df['qty'].sum()) if self.orders_df is not None else 0,
            'unique_products': int(self.orders_df['sku_code'].nunique()) if self.orders_df is not None else 0,
        }
        
        # حساب COGS الإجمالي
        sales_with_cost = self.calculate_cogs_for_sales()
        if sales_with_cost is not None:
            report['total_cogs'] = float(sales_with_cost['total_cogs'].sum())
            report['items_found_in_pricing'] = int(sales_with_cost['found_in_pricing'].sum())
            report['coverage_percentage'] = (sales_with_cost['found_in_pricing'].sum() / len(sales_with_cost) * 100) if len(sales_with_cost) > 0 else 0
        
        return report
    
    def save_insights(self, output_dir="data"):
        """
        حفظ كل التحليلات في ملفات منفصلة
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # التوصيات الموسمية
        seasonal = self.get_seasonal_recommendations()
        if seasonal is not None:
            seasonal.to_csv(output_dir / "salla_seasonal_recommendations.csv", index=False)
        
        # الارتباطات
        associations = self.find_product_associations()
        if associations is not None:
            associations.to_csv(output_dir / "salla_product_associations.csv", index=False)
        
        # البكجات المقترحة
        bundles = self.suggest_bundles()
        if bundles is not None:
            bundles.to_csv(output_dir / "salla_suggested_bundles.csv", index=False)
        
        # تحليل VLOOKUP - المفقودات والموجودات
        missing, found, vlookup_summary = self.get_missing_skus()
        if missing is not None:
            missing.to_csv(output_dir / "salla_missing_skus.csv", index=False)
        if found is not None:
            found.to_csv(output_dir / "salla_found_skus.csv", index=False)
        if vlookup_summary is not None:
            with open(output_dir / "salla_vlookup_summary.json", "w", encoding="utf-8") as f:
                json.dump(vlookup_summary, f, ensure_ascii=False, indent=2)
        
        # التكاليف
        sales_with_cost = self.calculate_cogs_for_sales()
        if sales_with_cost is not None:
            sales_with_cost.to_csv(output_dir / "salla_sales_with_cogs.csv", index=False)
        
        # التقرير الشامل
        summary = self.generate_summary_report()
        with open(output_dir / "salla_insights_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"✅ تم حفظ جميع التحليلات في: {output_dir.resolve()}")


def main():
    """
    تشغيل التحليلات وحفظ النتائج
    """
    print("🔄 جاري تحليل بيانات سلة...")
    
    analyzer = SallaInsights()
    analyzer.load_pricing_data()
    
    if analyzer.orders_df is None:
        print("❌ لم يتم العثور على ملف الطلبات!")
        return
    
    print(f"📊 تم تحميل {len(analyzer.orders_df):,} صف من الطلبات")
    
    # حفظ جميع التحليلات
    analyzer.save_insights()
    
    # عرض ملخص
    summary = analyzer.generate_summary_report()
    print("\n📈 ملخص التحليل:")
    print(f"  - إجمالي الطلبات: {summary['total_orders']:,}")
    print(f"  - إجمالي الكمية المباعة: {summary['total_items_sold']:,}")
    print(f"  - عدد المنتجات الفريدة: {summary['unique_products']:,}")
    
    if 'total_cogs' in summary:
        print(f"  - إجمالي تكلفة البضاعة: {summary['total_cogs']:,.2f} ريال")
        print(f"  - نسبة التغطية: {summary['coverage_percentage']:.1f}%")


if __name__ == "__main__":
    main()

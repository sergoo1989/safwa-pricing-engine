import streamlit as st
import pandas as pd
from pricing_app.data_loader import load_cost_data
from pricing_app.models import ChannelFees
from pricing_app.fees import extract_channel_fees_from_pl
from pricing_app.channels import load_channels, save_channels, ChannelFees as ChannelFeesData
from pricing_app.advanced_pricing import calculate_price_breakdown, create_pricing_table
import plotly.express as px
import plotly.graph_objects as go
import json
import os

st.set_page_config(page_title="محرك تسعير صفوة", page_icon="SA", layout="wide")

# Initialize session state for page navigation
if 'page' not in st.session_state:
    st.session_state.page = 'main'

st.title("محرك تسعير صفوة - Safwa Pricing Engine")
st.markdown("---")

# Load data
@st.cache_data
def load_all_data():
    materials, product_recipes, products_summary, package_compositions, packages_summary = load_cost_data('data')
    return materials, product_recipes, products_summary, package_compositions, packages_summary

try:
    materials, product_recipes, products_summary, package_compositions, packages_summary = load_all_data()
except Exception as e:
    st.error(f"خطأ في تحميل البيانات: {e}")
    st.info("تأكد من وجود مجلد data مع جميع الملفات المطلوبة")
    st.stop()

# Sidebar Navigation
with st.sidebar:
    st.markdown("### القائمة الرئيسية")
    
    # Navigation buttons - vertical layout
    if st.button("📤 رفع الملفات", help="رفع الملفات", key="btn_upload", use_container_width=True):
        st.session_state.page = 'upload'
    
    if st.button("💰 تكلفة البضاعة", help="تكلفة البضاعة", key="btn_cogs", use_container_width=True):
        st.session_state.page = 'cogs'
    
    if st.button("⚙️ المنصات", help="إعدادات المنصات", key="btn_settings", use_container_width=True):
        st.session_state.page = 'settings'
    
    if st.button("💵 تسعير منتج/بكج فردي", help="التسعير للمنتج أو البكج الفردي", key="btn_pricing", use_container_width=True):
        st.session_state.page = 'pricing'
    
    if st.button("📊 تسعير منصة كاملة", help="تسعير منصة كاملة", key="btn_profit_margins", use_container_width=True):
        st.session_state.page = 'profit_margins'
    

# Page: Upload Files
if st.session_state.page == 'upload':
    st.header("رفع الملفات")
    st.markdown("---")
    
    # Clear data button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ مسح جميع البيانات", type="secondary", use_container_width=True):
            # Confirm deletion
            if 'confirm_delete' not in st.session_state:
                st.session_state.confirm_delete = True
                st.rerun()
    
    # Show confirmation dialog
    if st.session_state.get('confirm_delete', False):
        st.warning("⚠️ هل أنت متأكد من حذف جميع البيانات؟ هذا الإجراء لا يمكن التراجع عنه!")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ نعم، امسح البيانات", type="primary"):
                try:
                    import os
                    files_to_delete = [
                        'data/raw_materials_template.csv',
                        'data/products_template.csv',
                        'data/packages_template.csv'
                    ]
                    deleted_files = []
                    for file in files_to_delete:
                        if os.path.exists(file):
                            os.remove(file)
                            deleted_files.append(file)
                    
                    if deleted_files:
                        st.success(f"✅ تم حذف {len(deleted_files)} ملف بنجاح")
                        # Clear cache to reload data
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
    
    tab_materials, tab_products, tab_packages = st.tabs([
        "المواد الخام",
        "المنتجات",
        "البكجات"
    ])
    
    # Tab 1: Materials
    with tab_materials:
        st.subheader("رفع المواد الخام")
        st.info("صيغة الملف: CSV أو Excel (.xlsx)")
        
        raw_materials_file = st.file_uploader(
            "اختر ملف المواد الخام",
            type=["csv", "xlsx"],
            key="upload_raw_materials"
        )
        
        if raw_materials_file is not None:
            try:
                if raw_materials_file.name.endswith('.csv'):
                    df = pd.read_csv(raw_materials_file)
                else:
                    df = pd.read_excel(raw_materials_file)
                
                st.success(f"تم تحميل الملف بنجاح ({len(df)} صف)")
                st.dataframe(df, use_container_width=True)
                
                if st.button("حفظ المواد الخام"):
                    try:
                        df.to_csv('data/raw_materials_template.csv', index=False, encoding='utf-8-sig')
                        st.success("تم حفظ المواد الخام في data/raw_materials_template.csv")
                        # Clear cache to reload new data
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"خطأ في الحفظ: {e}")
            except Exception as e:
                st.error(f"خطأ في تحميل الملف: {e}")
        
        st.markdown("---")
        st.subheader("متطلبات الملف:")
        st.code("""material_sku
material_name
category
unit
cost_per_unit""")
    
    # Tab 2: Products
    with tab_products:
        st.subheader("رفع المنتجات")
        st.info("صيغة الملف: CSV أو Excel (.xlsx)")
        
        products_file = st.file_uploader(
            "اختر ملف المنتجات",
            type=["csv", "xlsx"],
            key="upload_products"
        )
        
        if products_file is not None:
            try:
                if products_file.name.endswith('.csv'):
                    df = pd.read_csv(products_file)
                else:
                    df = pd.read_excel(products_file)
                
                st.success(f"تم تحميل الملف بنجاح ({len(df)} صف)")
                st.dataframe(df, use_container_width=True)
                
                if st.button("حفظ المنتجات"):
                    try:
                        df.to_csv('data/products_template.csv', index=False, encoding='utf-8-sig')
                        st.success("تم حفظ المنتجات في data/products_template.csv")
                        # Clear cache to reload new data
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"خطأ في الحفظ: {e}")
            except Exception as e:
                st.error(f"خطأ في تحميل الملف: {e}")
        
        st.markdown("---")
        st.subheader("متطلبات الملف:")
        st.code("""product_sku
product_name
material_code
quantity""")
    
    # Tab 3: Packages
    with tab_packages:
        st.subheader("رفع البكجات")
        st.info("صيغة الملف: CSV أو Excel (.xlsx)")
        
        packages_file = st.file_uploader(
            "اختر ملف البكجات",
            type=["csv", "xlsx"],
            key="upload_packages"
        )
        
        if packages_file is not None:
            try:
                if packages_file.name.endswith('.csv'):
                    df = pd.read_csv(packages_file)
                else:
                    df = pd.read_excel(packages_file)
                
                st.success(f"تم تحميل الملف بنجاح ({len(df)} صف)")
                st.dataframe(df, use_container_width=True)
                
                if st.button("حفظ البكجات"):
                    try:
                        df.to_csv('data/packages_template.csv', index=False, encoding='utf-8-sig')
                        st.success("تم حفظ البكجات في data/packages_template.csv")
                        # Clear cache to reload new data
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"خطأ في الحفظ: {e}")
            except Exception as e:
                st.error(f"خطأ في تحميل الملف: {e}")
        
        st.markdown("---")
        st.subheader("متطلبات الملف:")
        st.code("""package_sku
package_name
product_sku
quantity""")

# Page: COGS (Cost of Goods Sold)
elif st.session_state.page == 'cogs':
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
                if (component_sku not in product_skus and 
                    component_sku not in package_skus and 
                    component_sku not in material_skus):
                    missing_components.append(component_sku)
            
            if missing_components:
                packages_warnings.append(f"الباقة {package_sku} تحتوي على مكونات غير موجودة: {', '.join(missing_components)}")
    
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
    def calculate_component_cost(sku, component_type='product'):
        """Calculate cost of a component based on its type"""
        if component_type == 'material' and sku in materials:
            return materials[sku].cost_per_unit
        elif component_type == 'product' and sku in product_recipes:
            # Sum all materials in this product
            total = 0
            for material_code, mat_qty in product_recipes[sku].items():
                if material_code in materials:
                    total += materials[material_code].cost_per_unit * mat_qty
            return total
        elif component_type == 'package' and sku in package_compositions:
            # Recursively calculate package cost
            total = 0
            for comp_sku, comp_qty in package_compositions[sku].items():
                # Determine type: check if it's a product, package, or material
                if comp_sku in product_recipes:
                    comp_cost = calculate_component_cost(comp_sku, 'product')
                elif comp_sku in package_compositions:
                    comp_cost = calculate_component_cost(comp_sku, 'package')
                elif comp_sku in materials:
                    comp_cost = calculate_component_cost(comp_sku, 'material')
                else:
                    comp_cost = 0
                total += comp_cost * comp_qty
            return total
        return 0
    
    # Product COGS
    st.write("**تكلفة المنتجات:**")
    for product_sku, materials_dict in product_recipes.items():
        product_name = products_summary[products_summary['Product_SKU'] == product_sku]['Product_Name'].values
        product_name = product_name[0] if len(product_name) > 0 else product_sku
        
        total_cost = 0
        details = []
        
        for material_code, quantity in materials_dict.items():
            if material_code in materials:
                material = materials[material_code]
                cost = material.cost_per_unit * quantity
                total_cost += cost
                details.append(f"{material_code}: {quantity} x {material.cost_per_unit:.2f} = {cost:.2f}")
        
        cogs_data.append({
            'النوع': 'منتج',
            'SKU': product_sku,
            'الاسم': product_sku,
            'التكلفة': total_cost,
            'التفاصيل': ' | '.join(details) if details else 'بدون مواد'
        })
    
    # Package COGS
    st.write("**تكلفة البكجات:**")
    for package_sku, components_dict in package_compositions.items():
        package_name = packages_summary[packages_summary['Package_SKU'] == package_sku]['Package_Name'].values
        package_name = package_name[0] if len(package_name) > 0 else package_sku
        
        total_cost = 0
        details = []
        
        for component_sku, quantity in components_dict.items():
            # Determine component type and calculate its cost
            if component_sku in product_recipes:
                # It's a product
                comp_cost = calculate_component_cost(component_sku, 'product')
                comp_type = 'منتج'
            elif component_sku in package_compositions:
                # It's a package
                comp_cost = calculate_component_cost(component_sku, 'package')
                comp_type = 'بكج'
            elif component_sku in materials:
                # It's a material
                comp_cost = calculate_component_cost(component_sku, 'material')
                comp_type = 'مادة'
            else:
                comp_cost = 0
                comp_type = 'غير معروف'
            
            cost = comp_cost * quantity
            total_cost += cost
            details.append(f"{component_sku} ({comp_type}): {quantity} x {comp_cost:.2f} = {cost:.2f}")
        
        cogs_data.append({
            'النوع': 'بكج',
            'SKU': package_sku,
            'الاسم': package_sku,
            'التكلفة': total_cost,
            'التفاصيل': ' | '.join(details) if details else 'بدون مكونات'
        })
    
    cogs_df = pd.DataFrame(cogs_data)
    
    # Separate dataframes for products and packages
    products_cogs_df = cogs_df[cogs_df['النوع'] == 'منتج'].copy()
    packages_cogs_df = cogs_df[cogs_df['النوع'] == 'بكج'].copy()
    
    # Products Table
    st.write("**جدول تكلفة المنتجات:**")
    if len(products_cogs_df) > 0:
        st.dataframe(products_cogs_df[['SKU', 'التكلفة', 'التفاصيل']].style.format({
            'التكلفة': '{:.2f} SAR'
        }), use_container_width=True)
    else:
        st.info("لا توجد منتجات")
    
    st.markdown("---")
    
    # Packages Table
    st.write("**جدول تكلفة البكجات:**")
    if len(packages_cogs_df) > 0:
        st.dataframe(packages_cogs_df[['SKU', 'التكلفة', 'التفاصيل']].style.format({
            'التكلفة': '{:.2f} SAR'
        }), use_container_width=True)
    else:
        st.info("لا توجد بكجات")
    
    # Summary Statistics
    st.subheader("إحصائيات التكاليف")
    
    col1, col2, col3, col4 = st.columns(4)
    
    products_cogs = products_cogs_df['التكلفة']
    packages_cogs = packages_cogs_df['التكلفة']
    
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
            x='SKU', 
            y='التكلفة',
            title='تكلفة المنتجات (COGS)',
            labels={'التكلفة': 'التكلفة (SAR)', 'SKU': 'رمز المنتج'},
            color='التكلفة',
            color_continuous_scale='Blues',
            text='التكلفة'
        )
        fig_products.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_products.update_layout(
            xaxis_tickangle=-45,
            height=500,
            hovermode='x unified',
            showlegend=False
        )
        st.plotly_chart(fig_products, use_container_width=True)
    else:
        st.info("لا توجد منتجات")
    
    st.markdown("---")
    st.subheader("رسم بياني - تكاليف البكجات")
    
    if len(packages_cogs_df) > 0:
        fig_packages = px.bar(
            packages_cogs_df, 
            x='SKU', 
            y='التكلفة',
            title='تكلفة البكجات (COGS)',
            labels={'التكلفة': 'التكلفة (SAR)', 'SKU': 'رمز الباقة'},
            color='التكلفة',
            color_continuous_scale='Greens',
            text='التكلفة'
        )
        fig_packages.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_packages.update_layout(
            xaxis_tickangle=-45,
            height=500,
            hovermode='x unified',
            showlegend=False
        )
        st.plotly_chart(fig_packages, use_container_width=True)
    else:
        st.info("لا توجد بكجات")
    
    st.markdown("---")
    
    # Summary charts - Distribution
    st.subheader("الرسوم البيانية الملخصة")
    
    col_summary1, col_summary2, col_summary3 = st.columns(3)
    
    # Chart 1: Distribution by Type
    with col_summary1:
        st.write("**توزيع التكاليف حسب النوع**")
        type_summary = cogs_df.groupby('النوع')['التكلفة'].sum().reset_index()
        fig_pie = px.pie(
            type_summary,
            values='التكلفة',
            names='النوع',
            title='نسبة التكاليف',
            color_discrete_map={'منتج': '#1f77b4', 'بكج': '#2ca02c'},
            labels={'التكلفة': 'التكلفة (SAR)'}
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Chart 2: Top 10 Items
    with col_summary2:
        st.write("**أعلى 10 عناصر تكلفة**")
        top_items = cogs_df.nlargest(10, 'التكلفة')[['SKU', 'النوع', 'التكلفة']].copy()
        fig_top = px.bar(
            top_items,
            y='SKU',
            x='التكلفة',
            orientation='h',
            color='النوع',
            title='أعلى العناصر تكلفة',
            labels={'التكلفة': 'التكلفة (SAR)', 'SKU': 'رمز العنصر'},
            color_discrete_map={'منتج': '#1f77b4', 'بكج': '#2ca02c'},
            text='التكلفة'
        )
        fig_top.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_top.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_top, use_container_width=True)
    
    # Chart 3: Statistics Summary
    with col_summary3:
        st.write("**إحصائيات ملخصة**")
        
        # Create summary statistics dataframe
        stats_data = {
            'البيان': [
                'إجمالي المنتجات',
                'إجمالي البكجات',
                'إجمالي التكاليف',
                'متوسط تكلفة المنتج',
                'متوسط تكلفة الباقة',
                'أعلى منتج تكلفة',
                'أعلى بكجة تكلفة'
            ],
            'القيمة': [
                f"{len(products_cogs_df)}",
                f"{len(packages_cogs_df)}",
                f"{cogs_df['التكلفة'].sum():.2f} SAR",
                f"{products_cogs.mean():.2f} SAR" if len(products_cogs) > 0 else "0",
                f"{packages_cogs.mean():.2f} SAR" if len(packages_cogs) > 0 else "0",
                f"{products_cogs.max():.2f} SAR" if len(products_cogs) > 0 else "0",
                f"{packages_cogs.max():.2f} SAR" if len(packages_cogs) > 0 else "0"
            ]
        }
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

# Page: Settings
elif st.session_state.page == 'settings':
    st.header("إعدادات القنوات والتسعير")
    st.markdown("---")
    
    # Load existing channels
    channels_file = 'data/channels.json'
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
            
            platform_pct = st.number_input("رسوم المنصات %", min_value=0.0, max_value=20.0, value=default_platform, step=0.1) / 100
            marketing_pct = st.number_input("نسبة التسويق %", min_value=0.0, max_value=50.0, value=default_marketing, step=0.1) / 100
            opex_pct = st.number_input("نسبة التشغيل %", min_value=0.0, max_value=20.0, value=default_opex, step=0.1) / 100
        
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
            
            shipping_fixed = st.number_input("رسوم الشحن الثابتة (SAR)", min_value=0.0, value=default_shipping, step=0.01)
            preparation_fee = st.number_input("رسوم التحضير (SAR)", min_value=0.0, value=default_prep, step=0.01)
            free_threshold = st.number_input("الحد الأدنى للشحن والتجهيز مجاني (SAR)", min_value=0.0, value=default_threshold, step=0.01,
                                           help="إذا كان السعر قبل الخصم ≥ هذا الحد، يكون الشحن والتجهيز مجاني")
        
        st.markdown("---")
        
        # Set fixed fees
        payment_pct = 0.025  # Fixed payment fee 2.5%
        
        # ===== Custom Fees Management =====
        st.subheader("إدارة الرسوم الإضافية المخصصة")
        
        custom_fees = {}
        if selected_channel != "إضافة جديدة" and selected_channel in channels:
            current = channels[selected_channel]
            custom_fees = current.custom_fees if hasattr(current, 'custom_fees') else {}
        
        col1, col2, col3 = st.columns(3)
        with col1:
            fee_name = st.text_input("اسم الرسم الجديد", placeholder="مثال: رسم معالجة", key="fee_name_input")
        with col2:
            fee_amount = st.number_input("المبلغ أو النسبة", min_value=0.0, step=0.01, key="fee_amount_input")
        with col3:
            fee_type = st.selectbox("نوع الرسم", ["نسبة %", "مبلغ ثابت SAR"], key="fee_type_select")
        
        if st.button("إضافة رسم جديد", key="add_fee_btn"):
            if fee_name.strip():
                fee_type_key = "percentage" if fee_type == "نسبة %" else "fixed"
                if fee_type_key == "percentage":
                    custom_fees[fee_name] = {"name": fee_name, "amount": fee_amount / 100, "fee_type": fee_type_key}
                else:
                    custom_fees[fee_name] = {"name": fee_name, "amount": fee_amount, "fee_type": fee_type_key}
                st.success(f"تم إضافة الرسم: {fee_name}")
        
        # Display existing custom fees
        if custom_fees:
            st.write("**الرسوم المضافة:**")
            for fee_key, fee_data in list(custom_fees.items()):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.write(f"**{fee_data['name']}**")
                with col2:
                    if fee_data['fee_type'] == 'percentage':
                        st.write(f"{fee_data['amount']*100:.1f}%")
                    else:
                        st.write(f"{fee_data['amount']:.2f} SAR")
                with col3:
                    st.write("نسبة" if fee_data['fee_type'] == 'percentage' else "مبلغ ثابت")
                with col4:
                    if st.button("حذف", key=f"delete_fee_{fee_key}"):
                        del custom_fees[fee_key]
                        st.rerun()
        
        st.markdown("---")
        
        if st.button("حفظ القناة"):
            if channel_name.strip():
                new_channel = ChannelFeesData(
                    platform_pct=platform_pct,
                    payment_pct=payment_pct,
                    marketing_pct=marketing_pct,
                    opex_pct=opex_pct,
                    vat_rate=0.15,  # Default VAT 15%
                    discount_rate=0.10,  # Default discount 10%
                    shipping_fixed=shipping_fixed,
                    preparation_fee=preparation_fee,
                    free_shipping_threshold=free_threshold,
                    custom_fees=custom_fees
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
                        st.metric("الحد الأدنى للشحن مجاني", f"{ch_fees.free_shipping_threshold:.2f} SAR" if ch_fees.free_shipping_threshold > 0 else "معطل")
                    
                    # Display custom fees if any
                    if hasattr(ch_fees, 'custom_fees') and ch_fees.custom_fees:
                        st.write("**الرسوم الإضافية:**")
                        for fee_key, fee_data in ch_fees.custom_fees.items():
                            if fee_data['fee_type'] == 'percentage':
                                st.write(f"• {fee_data['name']}: {fee_data['amount']*100:.1f}%")
                            else:
                                st.write(f"• {fee_data['name']}: {fee_data['amount']:.2f} SAR")

# Page: Info
elif st.session_state.page == 'info':
    st.header("📊 تحليل هوامش الربح")
    st.markdown("---")
    
    # التحقق من وجود جدول تسعير محفوظ
    if "last_pricing_breakdown" not in st.session_state:
        st.info("⚠️ لم يتم حساب التسعير بعد. اذهب إلى تبويب '💵 شاشة تسعير المنتجات والبكجات' أولاً، اختر منتج أو بكج، واضغط على زر 'حساب السعر الكامل'.")
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
            'تكلفة البضاعة': breakdown.get('cogs', 0),
            'مصاريف إدارية': breakdown.get('admin_fee', 0),
            'مصاريف تسويق': breakdown.get('marketing_fee', 0),
            'شحن': breakdown.get('shipping_fee', 0),
            'تحضير': breakdown.get('preparation_fee', 0),
            'دفع': breakdown.get('payment_fee', 0)
        }
        
        # إضافة الرسوم المخصصة
        custom_fees = breakdown.get('custom_fees', {})
        if custom_fees:
            for fee_name, fee_amount in custom_fees.items():
                if fee_amount > 0:
                    costs[fee_name] = fee_amount
        
        costs_df = pd.DataFrame(list(costs.items()), columns=['النوع', 'المبلغ'])
        costs_df = costs_df[costs_df['المبلغ'] > 0]
        
        fig_costs = px.pie(
            costs_df,
            values='المبلغ',
            names='النوع',
            title='توزيع التكاليف والرسوم'
        )
        st.plotly_chart(fig_costs, use_container_width=True)
        
        st.markdown("---")
        
        # رسم بياني لتكوين السعر
        st.markdown("### تكوين السعر النهائي")
        
        price_elements = {
            'COGS': breakdown.get('cogs', 0),
            'الرسوم': breakdown.get('total_costs_fees', 0) - breakdown.get('cogs', 0) - breakdown.get('shipping_fee', 0) - breakdown.get('preparation_fee', 0),
            'الربح': breakdown.get('profit', 0)
        }
        price_df = pd.DataFrame(list(price_elements.items()), columns=['العنصر', 'المبلغ'])
        
        fig_price = px.bar(
            price_df,
            x='العنصر',
            y='المبلغ',
            title='تكوين السعر',
            text='المبلغ',
            color='العنصر',
            color_discrete_map={'COGS': '#1f77b4', 'الرسوم': '#ff7f0e', 'الربح': '#2ca02c'}
        )
        fig_price.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        st.plotly_chart(fig_price, use_container_width=True)

# Main Page
elif st.session_state.page == 'main':
    st.header("لوحة التحكم الرئيسية")
    st.markdown("---")
    
    st.info("ملاحظة: صفحة التسعير الكامل قيد التطوير. يرجى استخدام صفحة تكلفة البضاعة لعرض البيانات.")
    
    st.subheader("الخطوات التالية:")
    st.write("""
    1. رفع الملفات - قم برفع ملفات المواد الخام والمنتجات والبكجات
    2. تكلفة البضاعة - تحقق من صحة البيانات وحساب التكاليف
    3. المنصات - ضبط معايير التسعير والرسوم
    4. جدول التسعير - سيتم عرض جدول التسعير الكامل هنا قريباً
    """)
    
    st.markdown("---")
    st.subheader("ملخص البيانات الحالية")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("المواد الخام", len(materials))
    with col2:
        st.metric("المنتجات", len(product_recipes))
    with col3:
        st.metric("البكجات", len(package_compositions))

# Page: Advanced Pricing
elif st.session_state.page == 'pricing':
    st.header("💵 تسعير منتج/بكج فردي")
    st.markdown("حساب التكلفة الكاملة وتحليل هوامش الربح لمنتج أو بكج واحد")
    st.markdown("---")
    
    # Load channels
    channels_file = 'data/channels.json'
    channels = load_channels(channels_file)
    
    if not channels:
        st.error("⚠️ لا توجد قنوات محفوظة! يجب إضافة قناة أولاً من صفحة الإعدادات")
    else:
        # Load all data to get products and packages
        materials, product_recipes, products_df, package_compositions, packages_df = load_cost_data('data')
        
        # Helper function to calculate cost of any component
        def calculate_component_cost(sku, component_type='product'):
            """Calculate cost of a component based on its type"""
            if component_type == 'material' and sku in materials:
                return materials[sku].cost_per_unit
            elif component_type == 'product' and sku in product_recipes:
                # Sum all materials in this product
                total = 0
                for material_code, mat_qty in product_recipes[sku].items():
                    if material_code in materials:
                        total += materials[material_code].cost_per_unit * mat_qty
                return total
            elif component_type == 'package' and sku in package_compositions:
                # Sum all components in this package
                total = 0
                for comp_sku, comp_qty in package_compositions[sku].items():
                    # Try each type
                    if comp_sku in materials:
                        total += materials[comp_sku].cost_per_unit * comp_qty
                    elif comp_sku in product_recipes:
                        comp_cost = calculate_component_cost(comp_sku, 'product')
                        total += comp_cost * comp_qty
                    elif comp_sku in package_compositions:
                        comp_cost = calculate_component_cost(comp_sku, 'package')
                        total += comp_cost * comp_qty
                return total
            return 0
        
        # Create options list for SKU selector
        sku_options = []
        sku_to_name = {}
        sku_to_type = {}
        sku_to_cogs = {}
        
        # Add products
        if not products_df.empty:
            for _, row in products_df.iterrows():
                sku = row['Product_SKU']
                name = row['Product_Name']
                option = f"{name} - {sku}"
                sku_options.append(option)
                sku_to_name[option] = name
                sku_to_type[option] = "منتج"
                sku_to_cogs[option] = calculate_component_cost(sku, 'product')
        
        # Add packages
        if not packages_df.empty:
            for _, row in packages_df.iterrows():
                sku = row['Package_SKU']
                name = row['Package_Name']
                option = f"{name} - {sku}"
                sku_options.append(option)
                sku_to_name[option] = name
                sku_to_type[option] = "باقة"
                sku_to_cogs[option] = calculate_component_cost(sku, 'package')
        
        # Add products
        if not products_df.empty:
            for _, row in products_df.iterrows():
                sku = row['Product_SKU']
                name = row['Product_Name']
                option = f"{name} - {sku}"
                sku_options.append(option)
                sku_to_name[option] = name
                sku_to_type[option] = "منتج"
                sku_to_cogs[option] = calculate_component_cost(sku, 'product')
        
        # Add packages
        if not packages_df.empty:
            for _, row in packages_df.iterrows():
                sku = row['Package_SKU']
                name = row['Package_Name']
                option = f"{name} - {sku}"
                sku_options.append(option)
                sku_to_name[option] = name
                sku_to_type[option] = "باقة"
                sku_to_cogs[option] = calculate_component_cost(sku, 'package')
        
        # Section 1: Product Selection
        st.subheader("🔍 1. اختيار المنتج الفردي والقناة")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_channel = st.selectbox(
                "📍 اختر قناة البيع",
                list(channels.keys()),
                help="اختر القناة التي تريد حساب التسعير لها"
            )
        
        with col2:
            # Add search box for SKU
            search_term = st.text_input(
                "🔎 بحث",
                placeholder="ابحث بالاسم أو رمز المنتج (SKU)"
            )
        
        # Filter options based on search term
        filtered_sku_options = sku_options
        if search_term:
            filtered_sku_options = [opt for opt in sku_options if search_term.lower() in opt.lower()]
        
        if filtered_sku_options:
            selected_sku_option = st.selectbox(
                "📦 المنتج/الباقة",
                filtered_sku_options,
                help="اختر المنتج أو الباقة من القائمة"
            )
            # Extract SKU from the selected option
            sku_input = selected_sku_option.split(" - ")[-1]
            item_type_display = sku_to_type.get(selected_sku_option, "منتج")
            item_type = item_type_display
        else:
            st.warning("⚠️ لم يتم العثور على نتائج مطابقة للبحث")
            sku_input = ""
            item_type = "منتج"
        
        st.markdown("---")
        
        # Section 2: Pricing Inputs
        st.subheader("📝 2. إدخال بيانات التسعير")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Get COGS based on selected SKU option
            if sku_options and selected_sku_option in sku_to_cogs:
                default_cogs = sku_to_cogs[selected_sku_option]
            else:
                default_cogs = 0.0
            
            cogs = st.number_input(
                "💰 تكلفة البضاعة (COGS)",
                min_value=0.0,
                step=0.01,
                value=default_cogs,
                help="التكلفة الإجمالية للمنتج (يتم حسابها تلقائياً)"
            )
        
        with col2:
            price_with_vat = st.number_input(
                "💵 سعر البيع شامل الضريبة",
                min_value=0.0,
                step=0.01,
                value=0.0,
                help="السعر النهائي للعميل قبل الخصم (شامل ضريبة 15%)"
            )
        
        with col3:
            discount_pct = st.number_input(
                "🏷️ نسبة الخصم %",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                value=0.0,
                help="نسبة الخصم المقدمة للعميل"
            )
        
        st.markdown("---")
        
        # Calculate button - centered and prominent
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            calculate_btn = st.button(
                "🧮 حساب السعر الكامل",
                key="calc_pricing",
                use_container_width=True,
                type="primary"
            )
        
        if calculate_btn:
            if cogs > 0 and selected_channel in channels and sku_input.strip() and price_with_vat > 0:
                ch = channels[selected_channel]
                free_threshold = ch.free_shipping_threshold
                
                # Use channel's default shipping and preparation fees
                shipping = ch.shipping_fixed
                preparation = ch.preparation_fee
                
                # Convert discount percentage to decimal
                discount_rate = discount_pct / 100.0
                
                # Convert to dict for calculation
                channel_dict = {
                    'opex_pct': ch.opex_pct,
                    'marketing_pct': ch.marketing_pct,
                    'platform_pct': ch.platform_pct,
                    'payment_pct': ch.payment_pct,
                    'vat_rate': ch.vat_rate,
                    'discount_rate': discount_rate
                }
                
                # Calculate breakdown
                breakdown = calculate_price_breakdown(
                    cogs=cogs,
                    channel_fees=channel_dict,
                    shipping=shipping,
                    preparation=preparation,
                    discount_rate=discount_rate,
                    vat_rate=ch.vat_rate,
                    free_shipping_threshold=free_threshold,
                    custom_fees=ch.custom_fees if hasattr(ch, 'custom_fees') else {},
                    price_with_vat=price_with_vat
                )
                
                # Section 3: Results Summary
                st.markdown("---")
                st.subheader("📊 3. ملخص النتائج")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "💵 سعر البيع شامل الضريبة",
                        f"{breakdown['sale_price']:.2f} SAR",
                        help="سعر البيع النهائي للعميل قبل الخصم (شامل ضريبة 15%)"
                    )
                with col2:
                    st.metric(
                        "📦 إجمالي التكاليف",
                        f"{breakdown['total_costs_fees']:.2f} SAR",
                        help="مجموع كل التكاليف والرسوم (COGS + الشحن + التجهيز + الرسوم)"
                    )
                with col3:
                    profit_color = "normal" if breakdown['profit'] > 0 else "inverse"
                    st.metric(
                        "💰 الربح",
                        f"{breakdown['profit']:.2f} SAR",
                        delta=f"{breakdown['margin_pct']*100:.1f}%",
                        delta_color=profit_color,
                        help="صافي الربح بعد خصم جميع التكاليف والرسوم"
                    )
                with col4:
                    st.metric(
                        "📈 هامش الربح",
                        f"{breakdown['margin_pct']*100:.1f}%",
                        help="نسبة الربح من السعر الصافي"
                    )
                
                st.markdown("---")
                
                # Section 4: Financial Metrics
                st.subheader("📈 4. المؤشرات المالية")
                
                # Display margin-based prices
                if 'margin_prices' in breakdown and breakdown['margin_prices']:
                    st.markdown("##### 💎 أسعار البيع عند هوامش ربح مختلفة")
                    st.caption("سعر البيع شامل الضريبة قبل الخصم")
                    
                    cols = st.columns(5)
                    margin_percentages = [0.00, 0.05, 0.10, 0.15, 0.20]
                    
                    for idx, margin in enumerate(margin_percentages):
                        with cols[idx]:
                            price = breakdown['margin_prices'].get(margin, 0.0)
                            margin_pct = margin * 100
                            
                            # Highlight current margin
                            is_current = abs(breakdown['margin_pct'] - margin) < 0.001
                            delta_text = "السعر الحالي" if is_current else None
                            
                            st.metric(
                                f"🎯 هامش {margin_pct:.0f}%",
                                f"{price:.2f} SAR",
                                delta=delta_text,
                                help=f"سعر البيع المطلوب لتحقيق هامش ربح {margin_pct:.0f}%"
                            )
                
                st.markdown("---")
                
                # Section 5: Visual Analytics
                st.subheader("📊 5. التحليل البصري")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Cost breakdown pie chart
                    costs = {
                        'تكلفة البضاعة': breakdown['cogs'],
                        'مصاريف إدارية': breakdown['admin_fee'],
                        'مصاريف تسويق': breakdown['marketing_fee'],
                        'رسوم المنصة': breakdown['platform_fee'],
                        'شحن': breakdown['shipping_fee'],
                        'تحضير': breakdown['preparation_fee'],
                        'دفع': breakdown['payment_fee']
                    }
                    
                    # Add custom fees to pie chart
                    if breakdown.get('custom_fees'):
                        for fee_name, fee_amount in breakdown['custom_fees'].items():
                            if fee_amount > 0:
                                costs[fee_name] = fee_amount
                    
                    costs_df = pd.DataFrame(list(costs.items()), columns=['النوع', 'المبلغ'])
                    costs_df = costs_df[costs_df['المبلغ'] > 0]
                    
                    fig_costs = px.pie(
                        costs_df,
                        values='المبلغ',
                        names='النوع',
                        title='توزيع التكاليف والرسوم'
                    )
                    st.plotly_chart(fig_costs, use_container_width=True)
                
                with col2:
                    # Price breakdown bar chart
                    price_elements = {
                        'COGS': breakdown['cogs'],
                        'الرسوم': breakdown['total_costs_fees'] - breakdown['cogs'] - breakdown['shipping_fee'] - breakdown['preparation_fee'],
                        'الربح': breakdown['profit']
                    }
                    price_df = pd.DataFrame(list(price_elements.items()), columns=['العنصر', 'المبلغ'])
                    
                    fig_price = px.bar(
                        price_df,
                        x='العنصر',
                        y='المبلغ',
                        title='تكوين السعر',
                        text='المبلغ',
                        color='العنصر',
                        color_discrete_map={'COGS': '#1f77b4', 'الرسوم': '#ff7f0e', 'الربح': '#2ca02c'}
                    )
                    fig_price.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                    st.plotly_chart(fig_price, use_container_width=True)
                
                st.markdown("---")
                
                # Section 6: Save Pricing
                st.subheader("💾 6. حفظ التسعير")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.info("احفظ هذا التسعير في جدول سجل الأسعار للرجوع إليه لاحقاً")
                    st.markdown(
                        """
                        #### كيفية استخدام سجل الأسعار
                        1. احسب التسعير المطلوب
                        2. اضغط على **💾 حفظ التسعير**
                        3. نزّل السجل بصيغة CSV للاحتفاظ به أو مشاركته
                        """
                    )
                
                with col2:
                    if st.button("💾 حفظ التسعير", type="primary", use_container_width=True, key="save_pricing_btn"):
                        with st.spinner("جاري حفظ التسعير..."):
                            try:
                                import os
                                import datetime
                                
                                # Ensure data directory exists
                                os.makedirs('data', exist_ok=True)
                                
                                # Get product/package name
                                item_name = sku_to_name.get(selected_sku_option, sku_input.strip())
                                
                                # Create pricing record
                                pricing_record = {
                                    'التاريخ': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'اسم المنتج/البكج': item_name,
                                    'SKU': sku_input.strip(),
                                    'النوع': item_type,
                                    'المنصة': selected_channel,
                                    'التكلفة': cogs,
                                    'سعر البيع': breakdown['sale_price'],
                                    'الربح': breakdown['profit'],
                                    'هامش الربح %': breakdown['margin_pct']*100,
                                    'رسوم الشحن': breakdown['shipping_fee'],
                                    'رسوم التحضير': breakdown['preparation_fee'],
                                    'رسوم إدارية': breakdown['admin_fee'],
                                    'رسوم تسويق': breakdown['marketing_fee'],
                                    'رسوم المنصة': breakdown['platform_fee'],
                                    'رسوم الدفع': breakdown['payment_fee'],
                                    'نسبة الخصم': discount_pct,
                                    'السعر النهائي للعميل': breakdown['price_after_discount'],
                                    'صافي السعر': breakdown['net_price'],
                                    'إجمالي التكاليف': breakdown['total_costs_fees'],
                                    'نقطة التعادل': breakdown['breakeven_price']
                                }
                                
                                # Load or create pricing history file
                                history_file = 'data/pricing_history.csv'
                                
                                if os.path.exists(history_file):
                                    history_df = pd.read_csv(history_file, encoding='utf-8-sig')
                                    history_df = pd.concat([history_df, pd.DataFrame([pricing_record])], ignore_index=True)
                                else:
                                    history_df = pd.DataFrame([pricing_record])
                                
                                # Save to CSV
                                history_df.to_csv(history_file, index=False, encoding='utf-8-sig')
                                st.success(f"✅ تم حفظ التسعير بنجاح! إجمالي السجلات: {len(history_df)}")
                                st.balloons()
                                
                                # Display summary table with key columns
                                st.markdown("---")
                                st.subheader("📋 السجلات المحفوظة")
                                
                                # Prepare display dataframe with main columns
                                display_df = history_df[['التاريخ', 'اسم المنتج/البكج', 'SKU', 'المنصة', 'التكلفة', 'سعر البيع', 'الربح', 'هامش الربح %']].copy()
                                
                                # Format the display
                                display_df = display_df.tail(20).iloc[::-1]  # Show last 20 records, newest first
                                
                                st.dataframe(
                                    display_df.style.format({
                                        'التكلفة': '{:.2f} SAR',
                                        'سعر البيع': '{:.2f} SAR',
                                        'الربح': '{:.2f} SAR',
                                        'هامش الربح %': '{:.2f}%'
                                    }),
                                    use_container_width=True,
                                    hide_index=True
                                )
                                
                                # Offer download of full CSV
                                csv_bytes = history_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                                st.download_button(
                                    "📥 تنزيل السجل الكامل (CSV)",
                                    data=csv_bytes,
                                    file_name="pricing_history.csv",
                                    mime="text/csv",
                                    use_container_width=True,
                                    key="download_history_btn"
                                )
                                
                            except Exception as e:
                                st.error(f"خطأ في حفظ التسعير: {e}")
                                import traceback
                                st.code(traceback.format_exc())
                
                # Display saved pricing records if file exists
                st.markdown("---")
                history_file = 'data/pricing_history.csv'
                if os.path.exists(history_file):
                    try:
                        history_df = pd.read_csv(history_file, encoding='utf-8-sig')
                        if len(history_df) > 0:
                            st.subheader("📋 السجلات المحفوظة")
                            
                            # Prepare display dataframe with main columns
                            display_cols = ['التاريخ', 'اسم المنتج/البكج', 'SKU', 'المنصة', 'التكلفة', 'سعر البيع', 'الربح', 'هامش الربح %']
                            display_df = history_df[display_cols].copy()
                            
                            # Format the display - show last 20 records, newest first
                            display_df = display_df.tail(20).iloc[::-1]
                            
                            st.dataframe(
                                display_df.style.format({
                                    'التكلفة': '{:.2f} SAR',
                                    'سعر البيع': '{:.2f} SAR',
                                    'الربح': '{:.2f} SAR',
                                    'هامش الربح %': '{:.2f}%'
                                }),
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Offer download
                            csv_bytes = history_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                            st.download_button(
                                "📥 تنزيل السجل الكامل (CSV)",
                                data=csv_bytes,
                                file_name="pricing_history.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="download_history_permanent_btn"
                            )
                    except Exception as e:
                        st.warning(f"تعذر تحميل سجل الأسعار: {e}")
                
                # حفظ بيانات العملية في session_state لاستخدامها في تبويب التحليل
                st.session_state["last_pricing_breakdown"] = breakdown
                st.session_state["last_pricing_meta"] = {
                    "sku": sku_input.strip(),
                    "sku_type": item_type,
                    "platform": selected_channel,
                    "base_price": price_with_vat,
                    "discount_pct": discount_pct,
                    "cogs": cogs,
                }
            
            else:
                st.error("يجب إدخال جميع البيانات المطلوبة بشكل صحيح")

# Page: Profit Margins Analysis
elif st.session_state.page == 'profit_margins':
    st.header("📊 تحليل هوامش الربح")
    st.markdown("احسب أسعار البيع لجميع المنتجات والبكجات بناءً على هامش ربح ونسبة خصم محددة")
    st.markdown("---")
    
    # Load channels
    channels_file = 'data/channels.json'
    channels_data = load_channels(channels_file)
    if not channels_data:
        st.warning("لا توجد قنوات محفوظة. يرجى إضافة قناة من صفحة الإعدادات أولاً.")
        st.stop()
    
    # Section 1: Configuration
    st.subheader("⚙️ 1. الإعدادات العامة")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_channel = st.selectbox(
            "اختر القناة / المنصة",
            options=list(channels_data.keys()),
            key="pm_channel"
        )
    
    with col2:
        target_margin_pct = st.number_input(
            "هامش الربح المستهدف (%)",
            min_value=0.0,
            max_value=100.0,
            value=15.0,
            step=1.0,
            key="pm_margin"
        )
    
    with col3:
        discount_pct = st.number_input(
            "نسبة الخصم (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            key="pm_discount"
        )
    
    # Convert inputs
    target_margin = target_margin_pct / 100
    discount_rate = discount_pct / 100
    
    # Get channel data
    channel = channels_data[selected_channel]
    
    st.markdown("---")
    
    # Section 2: Calculate Prices
    if st.button("🔄 احسب أسعار البيع لجميع المنتجات", use_container_width=True, type="primary"):
        st.subheader("📊 2. نتائج التسعير")
        
        # Helper function to calculate COGS
        def calculate_component_cost(sku, component_type):
            """Calculate the cost of a component (material, product, or package)"""
            if component_type == 'material' and sku in materials:
                return materials[sku].cost_per_unit
            elif component_type == 'product' and sku in product_recipes:
                # Sum all materials in this product
                total = 0
                for material_code, mat_qty in product_recipes[sku].items():
                    if material_code in materials:
                        total += materials[material_code].cost_per_unit * mat_qty
                return total
            elif component_type == 'package' and sku in package_compositions:
                # Sum all components in this package
                total = 0
                for comp_sku, comp_qty in package_compositions[sku].items():
                    # Try each type
                    if comp_sku in materials:
                        total += materials[comp_sku].cost_per_unit * comp_qty
                    elif comp_sku in product_recipes:
                        comp_cost = calculate_component_cost(comp_sku, 'product')
                        total += comp_cost * comp_qty
                    elif comp_sku in package_compositions:
                        comp_cost = calculate_component_cost(comp_sku, 'package')
                        total += comp_cost * comp_qty
                return total
            return 0
        
        results = []
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Combine all items (products + packages)
        all_items = []
        
        # Add products
        for idx, row in products_summary.iterrows():
            sku = row['Product_SKU']
            all_items.append({
                'sku': sku,
                'type': 'منتج',
                'cogs': calculate_component_cost(sku, 'product')
            })
        
        # Add packages
        for idx, row in packages_summary.iterrows():
            sku = row['Package_SKU']
            all_items.append({
                'sku': sku,
                'type': 'بكج',
                'cogs': calculate_component_cost(sku, 'package')
            })
        
        total_items = len(all_items)
        
        # Calculate for each item
        for idx, item in enumerate(all_items):
            status_text.text(f"جاري معالجة {item['sku']}...")
            
            try:
                # Calculate required price for target margin
                from pricing_app.advanced_pricing import calculate_price_breakdown
                
                # We need to find the price that gives us the target margin
                # Using iterative approach
                cogs = item['cogs']
                
                # Get channel fees
                shipping = channel.shipping_fixed
                preparation = channel.preparation_fee
                admin_pct = channel.opex_pct
                marketing_pct = channel.marketing_pct
                platform_pct = channel.platform_pct
                payment_pct = channel.payment_pct
                vat_rate = channel.vat_rate
                
                # Calculate total percentage fees
                total_pct = admin_pct + marketing_pct + platform_pct + payment_pct
                
                # Fixed costs
                fixed_costs = cogs + shipping + preparation
                
                # Calculate required net price for target margin
                # net_price * (1 - total_pct) - fixed_costs = net_price * target_margin
                # net_price * (1 - total_pct - target_margin) = fixed_costs
                # net_price = fixed_costs / (1 - total_pct - target_margin)
                
                denominator = 1 - total_pct - target_margin
                
                if denominator <= 0:
                    # Margin not achievable
                    results.append({
                        'SKU': item['sku'],
                        'النوع': item['type'],
                        'التكلفة': cogs,
                        'رسوم الشحن': '-',
                        'رسوم التحضير': '-',
                        'رسوم إدارية': '-',
                        'رسوم تسويق': '-',
                        'رسوم المنصة': '-',
                        'رسوم الدفع': '-',
                        'إجمالي الرسوم': '-',
                        'سعر البيع قبل الخصم': 'غير قابل للتحقيق',
                        'السعر النهائي للعميل': 'غير قابل للتحقيق',
                        'الربح': 'غير قابل للتحقيق',
                        'هامش الربح': 'غير قابل للتحقيق'
                    })
                else:
                    # Calculate net price
                    net_price = fixed_costs / denominator
                    
                    # Calculate sale price with VAT
                    price_with_vat_before_discount = net_price * (1 + vat_rate)
                    
                    # Calculate price after discount
                    if discount_rate > 0:
                        price_with_vat = price_with_vat_before_discount / (1 - discount_rate)
                    else:
                        price_with_vat = price_with_vat_before_discount
                    
                    # Prepare channel_fees dict for breakdown calculation
                    channel_fees_dict = {
                        'opex_pct': admin_pct,
                        'marketing_pct': marketing_pct,
                        'platform_pct': platform_pct,
                        'payment_pct': payment_pct,
                        'vat_rate': vat_rate
                    }
                    
                    # Verify by calculating breakdown
                    breakdown = calculate_price_breakdown(
                        cogs=cogs,
                        channel_fees=channel_fees_dict,
                        shipping=shipping,
                        preparation=preparation,
                        discount_rate=discount_rate,
                        vat_rate=vat_rate,
                        price_with_vat=price_with_vat
                    )
                    
                    results.append({
                        'SKU': item['sku'],
                        'النوع': item['type'],
                        'التكلفة': f"{cogs:.2f}",
                        'رسوم الشحن': f"{breakdown['shipping_fee']:.2f}",
                        'رسوم التحضير': f"{breakdown['preparation_fee']:.2f}",
                        'رسوم إدارية': f"{breakdown['admin_fee']:.2f}",
                        'رسوم تسويق': f"{breakdown['marketing_fee']:.2f}",
                        'رسوم المنصة': f"{breakdown['platform_fee']:.2f}",
                        'رسوم الدفع': f"{breakdown['payment_fee']:.2f}",
                        'إجمالي الرسوم': f"{breakdown['total_costs_fees'] - cogs:.2f}",
                        'سعر البيع قبل الخصم': f"{breakdown['sale_price']:.2f}",
                        'السعر النهائي للعميل': f"{breakdown['price_after_discount']:.2f}",
                        'الربح': f"{breakdown['profit']:.2f}",
                        'هامش الربح': f"{breakdown['margin_pct']*100:.1f}%"
                    })
                    
            except Exception as e:
                results.append({
                    'SKU': item['sku'],
                    'النوع': item['type'],
                    'التكلفة': f"{cogs:.2f}",
                    'رسوم الشحن': '-',
                    'رسوم التحضير': '-',
                    'رسوم إدارية': '-',
                    'رسوم تسويق': '-',
                    'رسوم المنصة': '-',
                    'رسوم الدفع': '-',
                    'إجمالي الرسوم': '-',
                    'سعر البيع قبل الخصم': f'خطأ: {str(e)}',
                    'السعر النهائي للعميل': '-',
                    'الربح': '-',
                    'هامش الربح': '-'
                })
            
            # Update progress
            progress_bar.progress((idx + 1) / total_items)
        
        # Clear progress indicators
        status_text.empty()
        progress_bar.empty()
        
        # Display results
        if results:
            df_results = pd.DataFrame(results)
            
            # Summary metrics
            st.markdown("### 📈 ملخص النتائج")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("إجمالي المنتجات", len(df_results))
            
            with col2:
                successful = len([r for r in results if 'غير قابل' not in str(r['سعر البيع قبل الخصم'])])
                st.metric("تم التسعير بنجاح", successful)
            
            with col3:
                st.metric("هامش الربح المستهدف", f"{target_margin_pct:.0f}%")
            
            with col4:
                st.metric("نسبة الخصم", f"{discount_pct:.0f}%")
            
            st.markdown("---")
            
            # Display table
            st.markdown("### 📋 جدول التسعير الكامل")
            st.dataframe(
                df_results,
                use_container_width=True,
                height=600
            )
            
            # Download button
            csv = df_results.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 تحميل النتائج (CSV)",
                data=csv,
                file_name=f"pricing_results_{selected_channel}_{target_margin_pct}pct.csv",
                mime="text/csv"
            )
        else:
            st.warning("لا توجد نتائج للعرض")


# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>محرك تسعير صفوة - Safwa Pricing Engine v1.0</p>
    <p>نظام محاسبي متقدم لحساب COGS والتسعير الامثل</p>
</div>
""", unsafe_allow_html=True)

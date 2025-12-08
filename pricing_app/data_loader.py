import pandas as pd
from typing import Dict, Tuple
from .models import Material, Product, Package

def load_materials(filepath: str) -> Dict[str, Material]:
    """Load raw materials from CSV"""
    df = pd.read_csv(filepath)
    
    # Normalize column names
    df.columns = df.columns.str.strip()
    
    materials = {}
    for _, row in df.iterrows():
        try:
            sku = str(row.get('Material_SKU', '')).strip()
            name = str(row.get('Material_Name', '')).strip()
            category = str(row.get('Category', 'Unknown')).strip()
            unit = str(row.get('Purchase_UoM', 'Unit')).strip()
            cost = float(row.get('Cost_Price', 0))
            
            if sku and cost > 0:
                mat = Material(
                    material_sku=sku,
                    material_name=name or sku,
                    category=category,
                    unit=unit,
                    cost_per_unit=cost
                )
                materials[mat.material_sku] = mat
        except Exception as e:
            print(f"Warning: Could not load material row: {e}")
            continue
    
    return materials

def load_products(filepath: str) -> Tuple[pd.DataFrame, Dict]:
    """Load products BOM from CSV - returns DataFrame and product recipe dictionary"""
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    
    # Create a dictionary mapping Product_SKU to list of materials
    product_recipes = {}
    
    for _, row in df.iterrows():
        product_sku = str(row.get('Product_SKU', '')).strip()
        material_code = str(row.get('Material_Code', '')).strip()
        quantity = float(row.get('Quantity', 0))
        
        if product_sku and material_code:
            if product_sku not in product_recipes:
                product_recipes[product_sku] = {}
            product_recipes[product_sku][material_code] = quantity
    
    # Create a summary DataFrame with unique products
    products_summary = df.groupby('Product_SKU').agg({
        'Product_Name': 'first'
    }).reset_index()
    
    return df, product_recipes, products_summary

def load_packages(filepath: str) -> Tuple[pd.DataFrame, Dict]:
    """Load packages components from CSV - returns DataFrame and package composition dictionary.
    البكج قد يحتوي على:
    - مواد خام مباشرة (يتم تخزينها مع بادئة MAT_)
    - منتجات (يتم تخزينها مع بادئة PRD_)
    - بكجات أخرى (يتم تخزينها مع بادئة PKG_)
    """
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    
    # Create a dictionary mapping Package_SKU to list of components
    # Key format: "MAT_<sku>" for materials, "PRD_<sku>" for products, "PKG_<sku>" for packages
    package_compositions = {}
    
    for _, row in df.iterrows():
        package_sku = str(row.get('Package_SKU', '')).strip()
        component_sku = str(row.get('Product_SKU', '')).strip()  # Can be product, package, or material SKU
        quantity = float(row.get('Quantity', 0))
        
        if package_sku and component_sku:
            if package_sku not in package_compositions:
                package_compositions[package_sku] = {}
            # Store with the component SKU as-is (caller will determine type)
            package_compositions[package_sku][component_sku] = quantity
    
    # Create a summary DataFrame with unique packages
    packages_summary = df.groupby('Package_SKU').agg({
        'Package_Name': 'first'
    }).reset_index()
    
    return df, package_compositions, packages_summary

def load_cost_data(data_dir: str) -> Tuple[Dict, Dict, pd.DataFrame, Dict, pd.DataFrame]:
    """Load all cost-related data"""
    import os
    
    materials = load_materials(os.path.join(data_dir, 'raw_materials_template.csv'))
    
    products_df, product_recipes, products_summary = load_products(
        os.path.join(data_dir, 'products_template.csv')
    )
    
    packages_df, package_compositions, packages_summary = load_packages(
        os.path.join(data_dir, 'packages_template.csv')
    )
    
    return materials, product_recipes, products_summary, package_compositions, packages_summary
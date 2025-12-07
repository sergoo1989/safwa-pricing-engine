import pandas as pd
from typing import Dict, Tuple
from .models import Material, Product, Package

def load_materials(filepath: str) -> Dict[str, Material]:
    """Load raw materials from CSV"""
    df = pd.read_csv(filepath)
    materials = {}
    for _, row in df.iterrows():
        mat = Material(
            material_sku=row['Material_SKU'],
            material_name=row['Material_Name'],
            category=row['Category'],
            unit=row['Unit'],
            cost_per_unit=float(row['Cost_Price'])
        )
        materials[mat.material_sku] = mat
    return materials

def load_products(filepath: str) -> pd.DataFrame:
    """Load products BOM from CSV"""
    return pd.read_csv(filepath)

def load_packages(filepath: str) -> pd.DataFrame:
    """Load packages components from CSV"""
    return pd.read_csv(filepath)

def load_cost_data(data_dir: str) -> Tuple[Dict, pd.DataFrame, pd.DataFrame]:
    """Load all cost-related data"""
    import os
    materials = load_materials(os.path.join(data_dir, 'raw_materials_template.csv'))
    products_df = load_products(os.path.join(data_dir, 'products_template.csv'))
    packages_df = load_packages(os.path.join(data_dir, 'packages_template.csv'))
    return materials, products_df, packages_df
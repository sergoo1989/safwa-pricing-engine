import pandas as pd
from typing import Dict

def compute_product_costs(products_df: pd.DataFrame, materials: Dict) -> Dict[str, float]:
    """
    Compute COGS for each product based on BOM
    BOM format: MAT001:0.5;MAT002:1.0
    """
    product_costs = {}
    
    for _, row in products_df.iterrows():
        sku = row['Product_SKU']
        bom = row['BOM']
        
        total_cost = 0.0
        for component in bom.split(';'):
            mat_sku, qty = component.split(':')
            qty = float(qty)
            if mat_sku in materials:
                total_cost += materials[mat_sku].cost_per_unit * qty
        
        product_costs[sku] = total_cost
    
    return product_costs

def compute_package_costs(
    packages_df: pd.DataFrame,
    product_costs: Dict[str, float],
    materials: Dict,
    max_depth: int = 10
) -> Dict[str, float]:
    """
    Compute COGS for packages (supports nested packages)
    Components format: PROD001:2:product;MAT010:1:material;PKG001:1:package
    """
    package_costs = {}
    unresolved = set(packages_df['Package_SKU'].tolist())
    
    # Iterative resolution for nested packages
    for _ in range(max_depth):
        if not unresolved:
            break
            
        resolved_this_round = []
        
        for _, row in packages_df.iterrows():
            pkg_sku = row['Package_SKU']
            if pkg_sku not in unresolved:
                continue
                
            components = row['Components']
            total_cost = 0.0
            can_resolve = True
            
            for comp in components.split(';'):
                parts = comp.split(':')
                comp_sku = parts[0]
                qty = float(parts[1])
                comp_type = parts[2]
                
                if comp_type == 'product':
                    if comp_sku in product_costs:
                        total_cost += product_costs[comp_sku] * qty
                    else:
                        can_resolve = False
                        break
                elif comp_type == 'material':
                    if comp_sku in materials:
                        total_cost += materials[comp_sku].cost_per_unit * qty
                    else:
                        can_resolve = False
                        break
                elif comp_type == 'package':
                    if comp_sku in package_costs:
                        total_cost += package_costs[comp_sku] * qty
                    else:
                        can_resolve = False
                        break
            
            if can_resolve:
                package_costs[pkg_sku] = total_cost
                resolved_this_round.append(pkg_sku)
        
        for sku in resolved_this_round:
            unresolved.remove(sku)
    
    return package_costs
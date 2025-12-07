import pandas as pd
from typing import Dict

def extract_channel_fees_from_pl(
    pl_filepath: str,
    channel_name: str = "سلة"
) -> Dict[str, float]:
    """
    Extract marketing_pct and opex_pct from PL file
    
    Returns dict with 'marketing_pct' and 'opex_pct'
    """
    df = pd.read_csv(pl_filepath)
    
    # Filter by channel
    channel_df = df[df['Cost_Center'] == channel_name].copy()
    
    # Calculate total revenue
    revenue_df = channel_df[channel_df['Account_Level_2'] == 'Revenue']
    total_revenue = revenue_df['net_amount'].sum()
    
    if total_revenue == 0:
        return {'marketing_pct': 0.28, 'opex_pct': 0.04}  # defaults
    
    # Calculate marketing expenses
    marketing_df = channel_df[channel_df['Account_Level_2'] == 'Marketing Expenses']
    total_marketing = abs(marketing_df['net_amount'].sum())
    marketing_pct = total_marketing / total_revenue
    
    # Calculate operating expenses
    opex_df = channel_df[channel_df['Account_Level_2'] == 'Operating Expenses']
    total_opex = abs(opex_df['net_amount'].sum())
    opex_pct = total_opex / total_revenue
    
    return {
        'marketing_pct': marketing_pct,
        'opex_pct': opex_pct
    }
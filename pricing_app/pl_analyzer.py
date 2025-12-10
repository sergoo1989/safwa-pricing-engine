"""
P&L Analyzer - محلل الأرباح والخسائر
يحلل بيانات P&L ويستخرج نسب التكاليف الفعلية لاستخدامها في التسعير
"""

import pandas as pd
import os
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ChannelPLAnalysis:
    """تحليل P&L لقناة بيع معينة"""
    
    channel_name: str
    
    # Revenue
    total_revenue: float
    revenue_share_pct: float  # نسبة هذه القناة من إجمالي الإيرادات
    
    # Costs
    total_cogs: float
    total_expenses: float
    total_marketing: float
    total_platform_fees: float
    total_admin_expenses: float
    total_other_opex: float
    
    # Calculated Percentages (من الإيراد)
    cogs_pct: float
    marketing_pct: float
    platform_pct: float
    admin_pct: float
    other_opex_pct: float
    total_expenses_pct: float
    
    # Profitability
    gross_profit: float
    net_profit: float
    gross_margin_pct: float
    net_margin_pct: float
    
    # Share of total expenses
    marketing_expense_share_pct: float  # نسبة هذه القناة من إجمالي مصاريف التسويق
    admin_expense_share_pct: float  # نسبة هذه القناة من إجمالي المصاريف الإدارية


class PLAnalyzer:
    """محلل بيانات الأرباح والخسائر"""
    
    def __init__(self, pl_file_path: str = "data/profit_loss.csv"):
        self.pl_file_path = pl_file_path
        self.df = None
        self.amount_col = None
        
    def load_data(self) -> bool:
        """تحميل ملف P&L"""
        if not os.path.exists(self.pl_file_path):
            return False
        
        try:
            self.df = pd.read_csv(self.pl_file_path, encoding="utf-8-sig")
            self.df.columns = self.df.columns.str.strip()
            
            # Detect amount column
            self.amount_col = 'net_amount' if 'net_amount' in self.df.columns else ' net_amount '
            
            # Clean amount column
            self.df[self.amount_col] = self.df[self.amount_col].astype(str).str.replace(',', '').astype(float)
            
            return True
        except Exception as e:
            print(f"Error loading P&L file: {e}")
            return False
    
    def get_total_revenue(self, year: Optional[str] = None) -> float:
        """حساب إجمالي الإيرادات"""
        df = self.df.copy()
        
        if year:
            df = df[df['Years'] == year]
        
        income_df = df[df['Account Level 1'] == 'income']
        return income_df[self.amount_col].sum()
    
    def get_channel_analysis(self, channel_name: str, year: Optional[str] = None) -> Optional[ChannelPLAnalysis]:
        """تحليل شامل لقناة بيع معينة"""
        
        if self.df is None:
            if not self.load_data():
                return None
        
        df = self.df.copy()
        
        # Filter by year if specified
        if year:
            df = df[df['Years'] == year]
        
        # Filter by channel
        if 'Cost Center' not in df.columns:
            return None
        
        channel_df = df[df['Cost Center'] == channel_name].copy()
        
        if channel_df.empty:
            return None
        
        # Calculate revenue
        income_df = channel_df[channel_df['Account Level 1'] == 'income']
        total_revenue = income_df[self.amount_col].sum()
        
        if total_revenue == 0:
            return None
        
        # Calculate total revenue across all channels
        total_revenue_all = self.get_total_revenue(year)
        revenue_share_pct = (total_revenue / total_revenue_all * 100) if total_revenue_all > 0 else 0
        
        # Calculate COGS
        cogs_df = channel_df[channel_df['Account Level 1'] == 'cost_of_goods_sold']
        total_cogs = abs(cogs_df[self.amount_col].sum())
        
        # Calculate expenses by type
        expense_df = channel_df[channel_df['Account Level 1'] == 'expense']
        
        # Marketing expenses
        marketing_df = expense_df[expense_df['Account Level 2'].str.contains('marketing|تسويق|اعلان|إعلان', case=False, na=False)]
        total_marketing = abs(marketing_df[self.amount_col].sum())
        
        # Platform/Commission fees
        platform_df = expense_df[expense_df['Account Level 2'].str.contains('platform|commission|عمولة|منصة', case=False, na=False)]
        total_platform_fees = abs(platform_df[self.amount_col].sum())
        
        # Admin expenses
        admin_df = expense_df[expense_df['Account Level 2'].str.contains('admin|إدار|رواتب|مكتب|إيجار|كهرباء', case=False, na=False)]
        total_admin_expenses = abs(admin_df[self.amount_col].sum())
        
        # Other operating expenses
        accounted_expenses = total_marketing + total_platform_fees + total_admin_expenses
        total_expenses = abs(expense_df[self.amount_col].sum())
        total_other_opex = total_expenses - accounted_expenses
        
        # Calculate percentages from revenue
        cogs_pct = (total_cogs / total_revenue) if total_revenue > 0 else 0
        marketing_pct = (total_marketing / total_revenue) if total_revenue > 0 else 0
        platform_pct = (total_platform_fees / total_revenue) if total_revenue > 0 else 0
        admin_pct = (total_admin_expenses / total_revenue) if total_revenue > 0 else 0
        other_opex_pct = (total_other_opex / total_revenue) if total_revenue > 0 else 0
        total_expenses_pct = (total_expenses / total_revenue) if total_revenue > 0 else 0
        
        # Calculate profitability
        gross_profit = total_revenue - total_cogs
        net_profit = gross_profit - total_expenses
        gross_margin_pct = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        net_margin_pct = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        # Calculate share of total expenses
        total_marketing_all = abs(df[df['Account Level 1'] == 'expense'][df['Account Level 2'].str.contains('marketing|تسويق|اعلان|إعلان', case=False, na=False)][self.amount_col].sum())
        total_admin_all = abs(df[df['Account Level 1'] == 'expense'][df['Account Level 2'].str.contains('admin|إدار|رواتب|مكتب|إيجار|كهرباء', case=False, na=False)][self.amount_col].sum())
        
        marketing_expense_share_pct = (total_marketing / total_marketing_all * 100) if total_marketing_all > 0 else 0
        admin_expense_share_pct = (total_admin_expenses / total_admin_all * 100) if total_admin_all > 0 else 0
        
        return ChannelPLAnalysis(
            channel_name=channel_name,
            total_revenue=total_revenue,
            revenue_share_pct=revenue_share_pct,
            total_cogs=total_cogs,
            total_expenses=total_expenses,
            total_marketing=total_marketing,
            total_platform_fees=total_platform_fees,
            total_admin_expenses=total_admin_expenses,
            total_other_opex=total_other_opex,
            cogs_pct=cogs_pct,
            marketing_pct=marketing_pct,
            platform_pct=platform_pct,
            admin_pct=admin_pct,
            other_opex_pct=other_opex_pct,
            total_expenses_pct=total_expenses_pct,
            gross_profit=gross_profit,
            net_profit=net_profit,
            gross_margin_pct=gross_margin_pct,
            net_margin_pct=net_margin_pct,
            marketing_expense_share_pct=marketing_expense_share_pct,
            admin_expense_share_pct=admin_expense_share_pct
        )
    
    def get_all_channels_analysis(self, year: Optional[str] = None) -> Dict[str, ChannelPLAnalysis]:
        """تحليل جميع القنوات"""
        
        if self.df is None:
            if not self.load_data():
                return {}
        
        df = self.df.copy()
        
        if year:
            df = df[df['Years'] == year]
        
        if 'Cost Center' not in df.columns:
            return {}
        
        channels = df['Cost Center'].dropna().unique()
        
        results = {}
        for channel in channels:
            analysis = self.get_channel_analysis(channel, year)
            if analysis:
                results[channel] = analysis
        
        return results
    
    def get_recommended_fees_for_channel(self, channel_name: str, year: Optional[str] = None) -> Optional[Dict[str, float]]:
        """
        استخراج النسب الموصى بها للتسعير بناءً على البيانات الفعلية
        
        Returns:
            Dict with: platform_pct, marketing_pct, opex_pct (admin + other)
        """
        
        analysis = self.get_channel_analysis(channel_name, year)
        
        if not analysis:
            return None
        
        # Use actual percentages from P&L
        return {
            'platform_pct': analysis.platform_pct,
            'marketing_pct': analysis.marketing_pct,
            'opex_pct': analysis.admin_pct + analysis.other_opex_pct,  # Combined admin + other opex
            'admin_pct': analysis.admin_pct,  # Separate admin for transparency
            'other_opex_pct': analysis.other_opex_pct,
        }
    
    def get_overall_expense_breakdown(self, year: Optional[str] = None) -> Dict[str, float]:
        """
        نصيب المصاريف الإدارية من إجمالي الإيراد (عبر جميع القنوات)
        """
        
        if self.df is None:
            if not self.load_data():
                return {}
        
        df = self.df.copy()
        
        if year:
            df = df[df['Years'] == year]
        
        # Total revenue
        total_revenue = df[df['Account Level 1'] == 'income'][self.amount_col].sum()
        
        if total_revenue == 0:
            return {}
        
        # Total expenses by category
        expense_df = df[df['Account Level 1'] == 'expense']
        
        marketing_total = abs(expense_df[expense_df['Account Level 2'].str.contains('marketing|تسويق|اعلان|إعلان', case=False, na=False)][self.amount_col].sum())
        platform_total = abs(expense_df[expense_df['Account Level 2'].str.contains('platform|commission|عمولة|منصة', case=False, na=False)][self.amount_col].sum())
        admin_total = abs(expense_df[expense_df['Account Level 2'].str.contains('admin|إدار|رواتب|مكتب|إيجار|كهرباء', case=False, na=False)][self.amount_col].sum())
        other_total = abs(expense_df[self.amount_col].sum()) - (marketing_total + platform_total + admin_total)
        
        return {
            'total_revenue': total_revenue,
            'marketing_total': marketing_total,
            'marketing_pct': (marketing_total / total_revenue * 100),
            'platform_total': platform_total,
            'platform_pct': (platform_total / total_revenue * 100),
            'admin_total': admin_total,
            'admin_pct': (admin_total / total_revenue * 100),
            'other_opex_total': other_total,
            'other_opex_pct': (other_total / total_revenue * 100),
        }


def get_smart_channel_fees(channel_name: str, year: Optional[str] = None, fallback_defaults: bool = True) -> Dict[str, float]:
    """
    دالة ذكية لاستخراج رسوم القناة من البيانات الفعلية
    
    Args:
        channel_name: اسم القناة
        year: السنة (اختياري)
        fallback_defaults: استخدام قيم افتراضية إذا لم تتوفر بيانات
    
    Returns:
        Dict with platform_pct, marketing_pct, opex_pct
    """
    
    analyzer = PLAnalyzer()
    fees = analyzer.get_recommended_fees_for_channel(channel_name, year)
    
    if fees:
        return fees
    
    # Fallback to defaults if no data available
    if fallback_defaults:
        return {
            'platform_pct': 0.03,
            'marketing_pct': 0.28,
            'opex_pct': 0.04,
            'admin_pct': 0.02,
            'other_opex_pct': 0.02,
        }
    
    return None

"""
مكونات واجهة المستخدم الاحترافية
Professional UI Components
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any
import pandas as pd


class UIComponents:
    """مكونات واجهة المستخدم المتقدمة"""
    
    @staticmethod
    def render_metric_card(title: str, value: str, delta: Optional[str] = None, 
                          icon: str = "📊", color: str = "#1E88E5"):
        """عرض بطاقة مقياس احترافية"""
        delta_html = f'<p style="color: #666; font-size: 0.9em; margin: 5px 0 0 0;">{delta}</p>' if delta else ''
        
        card_html = f"""
        <div style="
            background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
            border-left: 4px solid {color};
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2em;">{icon}</span>
                <div style="flex: 1;">
                    <p style="color: #666; font-size: 0.85em; margin: 0; font-weight: 500;">{title}</p>
                    <p style="color: #1a1a1a; font-size: 1.8em; margin: 5px 0 0 0; font-weight: bold;">{value}</p>
                    {delta_html}
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
    
    @staticmethod
    def render_info_box(message: str, box_type: str = "info"):
        """عرض صندوق معلومات"""
        colors = {
            "info": ("#29B6F6", "#E1F5FE"),
            "success": ("#66BB6A", "#E8F5E9"),
            "warning": ("#FFA726", "#FFF3E0"),
            "error": ("#EF5350", "#FFEBEE")
        }
        
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        
        border_color, bg_color = colors.get(box_type, colors["info"])
        icon = icons.get(box_type, "ℹ️")
        
        box_html = f"""
        <div style="
            background-color: {bg_color};
            border-left: 4px solid {border_color};
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        ">
            <p style="margin: 0; color: #333;">
                <span style="font-size: 1.2em; margin-right: 10px;">{icon}</span>
                {message}
            </p>
        </div>
        """
        st.markdown(box_html, unsafe_allow_html=True)
    
    @staticmethod
    def render_progress_bar(progress: float, label: str = ""):
        """عرض شريط تقدم"""
        color = "#66BB6A" if progress >= 0.7 else "#FFA726" if progress >= 0.4 else "#EF5350"
        
        progress_html = f"""
        <div style="margin: 10px 0;">
            <p style="margin: 0 0 5px 0; color: #666; font-size: 0.9em;">{label}</p>
            <div style="
                background-color: #f0f0f0;
                border-radius: 10px;
                height: 20px;
                overflow: hidden;
            ">
                <div style="
                    background: linear-gradient(90deg, {color} 0%, {color}dd 100%);
                    height: 100%;
                    width: {progress * 100}%;
                    border-radius: 10px;
                    transition: width 0.3s ease;
                "></div>
            </div>
            <p style="margin: 5px 0 0 0; color: #666; font-size: 0.85em; text-align: right;">{progress * 100:.1f}%</p>
        </div>
        """
        st.markdown(progress_html, unsafe_allow_html=True)
    
    @staticmethod
    def render_section_header(title: str, subtitle: Optional[str] = None, icon: str = ""):
        """عرض عنوان قسم احترافي"""
        subtitle_html = f'<p style="color: #666; font-size: 1em; margin: 5px 0 0 0;">{subtitle}</p>' if subtitle else ''
        
        header_html = f"""
        <div style="margin: 30px 0 20px 0; padding-bottom: 15px; border-bottom: 2px solid #1E88E5;">
            <h2 style="color: #1a1a1a; margin: 0; display: flex; align-items: center; gap: 10px;">
                {f'<span style="font-size: 1.2em;">{icon}</span>' if icon else ''}
                {title}
            </h2>
            {subtitle_html}
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)


class ChartBuilder:
    """بناء الرسوم البيانية الاحترافية"""
    
    @staticmethod
    def create_gauge_chart(value: float, title: str, max_value: float = 1.0, 
                          thresholds: Dict[str, float] = None) -> go.Figure:
        """إنشاء مؤشر دائري"""
        if thresholds is None:
            thresholds = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title, 'font': {'size': 20}},
            delta={'reference': max_value * 100 * 0.5},
            gauge={
                'axis': {'range': [None, max_value * 100], 'ticksuffix': '%'},
                'bar': {'color': "#1E88E5"},
                'steps': [
                    {'range': [0, thresholds['low'] * 100], 'color': "#FFEBEE"},
                    {'range': [thresholds['low'] * 100, thresholds['medium'] * 100], 'color': "#FFF3E0"},
                    {'range': [thresholds['medium'] * 100, max_value * 100], 'color': "#E8F5E9"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': max_value * 100 * 0.9
                }
            }
        ))
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
        return fig
    
    @staticmethod
    def create_waterfall_chart(data: Dict[str, float], title: str) -> go.Figure:
        """إنشاء مخطط شلال (Waterfall)"""
        labels = list(data.keys())
        values = list(data.values())
        
        # Determine measure type
        measures = ["relative"] * len(labels)
        measures[-1] = "total"
        
        fig = go.Figure(go.Waterfall(
            name=title,
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#66BB6A"}},
            decreasing={"marker": {"color": "#EF5350"}},
            totals={"marker": {"color": "#1E88E5"}}
        ))
        
        fig.update_layout(
            title=title,
            showlegend=False,
            height=500,
            xaxis_tickangle=-45
        )
        
        return fig
    
    @staticmethod
    def create_heatmap(data: pd.DataFrame, x_col: str, y_col: str, 
                       value_col: str, title: str) -> go.Figure:
        """إنشاء خريطة حرارية"""
        pivot_table = data.pivot_table(values=value_col, index=y_col, columns=x_col, aggfunc='mean')
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=pivot_table.columns,
            y=pivot_table.index,
            colorscale='RdYlGn',
            text=pivot_table.values,
            texttemplate='%{text:.2f}',
            textfont={"size": 10},
            colorbar=dict(title=value_col)
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title=y_col,
            height=500
        )
        
        return fig
    
    @staticmethod
    def create_funnel_chart(data: Dict[str, float], title: str) -> go.Figure:
        """إنشاء مخطط قمع (Funnel)"""
        fig = go.Figure(go.Funnel(
            y=list(data.keys()),
            x=list(data.values()),
            textinfo="value+percent initial",
            marker={"color": ["#1E88E5", "#29B6F6", "#4FC3F7", "#81D4FA", "#B3E5FC"]}
        ))
        
        fig.update_layout(title=title, height=500)
        return fig
    
    @staticmethod
    def create_comparison_chart(categories: List[str], 
                               values1: List[float], 
                               values2: List[float],
                               label1: str,
                               label2: str,
                               title: str) -> go.Figure:
        """إنشاء مخطط مقارنة"""
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name=label1,
            x=categories,
            y=values1,
            marker_color='#1E88E5'
        ))
        
        fig.add_trace(go.Bar(
            name=label2,
            x=categories,
            y=values2,
            marker_color='#43A047'
        ))
        
        fig.update_layout(
            title=title,
            barmode='group',
            height=500,
            xaxis_tickangle=-45
        )
        
        return fig


class TableFormatter:
    """تنسيق الجداول الاحترافي"""
    
    @staticmethod
    def style_dataframe(df: pd.DataFrame, 
                       highlight_cols: Optional[List[str]] = None,
                       precision: int = 2) -> pd.DataFrame.style:
        """تطبيق تنسيق احترافي على DataFrame"""
        
        def highlight_positive(val):
            if isinstance(val, (int, float)):
                color = '#E8F5E9' if val > 0 else '#FFEBEE' if val < 0 else ''
                return f'background-color: {color}'
            return ''
        
        styled = df.style
        
        # Apply highlighting
        if highlight_cols:
            for col in highlight_cols:
                if col in df.columns:
                    styled = styled.applymap(highlight_positive, subset=[col])
        
        # Format numeric columns
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        format_dict = {col: f'{{:.{precision}f}}' for col in numeric_cols}
        styled = styled.format(format_dict)
        
        return styled

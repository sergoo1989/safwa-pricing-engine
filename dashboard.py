import streamlit as st
import pandas as pd
import plotly.express as px
from pricing_app import pricing_data, margin_analysis, salla_comparison, export_reports  # Assuming these modules exist

# Set the title of the dashboard
st.title("Pricing Engine Dashboard")

# Create tabs
tabs = ["Full Pricing Table", "Single SKU Pricing", "Raw Materials Analysis", "Margin Analysis", "Salla Comparison", "Export Reports"]
selected_tab = st.sidebar.selectbox("Select a tab", tabs)

if selected_tab == "Full Pricing Table":
    st.header("Full Pricing Table")
    data = pricing_data.load_full_pricing()  # Load data using your pricing_app module
    st.dataframe(data)

elif selected_tab == "Single SKU Pricing":
    st.header("Single SKU Pricing")
    sku = st.text_input("Enter SKU:")
    if sku:
        sku_data = pricing_data.get_sku_data(sku)  # Function to get SKU data
        if sku_data is not None:
            st.dataframe(sku_data)
        else:
            st.warning("SKU not found!")

elif selected_tab == "Raw Materials Analysis":
    st.header("Raw Materials Analysis")
    materials_data = pricing_data.load_raw_materials()  # Load raw materials data
    st.dataframe(materials_data)
    fig = px.pie(materials_data, names='Material', values='Cost')
    st.plotly_chart(fig)

elif selected_tab == "Margin Analysis":
    st.header("Margin Analysis")
    margin_data = margin_analysis.calculate_margin()  # Calculate margins using your pricing_app module
    st.dataframe(margin_data)
    fig = px.bar(margin_data, x='Product', y='Margin')
    st.plotly_chart(fig)

elif selected_tab == "Salla Comparison":
    st.header("Salla Comparison")
    comparison_data = salla_comparison.compare_prices()  # Compare prices on Salla
    st.dataframe(comparison_data)

elif selected_tab == "Export Reports":
    st.header("Export Reports")
    if st.button("Export Pricing Reports"):
        export_reports.generate_reports()  # Function to generate and download reports
        st.success("Reports have been generated and exported.")
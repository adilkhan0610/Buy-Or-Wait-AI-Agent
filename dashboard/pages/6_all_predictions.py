"""
All Predictions Page — Searchable Table & Official Output CSV Exporter.
"""

import streamlit as st
import pandas as pd
from dashboard.utils.data_loader import load_predictions_data, load_merged_data
from dashboard.utils.formatting import format_currency


def render_all_predictions_page():
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            All Predictions & Submission Export
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Complete evaluation dataset predictions matching the challenge schema contract.
        </p>
    </div>
    """, unsafe_allow_html=True)

    pred_df = load_predictions_data()
    merged_df = load_merged_data()

    if pred_df.empty:
        st.error("No predictions data loaded.")
        return

    # Filter Controls
    col_f1, col_f2, col_search = st.columns([1, 1, 2])
    
    with col_f1:
        status_options = ["All"] + sorted(pred_df["affordability_status"].unique().tolist())
        selected_status = st.selectbox("Affordability Status:", status_options, index=0)

    with col_f2:
        method_options = ["All"] + sorted(pred_df["recommended_payment_method"].unique().tolist())
        selected_method = st.selectbox("Payment Method:", method_options, index=0)

    with col_search:
        search_query = st.text_input("Search Request ID or Explanation:", placeholder="e.g. req_01, cash flow, installment...")

    # Apply filters
    filtered_df = pred_df.copy()
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["affordability_status"] == selected_status]
    if selected_method != "All":
        filtered_df = filtered_df[filtered_df["recommended_payment_method"] == selected_method]
    if search_query:
        query_lower = search_query.lower()
        filtered_df = filtered_df[
            filtered_df["request_id"].str.lower().str.contains(query_lower) |
            filtered_df["decision_explanation"].str.lower().str.contains(query_lower)
        ]

    # Export & Row count bar
    col_count, col_download = st.columns([3, 1])
    with col_count:
        st.markdown(f"<div style='margin-top: 8px; font-size: 14px; font-weight: 600; color: #475569;'>Showing {len(filtered_df)} of {len(pred_df)} records</div>", unsafe_allow_html=True)
    with col_download:
        csv_bytes = pred_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download output.csv",
            data=csv_bytes,
            file_name="output.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Interactive DataFrame
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "request_id": st.column_config.TextColumn("Request ID", width="small"),
            "amount_safe_to_pay": st.column_config.NumberColumn("Safe Today ($)", format="$%.2f", width="small"),
            "affordability_status": st.column_config.TextColumn("Affordability Status", width="medium"),
            "recommended_payment_method": st.column_config.TextColumn("Payment Method", width="small"),
            "payment_plan": st.column_config.TextColumn("Payment Plan", width="medium"),
            "earliest_date_for_full_payment": st.column_config.TextColumn("Earliest Full Date", width="small"),
            "spending_changes_needed": st.column_config.TextColumn("Spending Changes", width="medium"),
            "decision_explanation": st.column_config.TextColumn("Decision Explanation", width="large"),
        }
    )


if __name__ == "__main__" or True:
    render_all_predictions_page()


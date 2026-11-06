"""
Decision Explorer Page — Deep Dive into Individual Purchase Decisions.
"""

import streamlit as st
import pandas as pd
from dashboard.utils.data_loader import load_merged_data, load_profiles_data
from dashboard.utils.formatting import (
    format_currency,
    format_date,
    get_status_badge,
    get_method_badge,
    parse_payment_plan,
    parse_spending_changes
)
from dashboard.components.decision_cards import render_decision_hero, render_payment_plan_schedule


def render_decision_explorer_page():
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            Purchase Decision Explorer
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Inspect comprehensive decision rationale, plan mechanics, and evidence for any request.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_merged_data()
    if df.empty:
        st.error("No dataset available.")
        return

    # Filter Controls
    col_filter1, col_filter2 = st.columns([2, 1])
    with col_filter1:
        # Create user-friendly label for selectbox
        options = []
        for _, row in df.iterrows():
            amt = f"${row.get('requested_amount', 0):,.2f}"
            status = row.get('affordability_status', '')
            options.append(f"{row['request_id']} | {row.get('user_id', '')} | {status} ({amt})")
            
        selected_option = st.selectbox("Select Request to Inspect:", options=options, index=0)
        selected_req_id = selected_option.split(" | ")[0]

    with col_filter2:
        status_filter = st.selectbox(
            "Quick Filter by Status:",
            options=["All", "affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"],
            index=0
        )
        if status_filter != "All":
            filtered_df = df[df["affordability_status"] == status_filter]
            if not filtered_df.empty:
                if selected_req_id not in filtered_df["request_id"].values:
                    selected_req_id = filtered_df["request_id"].iloc[0]

    # Fetch matching row
    match = df[df["request_id"] == selected_req_id]
    if match.empty:
        st.warning(f"Request {selected_req_id} not found.")
        return
        
    row = match.iloc[0].to_dict()

    # Load User Profile
    profiles_df = load_profiles_data()
    user_profile = {}
    if not profiles_df.empty and "user_id" in profiles_df.columns:
        p_match = profiles_df[profiles_df["user_id"] == row.get("user_id")]
        if not p_match.empty:
            user_profile = p_match.iloc[0].to_dict()

    user_currency = user_profile.get("home_currency", "USD")

    # Render Hero Decision Card
    render_decision_hero(row, currency=user_currency)

    # Two column layout: Request Info & User Financial Context
    col_req, col_user = st.columns(2)

    with col_req:
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; height: 100%;">
            <h4 style="margin: 0 0 12px 0; color: #0F172A; font-size: 16px;">🛍️ Request Details</h4>
            <div style="font-size: 13px; line-height: 1.8; color: #334155;">
                <b>Request ID:</b> {row.get('request_id')}<br>
                <b>Request Date:</b> {format_date(row.get('request_date'))}<br>
                <b>Requested Amount:</b> {format_currency(row.get('requested_amount'), user_currency)}<br>
                <b>Desired Completion Date:</b> {format_date(row.get('desired_completion_date'))}<br>
                <b>Partial Payment Permitted:</b> {'Yes ✓' if str(row.get('allows_partial_payment')).lower() in ['true', 'yes', '1'] else 'No ✕'}<br>
                <b>Purchase Purpose:</b> <em>{row.get('request_text', 'N/A')}</em>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_user:
        current_bal = user_profile.get("current_available_balance", "—")
        min_bal = user_profile.get("minimum_balance_to_keep", "—")
        max_inst = user_profile.get("max_installment_months", "Not Accepted")
        if pd.isna(max_inst) or str(max_inst).strip() == "":
            max_inst = "Not Accepted"

        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; height: 100%;">
            <h4 style="margin: 0 0 12px 0; color: #0F172A; font-size: 16px;">👤 User Financial Profile</h4>
            <div style="font-size: 13px; line-height: 1.8; color: #334155;">
                <b>User ID:</b> {row.get('user_id')}<br>
                <b>Home Currency:</b> {user_currency}<br>
                <b>Current Available Balance:</b> {format_currency(current_bal, user_currency)}<br>
                <b>Minimum Required Balance:</b> {format_currency(min_bal, user_currency)}<br>
                <b>Max Installment Duration:</b> {max_inst}<br>
                <b>Financial Priorities:</b> {user_profile.get('financial_priorities', 'N/A')}<br>
                <b>Protected Categories:</b> {user_profile.get('protected_spending_categories', 'N/A')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Payment Plan schedule section
    plan_str = row.get("payment_plan", "none")
    render_payment_plan_schedule(plan_str, currency=user_currency)


if __name__ == "__main__" or True:
    render_decision_explorer_page()


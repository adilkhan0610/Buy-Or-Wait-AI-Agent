"""
Overview Page — Executive KPI Dashboard and Affordability Breakdown.
"""

import streamlit as st
import pandas as pd
from dashboard.utils.data_loader import load_merged_data, load_predictions_data
from dashboard.utils.formatting import (
    COLOR_AFFORDABLE_NOW,
    COLOR_AFFORDABLE_WITH_PLAN,
    COLOR_AFFORDABLE_LATER,
    COLOR_NOT_AFFORDABLE,
    format_currency
)
from dashboard.components.metric_cards import render_kpi_row
from dashboard.components.charts import (
    render_status_donut_chart,
    render_payment_methods_bar_chart,
    render_safe_amount_distribution
)


def render_overview_page():
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            Financial Affordability Executive Overview
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Comprehensive decision analysis across 250 evaluation requests for the Buy or Wait? AI Agent.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_merged_data()
    if df.empty:
        st.error("No decision dataset loaded. Please verify output.csv exists.")
        return

    # Compute key executive metrics
    total_requests = len(df)
    now_cnt = (df["affordability_status"] == "affordable_now").sum()
    plan_cnt = (df["affordability_status"] == "affordable_with_plan").sum()
    later_cnt = (df["affordability_status"] == "affordable_later").sum()
    not_cnt = (df["affordability_status"] == "not_affordable").sum()

    total_requested = df["requested_amount"].sum() if "requested_amount" in df.columns else 0.0
    total_safe_today = df["amount_safe_to_pay"].sum() if "amount_safe_to_pay" in df.columns else 0.0

    # Top KPI Cards Row
    kpis_1 = [
        {
            "title": "Total Requests",
            "value": f"{total_requests:,}",
            "subtitle": "Evaluated against 90-day cash flows",
            "icon": "📋",
            "border_left_color": "#0284C7"
        },
        {
            "title": "Affordable Now",
            "value": f"{now_cnt:,}",
            "subtitle": f"{(now_cnt / total_requests * 100):.1f}% of volume",
            "icon": "✅",
            "border_left_color": COLOR_AFFORDABLE_NOW
        },
        {
            "title": "Affordable w/ Plan",
            "value": f"{plan_cnt:,}",
            "subtitle": f"{(plan_cnt / total_requests * 100):.1f}% installment/partial",
            "icon": "📅",
            "border_left_color": COLOR_AFFORDABLE_WITH_PLAN
        },
        {
            "title": "Affordable Later",
            "value": f"{later_cnt:,}",
            "subtitle": f"{(later_cnt / total_requests * 100):.1f}% wait for safe cash",
            "icon": "⏳",
            "border_left_color": COLOR_AFFORDABLE_LATER
        },
        {
            "title": "Not Affordable",
            "value": f"{not_cnt:,}",
            "subtitle": f"{(not_cnt / total_requests * 100):.1f}% violates balance rule",
            "icon": "🚫",
            "border_left_color": COLOR_NOT_AFFORDABLE
        }
    ]
    render_kpi_row(kpis_1)

    # Secondary Financial Volume Metrics
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    kpis_2 = [
        {
            "title": "Total Volume Requested",
            "value": format_currency(total_requested, "USD"),
            "subtitle": "Sum of all purchase requests",
            "icon": "💰",
            "border_left_color": "#6366F1"
        },
        {
            "title": "Total Safe to Pay Today",
            "value": format_currency(total_safe_today, "USD"),
            "subtitle": f"{(total_safe_today / max(total_requested, 1) * 100):.1f}% capital safe today",
            "icon": "🛡️",
            "border_left_color": "#10B981"
        },
        {
            "title": "Feasibility Rate",
            "value": f"{((now_cnt + plan_cnt + later_cnt) / total_requests * 100):.1f}%",
            "subtitle": f"{now_cnt + plan_cnt + later_cnt} of {total_requests} actionable purchases",
            "icon": "🎯",
            "border_left_color": "#3B82F6"
        }
    ]
    render_kpi_row(kpis_2)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Core Charts Section
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px;">
        """, unsafe_allow_html=True)
        render_status_donut_chart(df)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_chart2:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px;">
        """, unsafe_allow_html=True)
        render_payment_methods_bar_chart(df)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Scatter Distribution
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px;">
    """, unsafe_allow_html=True)
    render_safe_amount_distribution(df)
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__" or True:
    render_overview_page()


"""
Overview Page — Executive KPI Dashboard and Affordability Breakdown.
Clean fintech layout with 4x2 responsive KPI grid and native containers.
"""

import streamlit as st
import pandas as pd
from dashboard.utils.data_loader import load_merged_data
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
    # Header Title Banner
    header_html = (
        '<div style="margin-bottom: 16px;">'
        '<h1 style="font-size: 26px; font-weight: 800; color: #0F172A; margin: 0 0 4px 0; letter-spacing: -0.5px;">'
        'Financial Affordability Executive Overview</h1>'
        '<p style="font-size: 13.5px; color: #64748B; margin: 0;">'
        'Analysis of 250 purchase requests evaluated against 90-day cash flows, liquidity buffers, and payment terms.'
        '</p>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(header_html)
    else:
        st.markdown(header_html, unsafe_allow_html=True)

    df = load_merged_data()
    if df.empty:
        st.error("No decision dataset loaded. Please verify output.csv exists.")
        return

    # Compute key metrics from actual predictions data
    total_requests = len(df)
    now_cnt = int((df["affordability_status"] == "affordable_now").sum())
    plan_cnt = int((df["affordability_status"] == "affordable_with_plan").sum())
    later_cnt = int((df["affordability_status"] == "affordable_later").sum())
    not_cnt = int((df["affordability_status"] == "not_affordable").sum())

    total_requested = float(df["requested_amount"].sum()) if "requested_amount" in df.columns else 0.0
    total_safe_today = float(df["amount_safe_to_pay"].sum()) if "amount_safe_to_pay" in df.columns else 0.0
    actionable_count = now_cnt + plan_cnt + later_cnt
    feasibility_pct = (actionable_count / total_requests * 100) if total_requests > 0 else 0.0
    safe_pct = (total_safe_today / max(total_requested, 1.0) * 100)

    # Row 1: 4 Cards (Volume & Affordability Status)
    row_1_cards = [
        {
            "title": "Total Requests",
            "value": f"{total_requests:,}",
            "subtitle": "250 evaluated decisions",
            "icon": "📋",
            "border_left_color": "#0284C7"
        },
        {
            "title": "Affordable Now",
            "value": f"{now_cnt:,}",
            "subtitle": f"{(now_cnt / total_requests * 100):.1f}% of volume",
            "icon": "✓",
            "delta": f"+{now_cnt}",
            "delta_color": COLOR_AFFORDABLE_NOW,
            "border_left_color": COLOR_AFFORDABLE_NOW
        },
        {
            "title": "Affordable With Plan",
            "value": f"{plan_cnt:,}",
            "subtitle": f"{(plan_cnt / total_requests * 100):.1f}% split/installment",
            "icon": "📅",
            "delta": f"{plan_cnt}",
            "delta_color": COLOR_AFFORDABLE_WITH_PLAN,
            "border_left_color": COLOR_AFFORDABLE_WITH_PLAN
        },
        {
            "title": "Affordable Later",
            "value": f"{later_cnt:,}",
            "subtitle": f"{(later_cnt / total_requests * 100):.1f}% wait for cash inflow",
            "icon": "⏳",
            "delta": f"{later_cnt}",
            "delta_color": COLOR_AFFORDABLE_LATER,
            "border_left_color": COLOR_AFFORDABLE_LATER
        }
    ]
    render_kpi_row(row_1_cards)

    # Row 2: 4 Cards (Capital, Safety, & Risk - normalized across currencies)
    mean_safe_pct = float(df["safe_to_pay_pct"].mean()) if "safe_to_pay_pct" in df.columns else 0.0
    num_currencies = df["home_currency"].nunique() if "home_currency" in df.columns else 5

    row_2_cards = [
        {
            "title": "Not Affordable",
            "value": f"{not_cnt:,}",
            "subtitle": f"{(not_cnt / total_requests * 100):.1f}% violates reserve limit",
            "icon": "✕",
            "delta": f"{not_cnt}",
            "delta_color": COLOR_NOT_AFFORDABLE,
            "border_left_color": COLOR_NOT_AFFORDABLE,
        },
        {
            "title": "Feasibility Rate",
            "value": f"{feasibility_pct:.1f}%",
            "subtitle": f"{actionable_count} of {total_requests} feasible purchases",
            "icon": "🎯",
            "delta": f"{actionable_count} feasible",
            "delta_color": "#0284C7",
            "border_left_color": "#0284C7",
        },
        {
            "title": "Mean Safe Coverage",
            "value": f"{mean_safe_pct:.1f}%",
            "subtitle": "Average safe outlay ratio today",
            "icon": "🛡️",
            "delta": f"{mean_safe_pct:.1f}%",
            "delta_color": COLOR_AFFORDABLE_NOW,
            "border_left_color": COLOR_AFFORDABLE_NOW,
        },
        {
            "title": "Active Currencies",
            "value": f"{num_currencies} Currencies",
            "subtitle": "INR, EUR, IDR, ZAR, USD",
            "icon": "💱",
            "border_left_color": "#6366F1",
        },
    ]
    render_kpi_row(row_2_cards)

    # Multi-Currency Volume & Safe Outlay Breakdown Table
    if "home_currency" in df.columns:
        st.markdown("#### 💱 Purchase Volume & Safe Outlay by Currency")
        st.caption("Normalized accounting by user home currency (preventing invalid cross-currency summation):")

        currency_summary = []
        for curr in sorted(df["home_currency"].dropna().unique()):
            sub = df[df["home_currency"] == curr]
            req_tot = float(sub["requested_amount"].sum())
            safe_tot = float(sub["amount_safe_to_pay"].sum())
            curr_mean_pct = float(sub["safe_to_pay_pct"].mean())
            currency_summary.append({
                "Currency": curr,
                "Requests": len(sub),
                "Total Requested": format_currency(req_tot, curr),
                "Total Safe Today": format_currency(safe_tot, curr),
                "Avg Safe Coverage": f"{curr_mean_pct:.1f}%",
                "Affordable Now": int((sub["affordability_status"] == "affordable_now").sum()),
                "With Plan": int((sub["affordability_status"] == "affordable_with_plan").sum()),
                "Later": int((sub["affordability_status"] == "affordable_later").sum()),
                "Not Affordable": int((sub["affordability_status"] == "not_affordable").sum()),
            })
        st.dataframe(pd.DataFrame(currency_summary), use_container_width=True, hide_index=True)

    # Section divider with small clean margin
    st.write("")

    # Visual Analytics: Two Column Layout
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        with st.container(border=True):
            render_status_donut_chart(df, height=330)

    with col_chart2:
        with st.container(border=True):
            render_payment_methods_bar_chart(df, height=330)

    # Full-width distribution chart
    with st.container(border=True):
        render_safe_amount_distribution(df, height=340)


if __name__ == "__main__" or True:
    render_overview_page()

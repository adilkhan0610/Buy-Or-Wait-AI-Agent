"""
Plotly chart components for the Buy or Wait dashboard.
Features sleek themes, branded colors, interactive tooltips, and responsive layout.
"""

from typing import Optional, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils.formatting import (
    COLOR_AFFORDABLE_NOW,
    COLOR_AFFORDABLE_WITH_PLAN,
    COLOR_AFFORDABLE_LATER,
    COLOR_NOT_AFFORDABLE,
    STATUS_COLORS
)


PLOT_FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def render_status_donut_chart(df: pd.DataFrame, height: int = 350) -> None:
    """Render an interactive donut chart of Affordability Status breakdown."""
    if df.empty or "affordability_status" not in df.columns:
        st.info("No affordability status data available.")
        return

    counts = df["affordability_status"].value_counts().reset_index()
    counts.columns = ["status", "count"]
    
    color_map = {
        "affordable_now": COLOR_AFFORDABLE_NOW,
        "affordable_with_plan": COLOR_AFFORDABLE_WITH_PLAN,
        "affordable_later": COLOR_AFFORDABLE_LATER,
        "not_affordable": COLOR_NOT_AFFORDABLE
    }
    
    label_map = {
        "affordable_now": "Affordable Now",
        "affordable_with_plan": "Affordable with Plan",
        "affordable_later": "Affordable Later",
        "not_affordable": "Not Affordable"
    }
    
    counts["label"] = counts["status"].map(label_map).fillna(counts["status"])
    counts["color"] = counts["status"].map(color_map).fillna("#94A3B8")
    
    fig = go.Figure(data=[
        go.Pie(
            labels=counts["label"],
            values=counts["count"],
            hole=0.58,
            marker=dict(colors=counts["color"], line=dict(color="#FFFFFF", width=2)),
            textinfo="percent+value",
            textposition="inside",
            insidetextorientation="horizontal",
            hovertemplate="<b>%{label}</b><br>Decisions: %{value}<br>Share: %{percent}<extra></extra>"
        )
    ])
    
    total = len(df)
    fig.update_layout(
        title=dict(text="<b>Affordability Status Distribution</b>", font=dict(size=15, family=PLOT_FONT_FAMILY, color="#0F172A")),
        annotations=[
            dict(
                text=f"<span style='font-size:22px; font-weight:700; color:#0F172A;'>{total}</span><br><span style='font-size:12px; color:#64748B;'>Requests</span>",
                x=0.5, y=0.5, font_size=14, showarrow=False
            )
        ],
        margin=dict(l=10, r=10, t=40, b=10),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11, family=PLOT_FONT_FAMILY, color="#334155")
        )
    )
    st.plotly_chart(fig, use_container_width=True)


def render_payment_methods_bar_chart(df: pd.DataFrame, height: int = 350) -> None:
    """Render a horizontal bar chart of Recommended Payment Methods."""
    if df.empty or "recommended_payment_method" not in df.columns:
        st.info("No payment method data available.")
        return

    counts = df["recommended_payment_method"].value_counts().reset_index()
    counts.columns = ["method", "count"]
    
    method_labels = {
        "full_payment": "Full Payment",
        "partial_payment": "Partial Payment",
        "installments": "Installments",
        "wait": "Wait",
        "not_recommended": "Not Recommended"
    }
    method_colors = {
        "full_payment": "#10B981",
        "partial_payment": "#2563EB",
        "installments": "#8B5CF6",
        "wait": "#F59E0B",
        "not_recommended": "#EF4444"
    }
    
    counts["label"] = counts["method"].map(method_labels).fillna(counts["method"])
    counts["color"] = counts["method"].map(method_colors).fillna("#64748B")
    counts = counts.sort_values(by="count", ascending=True)

    fig = go.Figure(go.Bar(
        x=counts["count"],
        y=counts["label"],
        orientation="h",
        marker=dict(color=counts["color"], line=dict(color="#FFFFFF", width=1)),
        text=counts["count"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(text="<b>Recommended Payment Methods</b>", font=dict(size=15, family=PLOT_FONT_FAMILY, color="#0F172A")),
        margin=dict(l=10, r=30, t=40, b=10),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", title=dict(text="Count", font=dict(size=11, color="#64748B"))),
        yaxis=dict(title="", tickfont=dict(size=12, color="#334155"))
    )
    st.plotly_chart(fig, use_container_width=True)


def render_safe_amount_distribution(df: pd.DataFrame, height: int = 350) -> None:
    """Render scatter / comparison of requested amount vs amount safe to pay."""
    if df.empty or "requested_amount" not in df.columns or "amount_safe_to_pay" not in df.columns:
        return
        
    color_map = {
        "affordable_now": COLOR_AFFORDABLE_NOW,
        "affordable_with_plan": COLOR_AFFORDABLE_WITH_PLAN,
        "affordable_later": COLOR_AFFORDABLE_LATER,
        "not_affordable": COLOR_NOT_AFFORDABLE
    }
    
    fig = px.scatter(
        df,
        x="requested_amount",
        y="amount_safe_to_pay",
        color="affordability_status",
        color_discrete_map=color_map,
        hover_data=["request_id", "recommended_payment_method"],
        title="<b>Amount Safe to Pay vs. Requested Amount</b>",
        labels={"requested_amount": "Requested Amount ($)", "amount_safe_to_pay": "Amount Safe Today ($)"}
    )
    
    # 45-degree parity reference line
    max_val = max(df["requested_amount"].max(), df["amount_safe_to_pay"].max(), 100)
    fig.add_trace(go.Scatter(
        x=[0, max_val],
        y=[0, max_val],
        mode="lines",
        line=dict(color="#CBD5E1", dash="dash"),
        name="100% Safe Today",
        hoverinfo="skip"
    ))
    
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOT_FONT_FAMILY),
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5, font=dict(size=11))
    )
    st.plotly_chart(fig, use_container_width=True)


def render_cash_flow_trajectory(
    dates: List[str],
    balances: List[float],
    min_balance: float,
    currency: str = "USD",
    request_date: Optional[str] = None,
    height: int = 380
) -> None:
    """Render cash flow trajectory line chart over 90 days with safe minimum threshold."""
    if not dates or not balances:
        st.info("No cash flow projection points available.")
        return

    df_cf = pd.DataFrame({"date": dates, "balance": balances})
    
    fig = go.Figure()
    
    # Balance projection curve
    fig.add_trace(go.Scatter(
        x=df_cf["date"],
        y=df_cf["balance"],
        mode="lines+markers",
        line=dict(color="#2563EB", width=2.5),
        marker=dict(size=4, color="#1D4ED8"),
        name="Projected Balance",
        hovertemplate=f"<b>Date:</b> %{{x}}<br><b>Projected Balance:</b> %{{y:,.2f}} {currency}<extra></extra>"
    ))
    
    # Minimum required balance line
    fig.add_hline(
        y=min_balance,
        line_dash="dash",
        line_color="#EF4444",
        annotation_text=f"Minimum Required Balance ({min_balance:,.0f} {currency})",
        annotation_position="top left",
        annotation_font=dict(color="#EF4444", size=11, family=PLOT_FONT_FAMILY)
    )
    
    # Request date vertical line if supplied
    if request_date and request_date in dates:
        fig.add_vline(
            x=request_date,
            line_dash="dot",
            line_color="#64748B",
            annotation_text="Evaluation Date",
            annotation_position="bottom right",
            annotation_font=dict(color="#64748B", size=11, family=PLOT_FONT_FAMILY)
        )

    fig.update_layout(
        title=dict(text="<b>90-Day Cash Flow Projection & Safety Boundary</b>", font=dict(size=16, family=PLOT_FONT_FAMILY, color="#0F172A")),
        margin=dict(l=20, r=20, t=50, b=20),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=PLOT_FONT_FAMILY),
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="Date"),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title=f"Available Balance ({currency})"),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)


"""
Decision cards and visual blocks for presenting purchase recommendations.
"""

from typing import Dict, Any, Optional
import html
import streamlit as st

from dashboard.utils.formatting import (
    get_status_badge,
    get_method_badge,
    format_currency,
    format_date,
    parse_payment_plan,
    parse_spending_changes,
    STATUS_COLORS
)


def render_decision_hero(decision: Dict[str, Any], currency: str = "USD") -> None:
    """Render a prominent decision card with color-coded accent, badges, and explanation."""
    status = str(decision.get("affordability_status", "not_affordable"))
    status_conf = STATUS_COLORS.get(status, STATUS_COLORS["not_affordable"])
    border_color = status_conf["color"]
    
    amount_safe = float(decision.get("amount_safe_to_pay", 0.0))
    requested_amt = float(decision.get("requested_amount", amount_safe))
    method = str(decision.get("recommended_payment_method", "not_recommended"))
    earliest_date = format_date(decision.get("earliest_date_for_full_payment"))
    spending_changes = str(decision.get("spending_changes_needed", "none"))
    explanation = html.escape(str(decision.get("decision_explanation", "")))
    req_id = decision.get("request_id", "N/A")
    user_id = decision.get("user_id", "N/A")
    
    st.markdown(f"""
    <div style="
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 24px 28px;
        border: 1px solid #E2E8F0;
        border-top: 5px solid {border_color};
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
            <div>
                <span style="font-size: 12px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">
                    Request {req_id} &bull; User {user_id}
                </span>
                <h2 style="margin: 4px 0 0 0; font-size: 24px; font-weight: 700; color: #0F172A;">
                    Recommendation Summary
                </h2>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                {get_status_badge(status)}
                {get_method_badge(method)}
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; background: #F8FAFC; padding: 16px; border-radius: 10px; border: 1px solid #F1F5F9;">
            <div>
                <div style="font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase;">Amount Safe Today</div>
                <div style="font-size: 22px; font-weight: 700; color: #0F172A; margin-top: 2px;">
                    {format_currency(amount_safe, currency)}
                </div>
                <div style="font-size: 11px; color: #64748B;">of {format_currency(requested_amt, currency)} requested</div>
            </div>
            <div>
                <div style="font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase;">Earliest Full Payment</div>
                <div style="font-size: 18px; font-weight: 600; color: #0F172A; margin-top: 4px;">
                    📅 {earliest_date}
                </div>
            </div>
            <div>
                <div style="font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase;">Spending Changes</div>
                <div style="font-size: 14px; font-weight: 600; color: {'#065F46' if spending_changes == 'none' else '#D97706'}; margin-top: 6px;">
                    {'✓ None Required' if spending_changes == 'none' else spending_changes}
                </div>
            </div>
        </div>

        <div style="margin-top: 16px;">
            <div style="font-size: 12px; font-weight: 700; color: #475569; text-transform: uppercase; margin-bottom: 6px;">
                💡 Decision Explanation:
            </div>
            <div style="font-size: 14px; line-height: 1.6; color: #1E293B; background: #F1F5F9; padding: 14px 18px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                {explanation}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_payment_plan_schedule(plan_str: str, currency: str = "USD") -> None:
    """Render structured table or step timeline of a payment plan."""
    items = parse_payment_plan(plan_str)
    if not items:
        st.markdown("""
        <div style="background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 14px; text-align: center; color: #64748B; font-size: 13px;">
            No split payment plan required or available.
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown("##### 📅 Payment Schedule Milestones")
    cols = st.columns(len(items))
    for idx, (dt, amt) in enumerate(items):
        with cols[idx]:
            st.markdown(f"""
            <div style="
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-top: 3px solid #2563EB;
                border-radius: 8px;
                padding: 12px;
                text-align: center;
                box-shadow: 0 1px 2px rgba(0,0,0,0.03);
            ">
                <div style="font-size: 11px; font-weight: 700; color: #64748B;">PAYMENT #{idx+1}</div>
                <div style="font-size: 13px; font-weight: 600; color: #0F172A; margin: 4px 0;">{dt}</div>
                <div style="font-size: 16px; font-weight: 700; color: #2563EB;">{format_currency(amt, currency)}</div>
            </div>
            """, unsafe_allow_html=True)


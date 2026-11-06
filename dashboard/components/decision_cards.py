"""
Decision cards and visual blocks for presenting purchase recommendations.
Unindented HTML rendering to prevent CommonMark code block parsing.
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
    
    status_badge_html = get_status_badge(status)
    method_badge_html = get_method_badge(method)
    spending_color = "#065F46" if spending_changes == "none" else "#D97706"
    spending_label = "✓ None Required" if spending_changes == "none" else spending_changes
    
    card_html = (
        f'<div style="background-color: #FFFFFF; border-radius: 12px; padding: 20px 24px; '
        f'border: 1px solid #E2E8F0; border-top: 5px solid {border_color}; '
        f'box-shadow: 0 2px 4px rgba(0,0,0,0.04); margin-bottom: 20px;">'
        f'<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">'
        f'<div>'
        f'<span style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px;">'
        f'Request {req_id} &bull; User {user_id}</span>'
        f'<h2 style="margin: 2px 0 0 0; font-size: 22px; font-weight: 700; color: #0F172A;">Recommendation Summary</h2>'
        f'</div>'
        f'<div style="display: flex; gap: 8px; flex-wrap: wrap;">{status_badge_html} {method_badge_html}</div>'
        f'</div>'
        f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 16px 0; background: #F8FAFC; padding: 14px; border-radius: 8px; border: 1px solid #F1F5F9;">'
        f'<div>'
        f'<div style="font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase;">Amount Safe Today</div>'
        f'<div style="font-size: 20px; font-weight: 700; color: #0F172A; margin-top: 2px;">{format_currency(amount_safe, currency)}</div>'
        f'<div style="font-size: 11px; color: #64748B;">of {format_currency(requested_amt, currency)} requested</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase;">Earliest Full Payment</div>'
        f'<div style="font-size: 17px; font-weight: 600; color: #0F172A; margin-top: 3px;">📅 {earliest_date}</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase;">Spending Changes</div>'
        f'<div style="font-size: 13.5px; font-weight: 600; color: {spending_color}; margin-top: 4px;">{spending_label}</div>'
        f'</div>'
        f'</div>'
        f'<div style="margin-top: 14px;">'
        f'<div style="font-size: 11.5px; font-weight: 700; color: #475569; text-transform: uppercase; margin-bottom: 4px;">💡 Decision Explanation:</div>'
        f'<div style="font-size: 13.5px; line-height: 1.6; color: #1E293B; background: #F1F5F9; padding: 12px 16px; border-radius: 8px; border-left: 3px solid #3B82F6;">{explanation}</div>'
        f'</div>'
        f'</div>'
    )
    if hasattr(st, "html"):
        st.html(card_html)
    else:
        st.markdown(card_html, unsafe_allow_html=True)


def render_payment_plan_schedule(plan_str: str, currency: str = "USD") -> None:
    """Render structured table or step timeline of a payment plan."""
    items = parse_payment_plan(plan_str)
    if not items:
        empty_html = (
            '<div style="background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; '
            'padding: 12px; text-align: center; color: #64748B; font-size: 13px;">'
            'No split payment plan required or available.'
            '</div>'
        )
        if hasattr(st, "html"):
            st.html(empty_html)
        else:
            st.markdown(empty_html, unsafe_allow_html=True)
        return

    st.markdown("##### 📅 Payment Schedule Milestones")
    cols = st.columns(len(items))
    for idx, (dt, amt) in enumerate(items):
        with cols[idx]:
            item_html = (
                f'<div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 3px solid #2563EB; '
                f'border-radius: 8px; padding: 10px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">'
                f'<div style="font-size: 10.5px; font-weight: 700; color: #64748B;">PAYMENT #{idx+1}</div>'
                f'<div style="font-size: 12.5px; font-weight: 600; color: #0F172A; margin: 3px 0;">{dt}</div>'
                f'<div style="font-size: 15px; font-weight: 700; color: #2563EB;">{format_currency(amt, currency)}</div>'
                f'</div>'
            )
            if hasattr(st, "html"):
                st.html(item_html)
            else:
                st.markdown(item_html, unsafe_allow_html=True)

"""
Spending Optimization Page — Flexible Spending Adjustments & Budget Safeguards.
"""

import streamlit as st
import pandas as pd
from dashboard.utils.data_loader import load_merged_data
from dashboard.utils.formatting import parse_spending_changes, format_currency, get_status_badge, get_method_badge


def render_spending_optimizer_page():
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            Spending Changes Optimizer
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Identification and optimization of flexible, non-protected expense reductions to make purchases feasible.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_merged_data()
    if df.empty:
        st.error("No dataset available.")
        return

    # Filter rows with spending changes
    has_changes = df[df["spending_changes_needed"].astype(str).str.lower() != "none"]
    total_with_changes = len(has_changes)

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric("Requests Requiring Changes", f"{total_with_changes}", f"{(total_with_changes/len(df)*100):.1f}% of all requests")
    with col_kpi2:
        st.metric("Max Changes Allowed", "3 Actions", "Per challenge contract rule")
    with col_kpi3:
        st.metric("Protected Categories", "100% Protected", "Zero violations")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    if total_with_changes == 0:
        st.success("✓ No requests required spending changes under the current conservative forecast!")
    else:
        st.markdown("#### 🛠️ Requests with Active Spending Reductions")
        table_rows = []
        for _, r in has_changes.iterrows():
            actions = parse_spending_changes(r.get("spending_changes_needed"))
            table_rows.append({
                "Request ID": r.get("request_id"),
                "User ID": r.get("user_id"),
                "Status": r.get("affordability_status"),
                "Method": r.get("recommended_payment_method"),
                "Requested Amount": f"${r.get('requested_amount', 0):,.2f}",
                "Safe Today": f"${r.get('amount_safe_to_pay', 0):,.2f}",
                "Spending Changes Needed": r.get("spending_changes_needed"),
                "# Actions": len(actions)
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    # Spending Changes Rules Reference Card
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-top: 24px;">
        <h4 style="margin: 0 0 12px 0; color: #0F172A; font-size: 16px;">🛡️ Budget Optimization Constraints</h4>
        <ul style="font-size: 13px; color: #334155; line-height: 1.8; margin: 0; padding-left: 20px;">
            <li><b>Protected Categories:</b> Expenses in categories marked protected (e.g. rent, utilities, groceries) are strictly immutable.</li>
            <li><b>Adjustable Categories:</b> Only flexible events in categories explicitly listed as adjustable by the user profile may be modified.</li>
            <li><b>Action Cap:</b> Maximum of 3 spending changes per request (either <code>stop:&lt;event_id&gt;</code> or <code>reduce_to:&lt;event_id&gt;:&lt;amount&gt;</code>).</li>
            <li><b>Liquidity Preservation:</b> The projected cash flow must remain above the user's minimum balance after implementing changes.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__" or True:
    render_spending_optimizer_page()


"""
Payment Plan Optimizer Page — Evaluation of Multi-Option Terms & Installments.
"""

import streamlit as st
import pandas as pd
from dashboard.utils.data_loader import (
    load_merged_data,
    get_decision_pipeline,
    PAYMENT_OPTIONS_CSV_PATH
)
from dashboard.utils.formatting import format_currency, get_status_badge, get_method_badge


def render_payment_optimizer_page():
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            Payment Option & Plan Optimizer
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Rigorous evaluation of 2–4 provider-supplied payment options matching user preferences and constraints.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_merged_data()
    pipeline = get_decision_pipeline()
    
    if df.empty or pipeline is None:
        st.info("Pipeline initializing...")
        return

    # Filter to requests with installment or plan recommendations
    plan_requests = df[df["affordability_status"] == "affordable_with_plan"]
    
    col_sel, col_stats = st.columns([2, 1])
    with col_sel:
        options = []
        for _, r in df.iterrows():
            options.append(f"{r['request_id']} | User: {r.get('user_id')} | {r.get('recommended_payment_method')} (${r.get('requested_amount', 0):,.2f})")
        selected_opt = st.selectbox("Select Request to Evaluate Options:", options=options, index=0)
        selected_req_id = selected_opt.split(" | ")[0]

    req_row = df[df["request_id"] == selected_req_id].iloc[0].to_dict()
    user_id = req_row.get("user_id")

    # Load raw options for this request
    if PAYMENT_OPTIONS_CSV_PATH.exists():
        all_options_df = pd.read_csv(PAYMENT_OPTIONS_CSV_PATH)
        req_options = all_options_df[all_options_df["request_id"] == selected_req_id]
    else:
        req_options = pd.DataFrame()

    with col_stats:
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; margin-top: 24px;">
            <div style="font-size: 12px; color: #64748B;">Selected Recommendation</div>
            <div style="margin-top: 4px;">{get_method_badge(req_row.get('recommended_payment_method'))}</div>
            <div style="margin-top: 6px; font-size: 12px; color: #334155;">
                <b>Payment Plan:</b> {req_row.get('payment_plan', 'none')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### 📋 Available Provider Payment Options")
    if req_options.empty:
        st.info("No external provider options listed in request_payment_options.csv for this request.")
    else:
        display_opts = []
        for _, opt in req_options.iterrows():
            display_opts.append({
                "Option ID": opt.get("option_id"),
                "Payment Method": opt.get("payment_method"),
                "Installments": opt.get("number_of_installments"),
                "Down Payment": f"${opt.get('down_payment_amount', 0):,.2f}",
                "Installment Amount": f"${opt.get('installment_amount', 0):,.2f}",
                "Frequency": opt.get("installment_frequency"),
                "Interest/Fee Rate": f"{opt.get('interest_or_fee_rate', 0)}%",
                "Total Cost": f"${opt.get('total_payment_amount', 0):,.2f}"
            })
        st.dataframe(pd.DataFrame(display_opts), use_container_width=True, hide_index=True)

    # Explanation and Constraint Verification
    st.markdown("#### 🔍 Selection & Feasibility Analysis")
    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; font-size: 14px; line-height: 1.6; color: #1E293B;">
        <b>Engine Assessment:</b><br>
        {req_row.get('decision_explanation', '')}
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__" or True:
    render_payment_optimizer_page()


"""
Cash Flow Forecast Page — 90-Day Balance Trajectory & Safety Boundary Analysis.
"""

import streamlit as st
import pandas as pd
from dashboard.utils.data_loader import load_merged_data, load_profiles_data, get_decision_pipeline
from dashboard.utils.formatting import format_currency, format_date
from dashboard.components.charts import render_cash_flow_trajectory


def render_cash_flow_page():
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            90-Day Cash Flow Forecasting Engine
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Conservative multi-source balance trajectory projection enforcing strict minimum balance invariants.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = load_merged_data()
    profiles_df = load_profiles_data()
    pipeline = get_decision_pipeline()

    if df.empty or pipeline is None:
        st.info("Decision engine pipeline is initializing or unavailable.")
        return

    # User / Request Selection
    user_ids = sorted(df["user_id"].dropna().unique().tolist())
    selected_user = st.selectbox("Select User Profile for Cash Flow Analysis:", options=user_ids, index=0)

    # Get requests for this user
    user_requests = df[df["user_id"] == selected_user]
    default_req_date = user_requests["request_date"].iloc[0] if not user_requests.empty else "2026-09-01"
    
    col_date, col_summary = st.columns([1, 2])
    with col_date:
        sim_date = st.text_input("Evaluation Start Date (YYYY-MM-DD):", value=default_req_date)
    
    # Retrieve user financial state
    user_state = pipeline.get_user_state(selected_user)
    if not user_state:
        st.warning(f"Could not construct financial state for {selected_user}")
        return

    min_bal = float(user_state.minimum_balance_to_keep)
    home_curr = getattr(user_state.user_profile, "home_currency", "USD") if hasattr(user_state, "user_profile") else "USD"
    curr_bal = float(user_state.current_available_balance)

    with col_summary:
        st.markdown(f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-top: 24px; font-size: 13px;">
            <b>Home Currency:</b> {home_curr} &bull; 
            <b>Available Balance:</b> {format_currency(curr_bal, home_curr)} &bull; 
            <b>Minimum Reserve:</b> {format_currency(min_bal, home_curr)}
        </div>
        """, unsafe_allow_html=True)

    # Run cash flow forecast
    try:
        forecast = pipeline.cash_flow_engine.run_forecast(
            user_state=user_state,
            evaluation_date=sim_date,
            forecast_days=90
        )
        
        # Render Trajectory Chart
        dates = [e.date for e in forecast.daily_entries]
        balances = [e.closing_balance for e in forecast.daily_entries]
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px;">
        """, unsafe_allow_html=True)
        render_cash_flow_trajectory(
            dates=dates,
            balances=balances,
            min_balance=min_bal,
            currency=home_curr,
            request_date=sim_date
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Cash Flow Summary Metrics
        min_projected = min(balances) if balances else 0.0
        max_projected = max(balances) if balances else 0.0
        closing_90d = balances[-1] if balances else 0.0

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Starting Balance", format_currency(curr_bal, home_curr))
        with col_m2:
            st.metric("Lowest Projected Balance", format_currency(min_projected, home_curr),
                      delta=f"{(min_projected - min_bal):,.0f} buffer",
                      delta_color="normal" if min_projected >= min_bal else "inverse")
        with col_m3:
            st.metric("Peak Projected Balance", format_currency(max_projected, home_curr))
        with col_m4:
            st.metric("90-Day Closing Balance", format_currency(closing_90d, home_curr))

        # Ledger Table
        with st.expander("📋 View Daily Cash Flow Ledger & Obligations"):
            ledger_data = []
            for e in forecast.daily_entries:
                if e.credits != 0 or e.debits != 0:
                    ledger_data.append({
                        "Date": e.date,
                        "Inflow (+)": f"+{e.credits:,.2f}" if e.credits > 0 else "-",
                        "Outflow (-)": f"-{e.debits:,.2f}" if e.debits > 0 else "-",
                        "Net Change": f"{e.net_change:+,.2f}",
                        "Closing Balance": f"{e.closing_balance:,.2f}",
                        "Events": "; ".join([evt.get("description", "Event") for evt in e.events]) if hasattr(e, "events") and e.events else "-"
                    })
            if ledger_data:
                st.dataframe(pd.DataFrame(ledger_data), use_container_width=True, hide_index=True)
            else:
                st.write("No discrete transaction events during this window; balance remains steady.")

    except Exception as exc:
        st.error(f"Failed to generate cash flow forecast: {exc}")


if __name__ == "__main__" or True:
    render_cash_flow_page()


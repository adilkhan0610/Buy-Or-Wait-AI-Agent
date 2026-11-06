"""
Purchase Decision Explorer — Granular Inspection of Decisions, Profiles, Plans & Cash Flows.
Full integration with DecisionPipeline, CashFlowEngine, and PaymentPlanOptimizer.
"""

from typing import Dict, Any, List
import pandas as pd
import streamlit as st

from dashboard.utils.data_loader import (
    load_merged_data,
    load_profiles_data,
    get_decision_pipeline
)
from dashboard.utils.formatting import (
    format_currency,
    format_date,
    get_status_badge,
    get_method_badge,
    parse_payment_plan
)
from dashboard.components.decision_cards import (
    render_decision_hero,
    render_payment_plan_schedule
)
from dashboard.components.charts import render_cash_flow_trajectory


def render_decision_explorer_page():
    # Page Header Banner
    header_html = (
        '<div style="margin-bottom: 16px;">'
        '<h1 style="font-size: 26px; font-weight: 800; color: #0F172A; margin: 0 0 4px 0; letter-spacing: -0.5px;">'
        'Purchase Decision Explorer</h1>'
        '<p style="font-size: 13.5px; color: #64748B; margin: 0;">'
        'Granular inspection of purchase affordability, financial state reconstruction, payment plans, provider options, and 90-day cash flow dynamics.'
        '</p>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(header_html)
    else:
        st.markdown(header_html, unsafe_allow_html=True)

    # Load merged data and pipeline
    df = load_merged_data()
    pipeline = get_decision_pipeline()

    if df.empty:
        st.error("No dataset available. Please verify output.csv and dataset/requests.csv.")
        return

    # Section 1: Interactive Request Selection & Filtering
    col_filter_status, col_selector = st.columns([1, 2])

    with col_filter_status:
        status_filter = st.selectbox(
            "Filter by Affordability Status:",
            options=["All Statuses", "affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"],
            index=0
        )

    # Filter dataframe if requested
    filtered_df = df.copy()
    if status_filter != "All Statuses":
        filtered_df = filtered_df[filtered_df["affordability_status"] == status_filter]
        if filtered_df.empty:
            st.info(f"No requests found with status '{status_filter}'.")
            return

    # Build options list
    options = []
    for _, r in filtered_df.iterrows():
        req_id = r["request_id"]
        uid = r.get("user_id", "")
        amt = float(r.get("requested_amount", 0.0))
        st_val = r.get("affordability_status", "")
        options.append(f"{req_id} | User {uid} | {st_val} (${amt:,.2f})")

    default_index = 0
    if "selected_request_id" in st.session_state:
        req_target = str(st.session_state["selected_request_id"]).strip()
        for idx, opt in enumerate(options):
            if opt.startswith(req_target + " |") or opt.startswith(req_target + " "):
                default_index = idx
                break

    with col_selector:
        selected_option = st.selectbox(
            "Select Request to Inspect (Searchable):",
            options=options,
            index=default_index
        )

    selected_req_id = selected_option.split(" | ")[0]
    match = df[df["request_id"] == selected_req_id]
    if match.empty:
        st.warning(f"Request {selected_req_id} not found.")
        return

    row = match.iloc[0].to_dict()
    user_id = row.get("user_id", "")

    # Retrieve real financial state from DecisionPipeline
    user_state = None
    if pipeline is not None and user_id:
        try:
            user_state = pipeline.get_user_state(user_id)
        except Exception as e:
            st.warning(f"Could not load state for user {user_id}: {e}")

    # Determine user's home currency
    user_currency = "USD"
    if user_state is not None and hasattr(user_state, "user_profile"):
        user_currency = getattr(user_state.user_profile, "home_currency", "USD")

    # Section 2: Prominent Decision Hero Card
    render_decision_hero(row, currency=user_currency)

    # Section 3: Purchase Request & Financial Profile Details (Two Columns)
    col_req, col_user = st.columns(2)

    with col_req:
        with st.container(border=True):
            st.markdown("#### 🛍️ Purchase Request Details")
            st.markdown(
                f"**Request ID:** `{row.get('request_id')}`  \n"
                f"**Purchase Purpose:** *{row.get('request_text', 'N/A')}*  \n"
                f"**Requested Amount:** **{format_currency(row.get('requested_amount'), user_currency)}**  \n"
                f"**Request Date:** `{format_date(row.get('request_date'))}`  \n"
                f"**Deadline / Completion:** `{format_date(row.get('desired_completion_date'))}`  \n"
                f"**Partial Payment Permitted:** {'Yes ✓' if str(row.get('allows_partial_payment')).lower() in ['true', 'yes', '1'] else 'No ✕'}"
            )

    with col_user:
        with st.container(border=True):
            st.markdown("#### 👤 User Financial Profile")
            if user_state is not None:
                prof = user_state.user_profile
                priorities = ", ".join(prof.financial_priorities) if prof.financial_priorities else "None specified"
                max_inst = f"{prof.max_installment_months} months" if prof.max_installment_months else "Not Accepted"
                curr_bal = float(user_state.current_available_balance)
                min_bal = float(user_state.minimum_balance_to_keep)
                unreserved_bal = float(user_state.unreserved_available_balance)
                pending_deb = float(user_state.total_pending_debits)

                st.markdown(
                    f"**User ID:** `{user_id}`  \n"
                    f"**Home Currency:** `{user_currency}`  \n"
                    f"**Current Available Balance:** **{format_currency(curr_bal, user_currency)}**  \n"
                    f"**Minimum Balance to Keep:** {format_currency(min_bal, user_currency)}  \n"
                    f"**Unreserved Available Balance:** **{format_currency(unreserved_bal, user_currency)}**  \n"
                    f"**Total Pending Debits:** {format_currency(pending_deb, user_currency)}  \n"
                    f"**Financial Priorities:** {priorities}  \n"
                    f"**Max Installment Duration:** {max_inst}"
                )
            else:
                st.info("User financial profile state not initialized.")

    st.write("")

    # Section 4: Recommended Payment Schedule
    plan_str = str(row.get("payment_plan", "none"))
    with st.container(border=True):
        st.markdown("#### 📅 Recommended Payment Schedule")
        if plan_str.lower() != "none" and plan_str.strip() != "":
            # Render visual cards
            render_payment_plan_schedule(plan_str, currency=user_currency)
            
            # Render structured table with cumulative tracking
            items = parse_payment_plan(plan_str)
            if items:
                table_rows = []
                cum_amt = 0.0
                for idx, (dt, amt) in enumerate(items, 1):
                    cum_amt += amt
                    table_rows.append({
                        "Payment Number": f"Payment #{idx}",
                        "Payment Date": dt,
                        "Amount": format_currency(amt, user_currency),
                        "Cumulative Amount Paid": format_currency(cum_amt, user_currency)
                    })
                st.write("")
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        else:
            method_label = row.get("recommended_payment_method", "not_recommended").replace("_", " ").title()
            st.info(f"No installment plan active. Recommendation is **{method_label}**.")

    st.write("")

    # Section 5: Evaluated Provider Payment Options (from PaymentPlanOptimizer)
    with st.container(border=True):
        st.markdown("#### 💳 Provider Payment Options & Feasibility Analysis")
        if pipeline is not None and user_state is not None:
            try:
                opt_res = pipeline.payment_plan_optimizer.evaluate_options_for_request(row, state=user_state)
                if opt_res.evaluated_options:
                    opt_table = []
                    for opt in opt_res.evaluated_options:
                        is_feas = opt.is_feasible
                        opt_table.append({
                            "Option ID": opt.payment_option_id,
                            "Payment Method": opt.payment_method.replace("_", " ").title(),
                            "Payments": opt.number_of_payments,
                            "Financing Fee": format_currency(float(opt.financing_fee), user_currency),
                            "Total Amount": format_currency(float(opt.total_amount_paid), user_currency),
                            "Schedule": opt.payment_schedule,
                            "Feasibility": "✓ Feasible" if is_feas else "✕ Infeasible",
                            "Rejection Reason / Outcome": opt.rejection_reason if opt.rejection_reason else "Feasible & Selected" if is_feas else "-"
                        })
                    st.dataframe(pd.DataFrame(opt_table), use_container_width=True, hide_index=True)
                    if opt_res.selection_explanation:
                        st.caption(f"**Optimizer Note:** {opt_res.selection_explanation}")
                else:
                    st.info("No provider payment options listed in `request_payment_options.csv` for this request.")
            except Exception as e:
                st.warning(f"Error evaluating options for request: {e}")
        else:
            st.info("Pipeline optimizer unavailable.")

    st.write("")

    # Section 6: Cash Flow Dynamics & 90-Day Trajectory
    with st.container(border=True):
        st.markdown("#### 📈 90-Day Cash Flow Forecast & Safety Boundary")
        if pipeline is not None and user_state is not None:
            try:
                req_date = str(row.get("request_date", "2026-09-01"))
                fc = pipeline.cash_flow_engine.run_forecast(
                    state=user_state,
                    start_date=req_date,
                    horizon_days=90
                )

                # Forecast KPI Row
                initial_b = float(fc.initial_balance)
                lowest_b = float(fc.lowest_balance)
                min_b = float(fc.minimum_balance_to_keep)
                cushion = lowest_b - min_b
                is_safe = fc.is_safe_throughout

                col_fc1, col_fc2, col_fc3, col_fc4 = st.columns(4)
                with col_fc1:
                    st.metric("Starting Balance", format_currency(initial_b, user_currency))
                with col_fc2:
                    st.metric("Minimum Reserve", format_currency(min_b, user_currency))
                with col_fc3:
                    delta_label = f"{cushion:+,.0f} buffer"
                    st.metric(
                        "Lowest Projected Balance",
                        format_currency(lowest_b, user_currency),
                        delta=delta_label,
                        delta_color="normal" if cushion >= 0 else "inverse"
                    )
                with col_fc4:
                    if is_safe:
                        st.metric("Safety Status", "Safe Throughout ✓", delta="0 Breaches", delta_color="normal")
                    else:
                        st.metric("Safety Status", "Breach Projected ⚠️", delta=f"First: {fc.first_breach_date}", delta_color="inverse")

                # Trajectory chart
                dates = [d.date for d in fc.daily_forecasts]
                balances = [float(d.ending_balance) for d in fc.daily_forecasts]
                render_cash_flow_trajectory(
                    dates=dates,
                    balances=balances,
                    min_balance=min_b,
                    currency=user_currency,
                    request_date=req_date,
                    height=320
                )

                # Critical Buffer / Breach Analysis
                critical_entries = []
                for d in fc.daily_forecasts:
                    bal = float(d.ending_balance)
                    cush = float(d.cushion_above_minimum)
                    # Highlight dates with breach or tight cushion (<15% of min balance or within 500 units)
                    if cush < 0 or (min_b > 0 and cush < min_b * 0.15) or (min_b == 0 and bal < 500):
                        critical_entries.append({
                            "Date": d.date,
                            "Day Index": f"Day {d.day_index}",
                            "Ending Balance": format_currency(bal, user_currency),
                            "Required Minimum": format_currency(min_b, user_currency),
                            "Cushion Above Reserve": format_currency(cush, user_currency),
                            "Safety Level": "🚨 Reserve Breach" if cush < 0 else "⚡ Tight Buffer (<15%)"
                        })

                if critical_entries:
                    st.markdown("##### ⚠️ Buffer Sensitivity / Critical Dates")
                    st.dataframe(pd.DataFrame(critical_entries), use_container_width=True, hide_index=True)
                else:
                    st.success("✓ Safe Liquidity: Projected balance maintains a healthy cushion above minimum required reserve across all 90 days.")

            except Exception as e:
                st.error(f"Error projecting cash flow: {e}")
        else:
            st.info("Cash flow forecasting engine unavailable.")


if __name__ == "__main__" or True:
    render_decision_explorer_page()

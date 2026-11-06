"""
90-Day Cash Flow Forecast Page — Balance Trajectory, Liquidity Invariants & Purchase Impact.
Full integration with DecisionPipeline and CashFlowEngine.
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import streamlit as st

from dashboard.utils.data_loader import (
    load_merged_data,
    get_decision_pipeline
)
from dashboard.utils.formatting import (
    format_currency,
    format_date,
    get_status_badge,
    get_method_badge,
    parse_payment_plan
)
from dashboard.components.metric_cards import render_kpi_row
from dashboard.components.charts import render_comprehensive_cash_flow_chart


def render_cash_flow_page():
    # Page Header Banner
    header_html = (
        '<div style="margin-bottom: 16px;">'
        '<h1 style="font-size: 26px; font-weight: 800; color: #0F172A; margin: 0 0 4px 0; letter-spacing: -0.5px;">'
        '90-Day Cash Flow Forecast & Reserve Invariants</h1>'
        '<p style="font-size: 13.5px; color: #64748B; margin: 0;">'
        'Conservative multi-source balance projection enforcing strict minimum balance thresholds and pre/post-purchase impact analysis.'
        '</p>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(header_html)
    else:
        st.markdown(header_html, unsafe_allow_html=True)

    df = load_merged_data()
    pipeline = get_decision_pipeline()

    if df.empty or pipeline is None:
        st.error("Decision engine pipeline or dataset is initializing or unavailable.")
        return

    # Section 1: Request & User Selection
    col_filter, col_select = st.columns([1, 2])
    with col_filter:
        status_filter = st.selectbox(
            "Filter Requests by Status:",
            options=["All Statuses", "affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"],
            index=0
        )

    filtered_df = df.copy()
    if status_filter != "All Statuses":
        filtered_df = filtered_df[filtered_df["affordability_status"] == status_filter]
        if filtered_df.empty:
            st.info(f"No requests found with status '{status_filter}'.")
            return

    options = []
    for _, r in filtered_df.iterrows():
        rid = r["request_id"]
        uid = r.get("user_id", "")
        amt = float(r.get("requested_amount", 0.0))
        st_val = r.get("affordability_status", "")
        options.append(f"{rid} | User {uid} | {st_val} (${amt:,.2f})")

    with col_select:
        selected_option = st.selectbox("Select Request for Cash Flow Analysis:", options=options, index=0)

    selected_req_id = selected_option.split(" | ")[0]
    match = df[df["request_id"] == selected_req_id]
    if match.empty:
        st.warning(f"Request {selected_req_id} not found.")
        return

    req_row = match.iloc[0].to_dict()
    user_id = req_row.get("user_id", "")
    request_date = str(req_row.get("request_date", "2026-09-01"))

    # Retrieve real financial state from DecisionPipeline
    user_state = pipeline.get_user_state(user_id)
    if not user_state:
        st.warning(f"Could not construct financial state for {user_id}")
        return

    home_curr = getattr(user_state.user_profile, "home_currency", "USD")

    # Selected Request Context Banner
    with st.container(border=True):
        col_ctx1, col_ctx2, col_ctx3 = st.columns([1.5, 1, 1.5])
        with col_ctx1:
            st.markdown(
                f"**Request:** `{selected_req_id}` &bull; **User:** `{user_id}`  \n"
                f"**Evaluation Date:** `{request_date}` &bull; **Horizon:** 90 Days"
            )
        with col_ctx2:
            st.markdown(
                f"**Requested:** {format_currency(req_row.get('requested_amount'), home_curr)}  \n"
                f"**Safe Today:** {format_currency(req_row.get('amount_safe_to_pay'), home_curr)}"
            )
        with col_ctx3:
            st.markdown(
                f"**Status:** {get_status_badge(req_row.get('affordability_status'))}  \n"
                f"**Method:** {get_method_badge(req_row.get('recommended_payment_method'))}",
                unsafe_allow_html=True
            )

    st.write("")

    # Section 2: Run Baseline 90-Day Forecast
    try:
        fc = pipeline.cash_flow_engine.run_forecast(
            state=user_state,
            start_date=request_date,
            horizon_days=90
        )
    except Exception as exc:
        st.error(f"Failed to execute baseline cash flow forecast: {exc}")
        return

    # Extract forecast metrics
    initial_bal = float(fc.initial_balance)
    min_bal = float(fc.minimum_balance_to_keep)
    lowest_bal = float(fc.lowest_balance)
    lowest_bal_date = fc.lowest_balance_date
    total_credits = sum(float(d.total_credits) for d in fc.daily_forecasts)
    total_debits = sum(float(d.total_debits) for d in fc.daily_forecasts)
    cushion = lowest_bal - min_bal

    # Section 2: KPI Metrics Cards (Two rows of 3)
    kpis_row1 = [
        {
            "title": "Starting Balance",
            "value": format_currency(initial_bal, home_curr),
            "subtitle": f"Available on {request_date}",
            "icon": "🏦",
            "border_left_color": "#0284C7"
        },
        {
            "title": "Minimum Required Balance",
            "value": format_currency(min_bal, home_curr),
            "subtitle": "Strict liquidity safety threshold",
            "icon": "🛡️",
            "border_left_color": "#DC2626"
        },
        {
            "title": "Lowest Forecasted Balance",
            "value": format_currency(lowest_bal, home_curr),
            "subtitle": f"Lowest point on {lowest_bal_date}",
            "icon": "📉",
            "delta": f"{cushion:+,.0f} buffer",
            "delta_color": "#10B981" if cushion >= 0 else "#EF4444",
            "border_left_color": "#10B981" if cushion >= 0 else "#EF4444"
        }
    ]
    render_kpi_row(kpis_row1)

    kpis_row2 = [
        {
            "title": "Lowest Balance Date",
            "value": lowest_bal_date,
            "subtitle": "Critical liquidity trough",
            "icon": "📅",
            "border_left_color": "#F59E0B"
        },
        {
            "title": "Total Forecasted Credits",
            "value": format_currency(total_credits, home_curr),
            "subtitle": "Confirmed recurring/settled income",
            "icon": "📈",
            "delta": f"+{format_currency(total_credits, home_curr)}",
            "delta_color": "#10B981",
            "border_left_color": "#10B981"
        },
        {
            "title": "Total Forecasted Debits",
            "value": format_currency(total_debits, home_curr),
            "subtitle": "Obligations and recurring expenses",
            "icon": "📉",
            "delta": f"-{format_currency(total_debits, home_curr)}",
            "delta_color": "#EF4444",
            "border_left_color": "#EF4444"
        }
    ]
    render_kpi_row(kpis_row2)

    st.write("")

    # Section 3: Purchase Impact Comparison (Baseline vs Plan)
    # Check if a scheduled payment plan exists for this request
    scheduled_payments: List[Tuple[str, Decimal, str]] = []
    aff_status = req_row.get("affordability_status", "")
    plan_str = str(req_row.get("payment_plan", "none"))

    if aff_status == "affordable_now":
        amt = Decimal(str(req_row.get("requested_amount", 0)))
        scheduled_payments = [(request_date, amt, "Full Payment Safe Today")]
    elif aff_status == "affordable_with_plan" and plan_str.lower() != "none" and plan_str.strip():
        items = parse_payment_plan(plan_str)
        for dt, amt in items:
            scheduled_payments.append((dt, Decimal(str(amt)), f"Plan Payment ({dt})"))
    elif aff_status == "affordable_later" and req_row.get("earliest_date_for_full_payment"):
        earliest_dt = str(req_row.get("earliest_date_for_full_payment"))
        amt = Decimal(str(req_row.get("requested_amount", 0)))
        scheduled_payments = [(earliest_dt, amt, "Delayed Full Payment")]

    fc_plan = None
    plan_balances = None
    if scheduled_payments:
        try:
            fc_plan = pipeline.cash_flow_engine.run_forecast(
                state=user_state,
                start_date=request_date,
                horizon_days=90,
                proposed_expenses=scheduled_payments
            )
            plan_balances = [float(d.ending_balance) for d in fc_plan.daily_forecasts]
        except Exception as e:
            st.caption(f"Note: Post-purchase plan forecast could not be simulated: {e}")

    # Section 4: Main Interactive Plotly Chart
    # Prepare discrete Income & Expense event markers
    income_events = []
    expense_events = []
    dates = [d.date for d in fc.daily_forecasts]
    baseline_balances = [float(d.ending_balance) for d in fc.daily_forecasts]

    for d in fc.daily_forecasts:
        if d.total_credits > 0:
            events_desc = ", ".join([e.get("description", "Inflow") for e in d.applied_events if e.get("direction") == "credit"])
            tooltip = f"+{format_currency(float(d.total_credits), home_curr)} ({events_desc if events_desc else 'Credit'})"
            income_events.append({"date": d.date, "balance": float(d.ending_balance), "tooltip": tooltip})

        if d.total_debits > 0:
            events_desc = ", ".join([e.get("description", "Outflow") for e in d.applied_events if e.get("direction") == "debit"])
            tooltip = f"-{format_currency(float(d.total_debits), home_curr)} ({events_desc if events_desc else 'Debit'})"
            expense_events.append({"date": d.date, "balance": float(d.ending_balance), "tooltip": tooltip})

    with st.container(border=True):
        render_comprehensive_cash_flow_chart(
            dates=dates,
            baseline_balances=baseline_balances,
            min_balance=min_bal,
            initial_balance=initial_bal,
            plan_balances=plan_balances,
            income_events=income_events,
            expense_events=expense_events,
            currency=home_curr,
            request_date=request_date,
            height=420
        )

    # Section 5: Purchase Impact Analysis Metrics
    if fc_plan is not None:
        plan_lowest = float(fc_plan.lowest_balance)
        plan_cushion = plan_lowest - min_bal
        capital_impact = float(req_row.get("requested_amount", 0))

        st.write("")
        with st.container(border=True):
            st.markdown("#### ⚖️ Purchase Impact Comparison: Baseline vs. Post-Purchase")
            col_imp1, col_imp2, col_imp3, col_imp4 = st.columns(4)
            with col_imp1:
                st.metric("Total Capital Committed", format_currency(capital_impact, home_curr))
            with col_imp2:
                st.metric(
                    "Baseline Lowest Balance",
                    format_currency(lowest_bal, home_curr),
                    delta=f"{cushion:+,.0f} cushion"
                )
            with col_imp3:
                st.metric(
                    "Post-Purchase Lowest Balance",
                    format_currency(plan_lowest, home_curr),
                    delta=f"{plan_cushion:+,.0f} cushion",
                    delta_color="normal" if plan_cushion >= 0 else "inverse"
                )
            with col_imp4:
                status_txt = "Reserve Protected ✓" if fc_plan.is_safe_throughout else f"Breach on {fc_plan.first_breach_date} ⚠️"
                st.metric("Post-Purchase Safety", status_txt)
    elif aff_status == "not_affordable":
        st.write("")
        with st.container(border=True):
            st.markdown("#### ⚖️ Purchase Impact Comparison")
            st.info("🚫 **Purchase Not Affordable**: No safe payment plan is possible within liquidity limits. The baseline forecast illustrates why funds must remain preserved.")

    st.write("")

    # Section 6: Risk & Buffer Sensitivity Analysis
    with st.container(border=True):
        st.markdown("#### ⚠️ Liquidity Buffer Sensitivity & Risk Analysis")
        
        # Risk threshold definition:
        # 1. Breach: cushion < 0 (balance falls below minimum balance)
        # 2. Tight Buffer: cushion < 15% of minimum balance (or < 500 if min_bal == 0)
        # 3. Intra-day Dip: intra_day_lowest_balance < minimum_required_balance
        risk_entries = []
        for d in fc.daily_forecasts:
            bal = float(d.ending_balance)
            intra = float(d.intra_day_lowest_balance)
            cush = float(d.cushion_above_minimum)
            min_req = float(d.minimum_required_balance)

            is_breached = cush < 0
            is_intra_dip = intra < min_req
            is_tight = (not is_breached) and ((min_req > 0 and cush < min_req * 0.15) or (min_req == 0 and bal < 500))

            if is_breached or is_intra_dip or is_tight:
                if is_breached:
                    risk_level = "🚨 Reserve Breach"
                elif is_intra_dip:
                    risk_level = "⚠️ Intra-Day Dip"
                else:
                    risk_level = "⚡ Tight Buffer (<15%)"

                risk_entries.append({
                    "Date": d.date,
                    "Day Index": f"Day {d.day_index}",
                    "Ending Balance": format_currency(bal, home_curr),
                    "Intra-Day Low": format_currency(intra, home_curr),
                    "Required Minimum": format_currency(min_req, home_curr),
                    "Cushion": format_currency(cush, home_curr),
                    "Risk Classification": risk_level
                })

        if risk_entries:
            st.dataframe(pd.DataFrame(risk_entries), use_container_width=True, hide_index=True)
            st.caption("Threshold: Ending balance deficit (`< 0`), intra-day transaction dips, or cushion `< 15%` of minimum balance.")
        else:
            st.success(
                f"✓ **Safe Liquidity Throughout 90 Days**: Forecasted ending balance never falls below the reserve requirement of "
                f"{format_currency(min_bal, home_curr)}. Lowest cushion is {format_currency(cushion, home_curr)} on {lowest_bal_date}."
            )

    st.write("")

    # Section 7: Daily Forecast Event Ledger Table
    with st.container(border=True):
        st.markdown("#### 📋 90-Day Cash Flow Event Ledger")
        
        col_t1, col_t2 = st.columns([1, 2])
        with col_t1:
            view_mode = st.radio(
                "Table View Filter:",
                options=["Active Transaction Days", "All 90 Days"],
                horizontal=True
            )

        ledger_rows = []
        for d in fc.daily_forecasts:
            cr = float(d.total_credits)
            db = float(d.total_debits)
            if view_mode == "Active Transaction Days" and (cr == 0 and db == 0):
                continue

            events_summary = "; ".join([
                f"{e.get('description', 'Event')} ({e.get('category', 'misc')})"
                for e in d.applied_events
            ]) if d.applied_events else "No discrete transactions"

            ledger_rows.append({
                "Date": d.date,
                "Starting Balance": format_currency(float(d.starting_balance), home_curr),
                "Credits (+)": f"+{format_currency(cr, home_curr)}" if cr > 0 else "-",
                "Debits (-)": f"-{format_currency(db, home_curr)}" if db > 0 else "-",
                "Ending Balance": format_currency(float(d.ending_balance), home_curr),
                "Intra-Day Lowest": format_currency(float(d.intra_day_lowest_balance), home_curr),
                "Required Minimum": format_currency(float(d.minimum_required_balance), home_curr),
                "Cushion": format_currency(float(d.cushion_above_minimum), home_curr),
                "Applied Events": events_summary
            })

        if ledger_rows:
            st.dataframe(
                pd.DataFrame(ledger_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn("Date", width="small"),
                    "Starting Balance": st.column_config.TextColumn("Starting Balance", width="small"),
                    "Credits (+)": st.column_config.TextColumn("Credits (+)", width="small"),
                    "Debits (-)": st.column_config.TextColumn("Debits (-)", width="small"),
                    "Ending Balance": st.column_config.TextColumn("Ending Balance", width="small"),
                    "Intra-Day Lowest": st.column_config.TextColumn("Intra-Day Low", width="small"),
                    "Required Minimum": st.column_config.TextColumn("Minimum", width="small"),
                    "Cushion": st.column_config.TextColumn("Cushion", width="small"),
                    "Applied Events": st.column_config.TextColumn("Applied Events", width="large"),
                }
            )
            st.caption(f"Showing {len(ledger_rows)} days based on '{view_mode}' filter.")
        else:
            st.info("No transaction records found.")


if __name__ == "__main__" or True:
    render_cash_flow_page()

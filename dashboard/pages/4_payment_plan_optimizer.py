"""
Payment Option & Plan Optimizer Page — Multi-Option Evaluation, Installments & Repayment Schedules.
"""

from decimal import Decimal
import pandas as pd
import streamlit as st

from dashboard.utils.data_loader import (
    load_merged_data,
    get_decision_pipeline,
)
from dashboard.utils.formatting import (
    format_currency,
    format_date,
    get_status_badge,
    get_method_badge,
    parse_payment_plan,
)
from dashboard.components.charts import (
    render_payment_schedule_chart,
    render_payment_options_comparison_chart,
)


def render_payment_optimizer_page():
    # 1. Header Banner
    st.markdown(
        """
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            Payment Option & Plan Optimizer
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Deterministic multi-option ranking across provider terms, installment horizons, financing fees, and user cash invariants.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    df = load_merged_data()
    pipeline = get_decision_pipeline()

    if df.empty or pipeline is None:
        st.info("Decision Pipeline initializing...")
        return

    # 2. Status Filter & Request Selector
    col_filter, col_select = st.columns([1, 2])
    with col_filter:
        status_filter = st.selectbox(
            "Filter by Affordability Status:",
            options=[
                "All Statuses",
                "affordable_with_plan",
                "affordable_now",
                "affordable_later",
                "not_affordable",
            ],
            index=0,
            help="Filter requests by their final evaluation status.",
        )

    filtered_df = df if status_filter == "All Statuses" else df[df["affordability_status"] == status_filter]
    if filtered_df.empty:
        st.warning(f"No requests found matching status '{status_filter}'.")
        filtered_df = df

    with col_select:
        options = []
        for _, r in filtered_df.iterrows():
            amt = float(r.get("requested_amount", 0))
            method = str(r.get("recommended_payment_method", "none")).replace("_", " ").title()
            options.append(
                f"{r['request_id']} | User: {r.get('user_id')} | {method} (${amt:,.2f})"
            )
        selected_opt = st.selectbox(
            "Select Request to Inspect Payment Options:",
            options=options,
            index=0,
            help="Choose a request to evaluate vendor payment options and repayment schedules.",
        )
        selected_req_id = selected_opt.split(" | ")[0]

    req_row = df[df["request_id"] == selected_req_id].iloc[0].to_dict()
    user_id = str(req_row.get("user_id")).strip()

    # 3. Retrieve Reconstructed Financial State & Evaluate Options
    user_state = pipeline.get_user_state(user_id)
    profile = user_state.user_profile
    currency = getattr(profile, "home_currency", "USD")
    min_balance = float(getattr(profile, "minimum_balance_to_keep", 0.0))
    current_balance = float(getattr(user_state, "current_available_balance", 0.0))
    user_methods = getattr(profile, "considered_payment_methods", [])
    max_inst_months = getattr(profile, "max_installment_months", None)

    # Run optimizer
    opt_result = pipeline.payment_plan_optimizer.evaluate_options_for_request(
        req_row, state=user_state
    )

    requested_amount = float(req_row.get("requested_amount", 0.0))
    safe_amount = float(req_row.get("amount_safe_to_pay", 0.0))
    rec_method = str(req_row.get("recommended_payment_method", "none"))
    aff_status = str(req_row.get("affordability_status", "none"))
    payment_plan = str(req_row.get("payment_plan", "none"))
    earliest_date = str(req_row.get("earliest_date_for_full_payment", ""))
    desired_date = str(req_row.get("desired_completion_date", ""))
    request_date = str(req_row.get("request_date", ""))

    # 4. Top KPI Metric Summary Cards
    st.markdown("#### 📊 Request & Liquidity Baseline")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        with st.container(border=True):
            st.caption("Requested Amount")
            st.markdown(f"### {format_currency(requested_amount, currency)}")
            st.caption(f"Due: {desired_date}")
    with kpi2:
        with st.container(border=True):
            st.caption("Available Cash")
            st.markdown(f"### {format_currency(current_balance, currency)}")
            st.caption("At evaluation date")
    with kpi3:
        with st.container(border=True):
            st.caption("Minimum Reserve")
            st.markdown(f"### {format_currency(min_balance, currency)}")
            st.caption("Protected buffer")
    with kpi4:
        with st.container(border=True):
            st.caption("Safe to Pay Today")
            st.markdown(f"### {format_currency(safe_amount, currency)}")
            st.caption("Before adjustments")
    with kpi5:
        with st.container(border=True):
            st.caption("Recommended Status")
            st.markdown(get_status_badge(aff_status), unsafe_allow_html=True)
            st.markdown(get_method_badge(rec_method), unsafe_allow_html=True)

    # 5. User Constraints & Preferences Panel
    st.markdown("#### ⚙️ User Financial Preferences & Evaluation Constraints")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**Accepted Payment Methods:**")
            badges = " ".join([f"`{m}`" for m in user_methods]) if user_methods else "_None specified_"
            st.markdown(badges)
        with c2:
            st.markdown("**Max Installment Horizon:**")
            if max_inst_months is not None:
                st.markdown(f"**{max_inst_months} Months** (Options > {max_inst_months}m rejected)")
            else:
                st.markdown("**None** (Installments rejected)")
        with c3:
            st.markdown("**Evaluation Period:**")
            st.markdown(f"**{request_date}** ➔ **{desired_date}**")
            st.caption(f"Desired deadline for completion")
        with c4:
            st.markdown("**Provider Options Evaluated:**")
            st.markdown(f"**{len(opt_result.evaluated_options)} Options** in catalog")
            feasible_count = sum(1 for o in opt_result.evaluated_options if o.is_feasible)
            st.caption(f"{feasible_count} feasible / {len(opt_result.evaluated_options) - feasible_count} rejected")

    # 6. Selected Option / Recommendation Hero Banner
    st.markdown("#### 🏆 Decision & Winning Payment Option")
    with st.container(border=True):
        if opt_result.has_feasible_option and opt_result.selected_option is not None:
            sel = opt_result.selected_option
            st.success(
                f"**Winning Option: `{sel.payment_option_id}`** — "
                f"{sel.number_of_payments} payments of {format_currency(float(sel.payment_amount), currency)} "
                f"({sel.payment_method.replace('_', ' ').title()})"
            )
            h1, h2, h3, h4 = st.columns(4)
            with h1:
                st.metric("Total Payable", format_currency(float(sel.total_amount_paid), currency))
            with h2:
                st.metric("Financing Fee", format_currency(float(sel.financing_fee), currency))
            with h3:
                st.metric("First Payment", format_date(sel.first_payment_date))
            with h4:
                st.metric("Final Payment", format_date(sel.last_payment_date))

            st.markdown(f"**Selection Explanation:** {opt_result.selection_explanation}")

        elif rec_method == "partial_payment":
            st.info(
                f"**Recommended: Custom Partial Payment Plan (2 Payments)** — "
                f"Safe amount {format_currency(safe_amount, currency)} on {request_date}, remainder "
                f"{format_currency(requested_amount - safe_amount, currency)} on {earliest_date}."
            )
            p1, p2, p3 = st.columns(3)
            with p1:
                st.metric("Total Payable", format_currency(requested_amount, currency))
            with p2:
                st.metric("Financing Fee", "$0.00")
            with p3:
                st.metric("Completion Date", format_date(earliest_date))
            st.markdown(f"**Decision Explanation:** {req_row.get('decision_explanation', '')}")

        elif rec_method == "full_payment":
            st.success(
                f"**Recommended: Full Payment Safe Today** — "
                f"The user can safely pay the full amount of {format_currency(requested_amount, currency)} "
                f"on {request_date} without financing fees or balance violations."
            )
            st.markdown(f"**Decision Explanation:** {req_row.get('decision_explanation', '')}")

        elif rec_method == "wait":
            st.warning(
                f"**Recommended: Wait until {format_date(earliest_date)}** — "
                f"No vendor installment option was feasible, but cash flow allows safe full payment by {earliest_date} "
                f"before desired completion date {desired_date}."
            )
            st.markdown(f"**Decision Explanation:** {req_row.get('decision_explanation', '')}")

        else:
            st.error(
                f"**Recommendation: Not Recommended** — "
                f"Neither immediate payment, vendor installments, nor 90-day cash flow forecast allow this purchase "
                f"without breaching the user's minimum reserve of {format_currency(min_balance, currency)}."
            )
            st.markdown(f"**Decision Explanation:** {req_row.get('decision_explanation', '')}")

    # 7. Provider Payment Options Comparison Table & Chart
    st.markdown("#### 📋 Provider Options Evaluation Matrix")
    if opt_result.evaluated_options:
        eval_rows = []
        for opt in opt_result.evaluated_options:
            is_win = (
                opt_result.selected_option is not None
                and opt.payment_option_id == opt_result.selected_option.payment_option_id
            )
            status_text = "🏆 Selected" if is_win else ("✓ Feasible" if opt.is_feasible else "✕ Infeasible")
            reason_text = "Selected winning option" if is_win else (opt.rejection_reason or "Feasible candidate")

            eval_rows.append({
                "Option ID": opt.payment_option_id,
                "Method": opt.payment_method.replace("_", " ").title(),
                "Payments": opt.number_of_payments,
                "Amount / Payment": format_currency(float(opt.payment_amount), currency),
                "Financing Fee": format_currency(float(opt.financing_fee), currency),
                "Total Payable": format_currency(float(opt.total_amount_paid), currency),
                "First Due": format_date(opt.first_payment_date),
                "Final Due": format_date(opt.last_payment_date),
                "Status": status_text,
                "Evaluation Finding": reason_text,
            })

        st.dataframe(
            pd.DataFrame(eval_rows),
            use_container_width=True,
            hide_index=True,
        )

        # Plotly Option Cost Comparison Chart
        render_payment_options_comparison_chart(
            opt_result.evaluated_options, currency=currency, height=320
        )
    else:
        st.info("No provider payment options are registered for this request.")

    # 8. Payment Schedule Deep-Dive & Due Date Ledger
    st.markdown("#### 📅 Active Repayment Schedule & Cash Outflow Timeline")
    parsed_schedule = parse_payment_plan(payment_plan)

    if parsed_schedule:
        total_plan_cost = sum(amt for _, amt in parsed_schedule)
        col_chart, col_ledger = st.columns([3, 2])

        with col_chart:
            render_payment_schedule_chart(
                parsed_schedule,
                total_cost=total_plan_cost,
                currency=currency,
                height=360,
            )

        with col_ledger:
            st.markdown("**Payment Schedule Breakdown**")
            ledger_data = []
            cum = 0.0
            for idx, (dt, amt) in enumerate(parsed_schedule, 1):
                cum += amt
                rem = max(0.0, total_plan_cost - cum)
                pct = (cum / total_plan_cost * 100.0) if total_plan_cost > 0 else 100.0
                ledger_data.append({
                    "Payment #": f"#{idx}",
                    "Due Date": dt,
                    "Amount": format_currency(amt, currency),
                    "Cum. Paid": format_currency(cum, currency),
                    "Remaining": format_currency(rem, currency),
                    "% Paid": f"{pct:.1f}%",
                })
            st.dataframe(pd.DataFrame(ledger_data), use_container_width=True, hide_index=True)
    else:
        with st.container(border=True):
            st.markdown(
                f"**No Active Payment Schedule** — The decision for this request is `{rec_method}` "
                f"with payment plan `{payment_plan}`. No installment outflows are scheduled against the user's cash reserves."
            )

    # 9. Cross-Method Affordability Comparison Matrix
    st.markdown("#### ⚖️ Cross-Method Affordability Comparison")
    st.caption("How alternative financial paths compare for this exact purchase request:")

    m1, m2, m3, m4 = st.columns(4)

    # 1. Full Payment
    with m1:
        with st.container(border=True):
            st.markdown("##### 💳 Full Payment")
            is_full_safe = safe_amount >= requested_amount
            if is_full_safe:
                st.markdown("<span style='color:#10B981; font-weight:700;'>✓ Affordable Now</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:#EF4444; font-weight:700;'>✕ Deficit Today</span>", unsafe_allow_html=True)
            st.markdown(f"**Cost:** {format_currency(requested_amount, currency)}")
            st.markdown(f"**Fee:** $0.00")
            st.markdown(f"**Timing:** Immediate ({request_date})")
            if not is_full_safe:
                st.caption(f"Shortfall: {format_currency(requested_amount - safe_amount, currency)}")
            else:
                st.caption("Zero interest or delay")

    # 2. Provider Installments
    with m2:
        with st.container(border=True):
            st.markdown("##### 📊 Vendor Installments")
            if opt_result.has_feasible_option:
                st.markdown("<span style='color:#2563EB; font-weight:700;'>✓ Feasible Plan</span>", unsafe_allow_html=True)
                opt = opt_result.selected_option
                st.markdown(f"**Cost:** {format_currency(float(opt.total_amount_paid), currency)}")
                st.markdown(f"**Fee:** {format_currency(float(opt.financing_fee), currency)}")
                st.markdown(f"**Payments:** {opt.number_of_payments} payments")
                st.caption(f"Finishes: {format_date(opt.last_payment_date)}")
            else:
                st.markdown("<span style='color:#EF4444; font-weight:700;'>✕ No Valid Option</span>", unsafe_allow_html=True)
                st.markdown(f"**Cost:** Provider terms")
                st.markdown(f"**Fee:** Provider fee")
                st.markdown(f"**Status:** Infeasible / Exceeded")
                st.caption("Breaches limits or preferences")

    # 3. Partial Payment
    with m3:
        with st.container(border=True):
            st.markdown("##### ✂️ Partial Split")
            allows_part = bool(req_row.get("allows_partial_payment", False))
            user_part = "partial_payment" in user_methods
            is_part_viable = (
                allows_part
                and user_part
                and 0 < safe_amount < requested_amount
                and earliest_date != ""
                and earliest_date <= desired_date
            )
            if is_part_viable:
                st.markdown("<span style='color:#2563EB; font-weight:700;'>✓ Viable Split</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:#64748B; font-weight:700;'>— Not Applicable</span>", unsafe_allow_html=True)
            st.markdown(f"**Cost:** {format_currency(requested_amount, currency)}")
            st.markdown(f"**Fee:** $0.00")
            st.markdown(f"**Payments:** Exactly 2 payments")
            if is_part_viable:
                st.caption(f"Split between today & {earliest_date}")
            elif not allows_part:
                st.caption("Seller forbids partial payment")
            elif not user_part:
                st.caption("User does not accept partial payment")
            else:
                st.caption("Cash flow timing incompatible")

    # 4. Wait for Full Cash
    with m4:
        with st.container(border=True):
            st.markdown("##### ⏳ Wait for Full Cash")
            if earliest_date and earliest_date <= desired_date:
                st.markdown("<span style='color:#F59E0B; font-weight:700;'>✓ Safe by Deadline</span>", unsafe_allow_html=True)
                st.markdown(f"**Cost:** {format_currency(requested_amount, currency)}")
                st.markdown(f"**Fee:** $0.00")
                st.markdown(f"**Date:** {format_date(earliest_date)}")
                st.caption("Meets user desired completion date")
            elif earliest_date:
                st.markdown("<span style='color:#EF4444; font-weight:700;'>✕ Past Deadline</span>", unsafe_allow_html=True)
                st.markdown(f"**Cost:** {format_currency(requested_amount, currency)}")
                st.markdown(f"**Fee:** $0.00")
                st.markdown(f"**Date:** {format_date(earliest_date)}")
                st.caption(f"Exceeds desired date {desired_date}")
            else:
                st.markdown("<span style='color:#EF4444; font-weight:700;'>✕ Not in 90 Days</span>", unsafe_allow_html=True)
                st.markdown(f"**Cost:** {format_currency(requested_amount, currency)}")
                st.markdown(f"**Fee:** $0.00")
                st.markdown(f"**Date:** None")
                st.caption("No safe full date within 90 days")


if __name__ == "__main__" or True:
    render_payment_optimizer_page()

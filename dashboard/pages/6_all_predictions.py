"""
All Predictions Page — Searchable Table, Multi-Criteria Filtering & Official Output CSV Exporter.
"""

from io import StringIO
import pandas as pd
import streamlit as st

from dashboard.utils.data_loader import (
    load_predictions_data,
    load_merged_data,
)
from dashboard.utils.formatting import (
    format_currency,
    COLOR_AFFORDABLE_NOW,
    COLOR_AFFORDABLE_WITH_PLAN,
    COLOR_AFFORDABLE_LATER,
    COLOR_NOT_AFFORDABLE,
)

REQUIRED_OUTPUT_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]


def render_all_predictions_page():
    # 1. Header Banner
    st.markdown(
        """
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            All Predictions & Submission Catalog
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Interactive exploration of all 250 evaluation requests, multidimensional filtering, and strict challenge-contract export.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    pred_df = load_predictions_data()
    merged_df = load_merged_data()

    if pred_df.empty:
        st.error("No predictions data loaded from output.csv.")
        return

    total_records = len(pred_df)

    # 2. Summary KPI Metrics Row
    aff_now_count = int((pred_df["affordability_status"] == "affordable_now").sum())
    aff_plan_count = int((pred_df["affordability_status"] == "affordable_with_plan").sum())
    aff_later_count = int((pred_df["affordability_status"] == "affordable_later").sum())
    not_aff_count = int((pred_df["affordability_status"] == "not_affordable").sum())

    st.markdown("#### 📊 Evaluation Decisions Summary")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

    with kpi1:
        with st.container(border=True):
            st.caption("Total Requests")
            st.markdown(f"### {total_records}")
            st.caption("100% evaluated")

    with kpi2:
        with st.container(border=True):
            st.caption("Affordable Now")
            st.markdown(
                f"<h3 style='color:{COLOR_AFFORDABLE_NOW}; margin:0;'>{aff_now_count}</h3>",
                unsafe_allow_html=True,
            )
            pct_now = (aff_now_count / total_records * 100) if total_records else 0
            st.caption(f"{pct_now:.1f}% of catalog")

    with kpi3:
        with st.container(border=True):
            st.caption("Affordable w/ Plan")
            st.markdown(
                f"<h3 style='color:{COLOR_AFFORDABLE_WITH_PLAN}; margin:0;'>{aff_plan_count}</h3>",
                unsafe_allow_html=True,
            )
            pct_plan = (aff_plan_count / total_records * 100) if total_records else 0
            st.caption(f"{pct_plan:.1f}% of catalog")

    with kpi4:
        with st.container(border=True):
            st.caption("Affordable Later")
            st.markdown(
                f"<h3 style='color:{COLOR_AFFORDABLE_LATER}; margin:0;'>{aff_later_count}</h3>",
                unsafe_allow_html=True,
            )
            pct_later = (aff_later_count / total_records * 100) if total_records else 0
            st.caption(f"{pct_later:.1f}% of catalog")

    with kpi5:
        with st.container(border=True):
            st.caption("Not Affordable")
            st.markdown(
                f"<h3 style='color:{COLOR_NOT_AFFORDABLE}; margin:0;'>{not_aff_count}</h3>",
                unsafe_allow_html=True,
            )
            pct_not = (not_aff_count / total_records * 100) if total_records else 0
            st.caption(f"{pct_not:.1f}% of catalog")

    # 3. Search & Filter Controls
    st.markdown("#### 🔍 Filter & Search Predictions")
    with st.container(border=True):
        f_row1_c1, f_row1_c2, f_row1_c3 = st.columns([2, 1, 1])

        with f_row1_c1:
            search_query = st.text_input(
                "Search Request ID or Decision Explanation:",
                placeholder="e.g. request_26, installment, emergency reserve, buffer...",
                help="Search by substring in request ID or decision explanation text.",
            )

        with f_row1_c2:
            status_options = sorted(pred_df["affordability_status"].unique().tolist())
            selected_statuses = st.multiselect(
                "Affordability Status:",
                options=status_options,
                default=[],
                placeholder="All statuses",
            )

        with f_row1_c3:
            method_options = sorted(pred_df["recommended_payment_method"].unique().tolist())
            selected_methods = st.multiselect(
                "Payment Method:",
                options=method_options,
                default=[],
                placeholder="All methods",
            )

        # Numerical range filters
        f_row2_c1, f_row2_c2 = st.columns(2)

        has_requested_amt = "requested_amount" in merged_df.columns
        max_req_val = float(merged_df["requested_amount"].max()) if has_requested_amt else 100000.0
        max_safe_val = float(pred_df["amount_safe_to_pay"].max()) if not pred_df.empty else 100000.0

        with f_row2_c1:
            safe_range = st.slider(
                "Safe Amount Today Range:",
                min_value=0.0,
                max_value=max_safe_val,
                value=(0.0, max_safe_val),
                step=max(1.0, max_safe_val / 200.0),
                format="$%.2f",
            )

        with f_row2_c2:
            if has_requested_amt:
                req_range = st.slider(
                    "Requested Purchase Amount Range:",
                    min_value=0.0,
                    max_value=max_req_val,
                    value=(0.0, max_req_val),
                    step=max(1.0, max_req_val / 200.0),
                    format="$%.2f",
                )
            else:
                req_range = (0.0, float("inf"))

    # 4. Apply Filters to Dataset
    filtered_df = merged_df.copy()

    # Search filter
    if search_query and search_query.strip():
        q = search_query.strip().lower()
        id_match = filtered_df["request_id"].astype(str).str.lower().str.contains(q, regex=False)
        expl_match = (
            filtered_df["decision_explanation"].astype(str).str.lower().str.contains(q, regex=False)
        )
        filtered_df = filtered_df[id_match | expl_match]

    # Status filter
    if selected_statuses:
        filtered_df = filtered_df[filtered_df["affordability_status"].isin(selected_statuses)]

    # Payment method filter
    if selected_methods:
        filtered_df = filtered_df[filtered_df["recommended_payment_method"].isin(selected_methods)]

    # Safe amount range
    filtered_df = filtered_df[
        (filtered_df["amount_safe_to_pay"] >= safe_range[0])
        & (filtered_df["amount_safe_to_pay"] <= safe_range[1])
    ]

    # Requested amount range
    if has_requested_amt:
        filtered_df = filtered_df[
            (filtered_df["requested_amount"] >= req_range[0])
            & (filtered_df["requested_amount"] <= req_range[1])
        ]

    # 5. Table Header & Download Bar
    col_count, col_exp_filt, col_exp_all = st.columns([2, 1, 1])

    with col_count:
        st.markdown(
            f"**Displaying {len(filtered_df):,} of {total_records:,} predictions** "
            f"({(len(filtered_df)/total_records*100):.1f}% matching filters)"
        )

    with col_exp_filt:
        # Export filtered predictions (Strictly 8 required columns)
        filtered_export = filtered_df[REQUIRED_OUTPUT_COLUMNS].copy()
        filt_csv_bytes = filtered_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"📥 Filtered CSV ({len(filtered_export)})",
            data=filt_csv_bytes,
            file_name="output_filtered.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download currently filtered rows formatted to official output schema.",
        )

    with col_exp_all:
        # Export complete output.csv (Strictly 8 required columns)
        full_export = pred_df[REQUIRED_OUTPUT_COLUMNS].copy()
        full_csv_bytes = full_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"📥 Official output.csv (250)",
            data=full_csv_bytes,
            file_name="output.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download complete 250 predictions in exact HackerRank competition format.",
        )

    # 6. Interactive Predictions Table
    display_cols = [
        "request_id",
        "requested_amount",
        "amount_safe_to_pay",
        "affordability_status",
        "recommended_payment_method",
        "payment_plan",
        "earliest_date_for_full_payment",
        "spending_changes_needed",
        "decision_explanation",
    ]
    # Keep only available display columns
    active_display_cols = [c for c in display_cols if c in filtered_df.columns]

    st.dataframe(
        filtered_df[active_display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "request_id": st.column_config.TextColumn("Request ID", width="small"),
            "requested_amount": st.column_config.NumberColumn(
                "Requested ($)", format="$%.2f", width="small"
            ),
            "amount_safe_to_pay": st.column_config.NumberColumn(
                "Safe Today ($)", format="$%.2f", width="small"
            ),
            "affordability_status": st.column_config.TextColumn(
                "Affordability Status", width="medium"
            ),
            "recommended_payment_method": st.column_config.TextColumn(
                "Payment Method", width="small"
            ),
            "payment_plan": st.column_config.TextColumn("Payment Plan", width="medium"),
            "earliest_date_for_full_payment": st.column_config.TextColumn(
                "Earliest Full Date", width="small"
            ),
            "spending_changes_needed": st.column_config.TextColumn(
                "Spending Changes", width="medium"
            ),
            "decision_explanation": st.column_config.TextColumn(
                "Decision Explanation", width="large"
            ),
        },
    )

    # 7. Request Details Navigation Panel
    st.markdown("#### 🎯 Quick Request Inspection & Deep-Dive Navigation")
    with st.container(border=True):
        col_nav_sel, col_nav_btn = st.columns([3, 1])

        inspect_options = (
            filtered_df["request_id"].tolist()
            if not filtered_df.empty
            else pred_df["request_id"].tolist()
        )

        with col_nav_sel:
            target_req_id = st.selectbox(
                "Select a Request ID to inspect:",
                options=inspect_options,
                help="Choose any request to inspect full details, cash flow curves, and provider terms.",
            )

        target_row = pred_df[pred_df["request_id"] == target_req_id].iloc[0]

        with col_nav_btn:
            st.write("")  # Alignment
            if st.button("Inspect in Decision Explorer ➔", use_container_width=True):
                st.session_state["selected_request_id"] = target_req_id
                try:
                    st.switch_page("pages/2_decision_explorer.py")
                except Exception:
                    st.info(
                        f"Target request `{target_req_id}` preselected! Open **Purchase Decision Explorer** in the sidebar."
                    )

        # Quick summary card of the chosen request
        st.caption(
            f"**Selected Request:** `{target_row['request_id']}` | "
            f"**Status:** `{target_row['affordability_status']}` | "
            f"**Method:** `{target_row['recommended_payment_method']}` | "
            f"**Safe Outlay Today:** ${float(target_row['amount_safe_to_pay']):,.2f} | "
            f"**Plan:** `{target_row['payment_plan']}`"
        )
        st.markdown(
            f"> _{target_row['decision_explanation']}_"
        )


if __name__ == "__main__" or True:
    render_all_predictions_page()

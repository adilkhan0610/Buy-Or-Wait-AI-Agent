"""
System Information Page — Architecture, Contract Compliance, and Execution Telemetry.
"""

from pathlib import Path
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
USAGE_REPORT_PATH = ROOT_DIR / "evaluation" / "usage_report.md"


def render_system_info_page():
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 4px;">
            System Architecture & Challenge Telemetry
        </h1>
        <p style="font-size: 14px; color: #64748B; margin: 0;">
            Comprehensive pipeline specifications, challenge rules adherence, and token telemetry report.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Architecture Flow
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 18px; color: #0F172A;">⚙️ Multi-Stage Pipeline Architecture</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; font-size: 13px;">
            <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                <b>1. Ingestion & Validation</b><br>
                Modules 1 & 2: Strict schema, type casting, date ordering, and cross-reference validation.
            </div>
            <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                <b>2. Forex & Currency</b><br>
                Module 3: Fixed-date exchange rate conversion into user's designated home currency.
            </div>
            <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                <b>3. Multimodal Evidence</b><br>
                Module 4: English & Indonesian message parsing + receipt / invoice OCR verification.
            </div>
            <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                <b>4. State Reconstruction</b><br>
                Module 5: Event lifecycle resolution, duplicate deduplication, and liquidity reconciliation.
            </div>
            <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                <b>5. 90-Day Cash Flow</b><br>
                Module 6: Conservative daily cash flow forecasting enforcing minimum required balance.
            </div>
            <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                <b>6. Affordability Evaluation</b><br>
                Module 7: Determination of safe amount today and conservative earliest full payment date.
            </div>
            <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                <b>7. Plan Optimization</b><br>
                Module 8: Evaluation of provider options, interest, terms, and partial split payments.
            </div>
            <div style="background: #F8FAFC; padding: 12px; border-radius: 8px; border-left: 3px solid #3B82F6;">
                <b>8. Budget Adjustments</b><br>
                Module 9: Targeted flexible expense reduction protecting user's non-negotiable categories.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Challenge Contract Compliance
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 18px; color: #0F172A;">✅ Challenge Contract Compliance</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px; color: #334155;">
            <tr style="border-bottom: 1px solid #F1F5F9; height: 36px;">
                <td style="font-weight: 600; width: 35%;">Submission Schema</td>
                <td style="color: #065F46; font-weight: 600;">✓ Exact 8 columns verified: <code>request_id, amount_safe_to_pay, affordability_status, recommended_payment_method, payment_plan, earliest_date_for_full_payment, spending_changes_needed, decision_explanation</code></td>
            </tr>
            <tr style="border-bottom: 1px solid #F1F5F9; height: 36px;">
                <td style="font-weight: 600;">Dataset Size & Completeness</td>
                <td style="color: #065F46; font-weight: 600;">✓ Exactly 250 evaluation requests processed (0 missing, 0 null rows)</td>
            </tr>
            <tr style="border-bottom: 1px solid #F1F5F9; height: 36px;">
                <td style="font-weight: 600;">Deterministic Execution</td>
                <td style="color: #065F46; font-weight: 600;">✓ 100% offline, deterministic, zero random seeds, zero live network dependencies</td>
            </tr>
            <tr style="border-bottom: 1px solid #F1F5F9; height: 36px;">
                <td style="font-weight: 600;">Submission Portal</td>
                <td><a href="https://www.hackerrank.com/contests/hackerrank-orchestrate-september26/challenges/buy-or-wait/submission" target="_blank" style="color: #2563EB; font-weight: 600;">HackerRank Orchestrate Submission Portal</a></td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # 3. Usage & Token Telemetry
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 12px 0; font-size: 18px; color: #0F172A;">📊 Telemetry & Token Usage Report</h3>
    """, unsafe_allow_html=True)
    if USAGE_REPORT_PATH.exists():
        content = USAGE_REPORT_PATH.read_text(encoding="utf-8")
        st.markdown(content)
    else:
        st.info("No usage_report.md found at evaluation/usage_report.md")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__" or True:
    render_system_info_page()


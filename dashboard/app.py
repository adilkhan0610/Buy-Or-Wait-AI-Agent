"""
Buy or Wait? — AI-Powered Financial Affordability Decision Agent
Streamlit Interactive Dashboard Application.
Fintech theme with dark navy sidebar, responsive navigation, and tight whitespace.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path so 'dashboard' and 'code' packages resolve cleanly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# 1. Page Configuration (must be called first)
st.set_page_config(
    page_title="Buy or Wait? — Financial Affordability Agent",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject Custom Clean Fintech Theme CSS
CUSTOM_CSS = """
<style>
/* Font and Base Typography */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

/* Main Container Background & Tight Whitespace */
.stApp {
    background-color: #F8FAFC !important;
    color: #0F172A;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}

/* Transparent Header to keep sidebar toggle button accessible */
header[data-testid="stHeader"] {
    background: transparent !important;
    z-index: 100;
}

/* Sidebar Toggle Button styling */
[data-testid="stSidebarCollapseButton"] {
    color: #0F172A !important;
}

/* Sidebar Styling: Premium Dark Navy */
section[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid #1E293B !important;
    min-width: 290px !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
    color: #F1F5F9;
}

/* Sidebar Navigation Items */
section[data-testid="stSidebar"] a {
    color: #CBD5E1 !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    padding: 6px 12px !important;
    transition: all 0.15s ease-in-out !important;
}

section[data-testid="stSidebar"] a:hover {
    color: #FFFFFF !important;
    background-color: #1E293B !important;
}

section[data-testid="stSidebar"] a[aria-current="page"] {
    color: #FFFFFF !important;
    background-color: #2563EB !important;
    font-weight: 700 !important;
}

/* Clean up footer */
footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# 3. Setup Multi-Page Navigation FIRST (official Streamlit standard)
PAGES_DIR = Path(__file__).resolve().parent / "pages"

sections = {
    "Overview & Analysis": [
        st.Page(str(PAGES_DIR / "1_overview.py"), title="Executive Overview", icon="📊", default=True),
        st.Page(str(PAGES_DIR / "2_decision_explorer.py"), title="Decision Explorer", icon="🔍"),
    ],
    "Financial Simulation": [
        st.Page(str(PAGES_DIR / "3_cash_flow_forecast.py"), title="90-Day Cash Flow Forecast", icon="📈"),
        st.Page(str(PAGES_DIR / "4_payment_plan_optimizer.py"), title="Payment Plan Optimizer", icon="💳"),
        st.Page(str(PAGES_DIR / "5_spending_optimization.py"), title="Spending Optimization", icon="✂️"),
    ],
    "Submission & System": [
        st.Page(str(PAGES_DIR / "6_all_predictions.py"), title="All Predictions & CSV", icon="📋"),
        st.Page(str(PAGES_DIR / "7_system_info.py"), title="System & Telemetry", icon="⚙️"),
    ]
}

nav = st.navigation(sections, position="sidebar")

# 4. Render Sidebar Branding & Context
with st.sidebar:
    branding_html = (
        '<div style="padding: 6px 0 16px 0; border-bottom: 1px solid #1E293B; margin-bottom: 14px;">'
        '<div style="display: inline-block; padding: 2px 7px; background: #1E293B; border-radius: 4px; '
        'font-size: 10px; font-weight: 700; color: #38BDF8; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 6px;">'
        'HackerRank Orchestrate 2026'
        '</div>'
        '<div style="display: flex; align-items: center; gap: 8px;">'
        '<span style="font-size: 24px;">💳</span>'
        '<div>'
        '<h2 style="margin: 0; font-size: 18px; font-weight: 800; color: #FFFFFF; line-height: 1.1;">'
        'Buy or Wait?'
        '</h2>'
        '<div style="font-size: 11px; color: #94A3B8; font-weight: 500;">'
        'AI Financial Affordability Agent'
        '</div>'
        '</div>'
        '</div>'
        '<div style="font-size: 11.5px; color: #94A3B8; line-height: 1.4; margin-top: 10px;">'
        'Autonomous financial agent evaluating 250 purchase requests against 90-day cash flow projections and liquidity invariants.'
        '</div>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(branding_html)
    else:
        st.markdown(branding_html, unsafe_allow_html=True)

    # Footer status & challenge portal link
    footer_html = (
        '<div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #1E293B; font-size: 11px; color: #94A3B8;">'
        '<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">'
        '<span style="width: 8px; height: 8px; border-radius: 50%; background: #10B981; display: inline-block;"></span>'
        '<span style="color: #F1F5F9; font-weight: 600;">Engine Active (Deterministic)</span>'
        '</div>'
        '<div><b>Evaluated:</b> 250 Requests</div>'
        '<div><b>Coverage:</b> 100% Validated</div>'
        '<div style="margin-top: 10px;">'
        '<a href="https://www.hackerrank.com/contests/hackerrank-orchestrate-september26/challenges/buy-or-wait/submission" '
        'target="_blank" style="color: #38BDF8; text-decoration: none; font-weight: 600;">'
        '↗ Submission Portal'
        '</a>'
        '</div>'
        '</div>'
    )
    if hasattr(st, "html"):
        st.html(footer_html)
    else:
        st.markdown(footer_html, unsafe_allow_html=True)

# 5. Execute Selected Page
nav.run()

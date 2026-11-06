"""
Reusable Metric Cards with clean modern HTML/CSS styling for Streamlit.
"""

from typing import List, Dict, Any, Optional
import streamlit as st


def render_metric_card(
    title: str,
    value: str,
    subtitle: Optional[str] = None,
    icon: Optional[str] = None,
    delta: Optional[str] = None,
    delta_color: str = "#10B981",
    border_left_color: Optional[str] = None
) -> None:
    """Render a single modern styled metric card."""
    border_style = f"border-left: 4px solid {border_left_color};" if border_left_color else ""
    
    icon_html = f'<span style="font-size: 22px; margin-right: 8px;">{icon}</span>' if icon else ""
    subtitle_html = f'<div style="font-size: 12px; color: #64748B; margin-top: 4px;">{subtitle}</div>' if subtitle else ""
    delta_html = f'<span style="font-size: 12px; font-weight: 600; color: {delta_color}; margin-left: 8px;">{delta}</span>' if delta else ""
    
    card_html = f"""
    <div style="
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 18px 20px;
        border: 1px solid #E2E8F0;
        {border_style}
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 100px;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <div style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">
                {title}
            </div>
            {icon_html}
        </div>
        <div style="display: flex; align-items: baseline;">
            <div style="font-size: 26px; font-weight: 700; color: #0F172A; line-height: 1.1;">
                {value}
            </div>
            {delta_html}
        </div>
        {subtitle_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_kpi_row(cards: List[Dict[str, Any]]) -> None:
    """
    Render a horizontal row of metric cards.
    Each item in cards is a dict with keys:
    - title
    - value
    - subtitle (optional)
    - icon (optional)
    - delta (optional)
    - delta_color (optional)
    - border_left_color (optional)
    """
    if not cards:
        return
    cols = st.columns(len(cards))
    for i, card in enumerate(cards):
        with cols[i]:
            render_metric_card(
                title=card.get("title", ""),
                value=card.get("value", ""),
                subtitle=card.get("subtitle"),
                icon=card.get("icon"),
                delta=card.get("delta"),
                delta_color=card.get("delta_color", "#10B981"),
                border_left_color=card.get("border_left_color")
            )


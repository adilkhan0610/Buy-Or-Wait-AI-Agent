"""
Reusable Metric Cards with clean modern HTML/CSS styling for Streamlit.
Constructed without multiline indentation to prevent CommonMark code block parsing.
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
    """Render a single modern styled metric card cleanly."""
    border_style = f"border-left: 4px solid {border_left_color};" if border_left_color else ""
    icon_html = f'<span style="font-size: 18px;">{icon}</span>' if icon else ""
    subtitle_html = f'<div style="font-size: 11px; color: #64748B; margin-top: 4px; line-height: 1.3;">{subtitle}</div>' if subtitle else ""
    delta_html = f'<span style="font-size: 11px; font-weight: 600; color: {delta_color}; background-color: {delta_color}18; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">{delta}</span>' if delta else ""
    
    card_html = (
        f'<div style="background-color: #FFFFFF; border-radius: 10px; padding: 14px 16px; '
        f'border: 1px solid #E2E8F0; {border_style} box-shadow: 0 1px 3px rgba(0,0,0,0.04); '
        f'display: flex; flex-direction: column; justify-content: space-between; min-height: 98px; box-sizing: border-box;">'
        f'<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">'
        f'<span style="font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">{title}</span>'
        f'{icon_html}'
        f'</div>'
        f'<div style="display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px;">'
        f'<span style="font-size: 22px; font-weight: 700; color: #0F172A; line-height: 1.1;">{value}</span>'
        f'{delta_html}'
        f'</div>'
        f'{subtitle_html}'
        f'</div>'
    )
    if hasattr(st, "html"):
        st.html(card_html)
    else:
        st.markdown(card_html, unsafe_allow_html=True)


def render_kpi_row(cards: List[Dict[str, Any]]) -> None:
    """Render a horizontal row of metric cards with equal spacing."""
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

"""
Formatting utilities for the Buy or Wait? Financial Decision Dashboard.
Provides color constants, currency formatters, date formatters, and HTML badge generators.
"""

from typing import List, Tuple, Optional
import html


# Theme color palette
COLOR_AFFORDABLE_NOW = "#10B981"       # Emerald Green
COLOR_AFFORDABLE_WITH_PLAN = "#2563EB"  # Royal Blue
COLOR_AFFORDABLE_LATER = "#F59E0B"      # Warm Amber
COLOR_NOT_AFFORDABLE = "#EF4444"        # Rose Red

STATUS_COLORS = {
    "affordable_now": {
        "badge_bg": "#ECFDF5",
        "badge_border": "#A7F3D0",
        "text": "#065F46",
        "color": COLOR_AFFORDABLE_NOW,
        "label": "Affordable Now",
        "icon": "✓"
    },
    "affordable_with_plan": {
        "badge_bg": "#EFF6FF",
        "badge_border": "#BFDBFE",
        "text": "#1E40AF",
        "color": COLOR_AFFORDABLE_WITH_PLAN,
        "label": "Affordable with Plan",
        "icon": "📅"
    },
    "affordable_later": {
        "badge_bg": "#FFFBEB",
        "badge_border": "#FDE68A",
        "text": "#92400E",
        "color": COLOR_AFFORDABLE_LATER,
        "label": "Affordable Later",
        "icon": "⏳"
    },
    "not_affordable": {
        "badge_bg": "#FEF2F2",
        "badge_border": "#FECACA",
        "text": "#991B1B",
        "color": COLOR_NOT_AFFORDABLE,
        "label": "Not Affordable",
        "icon": "✕"
    }
}

METHOD_CONFIG = {
    "full_payment": {"label": "Full Payment", "bg": "#ECFDF5", "border": "#A7F3D0", "text": "#065F46", "icon": "💳"},
    "partial_payment": {"label": "Partial Payment", "bg": "#EFF6FF", "border": "#BFDBFE", "text": "#1E40AF", "icon": "✂️"},
    "installments": {"label": "Installments", "bg": "#F5F3FF", "border": "#DDD6FE", "text": "#5B21B6", "icon": "📊"},
    "wait": {"label": "Wait", "bg": "#FFFBEB", "border": "#FDE68A", "text": "#92400E", "icon": "⏳"},
    "not_recommended": {"label": "Not Recommended", "bg": "#FEF2F2", "border": "#FECACA", "text": "#991B1B", "icon": "🚫"}
}


def format_currency(amount: Optional[float], currency: str = "USD") -> str:
    """Format an amount as currency with standard symbols and 2 decimal places."""
    if amount is None:
        return "—"
    try:
        val = float(amount)
        if currency.upper() in ["USD", "$"]:
            return f"${val:,.2f}"
        elif currency.upper() in ["EUR", "€"]:
            return f"€{val:,.2f}"
        elif currency.upper() in ["GBP", "£"]:
            return f"£{val:,.2f}"
        elif currency.upper() in ["IDR", "RP"]:
            return f"Rp {val:,.0f}"
        elif currency.upper() in ["JPY", "¥"]:
            return f"¥{val:,.0f}"
        else:
            return f"{val:,.2f} {currency}"
    except (ValueError, TypeError):
        return str(amount)


def format_date(date_str: Optional[str]) -> str:
    """Format ISO date YYYY-MM-DD cleanly, or return a placeholder if None/empty."""
    if not date_str or str(date_str).strip() == "" or str(date_str).lower() == "none":
        return "None"
    return str(date_str).strip()


def get_status_badge(status: str) -> str:
    """Return inline HTML badge for affordability status."""
    st_clean = str(status).strip().lower()
    conf = STATUS_COLORS.get(st_clean, {
        "badge_bg": "#F1F5F9",
        "badge_border": "#CBD5E1",
        "text": "#334155",
        "color": "#64748B",
        "label": str(status),
        "icon": "ℹ️"
    })
    return (
        f'<span style="display:inline-flex; align-items:center; gap:5px; '
        f'padding:4px 10px; border-radius:9999px; font-size:12px; font-weight:600; '
        f'background-color:{conf["badge_bg"]}; border:1px solid {conf["badge_border"]}; '
        f'color:{conf["text"]}; white-space:nowrap;">'
        f'{conf["icon"]} {conf["label"]}</span>'
    )


def get_method_badge(method: str) -> str:
    """Return inline HTML badge for payment method."""
    m_clean = str(method).strip().lower()
    conf = METHOD_CONFIG.get(m_clean, {
        "label": str(method),
        "bg": "#F1F5F9",
        "border": "#CBD5E1",
        "text": "#334155",
        "icon": "•"
    })
    return (
        f'<span style="display:inline-flex; align-items:center; gap:5px; '
        f'padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600; '
        f'background-color:{conf["bg"]}; border:1px solid {conf["border"]}; '
        f'color:{conf["text"]}; white-space:nowrap;">'
        f'{conf["icon"]} {conf["label"]}</span>'
    )


def parse_payment_plan(plan_str: Optional[str]) -> List[Tuple[str, float]]:
    """Parse payment_plan string 'YYYY-MM-DD:amount|YYYY-MM-DD:amount' into list of tuples."""
    if not plan_str or str(plan_str).strip().lower() in ["none", ""]:
        return []
    items = []
    parts = str(plan_str).strip().split("|")
    for p in parts:
        p = p.strip()
        if ":" in p:
            dt, amt = p.split(":", 1)
            try:
                items.append((dt.strip(), float(amt.strip())))
            except ValueError:
                continue
    return items


def parse_spending_changes(spending_str: Optional[str]) -> List[dict]:
    """Parse spending_changes_needed into list of change actions."""
    if not spending_str or str(spending_str).strip().lower() in ["none", ""]:
        return []
    changes = []
    items = [x.strip() for x in str(spending_str).split(";") if x.strip()]
    for item in items:
        if item.startswith("stop:"):
            parts = item.split(":")
            if len(parts) >= 2:
                changes.append({"action": "stop", "event_id": parts[1]})
        elif item.startswith("reduce_to:"):
            parts = item.split(":")
            if len(parts) >= 3:
                try:
                    changes.append({"action": "reduce_to", "event_id": parts[1], "new_amount": float(parts[2])})
                except ValueError:
                    changes.append({"action": "reduce_to", "event_id": parts[1], "new_amount": parts[2]})
    return changes


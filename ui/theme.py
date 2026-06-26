from __future__ import annotations

from string import Template

import streamlit as st


def get_theme_mode() -> str:
    return st.session_state.get("theme_mode", "Claro")


def render_theme_switcher(
    disabled: bool = False,
) -> str:
    theme_mode = st.sidebar.radio(
        "Tema",
        options=["Claro", "Escuro"],
        index=0,
        horizontal=True,
        key="theme_mode",
        disabled=disabled,
        help=(
            "Alterna entre um tema claro para ambientes iluminados "
            "e um tema escuro para reduzir brilho no ecrã."
        ),
    )

    if disabled:
        st.sidebar.caption(
            "Tema bloqueado enquanto a otimização está a correr."
        )

    return theme_mode


def apply_theme(theme_mode: str = "Claro") -> None:
    is_dark = theme_mode == "Escuro"

    if is_dark:
        colors = {
            "bg": "#0f1513",
            "panel": "#18211d",
            "panel_soft": "#202b26",
            "ink": "#f4fbf7",
            "muted": "#b8c9c0",
            "green": "#3ddc97",
            "green_soft": "#173f30",
            "mint": "#12251f",
            "line": "#32443c",
            "sidebar_1": "#07120e",
            "sidebar_2": "#10251d",
            "input_bg": "#101815",
            "input_ink": "#f6fff9",
            "input_border": "#4f6b5f",
            "help_icon": "#d8efe5",
            "help_icon_sidebar": "#d8efe5",
            "tooltip_bg": "#f4fbf7",
            "tooltip_ink": "#111c18",
            "tooltip_border": "#8fb7a5",
            "shadow": "0 14px 35px rgba(0, 0, 0, 0.28)",
        }
    else:
        colors = {
            "bg": "#f6f8f6",
            "panel": "#ffffff",
            "panel_soft": "#f9fcfa",
            "ink": "#17231f",
            "muted": "#52665d",
            "green": "#0f7b55",
            "green_soft": "#dff4eb",
            "mint": "#ebf8f2",
            "line": "#d4e2db",
            "sidebar_1": "#103a2d",
            "sidebar_2": "#17231f",
            "input_bg": "#ffffff",
            "input_ink": "#111c18",
            "input_border": "#b8cbc2",
            "help_icon": "#30443b",
            "help_icon_sidebar": "#d8efe5",
            "tooltip_bg": "#111c18",
            "tooltip_ink": "#f6fff9",
            "tooltip_border": "#365247",
            "shadow": "0 14px 35px rgba(23, 35, 31, 0.08)",
        }

    css = Template(
        """
        <style>
        :root {
            --uw-bg: $bg;
            --uw-panel: $panel;
            --uw-panel-soft: $panel_soft;
            --uw-ink: $ink;
            --uw-muted: $muted;
            --uw-green: $green;
            --uw-green-soft: $green_soft;
            --uw-mint: $mint;
            --uw-line: $line;
            --uw-amber: #c9831f;
            --uw-red: #b5413e;
            --uw-input-bg: $input_bg;
            --uw-input-ink: $input_ink;
            --uw-input-border: $input_border;
            --uw-help-icon: $help_icon;
            --uw-help-icon-sidebar: $help_icon_sidebar;
            --uw-tooltip-bg: $tooltip_bg;
            --uw-tooltip-ink: $tooltip_ink;
            --uw-tooltip-border: $tooltip_border;
            --uw-shadow: $shadow;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(15, 123, 85, 0.12), transparent 34rem),
                linear-gradient(180deg, var(--uw-panel-soft) 0%, var(--uw-bg) 100%);
            color: var(--uw-ink);
        }

        .block-container,
        [data-testid="stAppViewContainer"] {
            color: var(--uw-ink);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, $sidebar_1 0%, $sidebar_2 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        section[data-testid="stSidebar"] * {
            color: #f5fff9;
        }

        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #d8efe5;
            font-weight: 650;
        }

        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        label,
        p,
        span {
            color: var(--uw-ink);
        }

        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea {
            color: #f6fff9 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label {
            color: #f5fff9 !important;
        }

        h1, h2, h3 {
            color: var(--uw-ink);
            letter-spacing: 0;
        }

        div[data-testid="stMetric"] {
            background: var(--uw-panel);
            border: 1px solid var(--uw-line);
            border-radius: 8px;
            padding: 1rem 1.05rem;
            box-shadow: var(--uw-shadow);
        }

        div[data-testid="stMetric"] label p {
            color: var(--uw-muted);
            font-size: 0.84rem;
        }

        div[data-testid="stMetricValue"] {
            color: var(--uw-ink);
            font-weight: 760;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--uw-line);
            border-radius: 8px;
            background: var(--uw-panel);
            box-shadow: 0 8px 24px rgba(23, 35, 31, 0.05);
        }

        div[data-testid="stExpander"] details,
        div[data-testid="stExpander"] summary {
            background: var(--uw-panel) !important;
            color: var(--uw-ink) !important;
        }

        div[data-testid="stExpander"] summary p,
        div[data-testid="stExpander"] summary span,
        div[data-testid="stExpander"] [data-testid="stWidgetLabel"] p {
            color: var(--uw-ink) !important;
            font-weight: 700;
        }

        div[data-baseweb="input"],
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"],
        input,
        textarea {
            background: var(--uw-input-bg) !important;
            color: var(--uw-input-ink) !important;
            border-color: var(--uw-input-border) !important;
        }

        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea {
            color: var(--uw-input-ink) !important;
            -webkit-text-fill-color: var(--uw-input-ink) !important;
        }

        button[aria-label="Decrement"],
        button[aria-label="Increment"],
        button[title="Decrement"],
        button[title="Increment"] {
            color: var(--uw-input-ink) !important;
            background: var(--uw-input-bg) !important;
        }

        [data-testid="stNumberInput"] button {
            color: var(--uw-input-ink) !important;
            background: var(--uw-input-bg) !important;
            border-color: var(--uw-input-border) !important;
        }

        [data-testid="stNumberInput"] button *,
        [data-testid="stNumberInput"] button svg,
        [data-testid="stNumberInput"] button svg path {
            color: var(--uw-input-ink) !important;
            fill: var(--uw-input-ink) !important;
            stroke: var(--uw-input-ink) !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stNumberInput"] button,
        section[data-testid="stSidebar"] [data-testid="stNumberInput"] button:hover,
        section[data-testid="stSidebar"] [data-testid="stNumberInput"] button:focus {
            color: var(--uw-input-ink) !important;
            background: var(--uw-input-bg) !important;
            border-color: var(--uw-input-border) !important;
            box-shadow: none !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stNumberInput"] button *,
        section[data-testid="stSidebar"] [data-testid="stNumberInput"] button svg,
        section[data-testid="stSidebar"] [data-testid="stNumberInput"] button svg path {
            color: var(--uw-input-ink) !important;
            fill: var(--uw-input-ink) !important;
            stroke: var(--uw-input-ink) !important;
            opacity: 1 !important;
        }

        [data-baseweb="radio"] label,
        [data-baseweb="radio"] p,
        [data-baseweb="checkbox"] label,
        [data-baseweb="checkbox"] p {
            color: var(--uw-ink) !important;
        }

        [data-testid="stTooltipIcon"],
        [data-testid="stTooltipIcon"] *,
        [data-testid="stTooltipIcon"] svg,
        [aria-label="Help"],
        [aria-label="help"],
        [title="Help"],
        [title="help"] {
            color: var(--uw-help-icon) !important;
            fill: var(--uw-help-icon) !important;
            stroke: var(--uw-help-icon) !important;
            opacity: 1 !important;
        }

        [data-testid="stTooltipIcon"],
        [data-testid="stTooltipIcon"] button,
        [data-testid="stTooltipIcon"]:hover,
        [data-testid="stTooltipIcon"] button:hover,
        [data-testid="stTooltipIcon"] button:focus,
        button[aria-label="Help"],
        button[aria-label="help"],
        button[title="Help"],
        button[title="help"],
        button[aria-label="Help"]:hover,
        button[aria-label="help"]:hover,
        button[title="Help"]:hover,
        button[title="help"]:hover {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            outline: 0 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stTooltipIcon"],
        section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] *,
        section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] svg,
        section[data-testid="stSidebar"] [aria-label="Help"],
        section[data-testid="stSidebar"] [aria-label="help"],
        section[data-testid="stSidebar"] [title="Help"],
        section[data-testid="stSidebar"] [title="help"] {
            color: var(--uw-help-icon-sidebar) !important;
            fill: var(--uw-help-icon-sidebar) !important;
            stroke: var(--uw-help-icon-sidebar) !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stTooltipIcon"],
        section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] button,
        section[data-testid="stSidebar"] [data-testid="stTooltipIcon"]:hover,
        section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] button:hover,
        section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] button:focus,
        section[data-testid="stSidebar"] button[aria-label="Help"],
        section[data-testid="stSidebar"] button[aria-label="help"],
        section[data-testid="stSidebar"] button[title="Help"],
        section[data-testid="stSidebar"] button[title="help"],
        section[data-testid="stSidebar"] button[aria-label="Help"]:hover,
        section[data-testid="stSidebar"] button[aria-label="help"]:hover,
        section[data-testid="stSidebar"] button[title="Help"]:hover,
        section[data-testid="stSidebar"] button[title="help"]:hover {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            outline: 0 !important;
        }

        [data-baseweb="tooltip"],
        [data-baseweb="popover"],
        [role="tooltip"],
        div[data-testid="stTooltipContent"] {
            background: var(--uw-tooltip-bg) !important;
            color: var(--uw-tooltip-ink) !important;
            border: 1px solid var(--uw-tooltip-border) !important;
            border-radius: 8px !important;
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22) !important;
        }

        [data-baseweb="tooltip"] *,
        [data-baseweb="popover"] *,
        [role="tooltip"] *,
        div[data-testid="stTooltipContent"] * {
            color: var(--uw-tooltip-ink) !important;
            -webkit-text-fill-color: var(--uw-tooltip-ink) !important;
        }

        .stButton > button {
            border-radius: 8px;
            min-height: 2.85rem;
            font-weight: 750;
            border: 1px solid rgba(15, 123, 85, 0.18);
            box-shadow: 0 10px 25px rgba(15, 123, 85, 0.18);
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0f7b55 0%, #16a36f 100%);
            color: white;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--uw-line);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(23, 35, 31, 0.05);
        }

        .uw-hero {
            background:
                linear-gradient(135deg, rgba(15, 123, 85, 0.96), rgba(18, 53, 43, 0.98)),
                repeating-linear-gradient(45deg, rgba(255,255,255,0.08) 0 1px, transparent 1px 18px);
            color: white;
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 1.2rem;
            box-shadow: var(--uw-shadow);
        }

        .uw-hero h1 {
            color: white;
            font-size: 2.3rem;
            margin: 0 0 0.35rem 0;
        }

        .uw-hero p {
            color: #dff4eb;
            font-size: 1.05rem;
            margin: 0;
            max-width: 62rem;
        }

        .uw-section-label {
            color: var(--uw-green);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.78rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .uw-card {
            background: var(--uw-panel);
            border: 1px solid var(--uw-line);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 8px 24px rgba(23, 35, 31, 0.05);
        }

        .uw-card strong {
            color: var(--uw-ink);
        }

        .uw-card p {
            color: var(--uw-muted);
            margin-bottom: 0;
        }

        .uw-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.32rem 0.62rem;
            border-radius: 999px;
            background: var(--uw-green-soft);
            color: var(--uw-green);
            font-weight: 760;
            font-size: 0.82rem;
            border: 1px solid rgba(15, 123, 85, 0.18);
        }

        .uw-muted {
            color: var(--uw-muted);
        }

        .uw-slider-limits {
            display: flex;
            justify-content: space-between;
            color: var(--uw-muted);
            font-size: 0.78rem;
            font-weight: 700;
            margin-top: -0.35rem;
            margin-bottom: 0.45rem;
        }

        .uw-slider-limits span {
            color: var(--uw-muted) !important;
        }
        </style>
        """
    ).substitute(colors)

    st.markdown(
        css,
        unsafe_allow_html=True,
    )


def page_header(
    title: str,
    subtitle: str,
    label: str | None = None,
) -> None:
    label_html = (
        f'<div class="uw-section-label">{label}</div>'
        if label
        else ""
    )

    st.markdown(
        f"""
        <div class="uw-hero">
            {label_html}
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(
    title: str,
    body: str,
    badge: str | None = None,
) -> None:
    badge_html = (
        f'<span class="uw-pill">{badge}</span>'
        if badge
        else ""
    )

    st.markdown(
        f"""
        <div class="uw-card">
            {badge_html}
            <p><strong>{title}</strong></p>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

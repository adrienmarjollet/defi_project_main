"""
Shared Streamlit UI Components

This module provides reusable UI components used across multiple Streamlit pages
to reduce code duplication and ensure consistent user experience.
"""

import streamlit as st
from typing import Tuple, Optional, List

from .streamlit_config import COMMON_TOKENS, DEFAULT_TOKEN


def token_selector(
    show_subheader: bool = True,
    subheader_text: str = "Token Selection",
    custom_tokens: Optional[dict] = None,
    default_token: str = DEFAULT_TOKEN,
    help_text: str = "Select a common token or enter custom address"
) -> str:
    """
    Create a token selector component with quick select dropdown and custom address input.

    This is the most commonly duplicated UI pattern across all pages.

    Args:
        show_subheader: Whether to show a subheader above the selector
        subheader_text: Text for the subheader
        custom_tokens: Optional custom token dictionary (defaults to COMMON_TOKENS)
        default_token: Default token address for custom input
        help_text: Help text for the dropdown

    Returns:
        The selected token address
    """
    tokens = custom_tokens if custom_tokens is not None else COMMON_TOKENS

    if show_subheader:
        st.sidebar.subheader(subheader_text)

    selected_token = st.sidebar.selectbox(
        "Quick Select Token",
        options=["Custom"] + list(tokens.keys()),
        help=help_text
    )

    if selected_token == "Custom":
        token_address = st.sidebar.text_input(
            "Token Contract Address",
            value=default_token,
            help="ERC-20 token contract address to analyze"
        )
    else:
        token_address = tokens[selected_token]
        st.sidebar.code(token_address, language=None)

    return token_address


def demo_mode_toggle(key: str = "demo_mode") -> bool:
    """
    Create a demo mode toggle checkbox in the sidebar.

    Args:
        key: Unique key for the checkbox widget

    Returns:
        True if demo mode is enabled
    """
    return st.sidebar.checkbox(
        "Demo Mode",
        value=False,
        key=key,
        help="Enable to use sample data instead of live data"
    )


def metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    help_text: Optional[str] = None,
    delta_color: str = "normal"
) -> None:
    """
    Display a styled metric card.

    Args:
        label: Label for the metric
        value: Value to display
        delta: Optional delta/change value
        help_text: Optional help text
        delta_color: Color for delta - "normal", "inverse", or "off"
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        help=help_text,
        delta_color=delta_color
    )


def metric_row(metrics: List[dict], num_columns: int = 4) -> None:
    """
    Display a row of metric cards.

    Args:
        metrics: List of metric dictionaries with keys: label, value, delta (optional), help (optional)
        num_columns: Number of columns to display
    """
    cols = st.columns(num_columns)

    for i, metric in enumerate(metrics):
        col_idx = i % num_columns
        with cols[col_idx]:
            st.metric(
                label=metric.get("label", ""),
                value=metric.get("value", ""),
                delta=metric.get("delta"),
                help=metric.get("help")
            )


def severity_badge(severity: str, text: Optional[str] = None) -> str:
    """
    Create an HTML severity badge/indicator.

    Args:
        severity: Severity level - "critical", "high", "medium", "low", or custom
        text: Optional custom text (defaults to severity level)

    Returns:
        HTML string for the badge
    """
    colors = {
        "critical": "#dc3545",
        "high": "#fd7e14",
        "medium": "#ffc107",
        "low": "#17a2b8",
        "good": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "info": "#17a2b8",
    }

    color = colors.get(severity.lower(), "#6c757d")
    display_text = text if text else severity.title()

    return f"""
    <span style="background-color: {color}; color: white; padding: 3px 10px;
                border-radius: 4px; font-size: 12px; text-transform: uppercase;">
        {display_text}
    </span>
    """


def risk_level_indicator(risk_level: str) -> str:
    """
    Create HTML for a risk level indicator box.

    Args:
        risk_level: Risk level - "Low", "Medium", "High", or "Critical"

    Returns:
        HTML string for the indicator
    """
    colors = {
        "Low": "#28a745",
        "Medium": "#ffc107",
        "High": "#fd7e14",
        "Critical": "#dc3545"
    }
    color = colors.get(risk_level, "#6c757d")

    return f"""
    <div style="background-color: {color}; color: white; padding: 15px 25px;
                border-radius: 8px; text-align: center; font-weight: bold; font-size: 20px;">
        Risk Level: {risk_level}
    </div>
    """


def grade_indicator(grade: str, size: str = "large") -> str:
    """
    Create HTML for a grade indicator (A, B, C, D, F).

    Args:
        grade: Letter grade
        size: "large" or "small"

    Returns:
        HTML string for the grade indicator
    """
    colors = {
        "A": "#28a745",
        "B": "#5cb85c",
        "C": "#ffc107",
        "D": "#fd7e14",
        "F": "#dc3545",
    }
    color = colors.get(grade.upper(), "#6c757d")

    if size == "large":
        padding = "30px"
        font_size = "48px"
        border_radius = "10px"
    else:
        padding = "10px 15px"
        font_size = "24px"
        border_radius = "5px"

    return f"""
    <div style="background-color: {color}; color: white; padding: {padding};
                border-radius: {border_radius}; text-align: center; font-size: {font_size}; font-weight: bold;">
        {grade}
    </div>
    """


def interpretation_box(
    interpretation: str,
    severity: str,
    prefix: str = "Assessment"
) -> None:
    """
    Display an interpretation box with appropriate styling based on severity.

    Args:
        interpretation: The interpretation text
        severity: Severity level determining the box color
        prefix: Prefix text before the interpretation
    """
    severity_lower = severity.lower()

    if severity_lower in ["excellent", "good", "low"]:
        st.success(f"**{prefix}:** {interpretation}")
    elif severity_lower in ["moderate", "fair", "medium"]:
        st.warning(f"**{prefix}:** {interpretation}")
    elif severity_lower in ["mild_bullish", "mild_bearish", "info"]:
        st.info(f"**{prefix}:** {interpretation}")
    else:
        st.error(f"**{prefix}:** {interpretation}")


def section_divider() -> None:
    """Add a consistent section divider."""
    st.markdown("---")


def show_token_success(token_name: str, token_symbol: str) -> None:
    """
    Display a success message for token identification.

    Args:
        token_name: Name of the token
        token_symbol: Symbol of the token
    """
    st.success(f"Token: **{token_name}** ({token_symbol})")


def show_data_point_info(count: int, description: str = "holders") -> None:
    """
    Display an info message about data points.

    Args:
        count: Number of data points
        description: Description of what the count represents
    """
    st.info(f"Analyzing {count:,} {description}")


def empty_data_warning(
    message: str = "No data available for the selected parameters.",
    suggestion: str = "Try adjusting the filters or parameters."
) -> None:
    """
    Display a warning for empty data.

    Args:
        message: Main warning message
        suggestion: Suggestion for resolving the issue
    """
    st.warning(message)
    st.info(suggestion)


def sidebar_analysis_summary(
    metrics: dict,
    title: str = "Analysis Summary"
) -> None:
    """
    Add a comprehensive analysis summary section to the sidebar.

    Args:
        metrics: Dictionary of metric name -> value pairs
        title: Title for the summary section
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader(title)

    for name, value in metrics.items():
        st.sidebar.metric(name, value)

"""
Shared Streamlit Configuration Utilities

This module provides common configuration functions used across all Streamlit pages
to reduce code duplication and ensure consistency.
"""

import os
import sys
import streamlit as st
from typing import Optional

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import shared constants from consolidated module
from defi_library.constants import COMMON_TOKENS, DEFAULT_TOKEN

# Default subgraph URL (not in constants as it's Streamlit-specific)
DEFAULT_SUBGRAPH_URL = "https://api.studio.thegraph.com/query/YOUR_ID/erc20-tracker/version/latest"


def configure_page(
    page_title: str,
    page_icon: str,
    layout: str = "wide"
) -> None:
    """
    Configure the Streamlit page with common settings.

    Args:
        page_title: The title shown in the browser tab
        page_icon: The emoji or icon shown in the browser tab
        layout: Page layout - "wide" or "centered"
    """
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout
    )


def setup_sidebar_header(title: str = "Configuration") -> None:
    """
    Set up the common sidebar header.

    Args:
        title: Header text for the sidebar
    """
    st.sidebar.header(title)


def get_subgraph_url_input(
    default_url: Optional[str] = None,
    help_text: str = "URL of your deployed ERC-20 tracker subgraph"
) -> str:
    """
    Create a subgraph URL input in the sidebar.

    Args:
        default_url: Default URL to display
        help_text: Help text for the input

    Returns:
        The entered subgraph URL
    """
    if default_url is None:
        default_url = os.getenv("ERC20_SUBGRAPH_URL", DEFAULT_SUBGRAPH_URL)

    return st.sidebar.text_input(
        "Subgraph URL",
        value=default_url,
        help=help_text
    )


def init_session_state(defaults: Optional[dict] = None) -> None:
    """
    Initialize common session state variables.

    Args:
        defaults: Dictionary of default values to initialize
    """
    common_defaults = {
        "demo_mode": False,
        "token_address": DEFAULT_TOKEN,
        "last_analysis": None,
    }

    if defaults:
        common_defaults.update(defaults)

    for key, value in common_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def is_demo_mode(subgraph_url: str) -> bool:
    """
    Check if the application is running in demo mode.

    Args:
        subgraph_url: The configured subgraph URL

    Returns:
        True if running in demo mode (no valid subgraph configured)
    """
    return "YOUR_ID" in subgraph_url


def show_demo_mode_warning() -> None:
    """
    Display the standard demo mode warning message.
    """
    st.warning("""
    **Subgraph URL not configured**

    To use this feature, you need to deploy an ERC-20 tracker subgraph and provide its URL.

    1. Deploy the subgraph from `defi_library/subgraphs/erc20-tracker/`
    2. Set the URL in the sidebar or via `ERC20_SUBGRAPH_URL` environment variable

    **Demo Mode**: Showing sample data for illustration purposes.
    """)


def validate_token_address(token_address: str) -> bool:
    """
    Validate that a token address is properly formatted.

    Args:
        token_address: The token address to validate

    Returns:
        True if valid, False otherwise
    """
    if not token_address or not token_address.startswith("0x"):
        st.error("Please enter a valid Ethereum address (starting with 0x)")
        return False
    return True


def add_sidebar_summary(metrics: dict) -> None:
    """
    Add a summary section to the sidebar with metrics.

    Args:
        metrics: Dictionary of metric name -> value pairs
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("Summary")

    for name, value in metrics.items():
        st.sidebar.metric(name, value)

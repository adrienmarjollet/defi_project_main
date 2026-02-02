"""
Holder Count Over Time Analytics

This page tracks unique holder count evolution to detect growth/decline trends.

Features:
- Query holder count at different block intervals
- Visualize holder growth/decline as line chart
- Calculate holder growth rate (daily/weekly)
- Detect organic vs. artificial growth patterns
"""

import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from web3 import Web3

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from defi_library.blocks_scraping.dev.thegraph.holder_count_queries import (
    HolderCountQueries,
    calculate_growth_rate,
    calculate_growth_metrics,
    detect_growth_anomalies,
    BLOCKS_PER_DAY,
    BLOCKS_PER_WEEK,
)
from defi_library.blocks_scraping.dev.thegraph.graph_client import GraphClient

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Holder Count Analytics",
    page_icon="📈",
    layout="wide"
)

# Default values
DEFAULT_TOKEN = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
DEFAULT_SUBGRAPH_URL = "https://api.studio.thegraph.com/query/YOUR_ID/erc20-tracker/version/latest"

# Common tokens for quick selection
COMMON_TOKENS = {
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "PEPE": "0x6982508145454Ce325dDbE47a25d4ec3d2311933",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "SHIB": "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",
    "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
}

# Interval options
INTERVAL_OPTIONS = {
    "Daily (~7200 blocks)": BLOCKS_PER_DAY,
    "Weekly (~50400 blocks)": BLOCKS_PER_WEEK,
    "Custom": None,
}


def get_web3_connection():
    """Get Web3 connection for block number queries."""
    eth_rpc = os.getenv("ETH_RPC_URL")
    if not eth_rpc:
        return None
    try:
        w3 = Web3(Web3.HTTPProvider(eth_rpc))
        if w3.is_connected():
            return w3
    except Exception:
        pass
    return None


def get_latest_block():
    """Get the latest Ethereum block number."""
    w3 = get_web3_connection()
    if w3:
        return w3.eth.block_number
    # Fallback to approximate current block (updated for 2026)
    return 22000000


# Sidebar configuration
st.sidebar.header("Configuration")

# Subgraph URL input
subgraph_url = st.sidebar.text_input(
    "Subgraph URL",
    value=os.getenv("ERC20_SUBGRAPH_URL", DEFAULT_SUBGRAPH_URL),
    help="URL of your deployed ERC-20 tracker subgraph"
)

# Token selection
st.sidebar.subheader("Token Selection")

selected_token = st.sidebar.selectbox(
    "Quick Select Token",
    options=["Custom"] + list(COMMON_TOKENS.keys()),
    help="Select a common token or enter custom address"
)

if selected_token == "Custom":
    token_address = st.sidebar.text_input(
        "Token Contract Address",
        value=DEFAULT_TOKEN,
        help="ERC-20 token contract address to analyze"
    )
else:
    token_address = COMMON_TOKENS[selected_token]
    st.sidebar.code(token_address, language=None)

# Block range configuration
st.sidebar.subheader("Block Range")

latest_block = get_latest_block()

# Lookback period
lookback_days = st.sidebar.slider(
    "Lookback Period (days)",
    min_value=1,
    max_value=365,
    value=30,
    help="Number of days to look back for historical data"
)

lookback_blocks = lookback_days * BLOCKS_PER_DAY
from_block = max(0, latest_block - lookback_blocks)
to_block = latest_block

st.sidebar.text(f"Block range: {from_block:,} - {to_block:,}")

# Interval selection
interval_choice = st.sidebar.selectbox(
    "Snapshot Interval",
    options=list(INTERVAL_OPTIONS.keys()),
    index=0,
    help="How often to sample holder count"
)

if interval_choice == "Custom":
    interval_blocks = st.sidebar.number_input(
        "Custom Interval (blocks)",
        min_value=100,
        max_value=100000,
        value=7200,
        step=100
    )
else:
    interval_blocks = INTERVAL_OPTIONS[interval_choice]


def create_holder_count_chart(df: pd.DataFrame, token_symbol: str) -> go.Figure:
    """Create an interactive line chart for holder count over time."""
    fig = go.Figure()

    # Main holder count line
    fig.add_trace(go.Scatter(
        x=df["datetime"] if "datetime" in df.columns else df["block_number"],
        y=df["holder_count"],
        mode="lines+markers",
        marker=dict(symbol="circle", size=6, color="#1f77b4"),
        line=dict(width=2, color="#1f77b4"),
        name="Holder Count",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Holders: %{y:,}<br>"
            "<extra></extra>"
        )
    ))

    # Highlight anomalies if present
    if "is_anomaly" in df.columns and df["is_anomaly"].any():
        anomaly_df = df[df["is_anomaly"]]
        fig.add_trace(go.Scatter(
            x=anomaly_df["datetime"] if "datetime" in anomaly_df.columns else anomaly_df["block_number"],
            y=anomaly_df["holder_count"],
            mode="markers",
            marker=dict(
                symbol="star",
                size=15,
                color=anomaly_df["anomaly_type"].map({"pump": "green", "decline": "red", "normal": "gray"}),
                line=dict(width=2, color="white")
            ),
            name="Anomalies",
            hovertemplate=(
                "<b>Anomaly Detected</b><br>"
                "%{x}<br>"
                "Holders: %{y:,}<br>"
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title=f"Holder Count Over Time - {token_symbol}",
        xaxis_title="Date" if "datetime" in df.columns else "Block Number",
        yaxis_title="Number of Holders",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray", tickformat=",")

    return fig


def create_growth_rate_chart(df: pd.DataFrame) -> go.Figure:
    """Create a chart showing growth rate over time."""
    if "growth_rate" not in df.columns:
        df = calculate_growth_rate(df)

    fig = go.Figure()

    # Growth rate bars
    colors = ["green" if x >= 0 else "red" for x in df["growth_rate"].fillna(0)]

    fig.add_trace(go.Bar(
        x=df["datetime"] if "datetime" in df.columns else df["block_number"],
        y=df["growth_rate"],
        marker_color=colors,
        name="Growth Rate",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Growth: %{y:.2f}%<br>"
            "<extra></extra>"
        )
    ))

    # Add moving average if enough data points
    if "growth_rate_7d_avg" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["datetime"] if "datetime" in df.columns else df["block_number"],
            y=df["growth_rate_7d_avg"],
            mode="lines",
            line=dict(color="orange", width=2, dash="dash"),
            name="7-day Moving Avg"
        ))

    fig.update_layout(
        title="Holder Growth Rate",
        xaxis_title="Date" if "datetime" in df.columns else "Block Number",
        yaxis_title="Growth Rate (%)",
        template="plotly_white",
        hovermode="x unified"
    )

    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True, zeroline=True, zerolinewidth=2, zerolinecolor="black")

    return fig


def display_metrics(metrics: dict, token_symbol: str):
    """Display summary metrics in a nice layout."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Current Holders",
            value=f"{metrics['end_holders']:,}",
            delta=f"{metrics['total_growth']:+,}"
        )

    with col2:
        st.metric(
            label="Total Growth",
            value=f"{metrics['total_growth_rate']:+.2f}%",
            delta=None
        )

    with col3:
        st.metric(
            label="Avg. Daily Growth",
            value=f"{metrics['avg_daily_growth']:+.1f}",
            delta=f"{metrics['avg_daily_growth_rate']:+.2f}%"
        )

    with col4:
        trend = "Positive" if metrics['total_growth'] > 0 else "Negative" if metrics['total_growth'] < 0 else "Stable"
        color = "green" if metrics['total_growth'] > 0 else "red" if metrics['total_growth'] < 0 else "gray"
        st.metric(
            label="Growth Trend",
            value=trend
        )


def main():
    """Main entry point for the Streamlit app."""
    st.title("Holder Count Over Time Analytics")
    st.markdown("""
    Track unique holder count evolution to detect growth/decline trends.
    Use this to identify organic vs. artificial growth patterns and pump phases.
    """)

    # Validate inputs
    if not token_address or not token_address.startswith("0x"):
        st.error("Please enter a valid Ethereum address (starting with 0x)")
        st.stop()

    if "YOUR_ID" in subgraph_url:
        st.warning("""
        **Subgraph URL not configured**

        To use this feature, you need to deploy an ERC-20 tracker subgraph and provide its URL.

        1. Deploy the subgraph from `defi_library/subgraphs/erc20-tracker/`
        2. Set the URL in the sidebar or via `ERC20_SUBGRAPH_URL` environment variable

        **Demo Mode**: Showing sample data for illustration purposes.
        """)

        # Show demo with sample data
        demo_data = pd.DataFrame({
            "block_number": list(range(18000000, 18100000, 7200)),
            "holder_count": [1000, 1050, 1120, 1200, 1180, 1250, 1350, 1400, 1500, 1550, 1600, 1700, 1750, 1800],
            "timestamp": list(range(1695902400, 1695902400 + 14 * 86400, 86400))
        })
        demo_data["datetime"] = pd.to_datetime(demo_data["timestamp"], unit="s")

        st.subheader("Sample Data (Demo Mode)")
        display_metrics(calculate_growth_metrics(demo_data), "DEMO")

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_holder_count_chart(demo_data, "DEMO"), use_container_width=True)
        with col2:
            demo_data = calculate_growth_rate(demo_data)
            st.plotly_chart(create_growth_rate_chart(demo_data), use_container_width=True)

        st.stop()

    # Initialize queries
    try:
        client = GraphClient()
        queries = HolderCountQueries(subgraph_url=subgraph_url, client=client)
    except Exception as e:
        st.error(f"Failed to initialize The Graph client: {e}")
        st.stop()

    # Get token info
    with st.spinner("Fetching token information..."):
        try:
            token_info = queries.get_token_holder_info(token_address)
            if not token_info:
                st.error(f"Token not found: {token_address}")
                st.info("Make sure the token address is correct and the subgraph has indexed this token.")
                st.stop()

            token_symbol = token_info.symbol
            current_holders = token_info.holder_count

            st.success(f"Token: **{token_info.name}** ({token_symbol})")
        except Exception as e:
            st.error(f"Failed to fetch token info: {e}")
            st.stop()

    # Fetch historical data
    with st.spinner(f"Fetching holder count history (this may take a moment)..."):
        try:
            df = queries.get_holder_count_history(
                token_address=token_address,
                from_block=from_block,
                to_block=to_block,
                interval_blocks=interval_blocks,
                include_timestamps=True
            )
        except Exception as e:
            st.error(f"Failed to fetch holder count history: {e}")
            st.info("The subgraph may not support time-travel queries or the token has no history.")
            st.stop()

    if df.empty:
        st.warning("No historical data available for this token in the selected block range.")
        st.info("Try adjusting the lookback period or check if the token exists in the subgraph.")
        st.stop()

    # Calculate metrics and growth rate
    df = calculate_growth_rate(df)
    metrics = calculate_growth_metrics(df)

    # Display metrics
    st.subheader("Summary Metrics")
    display_metrics(metrics, token_symbol)

    # Anomaly detection
    df = detect_growth_anomalies(df)
    anomaly_count = df["is_anomaly"].sum() if "is_anomaly" in df.columns else 0
    if anomaly_count > 0:
        st.info(f"Detected {anomaly_count} anomalous growth/decline events")

    # Charts
    st.subheader("Holder Count Trends")
    col1, col2 = st.columns(2)

    with col1:
        fig_count = create_holder_count_chart(df, token_symbol)
        st.plotly_chart(fig_count, use_container_width=True)

    with col2:
        fig_growth = create_growth_rate_chart(df)
        st.plotly_chart(fig_growth, use_container_width=True)

    # Use cases section
    st.subheader("Analysis Insights")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Organic vs. Artificial Growth**")
        if metrics["avg_daily_growth_rate"] > 0:
            if metrics["avg_daily_growth_rate"] < 5:
                st.success("Growth appears organic (steady, moderate)")
            elif metrics["avg_daily_growth_rate"] < 20:
                st.warning("Elevated growth rate - monitor for sustainability")
            else:
                st.error("Rapid growth - potential artificial activity")
        else:
            st.info("Holder count declining or stable")

    with col2:
        st.markdown("**Pump Phase Detection**")
        pump_anomalies = df[df.get("anomaly_type", "") == "pump"] if "anomaly_type" in df.columns else pd.DataFrame()
        if len(pump_anomalies) > 0:
            st.warning(f"Detected {len(pump_anomalies)} potential pump events")
        else:
            st.success("No obvious pump phases detected")

    with col3:
        st.markdown("**Holder Retention**")
        if metrics["total_growth"] >= 0:
            st.success("Net positive holder growth")
        else:
            st.warning("Net holder decline - possible sell-off")

    # Data table
    with st.expander("View Raw Data"):
        display_cols = ["block_number", "holder_count", "datetime", "growth_absolute", "growth_rate"]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)

    # Sidebar summary
    st.sidebar.markdown("---")
    st.sidebar.subheader("Analysis Summary")
    st.sidebar.metric("Data Points", len(df))
    st.sidebar.metric("Period (days)", lookback_days)
    st.sidebar.metric("Start Holders", f"{metrics['start_holders']:,}")
    st.sidebar.metric("Current Holders", f"{metrics['end_holders']:,}")


if __name__ == "__main__":
    main()

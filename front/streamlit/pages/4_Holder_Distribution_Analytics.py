"""
Holder Distribution Analysis

This page analyzes the shape of holder distribution including:
- Gini coefficient (inequality measure)
- Holder tiers: Whales (>1%), Dolphins (0.1-1%), Fish (<0.1%)
- Distribution histogram with log scale
- Lorenz curve visualization
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, project_root)

from defi_library.blocks_scraping.dev.thegraph.holder_distribution_queries import (
    HolderDistributionQueries,
    interpret_gini_coefficient,
    interpret_hhi,
)
from defi_library.blocks_scraping.dev.thegraph.graph_client import GraphClient

# Import utility functions
from utils.data_analysis import (
    calculate_gini_coefficient,
    build_lorenz_curve,
    classify_holder_tiers,
    calculate_concentration_metrics,
    interpret_metric,
    create_distribution_histogram_data,
)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Holder Distribution Analytics",
    page_icon="📊",
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


def create_lorenz_curve_chart(population_pct: np.ndarray, wealth_pct: np.ndarray, gini: float) -> go.Figure:
    """Create Lorenz curve visualization."""
    fig = go.Figure()

    # Line of perfect equality (diagonal)
    fig.add_trace(go.Scatter(
        x=[0, 100],
        y=[0, 100],
        mode="lines",
        line=dict(color="gray", dash="dash", width=2),
        name="Perfect Equality",
        hoverinfo="skip"
    ))

    # Lorenz curve
    fig.add_trace(go.Scatter(
        x=population_pct,
        y=wealth_pct,
        mode="lines",
        fill="tonexty",
        fillcolor="rgba(31, 119, 180, 0.3)",
        line=dict(color="#1f77b4", width=3),
        name="Lorenz Curve",
        hovertemplate=(
            "<b>Population:</b> %{x:.1f}%<br>"
            "<b>Wealth:</b> %{y:.1f}%<br>"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title=f"Lorenz Curve (Gini: {gini:.4f})",
        xaxis_title="Cumulative % of Holders (poorest to richest)",
        yaxis_title="Cumulative % of Token Holdings",
        template="plotly_white",
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        hovermode="x unified"
    )

    fig.update_xaxes(range=[0, 100], showgrid=True, gridwidth=1, gridcolor="lightgray")
    fig.update_yaxes(range=[0, 100], showgrid=True, gridwidth=1, gridcolor="lightgray")

    return fig


def create_distribution_histogram(df: pd.DataFrame, token_symbol: str) -> go.Figure:
    """Create balance distribution histogram with log scale."""
    if df.empty or "balance" not in df.columns:
        return go.Figure()

    balances = df["balance"].values
    balances = balances[balances > 0]

    if len(balances) == 0:
        return go.Figure()

    fig = go.Figure()

    # Create histogram with log-spaced bins
    fig.add_trace(go.Histogram(
        x=balances,
        nbinsx=50,
        marker_color="#1f77b4",
        opacity=0.75,
        name="Holder Count",
        hovertemplate=(
            "<b>Balance Range:</b> %{x}<br>"
            "<b>Holders:</b> %{y}<br>"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title=f"Balance Distribution - {token_symbol}",
        xaxis_title=f"Balance ({token_symbol})",
        yaxis_title="Number of Holders",
        template="plotly_white",
        bargap=0.05
    )

    # Use log scale for x-axis
    fig.update_xaxes(type="log", showgrid=True, gridwidth=1, gridcolor="lightgray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

    return fig


def create_tier_pie_chart(tiers: dict) -> go.Figure:
    """Create pie chart showing holder tier distribution."""
    labels = ["Whales (>1%)", "Dolphins (0.1-1%)", "Fish (<0.1%)"]
    values = [tiers["whales"], tiers["dolphins"], tiers["fish"]]
    colors = ["#ff6b6b", "#4ecdc4", "#45b7d1"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors,
        textinfo="label+percent",
        textposition="outside",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Count: %{value}<br>"
            "Percentage: %{percent}<br>"
            "<extra></extra>"
        )
    )])

    fig.update_layout(
        title="Holder Tiers by Count",
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )

    return fig


def create_concentration_bar_chart(metrics: dict) -> go.Figure:
    """Create bar chart showing concentration metrics."""
    categories = ["Top 10", "Top 50", "Top 100"]
    values = [
        metrics.get("top_10_pct", 0),
        metrics.get("top_50_pct", 0),
        metrics.get("top_100_pct", 0)
    ]

    fig = go.Figure(data=[go.Bar(
        x=categories,
        y=values,
        marker_color=["#ff6b6b", "#feca57", "#48dbfb"],
        text=[f"{v:.1f}%" for v in values],
        textposition="auto",
        hovertemplate=(
            "<b>%{x} Holders</b><br>"
            "Own: %{y:.2f}% of supply<br>"
            "<extra></extra>"
        )
    )])

    fig.update_layout(
        title="Token Concentration by Top Holders",
        xaxis_title="Holder Group",
        yaxis_title="% of Total Supply",
        template="plotly_white",
        yaxis_range=[0, 100]
    )

    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

    return fig


def display_distribution_metrics(metrics: dict, tiers: dict, token_symbol: str):
    """Display distribution metrics in a nice layout."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        gini = metrics.get("gini", 0)
        st.metric(
            label="Gini Coefficient",
            value=f"{gini:.4f}",
            help="0 = perfect equality, 1 = perfect inequality"
        )

    with col2:
        top_10 = metrics.get("top_10_pct", 0)
        st.metric(
            label="Top 10 Concentration",
            value=f"{top_10:.1f}%",
            help="Percentage of supply held by top 10 holders"
        )

    with col3:
        st.metric(
            label="Total Holders",
            value=f"{tiers['total']:,}",
            help="Total number of token holders"
        )

    with col4:
        hhi = metrics.get("hhi", 0)
        st.metric(
            label="HHI Index",
            value=f"{hhi:.0f}",
            help="Herfindahl-Hirschman Index (0-10000)"
        )

    # Second row of metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Whales (>1%)",
            value=f"{tiers['whales']:,}",
            help="Holders with >1% of supply"
        )

    with col2:
        st.metric(
            label="Dolphins (0.1-1%)",
            value=f"{tiers['dolphins']:,}",
            help="Holders with 0.1-1% of supply"
        )

    with col3:
        st.metric(
            label="Fish (<0.1%)",
            value=f"{tiers['fish']:,}",
            help="Holders with <0.1% of supply"
        )

    with col4:
        median = metrics.get("median_balance", 0)
        st.metric(
            label="Median Balance",
            value=f"{median:.4f}",
            help="Median token balance"
        )


def generate_demo_data():
    """Generate realistic demo data for illustration."""
    np.random.seed(42)

    # Generate power-law distributed balances (realistic for tokens)
    num_holders = 500

    # Mix of distributions to simulate whales, dolphins, and fish
    whale_balances = np.random.pareto(1.5, 10) * 1000000  # 10 whales
    dolphin_balances = np.random.pareto(2.0, 40) * 50000  # 40 dolphins
    fish_balances = np.random.pareto(3.0, 450) * 1000  # 450 fish

    all_balances = np.concatenate([whale_balances, dolphin_balances, fish_balances])
    total_supply = all_balances.sum()

    # Create DataFrame
    df = pd.DataFrame({
        "account": [f"0x{''.join(np.random.choice(list('0123456789abcdef'), 40))}" for _ in range(num_holders)],
        "balance": all_balances,
        "percentage": (all_balances / total_supply) * 100
    })

    # Sort by balance descending
    df = df.sort_values("balance", ascending=False).reset_index(drop=True)

    return df, total_supply


def main():
    """Main entry point for the Streamlit app."""
    st.title("Holder Distribution Analysis")
    st.markdown("""
    Analyze the shape of token holder distribution to understand concentration and inequality.
    Use this to assess token health, decentralization, and identify potential risks.
    """)

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

    # Analysis settings
    st.sidebar.subheader("Analysis Settings")

    max_holders = st.sidebar.slider(
        "Max Holders to Analyze",
        min_value=100,
        max_value=1000,
        value=500,
        step=100,
        help="Maximum number of holders to include in analysis"
    )

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
        demo_df, total_supply = generate_demo_data()
        token_symbol = "DEMO"

        # Calculate metrics from demo data
        metrics = calculate_concentration_metrics(demo_df, "balance")
        tiers = classify_holder_tiers(demo_df, "balance", total_supply)

        # Build Lorenz curve
        population_pct, wealth_pct = build_lorenz_curve(demo_df["balance"].values)

        st.subheader("Sample Data (Demo Mode)")

        # Display metrics
        display_distribution_metrics(metrics, tiers, token_symbol)

        # Interpretation
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            gini_interp, gini_level = interpret_metric(metrics["gini"], "gini")
            if gini_level == "good":
                st.success(f"**Gini Interpretation:** {gini_interp}")
            elif gini_level == "moderate":
                st.info(f"**Gini Interpretation:** {gini_interp}")
            elif gini_level == "warning":
                st.warning(f"**Gini Interpretation:** {gini_interp}")
            else:
                st.error(f"**Gini Interpretation:** {gini_interp}")

        with col2:
            hhi_interp, hhi_level = interpret_metric(metrics["hhi"], "hhi")
            if hhi_level == "good":
                st.success(f"**HHI Interpretation:** {hhi_interp}")
            elif hhi_level == "moderate":
                st.info(f"**HHI Interpretation:** {hhi_interp}")
            else:
                st.warning(f"**HHI Interpretation:** {hhi_interp}")

        # Charts
        st.markdown("---")
        st.subheader("Distribution Visualizations")

        col1, col2 = st.columns(2)

        with col1:
            fig_lorenz = create_lorenz_curve_chart(population_pct, wealth_pct, metrics["gini"])
            st.plotly_chart(fig_lorenz, use_container_width=True)

        with col2:
            fig_histogram = create_distribution_histogram(demo_df, token_symbol)
            st.plotly_chart(fig_histogram, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            fig_tiers = create_tier_pie_chart(tiers)
            st.plotly_chart(fig_tiers, use_container_width=True)

        with col2:
            fig_concentration = create_concentration_bar_chart(metrics)
            st.plotly_chart(fig_concentration, use_container_width=True)

        # Top holders table
        with st.expander("View Top Holders"):
            display_cols = ["account", "balance", "percentage"]
            st.dataframe(
                demo_df[display_cols].head(20).style.format({
                    "balance": "{:,.2f}",
                    "percentage": "{:.4f}%"
                }),
                use_container_width=True
            )

        st.stop()

    # Initialize queries
    try:
        client = GraphClient()
        queries = HolderDistributionQueries(subgraph_url=subgraph_url, client=client)
    except Exception as e:
        st.error(f"Failed to initialize The Graph client: {e}")
        st.stop()

    # Fetch distribution data
    with st.spinner("Fetching holder distribution data..."):
        try:
            df = queries.get_all_holder_balances(token_address, limit=max_holders)

            if df.empty:
                st.error(f"No holder data found for token: {token_address}")
                st.info("Make sure the token address is correct and the subgraph has indexed this token.")
                st.stop()

            # Get token info for symbol
            token_info = queries.erc20_queries.get_token_info(token_address)
            token_symbol = token_info.symbol if token_info else "TOKEN"
            total_supply = float(token_info.total_supply) if token_info else df["balance"].sum()

            st.success(f"Token: **{token_info.name if token_info else 'Unknown'}** ({token_symbol})")
            st.info(f"Analyzing {len(df):,} holders")

        except Exception as e:
            st.error(f"Failed to fetch holder data: {e}")
            st.stop()

    # Calculate metrics
    metrics = calculate_concentration_metrics(df, "balance")
    tiers = classify_holder_tiers(df, "balance", total_supply)

    # Build Lorenz curve
    population_pct, wealth_pct = build_lorenz_curve(df["balance"].values)

    # Display metrics
    st.subheader("Distribution Metrics")
    display_distribution_metrics(metrics, tiers, token_symbol)

    # Interpretation
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        gini_interp, gini_level = interpret_metric(metrics["gini"], "gini")
        if gini_level == "good":
            st.success(f"**Gini Interpretation:** {gini_interp}")
        elif gini_level == "moderate":
            st.info(f"**Gini Interpretation:** {gini_interp}")
        elif gini_level == "warning":
            st.warning(f"**Gini Interpretation:** {gini_interp}")
        else:
            st.error(f"**Gini Interpretation:** {gini_interp}")

    with col2:
        hhi_interp, hhi_level = interpret_metric(metrics["hhi"], "hhi")
        if hhi_level == "good":
            st.success(f"**HHI Interpretation:** {hhi_interp}")
        elif hhi_level == "moderate":
            st.info(f"**HHI Interpretation:** {hhi_interp}")
        else:
            st.warning(f"**HHI Interpretation:** {hhi_interp}")

    # Charts
    st.markdown("---")
    st.subheader("Distribution Visualizations")

    col1, col2 = st.columns(2)

    with col1:
        fig_lorenz = create_lorenz_curve_chart(population_pct, wealth_pct, metrics["gini"])
        st.plotly_chart(fig_lorenz, use_container_width=True)

    with col2:
        fig_histogram = create_distribution_histogram(df, token_symbol)
        st.plotly_chart(fig_histogram, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        fig_tiers = create_tier_pie_chart(tiers)
        st.plotly_chart(fig_tiers, use_container_width=True)

    with col2:
        fig_concentration = create_concentration_bar_chart(metrics)
        st.plotly_chart(fig_concentration, use_container_width=True)

    # Analysis Insights
    st.markdown("---")
    st.subheader("Analysis Insights")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Decentralization Assessment**")
        if metrics["gini"] < 0.7 and tiers["whales"] < 5:
            st.success("Well decentralized - healthy distribution")
        elif metrics["gini"] < 0.85 and tiers["whales"] < 10:
            st.warning("Moderately centralized - some concentration risk")
        else:
            st.error("Highly centralized - significant whale dominance")

    with col2:
        st.markdown("**Whale Risk**")
        whale_pct = tiers["whales"] / tiers["total"] * 100 if tiers["total"] > 0 else 0
        if whale_pct < 1:
            st.success(f"Low whale presence ({whale_pct:.2f}% of holders)")
        elif whale_pct < 5:
            st.warning(f"Moderate whale presence ({whale_pct:.2f}% of holders)")
        else:
            st.error(f"High whale presence ({whale_pct:.2f}% of holders)")

    with col3:
        st.markdown("**Market Structure**")
        if metrics["hhi"] < 1500:
            st.success("Competitive market structure")
        elif metrics["hhi"] < 2500:
            st.info("Moderately concentrated market")
        else:
            st.warning("Oligopolistic market structure")

    # Top holders table
    with st.expander("View Top Holders"):
        display_cols = ["account", "balance", "percentage"]
        st.dataframe(
            df[display_cols].head(50).style.format({
                "balance": "{:,.4f}",
                "percentage": "{:.4f}%"
            }),
            use_container_width=True
        )

    # Sidebar summary
    st.sidebar.markdown("---")
    st.sidebar.subheader("Analysis Summary")
    st.sidebar.metric("Gini Coefficient", f"{metrics['gini']:.4f}")
    st.sidebar.metric("Top 10 Hold", f"{metrics['top_10_pct']:.1f}%")
    st.sidebar.metric("Whales", tiers["whales"])
    st.sidebar.metric("Total Holders", f"{tiers['total']:,}")


if __name__ == "__main__":
    main()

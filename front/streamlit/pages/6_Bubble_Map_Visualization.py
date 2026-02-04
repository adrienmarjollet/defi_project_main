"""
Bubble Map Visualization

This page provides an interactive bubble chart visualization of token holders:
- Bubble size represents balance/holdings
- Color coding by wallet type: EOAs (green), Contracts (blue), Exchanges (orange)
- Click to drill down into holder details
- Zoom levels: All, Whales (>1%), Dolphins (0.1-1%), Fish (<0.1%)
- Network graph showing transfers between holders
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

from defi_library.blocks_scraping.dev.thegraph.bubble_map_queries import (
    BubbleMapQueries,
    BubbleMapData,
    HolderBubble,
    WalletType,
    format_address,
    get_wallet_type_color,
    get_tier_from_percentage,
)
from defi_library.blocks_scraping.dev.thegraph.graph_client import GraphClient

# Import shared constants
from defi_library.constants import WALLET_COLORS

# Import shared Streamlit configuration
from utils.streamlit_config import (
    configure_page,
    setup_sidebar_header,
    get_subgraph_url_input,
    is_demo_mode,
    show_demo_mode_warning,
    validate_token_address,
    COMMON_TOKENS,
    DEFAULT_TOKEN,
)
from utils.components import (
    token_selector,
    sidebar_analysis_summary,
)

# Load environment variables
load_dotenv()

# Page configuration
configure_page(page_title="Bubble Map Visualization", page_icon="...")


def create_bubble_map(
    df: pd.DataFrame,
    token_symbol: str,
    size_column: str = "size",
    color_column: str = "wallet_type"
) -> go.Figure:
    """Create interactive bubble map visualization."""
    if df.empty:
        return go.Figure()

    # Create position layout (spiral or grid)
    n = len(df)
    positions = create_spiral_positions(n)
    df["x"] = positions[:, 0]
    df["y"] = positions[:, 1]

    # Map wallet types to colors
    df["color"] = df[color_column].map(WALLET_COLORS)

    fig = go.Figure()

    # Add bubbles for each wallet type (for legend)
    for wallet_type in df[color_column].unique():
        subset = df[df[color_column] == wallet_type]
        fig.add_trace(go.Scatter(
            x=subset["x"],
            y=subset["y"],
            mode="markers",
            name=wallet_type.upper(),
            marker=dict(
                size=subset[size_column],
                color=WALLET_COLORS.get(wallet_type, "#95a5a6"),
                opacity=0.7,
                line=dict(width=1, color="white"),
                sizemode="diameter",
                sizemin=5
            ),
            text=subset["short_address"],
            customdata=subset[["address", "balance", "percentage", "wallet_label", "rank"]].values,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Rank: #%{customdata[4]}<br>"
                "Balance: %{customdata[1]:,.4f} " + token_symbol + "<br>"
                "Holdings: %{customdata[2]:.4f}%<br>"
                "Type: %{customdata[3]}<br>"
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title=f"Holder Bubble Map - {token_symbol}",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, title=""),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, title=""),
        template="plotly_white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            title="Wallet Type"
        ),
        hovermode="closest",
        height=700
    )

    return fig


def create_spiral_positions(n: int, scale: float = 10.0) -> np.ndarray:
    """
    Create spiral positions for bubble layout.

    Args:
        n: Number of positions to generate
        scale: Scale factor for the spiral

    Returns:
        Array of (x, y) positions
    """
    positions = np.zeros((n, 2))

    # Fermat spiral for even distribution
    golden_angle = np.pi * (3 - np.sqrt(5))

    for i in range(n):
        radius = scale * np.sqrt(i + 1)
        theta = i * golden_angle
        positions[i, 0] = radius * np.cos(theta)
        positions[i, 1] = radius * np.sin(theta)

    return positions


def create_treemap(df: pd.DataFrame, token_symbol: str) -> go.Figure:
    """Create treemap visualization of holder distribution."""
    if df.empty:
        return go.Figure()

    # Prepare data for treemap
    df_treemap = df.copy()
    df_treemap["tier"] = df_treemap["percentage"].apply(get_tier_from_percentage)

    fig = px.treemap(
        df_treemap,
        path=["tier", "wallet_type", "short_address"],
        values="percentage",
        color="wallet_type",
        color_discrete_map=WALLET_COLORS,
        hover_data={"balance": ":.4f", "percentage": ":.4f%", "rank": True},
        title=f"Holder Treemap - {token_symbol}"
    )

    fig.update_layout(
        height=600,
        template="plotly_white"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Holdings: %{value:.4f}%<br>"
            "<extra></extra>"
        )
    )

    return fig


def create_sunburst(df: pd.DataFrame, token_symbol: str) -> go.Figure:
    """Create sunburst chart of holder distribution."""
    if df.empty:
        return go.Figure()

    df_sunburst = df.copy()
    df_sunburst["tier"] = df_sunburst["percentage"].apply(get_tier_from_percentage)

    fig = px.sunburst(
        df_sunburst,
        path=["tier", "wallet_type"],
        values="percentage",
        color="wallet_type",
        color_discrete_map=WALLET_COLORS,
        title=f"Holder Distribution Sunburst - {token_symbol}"
    )

    fig.update_layout(
        height=500,
        template="plotly_white"
    )

    return fig


def create_wallet_type_distribution(df: pd.DataFrame) -> go.Figure:
    """Create bar chart of wallet type distribution."""
    if df.empty:
        return go.Figure()

    # Aggregate by wallet type
    type_dist = df.groupby("wallet_type").agg({
        "percentage": "sum",
        "address": "count"
    }).reset_index()
    type_dist.columns = ["wallet_type", "total_holdings", "count"]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=type_dist["wallet_type"].str.upper(),
        y=type_dist["total_holdings"],
        marker_color=[WALLET_COLORS.get(t, "#95a5a6") for t in type_dist["wallet_type"]],
        text=[f"{v:.1f}%<br>({c} wallets)" for v, c in zip(type_dist["total_holdings"], type_dist["count"])],
        textposition="auto",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Total Holdings: %{y:.2f}%<br>"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Holdings by Wallet Type",
        xaxis_title="Wallet Type",
        yaxis_title="% of Total Supply",
        template="plotly_white",
        showlegend=False
    )

    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

    return fig


def create_tier_distribution(df: pd.DataFrame) -> go.Figure:
    """Create chart showing distribution by holder tier."""
    if df.empty:
        return go.Figure()

    df_tier = df.copy()
    df_tier["tier"] = df_tier["percentage"].apply(get_tier_from_percentage)

    tier_dist = df_tier.groupby("tier").agg({
        "percentage": "sum",
        "address": "count"
    }).reset_index()
    tier_dist.columns = ["tier", "total_holdings", "count"]

    # Order tiers
    tier_order = {"whale": 0, "dolphin": 1, "fish": 2}
    tier_dist["order"] = tier_dist["tier"].map(tier_order)
    tier_dist = tier_dist.sort_values("order")

    tier_colors = {"whale": "#e74c3c", "dolphin": "#3498db", "fish": "#2ecc71"}

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=tier_dist["tier"].str.upper(),
        y=tier_dist["total_holdings"],
        marker_color=[tier_colors.get(t, "#95a5a6") for t in tier_dist["tier"]],
        text=[f"{v:.1f}%<br>({c} holders)" for v, c in zip(tier_dist["total_holdings"], tier_dist["count"])],
        textposition="auto",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Total Holdings: %{y:.2f}%<br>"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Holdings by Tier",
        xaxis_title="Holder Tier",
        yaxis_title="% of Total Supply",
        template="plotly_white",
        showlegend=False
    )

    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

    return fig


def display_holder_details(df: pd.DataFrame, token_symbol: str):
    """Display detailed holder information."""
    st.subheader("Top Holders Details")

    # Add tier column
    df_display = df.copy()
    df_display["tier"] = df_display["percentage"].apply(get_tier_from_percentage)

    # Format for display
    display_cols = ["rank", "short_address", "balance", "percentage", "wallet_type", "wallet_label", "tier"]
    col_config = {
        "rank": st.column_config.NumberColumn("Rank", format="%d"),
        "short_address": st.column_config.TextColumn("Address"),
        "balance": st.column_config.NumberColumn(f"Balance ({token_symbol})", format="%.4f"),
        "percentage": st.column_config.NumberColumn("% Supply", format="%.4f%%"),
        "wallet_type": st.column_config.TextColumn("Type"),
        "wallet_label": st.column_config.TextColumn("Label"),
        "tier": st.column_config.TextColumn("Tier"),
    }

    st.dataframe(
        df_display[display_cols].head(50),
        column_config=col_config,
        use_container_width=True,
        hide_index=True
    )


def generate_demo_data() -> pd.DataFrame:
    """Generate realistic demo data for illustration."""
    np.random.seed(42)

    num_holders = 200

    # Generate power-law distributed balances
    # Mix of wallet types
    records = []

    # Generate whales (10)
    for i in range(10):
        balance = np.random.pareto(1.2) * 500000 + 100000
        records.append({
            "address": f"0x{''.join(np.random.choice(list('0123456789abcdef'), 40))}",
            "balance": balance,
            "wallet_type": np.random.choice(["whale", "exchange"], p=[0.6, 0.4]),
            "rank": i + 1
        })

    # Generate dolphins (40)
    for i in range(40):
        balance = np.random.pareto(1.5) * 50000 + 10000
        records.append({
            "address": f"0x{''.join(np.random.choice(list('0123456789abcdef'), 40))}",
            "balance": balance,
            "wallet_type": np.random.choice(["eoa", "contract", "exchange"], p=[0.6, 0.3, 0.1]),
            "rank": i + 11
        })

    # Generate fish (150)
    for i in range(150):
        balance = np.random.pareto(2.0) * 5000 + 100
        records.append({
            "address": f"0x{''.join(np.random.choice(list('0123456789abcdef'), 40))}",
            "balance": balance,
            "wallet_type": np.random.choice(["eoa", "contract"], p=[0.85, 0.15]),
            "rank": i + 51
        })

    df = pd.DataFrame(records)

    # Calculate totals and percentages
    total_supply = df["balance"].sum()
    df["percentage"] = (df["balance"] / total_supply) * 100
    df["log_balance"] = np.log10(df["balance"].clip(lower=1) + 1)
    df["size"] = df["log_balance"] * 5 + 5
    df["short_address"] = df["address"].apply(lambda x: format_address(x))
    df["wallet_label"] = df["wallet_type"].str.upper()

    # Sort by balance and reassign ranks
    df = df.sort_values("balance", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    return df


def main():
    """Main entry point for the Streamlit app."""
    st.title("🫧 Bubble Map Visualization")
    st.markdown("""
    Interactive visualization of token holder distribution. Explore holders by size,
    type, and tier. Click on bubbles to see holder details.
    """)

    # Sidebar configuration
    setup_sidebar_header()

    # Subgraph URL input
    subgraph_url = get_subgraph_url_input()

    # Token selection using shared component
    token_address = token_selector()

    # Visualization settings
    st.sidebar.subheader("Visualization Settings")

    max_holders = st.sidebar.slider(
        "Max Holders to Display",
        min_value=50,
        max_value=500,
        value=200,
        step=50,
        help="Maximum number of holders to include"
    )

    tier_filter = st.sidebar.selectbox(
        "Filter by Tier",
        options=["All", "Whales (>1%)", "Dolphins (0.1-1%)", "Fish (<0.1%)"],
        help="Filter holders by tier"
    )

    tier_map = {
        "All": "all",
        "Whales (>1%)": "whale",
        "Dolphins (0.1-1%)": "dolphin",
        "Fish (<0.1%)": "fish"
    }
    selected_tier = tier_map[tier_filter]

    wallet_type_filter = st.sidebar.multiselect(
        "Filter by Wallet Type",
        options=["EOA", "Contract", "Exchange", "Whale", "Bridge"],
        default=["EOA", "Contract", "Exchange", "Whale", "Bridge"],
        help="Select wallet types to include"
    )

    # Validate inputs
    if not validate_token_address(token_address):
        st.stop()

    if is_demo_mode(subgraph_url):
        show_demo_mode_warning()

        # Show demo with sample data
        df = generate_demo_data()
        token_symbol = "DEMO"

        st.subheader("Sample Data (Demo Mode)")

        # Apply filters
        if selected_tier != "all":
            df["tier"] = df["percentage"].apply(get_tier_from_percentage)
            df = df[df["tier"] == selected_tier]

        type_map = {"EOA": "eoa", "Contract": "contract", "Exchange": "exchange", "Whale": "whale", "Bridge": "bridge"}
        selected_types = [type_map[t] for t in wallet_type_filter]
        df = df[df["wallet_type"].isin(selected_types)]

        if df.empty:
            st.warning("No holders match the selected filters")
            st.stop()

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Holders", f"{len(df):,}")
        with col2:
            whale_count = len(df[df["percentage"] >= 1.0])
            st.metric("Whales (>1%)", whale_count)
        with col3:
            exchange_count = len(df[df["wallet_type"] == "exchange"])
            st.metric("Exchange Wallets", exchange_count)
        with col4:
            top_10_pct = df["percentage"].head(10).sum()
            st.metric("Top 10 Concentration", f"{top_10_pct:.1f}%")

        # Main bubble map
        st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["Bubble Map", "Treemap", "Sunburst"])

        with tab1:
            fig_bubble = create_bubble_map(df, token_symbol)
            st.plotly_chart(fig_bubble, use_container_width=True)

        with tab2:
            fig_treemap = create_treemap(df, token_symbol)
            st.plotly_chart(fig_treemap, use_container_width=True)

        with tab3:
            fig_sunburst = create_sunburst(df, token_symbol)
            st.plotly_chart(fig_sunburst, use_container_width=True)

        # Distribution charts
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            fig_type = create_wallet_type_distribution(df)
            st.plotly_chart(fig_type, use_container_width=True)

        with col2:
            fig_tier = create_tier_distribution(df)
            st.plotly_chart(fig_tier, use_container_width=True)

        # Holder details
        st.markdown("---")
        with st.expander("View Holder Details"):
            display_holder_details(df, token_symbol)

        # Legend
        st.sidebar.markdown("---")
        st.sidebar.subheader("Legend")
        st.sidebar.markdown("""
        **Wallet Types:**
        - 🟢 **EOA**: Regular user wallet
        - 🔵 **Contract**: Smart contract
        - 🟠 **Exchange**: Known exchange
        - 🔴 **Whale**: Large holder (>1%)
        - 🟣 **Bridge**: Bridge contract

        **Tiers:**
        - **Whale**: >1% of supply
        - **Dolphin**: 0.1-1% of supply
        - **Fish**: <0.1% of supply
        """)

        st.stop()

    # Initialize queries
    try:
        client = GraphClient()
        queries = BubbleMapQueries(subgraph_url=subgraph_url, client=client)
    except Exception as e:
        st.error(f"Failed to initialize The Graph client: {e}")
        st.stop()

    # Fetch holder data
    with st.spinner("Fetching holder data..."):
        try:
            bubble_data = queries.get_bubble_map_data(token_address, limit=max_holders)

            if not bubble_data:
                st.error(f"No holder data found for token: {token_address}")
                st.info("Make sure the token address is correct and the subgraph has indexed this token.")
                st.stop()

            token_symbol = bubble_data.token_symbol

            # Apply tier filter
            holders = bubble_data.holders
            if selected_tier != "all":
                holders = queries.filter_by_tier(holders, selected_tier)

            # Apply wallet type filter
            type_map = {"EOA": WalletType.EOA, "Contract": WalletType.CONTRACT,
                       "Exchange": WalletType.EXCHANGE, "Whale": WalletType.WHALE, "Bridge": WalletType.BRIDGE}
            selected_types = [type_map[t] for t in wallet_type_filter if t in type_map]
            holders = queries.filter_by_wallet_type(holders, selected_types)

            if not holders:
                st.warning("No holders match the selected filters")
                st.stop()

            # Convert to DataFrame
            df = queries.to_dataframe(holders)

            st.success(f"Token: **{token_symbol}** - {len(holders):,} holders")

        except Exception as e:
            st.error(f"Failed to fetch holder data: {e}")
            st.stop()

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Holders", f"{len(df):,}")
    with col2:
        st.metric("Whales (>1%)", bubble_data.whale_count)
    with col3:
        st.metric("Exchange Wallets", bubble_data.exchange_count)
    with col4:
        top_10_pct = df["percentage"].head(10).sum()
        st.metric("Top 10 Concentration", f"{top_10_pct:.1f}%")

    # Main bubble map
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Bubble Map", "Treemap", "Sunburst"])

    with tab1:
        fig_bubble = create_bubble_map(df, token_symbol)
        st.plotly_chart(fig_bubble, use_container_width=True)

    with tab2:
        fig_treemap = create_treemap(df, token_symbol)
        st.plotly_chart(fig_treemap, use_container_width=True)

    with tab3:
        fig_sunburst = create_sunburst(df, token_symbol)
        st.plotly_chart(fig_sunburst, use_container_width=True)

    # Distribution charts
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        fig_type = create_wallet_type_distribution(df)
        st.plotly_chart(fig_type, use_container_width=True)

    with col2:
        fig_tier = create_tier_distribution(df)
        st.plotly_chart(fig_tier, use_container_width=True)

    # Holder details
    st.markdown("---")
    with st.expander("View Holder Details"):
        display_holder_details(df, token_symbol)

    # Analysis Insights
    st.markdown("---")
    st.subheader("Analysis Insights")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Wallet Type Distribution**")
        eoa_pct = df[df["wallet_type"] == "eoa"]["percentage"].sum() if "eoa" in df["wallet_type"].values else 0
        if eoa_pct > 70:
            st.success(f"Healthy EOA dominance ({eoa_pct:.1f}%)")
        elif eoa_pct > 40:
            st.info(f"Mixed wallet types (EOA: {eoa_pct:.1f}%)")
        else:
            st.warning(f"Low EOA presence ({eoa_pct:.1f}%)")

    with col2:
        st.markdown("**Exchange Holdings**")
        exchange_pct = df[df["wallet_type"] == "exchange"]["percentage"].sum() if "exchange" in df["wallet_type"].values else 0
        if exchange_pct < 20:
            st.success(f"Low exchange holdings ({exchange_pct:.1f}%)")
        elif exchange_pct < 50:
            st.info(f"Moderate exchange holdings ({exchange_pct:.1f}%)")
        else:
            st.warning(f"High exchange holdings ({exchange_pct:.1f}%) - potential sell pressure")

    with col3:
        st.markdown("**Whale Concentration**")
        whale_pct = df[df["percentage"] >= 1.0]["percentage"].sum()
        if whale_pct < 30:
            st.success(f"Low whale concentration ({whale_pct:.1f}%)")
        elif whale_pct < 60:
            st.info(f"Moderate whale concentration ({whale_pct:.1f}%)")
        else:
            st.warning(f"High whale concentration ({whale_pct:.1f}%) - centralization risk")

    # Legend
    st.sidebar.markdown("---")
    st.sidebar.subheader("Legend")
    st.sidebar.markdown("""
    **Wallet Types:**
    - 🟢 **EOA**: Regular user wallet
    - 🔵 **Contract**: Smart contract
    - 🟠 **Exchange**: Known exchange
    - 🔴 **Whale**: Large holder (>1%)
    - 🟣 **Bridge**: Bridge contract

    **Tiers:**
    - **Whale**: >1% of supply
    - **Dolphin**: 0.1-1% of supply
    - **Fish**: <0.1% of supply
    """)


if __name__ == "__main__":
    main()

"""
Whale Tracking Dashboard

This page provides comprehensive whale (top holder) tracking and analysis:
- Track top N holders' balances over time
- Stacked area chart showing whale composition changes
- Individual whale balance sparklines
- Whale activity feed showing recent large movements
- Alert system for significant movements (>5% of holdings)
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

from defi_library.blocks_scraping.dev.thegraph.whale_tracking_queries import (
    WhaleTrackingQueries,
    WhaleInfo,
    format_whale_address,
    interpret_whale_activity,
    BLOCKS_PER_DAY,
    BLOCKS_PER_WEEK,
)
from defi_library.blocks_scraping.dev.thegraph.graph_client import GraphClient

# Import utility functions from modular analysis package
from utils.analysis import (
    calculate_whale_concentration_change,
    detect_whale_accumulation_pattern,
    calculate_whale_stability_score,
    prepare_stacked_area_data,
    calculate_whale_movement_alerts,
    interpret_pattern,
)

# Import shared Streamlit utilities
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
    section_divider,
    interpretation_box,
)

# Load environment variables
load_dotenv()

# Page configuration
configure_page(page_title="Whale Tracking Dashboard", page_icon="🐋")


def create_stacked_area_chart(pivot_df: pd.DataFrame, token_symbol: str) -> go.Figure:
    """Create stacked area chart showing whale composition over time."""
    if pivot_df.empty:
        return go.Figure()

    fig = go.Figure()

    # Get address columns (all columns except block_number)
    address_cols = [col for col in pivot_df.columns if col != "block_number"]

    colors = px.colors.qualitative.Set3[:len(address_cols)]

    for i, address in enumerate(address_cols):
        fig.add_trace(go.Scatter(
            x=pivot_df["block_number"],
            y=pivot_df[address],
            mode="lines",
            name=format_whale_address(address),
            stackgroup="whales",
            fillcolor=colors[i % len(colors)],
            line=dict(width=0.5, color=colors[i % len(colors)]),
            hovertemplate=(
                f"<b>{format_whale_address(address)}</b><br>"
                "Block: %{x:,.0f}<br>"
                "Holdings: %{y:.2f}%<br>"
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title=f"Whale Composition Over Time - {token_symbol}",
        xaxis_title="Block Number",
        yaxis_title="% of Total Supply",
        template="plotly_white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        ),
        hovermode="x unified"
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

    return fig


def create_whale_sparklines(history_df: pd.DataFrame, top_n: int = 5) -> go.Figure:
    """Create sparkline charts for individual whale balances."""
    if history_df.empty:
        return go.Figure()

    # Get top N whales by average balance
    whale_avg = history_df.groupby("address")["balance"].mean().sort_values(ascending=False)
    top_whales = whale_avg.head(top_n).index.tolist()

    fig = go.Figure()

    colors = px.colors.qualitative.Bold[:len(top_whales)]

    for i, address in enumerate(top_whales):
        whale_data = history_df[history_df["address"] == address].sort_values("block_number")

        fig.add_trace(go.Scatter(
            x=whale_data["block_number"],
            y=whale_data["percentage"],
            mode="lines+markers",
            name=format_whale_address(address),
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=4),
            hovertemplate=(
                f"<b>{format_whale_address(address)}</b><br>"
                "Block: %{x:,.0f}<br>"
                "Holdings: %{y:.4f}%<br>"
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title="Individual Whale Balance Trends",
        xaxis_title="Block Number",
        yaxis_title="% of Total Supply",
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        hovermode="x unified"
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

    return fig


def create_pattern_indicator(pattern_analysis: dict) -> go.Figure:
    """Create a visual indicator for whale accumulation/distribution pattern."""
    pattern = pattern_analysis.get("pattern", "unknown")

    # Map patterns to colors and positions
    pattern_map = {
        "strong_accumulation": ("#00cc00", 0.9, "Strong Accumulation"),
        "mild_accumulation": ("#66cc66", 0.7, "Mild Accumulation"),
        "neutral": ("#999999", 0.5, "Neutral"),
        "mild_distribution": ("#cc6666", 0.3, "Mild Distribution"),
        "strong_distribution": ("#cc0000", 0.1, "Strong Distribution"),
        "unknown": ("#cccccc", 0.5, "Unknown"),
    }

    color, position, label = pattern_map.get(pattern, ("#cccccc", 0.5, "Unknown"))

    fig = go.Figure()

    # Background gradient bar
    fig.add_trace(go.Bar(
        x=[1],
        y=["Pattern"],
        orientation="h",
        marker=dict(
            color=[[0, "#cc0000"], [0.5, "#999999"], [1, "#00cc00"]],
            colorscale=[[0, "#cc0000"], [0.5, "#999999"], [1, "#00cc00"]]
        ),
        showlegend=False,
        hoverinfo="skip"
    ))

    # Indicator marker
    fig.add_trace(go.Scatter(
        x=[position],
        y=["Pattern"],
        mode="markers+text",
        marker=dict(size=25, color=color, symbol="diamond", line=dict(width=2, color="white")),
        text=[label],
        textposition="top center",
        textfont=dict(size=14, color=color),
        showlegend=False,
        hovertemplate=f"<b>{label}</b><extra></extra>"
    ))

    fig.update_layout(
        title="Whale Activity Pattern",
        template="plotly_white",
        height=150,
        xaxis=dict(
            range=[0, 1],
            tickvals=[0, 0.5, 1],
            ticktext=["Distribution", "Neutral", "Accumulation"],
            showgrid=False
        ),
        yaxis=dict(showticklabels=False, showgrid=False),
        margin=dict(l=20, r=20, t=40, b=40)
    )

    return fig


def create_whale_activity_chart(alerts: list) -> go.Figure:
    """Create a chart showing whale activity events."""
    if not alerts:
        return go.Figure()

    df = pd.DataFrame(alerts)

    fig = go.Figure()

    # Accumulation events
    accum = df[df["type"] == "accumulation"]
    if not accum.empty:
        fig.add_trace(go.Scatter(
            x=accum["block_number"],
            y=accum["change_pct"],
            mode="markers",
            name="Accumulation",
            marker=dict(
                size=accum["change_pct"].abs() / 2 + 8,
                color="#00cc00",
                symbol="triangle-up",
                line=dict(width=1, color="darkgreen")
            ),
            hovertemplate=(
                "<b>Accumulation</b><br>"
                "Whale: %{customdata[0]}<br>"
                "Change: +%{y:.1f}%<br>"
                "Block: %{x:,.0f}<br>"
                "<extra></extra>"
            ),
            customdata=[[format_whale_address(a)] for a in accum["address"]]
        ))

    # Distribution events
    dist = df[df["type"] == "distribution"]
    if not dist.empty:
        fig.add_trace(go.Scatter(
            x=dist["block_number"],
            y=dist["change_pct"].abs() * -1,
            mode="markers",
            name="Distribution",
            marker=dict(
                size=dist["change_pct"].abs() / 2 + 8,
                color="#cc0000",
                symbol="triangle-down",
                line=dict(width=1, color="darkred")
            ),
            hovertemplate=(
                "<b>Distribution</b><br>"
                "Whale: %{customdata[0]}<br>"
                "Change: %{y:.1f}%<br>"
                "Block: %{x:,.0f}<br>"
                "<extra></extra>"
            ),
            customdata=[[format_whale_address(a)] for a in dist["address"]]
        ))

    fig.update_layout(
        title="Whale Movement Events (>5% change)",
        xaxis_title="Block Number",
        yaxis_title="Balance Change %",
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        hovermode="closest"
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="lightgray")

    return fig


def display_whale_metrics(
    concentration_metrics: dict,
    pattern_analysis: dict,
    stability_metrics: dict
):
    """Display whale tracking metrics in a nice layout."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Whale Concentration",
            value=f"{concentration_metrics.get('end_concentration', 0):.1f}%",
            delta=f"{concentration_metrics.get('concentration_change', 0):+.2f}%",
            help="Combined holdings of tracked whales"
        )

    with col2:
        st.metric(
            label="Accumulating Whales",
            value=pattern_analysis.get("accumulating_whales", 0),
            help="Whales increasing their holdings"
        )

    with col3:
        st.metric(
            label="Distributing Whales",
            value=pattern_analysis.get("distributing_whales", 0),
            help="Whales decreasing their holdings"
        )

    with col4:
        st.metric(
            label="Stability Score",
            value=f"{stability_metrics.get('stability_score', 0):.0f}/100",
            help="Higher = more stable whale holdings"
        )


def display_whale_table(whales: list, token_symbol: str):
    """Display current whale holdings table."""
    if not whales:
        st.info("No whale data available")
        return

    df = pd.DataFrame([{
        "Rank": w.rank,
        "Address": format_whale_address(w.address, 10),
        "Full Address": w.address,
        "Balance": w.balance,
        "% of Supply": w.percentage
    } for w in whales])

    st.dataframe(
        df[["Rank", "Address", "Balance", "% of Supply"]].style.format({
            "Balance": "{:,.4f}",
            "% of Supply": "{:.4f}%"
        }),
        use_container_width=True,
        hide_index=True
    )


def display_activity_feed(alerts: list):
    """Display whale activity feed."""
    if not alerts:
        st.info("No significant whale activity detected in this period")
        return

    for alert in alerts[:10]:  # Show top 10 alerts
        addr = format_whale_address(alert["address"])
        change = alert["change_pct"]
        severity = alert["severity"]

        if alert["type"] == "accumulation":
            icon = "🟢"
            action = "accumulated"
            color = "green"
        else:
            icon = "🔴"
            action = "distributed"
            color = "red"

        severity_badge = "🔥" if severity == "high" else ""

        st.markdown(
            f"{icon} **{addr}** {action} **{abs(change):.1f}%** of holdings "
            f"at block {alert['block_number']:,} {severity_badge}"
        )


def generate_demo_data():
    """Generate realistic demo data for illustration."""
    np.random.seed(42)

    # Generate whale addresses
    num_whales = 15
    whale_addresses = [
        f"0x{''.join(np.random.choice(list('0123456789abcdef'), 40))}"
        for _ in range(num_whales)
    ]

    # Generate historical data
    num_blocks = 30
    start_block = 18000000
    block_interval = BLOCKS_PER_DAY

    records = []

    for i in range(num_blocks):
        block_num = start_block + (i * block_interval)
        timestamp = 1696118400 + (i * 86400)  # Daily timestamps

        for j, address in enumerate(whale_addresses):
            # Base balance with some randomness
            base_balance = (num_whales - j) * 50000 + np.random.normal(0, 5000)
            # Add trend (some accumulating, some distributing)
            if j < 5:  # Top 5 accumulating
                trend = i * 1000
            elif j < 10:  # Next 5 distributing
                trend = -i * 500
            else:  # Rest stable
                trend = np.random.normal(0, 200)

            balance = max(0, base_balance + trend + np.random.normal(0, 2000))
            total_supply = 10000000  # Assume 10M total supply
            percentage = (balance / total_supply) * 100

            records.append({
                "block_number": block_num,
                "timestamp": timestamp,
                "address": address,
                "balance": balance,
                "percentage": round(percentage, 4)
            })

    df = pd.DataFrame(records)

    # Generate current whales list
    current_block = df["block_number"].max()
    current_data = df[df["block_number"] == current_block].sort_values("balance", ascending=False)

    whales = []
    for idx, row in current_data.iterrows():
        whales.append(WhaleInfo(
            address=row["address"],
            balance=row["balance"],
            percentage=row["percentage"],
            rank=len(whales) + 1
        ))

    return df, whales


def main():
    """Main entry point for the Streamlit app."""
    st.title("🐋 Whale Tracking Dashboard")
    st.markdown("""
    Track and analyze whale (top holder) behavior to understand accumulation and
    distribution patterns. Monitor large movements and whale concentration over time.
    """)

    # Sidebar configuration
    setup_sidebar_header()

    # Subgraph URL input
    subgraph_url = get_subgraph_url_input()

    # Token selection using shared component
    token_address = token_selector()

    # Tracking settings
    st.sidebar.subheader("Tracking Settings")

    num_whales = st.sidebar.slider(
        "Number of Whales to Track",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
        help="Top N holders to track"
    )

    lookback_days = st.sidebar.slider(
        "Lookback Period (days)",
        min_value=7,
        max_value=90,
        value=30,
        step=7,
        help="How far back to analyze whale activity"
    )

    movement_threshold = st.sidebar.slider(
        "Movement Alert Threshold (%)",
        min_value=1.0,
        max_value=20.0,
        value=5.0,
        step=1.0,
        help="Minimum balance change % to flag as movement"
    )

    # Validate inputs
    if not validate_token_address(token_address):
        st.stop()

    if is_demo_mode(subgraph_url):
        show_demo_mode_warning()

        # Show demo with sample data
        history_df, whales = generate_demo_data()
        token_symbol = "DEMO"

        st.subheader("Sample Data (Demo Mode)")

        # Calculate metrics from demo data
        concentration_metrics = calculate_whale_concentration_change(history_df)
        pattern_analysis = detect_whale_accumulation_pattern(history_df, threshold_pct=movement_threshold)
        stability_metrics = calculate_whale_stability_score(history_df)
        alerts = calculate_whale_movement_alerts(history_df, threshold_pct=movement_threshold)

        # Display metrics
        display_whale_metrics(concentration_metrics, pattern_analysis, stability_metrics)

        # Pattern interpretation
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            interpretation, sentiment = interpret_pattern(pattern_analysis["pattern"], "whale_pattern")
            if sentiment == "bullish":
                st.success(f"**Pattern Analysis:** {interpretation}")
            elif sentiment == "mild_bullish":
                st.info(f"**Pattern Analysis:** {interpretation}")
            elif sentiment == "neutral":
                st.warning(f"**Pattern Analysis:** {interpretation}")
            elif sentiment == "mild_bearish":
                st.warning(f"**Pattern Analysis:** {interpretation}")
            else:
                st.error(f"**Pattern Analysis:** {interpretation}")

        with col2:
            stability = stability_metrics.get("stability_score", 0)
            if stability > 80:
                st.success(f"**Stability:** High ({stability:.0f}/100) - Whales holding steady")
            elif stability > 50:
                st.info(f"**Stability:** Moderate ({stability:.0f}/100) - Some movement")
            else:
                st.warning(f"**Stability:** Low ({stability:.0f}/100) - Active repositioning")

        # Charts
        st.markdown("---")
        st.subheader("Whale Composition Over Time")

        stacked_data = prepare_stacked_area_data(history_df, top_n=10)
        fig_stacked = create_stacked_area_chart(stacked_data, token_symbol)
        st.plotly_chart(fig_stacked, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top Whale Balance Trends")
            fig_sparklines = create_whale_sparklines(history_df, top_n=5)
            st.plotly_chart(fig_sparklines, use_container_width=True)

        with col2:
            st.subheader("Whale Movement Events")
            fig_activity = create_whale_activity_chart(alerts)
            st.plotly_chart(fig_activity, use_container_width=True)

        # Activity Feed
        st.markdown("---")
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Whale Activity Feed")
            display_activity_feed(alerts)

        with col2:
            st.subheader("Current Top Whales")
            display_whale_table(whales[:10], token_symbol)

        # Raw data expander
        with st.expander("View Raw Whale Data"):
            st.dataframe(
                history_df.sort_values(["block_number", "balance"], ascending=[False, False]).style.format({
                    "balance": "{:,.4f}",
                    "percentage": "{:.4f}%"
                }),
                use_container_width=True
            )

        # Sidebar summary
        st.sidebar.markdown("---")
        st.sidebar.subheader("Summary")
        st.sidebar.metric("Tracked Whales", len(whales))
        st.sidebar.metric("Total Concentration", f"{concentration_metrics['end_concentration']:.1f}%")
        st.sidebar.metric("Pattern", pattern_analysis["pattern"].replace("_", " ").title())
        st.sidebar.metric("Movement Alerts", len(alerts))

        st.stop()

    # Initialize queries
    try:
        client = GraphClient()
        queries = WhaleTrackingQueries(subgraph_url=subgraph_url, client=client)
    except Exception as e:
        st.error(f"Failed to initialize The Graph client: {e}")
        st.stop()

    # Fetch whale data
    with st.spinner("Identifying top whales..."):
        try:
            whales = queries.get_top_whales(token_address, limit=num_whales)

            if not whales:
                st.error(f"No whale data found for token: {token_address}")
                st.info("Make sure the token address is correct and the subgraph has indexed this token.")
                st.stop()

            # Get token info for symbol
            token_info = queries.erc20_queries.get_token_info(token_address)
            token_symbol = token_info.symbol if token_info else "TOKEN"

            st.success(f"Token: **{token_info.name if token_info else 'Unknown'}** ({token_symbol})")
            st.info(f"Tracking {len(whales)} whales")

        except Exception as e:
            st.error(f"Failed to fetch whale data: {e}")
            st.stop()

    # Get historical data
    with st.spinner("Fetching whale balance history..."):
        try:
            # Calculate block range
            latest_block = 18500000  # Would need to query for actual latest
            lookback_blocks = lookback_days * BLOCKS_PER_DAY
            from_block = latest_block - lookback_blocks

            whale_addresses = [w.address for w in whales]

            history_df = queries.get_whale_balance_history(
                token_address=token_address,
                whale_addresses=whale_addresses,
                from_block=from_block,
                to_block=latest_block,
                interval_blocks=BLOCKS_PER_DAY
            )

            if history_df.empty:
                st.warning("Limited historical data available. Showing current snapshot only.")

        except Exception as e:
            st.warning(f"Could not fetch historical data: {e}")
            history_df = pd.DataFrame()

    # Calculate metrics
    concentration_metrics = calculate_whale_concentration_change(history_df)
    pattern_analysis = detect_whale_accumulation_pattern(history_df, threshold_pct=movement_threshold)
    stability_metrics = calculate_whale_stability_score(history_df)
    alerts = calculate_whale_movement_alerts(history_df, threshold_pct=movement_threshold)

    # Display metrics
    st.subheader("Whale Tracking Metrics")
    display_whale_metrics(concentration_metrics, pattern_analysis, stability_metrics)

    # Pattern interpretation
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        interpretation, sentiment = interpret_pattern(pattern_analysis["pattern"], "whale_pattern")
        if sentiment == "bullish":
            st.success(f"**Pattern Analysis:** {interpretation}")
        elif sentiment == "mild_bullish":
            st.info(f"**Pattern Analysis:** {interpretation}")
        elif sentiment == "neutral":
            st.warning(f"**Pattern Analysis:** {interpretation}")
        elif sentiment == "mild_bearish":
            st.warning(f"**Pattern Analysis:** {interpretation}")
        else:
            st.error(f"**Pattern Analysis:** {interpretation}")

    with col2:
        stability = stability_metrics.get("stability_score", 0)
        if stability > 80:
            st.success(f"**Stability:** High ({stability:.0f}/100) - Whales holding steady")
        elif stability > 50:
            st.info(f"**Stability:** Moderate ({stability:.0f}/100) - Some movement")
        else:
            st.warning(f"**Stability:** Low ({stability:.0f}/100) - Active repositioning")

    # Charts
    if not history_df.empty:
        st.markdown("---")
        st.subheader("Whale Composition Over Time")

        stacked_data = prepare_stacked_area_data(history_df, top_n=10)
        fig_stacked = create_stacked_area_chart(stacked_data, token_symbol)
        st.plotly_chart(fig_stacked, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top Whale Balance Trends")
            fig_sparklines = create_whale_sparklines(history_df, top_n=5)
            st.plotly_chart(fig_sparklines, use_container_width=True)

        with col2:
            st.subheader("Whale Movement Events")
            fig_activity = create_whale_activity_chart(alerts)
            st.plotly_chart(fig_activity, use_container_width=True)

    # Activity Feed
    st.markdown("---")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Whale Activity Feed")
        display_activity_feed(alerts)

    with col2:
        st.subheader("Current Top Whales")
        display_whale_table(whales[:10], token_symbol)

    # Analysis Insights
    st.markdown("---")
    st.subheader("Analysis Insights")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Concentration Risk**")
        total_conc = concentration_metrics.get("end_concentration", 0)
        if total_conc < 30:
            st.success(f"Low concentration ({total_conc:.1f}%) - healthy distribution")
        elif total_conc < 60:
            st.warning(f"Moderate concentration ({total_conc:.1f}%) - monitor closely")
        else:
            st.error(f"High concentration ({total_conc:.1f}%) - significant whale risk")

    with col2:
        st.markdown("**Movement Activity**")
        num_alerts = len(alerts)
        if num_alerts == 0:
            st.success("Calm period - no significant movements")
        elif num_alerts < 5:
            st.info(f"Moderate activity - {num_alerts} significant movements")
        else:
            st.warning(f"High activity - {num_alerts} significant movements detected")

    with col3:
        st.markdown("**Net Flow Direction**")
        net_flow = pattern_analysis.get("net_flow", 0)
        if net_flow > 0:
            st.success(f"Net accumulation: +{net_flow:,.2f} tokens")
        elif net_flow < 0:
            st.error(f"Net distribution: {net_flow:,.2f} tokens")
        else:
            st.info("Balanced flow")

    # Raw data expander
    if not history_df.empty:
        with st.expander("View Raw Whale Data"):
            st.dataframe(
                history_df.sort_values(["block_number", "balance"], ascending=[False, False]).style.format({
                    "balance": "{:,.4f}",
                    "percentage": "{:.4f}%"
                }),
                use_container_width=True
            )

    # Sidebar summary
    sidebar_analysis_summary({
        "Tracked Whales": len(whales),
        "Total Concentration": f"{concentration_metrics.get('end_concentration', 0):.1f}%",
        "Pattern": pattern_analysis.get("pattern", "unknown").replace("_", " ").title(),
        "Movement Alerts": len(alerts),
    })


if __name__ == "__main__":
    main()

"""
Token Health Score Dashboard

This page provides a comprehensive health assessment for ERC-20 tokens:
- Composite health score (0-100) with letter grade
- Component breakdown: holder count, concentration, growth, whale stability, contract ratio
- Risk level assessment and factor analysis
- Historical score tracking
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

from defi_library.blocks_scraping.dev.thegraph.token_health_score_queries import (
    TokenHealthScoreQueries,
    interpret_health_score,
    interpret_component_score,
    get_score_color,
    get_grade_color,
    SCORE_WEIGHTS,
)
from defi_library.blocks_scraping.dev.thegraph.graph_client import GraphClient

# Import utility functions
from utils.data_analysis import (
    calculate_health_score_trend,
    prepare_health_score_export_data,
    interpret_health_trend,
)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Token Health Score",
    page_icon="💊",
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


def create_gauge_chart(score: float, title: str = "Health Score") -> go.Figure:
    """Create a gauge chart for the health score."""
    color = get_score_color(score)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 24}},
        number={'font': {'size': 48}, 'suffix': '/100'},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "gray"},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': 'rgba(220, 53, 69, 0.3)'},
                {'range': [40, 60], 'color': 'rgba(255, 193, 7, 0.3)'},
                {'range': [60, 80], 'color': 'rgba(92, 184, 92, 0.3)'},
                {'range': [80, 100], 'color': 'rgba(40, 167, 69, 0.3)'},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def create_component_radar_chart(components: dict) -> go.Figure:
    """Create a radar chart showing component scores."""
    categories = ['Holder Count', 'Concentration', 'Growth Trend', 'Whale Stability', 'Contract Ratio']
    values = [
        components.get('holder_count_score', 0),
        components.get('concentration_score', 0),
        components.get('growth_trend_score', 0),
        components.get('whale_stability_score', 0),
        components.get('contract_ratio_score', 0),
    ]
    # Close the radar chart
    values.append(values[0])
    categories.append(categories[0])

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(31, 119, 180, 0.3)',
        line=dict(color='#1f77b4', width=2),
        name='Current Score'
    ))

    # Add reference circle at 60 (acceptable threshold)
    reference_values = [60] * 6
    fig.add_trace(go.Scatterpolar(
        r=reference_values,
        theta=categories,
        fill=None,
        line=dict(color='rgba(255, 193, 7, 0.5)', dash='dash', width=1),
        name='Acceptable (60)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showline=False,
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                gridcolor='lightgray'
            )
        ),
        showlegend=True,
        title="Component Score Breakdown",
        height=400,
        margin=dict(l=80, r=80, t=60, b=60)
    )

    return fig


def create_component_bar_chart(components: dict) -> go.Figure:
    """Create a horizontal bar chart for component scores."""
    component_names = ['Holder Count', 'Concentration', 'Growth Trend', 'Whale Stability', 'Contract Ratio']
    scores = [
        components.get('holder_count_score', 0),
        components.get('concentration_score', 0),
        components.get('growth_trend_score', 0),
        components.get('whale_stability_score', 0),
        components.get('contract_ratio_score', 0),
    ]
    weights = [
        SCORE_WEIGHTS['holder_count'] * 100,
        SCORE_WEIGHTS['concentration'] * 100,
        SCORE_WEIGHTS['growth_trend'] * 100,
        SCORE_WEIGHTS['whale_stability'] * 100,
        SCORE_WEIGHTS['contract_ratio'] * 100,
    ]

    # Get colors based on scores
    colors = [get_score_color(s) for s in scores]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=component_names,
        x=scores,
        orientation='h',
        marker_color=colors,
        text=[f"{s:.0f}" for s in scores],
        textposition='inside',
        textfont=dict(color='white', size=14),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Score: %{x:.1f}/100<br>"
            "<extra></extra>"
        )
    ))

    # Add weight annotations
    for i, (name, weight) in enumerate(zip(component_names, weights)):
        fig.add_annotation(
            x=105,
            y=name,
            text=f"({weight:.0f}%)",
            showarrow=False,
            font=dict(size=10, color='gray'),
            xanchor='left'
        )

    fig.update_layout(
        title="Component Scores (with weights)",
        xaxis_title="Score",
        xaxis=dict(range=[0, 120], showgrid=True, gridcolor='lightgray'),
        yaxis=dict(showgrid=False),
        height=350,
        margin=dict(l=20, r=60, t=50, b=40),
        template="plotly_white"
    )

    return fig


def create_risk_level_indicator(risk_level: str) -> str:
    """Create HTML for risk level indicator."""
    colors = {
        "Low": "#28a745",
        "Medium": "#ffc107",
        "High": "#fd7e14",
        "Critical": "#dc3545"
    }
    color = colors.get(risk_level, "#6c757d")
    return f"""
    <div style="background-color: {color}; color: white; padding: 10px 20px;
                border-radius: 5px; text-align: center; font-weight: bold; font-size: 18px;">
        Risk Level: {risk_level}
    </div>
    """


def display_factors(risk_factors: list, positive_factors: list):
    """Display risk and positive factors in columns."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Risk Factors")
        if risk_factors:
            for factor in risk_factors:
                st.markdown(f"- :red[{factor}]")
        else:
            st.success("No significant risk factors identified")

    with col2:
        st.markdown("### Positive Indicators")
        if positive_factors:
            for factor in positive_factors:
                st.markdown(f"- :green[{factor}]")
        else:
            st.info("No notable positive factors")


def generate_demo_health_score():
    """Generate realistic demo health score data."""
    np.random.seed(42)

    # Generate component scores
    holder_count_score = np.random.uniform(60, 85)
    concentration_score = np.random.uniform(40, 70)
    growth_trend_score = np.random.uniform(55, 80)
    whale_stability_score = np.random.uniform(50, 75)
    contract_ratio_score = np.random.uniform(65, 90)

    # Calculate overall score
    overall_score = (
        holder_count_score * SCORE_WEIGHTS['holder_count'] +
        concentration_score * SCORE_WEIGHTS['concentration'] +
        growth_trend_score * SCORE_WEIGHTS['growth_trend'] +
        whale_stability_score * SCORE_WEIGHTS['whale_stability'] +
        contract_ratio_score * SCORE_WEIGHTS['contract_ratio']
    )

    # Determine grade
    if overall_score >= 80:
        grade = "B+"
    elif overall_score >= 70:
        grade = "B"
    elif overall_score >= 60:
        grade = "C+"
    else:
        grade = "C"

    # Determine risk level
    if overall_score >= 80:
        risk_level = "Low"
    elif overall_score >= 60:
        risk_level = "Medium"
    else:
        risk_level = "High"

    # Generate factors
    risk_factors = [
        "Moderate concentration: Top 10 hold 45.2%",
        "Some whale distribution detected"
    ]
    positive_factors = [
        "Strong holder count (2,500+ holders)",
        "Healthy EOA ratio (72.3%)",
        "Stable growth pattern"
    ]

    return {
        'overall_score': round(overall_score, 2),
        'components': {
            'holder_count_score': round(holder_count_score, 2),
            'concentration_score': round(concentration_score, 2),
            'growth_trend_score': round(growth_trend_score, 2),
            'whale_stability_score': round(whale_stability_score, 2),
            'contract_ratio_score': round(contract_ratio_score, 2),
        },
        'health_grade': grade,
        'risk_level': risk_level,
        'risk_factors': risk_factors,
        'positive_factors': positive_factors,
        'holder_count': 2543,
        'total_supply': 1000000000.0
    }


def main():
    """Main entry point for the Streamlit app."""
    st.title("Token Health Score")
    st.markdown("""
    Comprehensive health assessment for ERC-20 tokens based on multiple metrics.
    The health score combines holder count, concentration, growth trends, whale behavior,
    and wallet type distribution into a single 0-100 score.
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
        demo_data = generate_demo_health_score()
        token_symbol = "DEMO"

        st.subheader("Sample Data (Demo Mode)")

        # Main score display
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            fig_gauge = create_gauge_chart(demo_data['overall_score'])
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col2:
            st.markdown("### Grade")
            grade_color = get_grade_color(demo_data['health_grade'])
            st.markdown(f"""
            <div style="background-color: {grade_color}; color: white; padding: 30px;
                        border-radius: 10px; text-align: center; font-size: 48px; font-weight: bold;">
                {demo_data['health_grade']}
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown("### Risk Level")
            st.markdown(create_risk_level_indicator(demo_data['risk_level']), unsafe_allow_html=True)
            st.metric("Holders", f"{demo_data['holder_count']:,}")

        st.markdown("---")

        # Interpretation
        interpretation, severity = interpret_health_score(demo_data['overall_score'])
        if severity in ["excellent", "good"]:
            st.success(f"**Assessment:** {interpretation}")
        elif severity in ["moderate", "fair"]:
            st.warning(f"**Assessment:** {interpretation}")
        else:
            st.error(f"**Assessment:** {interpretation}")

        st.markdown("---")

        # Component breakdown
        st.subheader("Component Analysis")

        col1, col2 = st.columns(2)

        with col1:
            fig_radar = create_component_radar_chart(demo_data['components'])
            st.plotly_chart(fig_radar, use_container_width=True)

        with col2:
            fig_bar = create_component_bar_chart(demo_data['components'])
            st.plotly_chart(fig_bar, use_container_width=True)

        # Component details
        st.markdown("### Component Details")

        components_data = []
        component_keys = ['holder_count', 'concentration', 'growth_trend', 'whale_stability', 'contract_ratio']
        component_names = ['Holder Count', 'Concentration', 'Growth Trend', 'Whale Stability', 'Contract Ratio']

        for key, name in zip(component_keys, component_names):
            score = demo_data['components'].get(f'{key}_score', 0)
            interp, status = interpret_component_score(key, score)
            components_data.append({
                'Component': name,
                'Score': f"{score:.1f}",
                'Weight': f"{SCORE_WEIGHTS[key]*100:.0f}%",
                'Status': status.title(),
                'Interpretation': interp
            })

        components_df = pd.DataFrame(components_data)
        st.dataframe(components_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Risk and positive factors
        st.subheader("Factor Analysis")
        display_factors(demo_data['risk_factors'], demo_data['positive_factors'])

        # Scoring methodology
        with st.expander("Scoring Methodology"):
            st.markdown("""
            ### How the Health Score is Calculated

            The Token Health Score is a weighted composite of five key metrics:

            | Component | Weight | Description |
            |-----------|--------|-------------|
            | **Holder Count** | 20% | More holders = healthier, more established token |
            | **Concentration** | 25% | Lower concentration = more decentralized (based on Gini & Top-10) |
            | **Growth Trend** | 20% | Positive holder growth with low volatility = healthier |
            | **Whale Stability** | 20% | Stable whale holdings = less manipulation risk |
            | **Contract Ratio** | 15% | Higher EOA ratio = more real users vs bots |

            ### Grade Scale

            | Score Range | Grade | Risk Level |
            |-------------|-------|------------|
            | 95-100 | A+ | Low |
            | 90-94 | A | Low |
            | 85-89 | A- | Low |
            | 80-84 | B+ | Low |
            | 75-79 | B | Medium |
            | 70-74 | B- | Medium |
            | 65-69 | C+ | Medium |
            | 60-64 | C | Medium |
            | 55-59 | C- | High |
            | 50-54 | D+ | High |
            | 45-49 | D | High |
            | 40-44 | D- | High |
            | <40 | F | Critical |
            """)

        st.stop()

    # Initialize queries
    try:
        client = GraphClient()
        queries = TokenHealthScoreQueries(subgraph_url=subgraph_url, client=client)
    except Exception as e:
        st.error(f"Failed to initialize The Graph client: {e}")
        st.stop()

    # Fetch health score
    with st.spinner("Calculating token health score..."):
        try:
            health = queries.calculate_health_score(
                token_address,
                max_holders=max_holders
            )

            if not health:
                st.error(f"Could not calculate health score for token: {token_address}")
                st.info("Make sure the token address is correct and the subgraph has indexed this token.")
                st.stop()

            # Get token info for symbol
            token_info = queries.erc20_queries.get_token_info(token_address)
            token_symbol = token_info.symbol if token_info else "TOKEN"

            st.success(f"Token: **{token_info.name if token_info else 'Unknown'}** ({token_symbol})")

        except Exception as e:
            st.error(f"Failed to calculate health score: {e}")
            st.stop()

    # Main score display
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        fig_gauge = create_gauge_chart(health.overall_score)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.markdown("### Grade")
        grade_color = get_grade_color(health.health_grade)
        st.markdown(f"""
        <div style="background-color: {grade_color}; color: white; padding: 30px;
                    border-radius: 10px; text-align: center; font-size: 48px; font-weight: bold;">
            {health.health_grade}
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("### Risk Level")
        st.markdown(create_risk_level_indicator(health.risk_level), unsafe_allow_html=True)
        st.metric("Holders", f"{health.holder_count:,}")

    st.markdown("---")

    # Interpretation
    interpretation, severity = interpret_health_score(health.overall_score)
    if severity in ["excellent", "good"]:
        st.success(f"**Assessment:** {interpretation}")
    elif severity in ["moderate", "fair"]:
        st.warning(f"**Assessment:** {interpretation}")
    else:
        st.error(f"**Assessment:** {interpretation}")

    st.markdown("---")

    # Component breakdown
    st.subheader("Component Analysis")

    col1, col2 = st.columns(2)

    components_dict = {
        'holder_count_score': health.components.holder_count_score,
        'concentration_score': health.components.concentration_score,
        'growth_trend_score': health.components.growth_trend_score,
        'whale_stability_score': health.components.whale_stability_score,
        'contract_ratio_score': health.components.contract_ratio_score,
    }

    with col1:
        fig_radar = create_component_radar_chart(components_dict)
        st.plotly_chart(fig_radar, use_container_width=True)

    with col2:
        fig_bar = create_component_bar_chart(components_dict)
        st.plotly_chart(fig_bar, use_container_width=True)

    # Component details
    st.markdown("### Component Details")

    components_data = []
    component_keys = ['holder_count', 'concentration', 'growth_trend', 'whale_stability', 'contract_ratio']
    component_names = ['Holder Count', 'Concentration', 'Growth Trend', 'Whale Stability', 'Contract Ratio']

    for key, name in zip(component_keys, component_names):
        score = getattr(health.components, f'{key}_score')
        interp, status = interpret_component_score(key, score)
        components_data.append({
            'Component': name,
            'Score': f"{score:.1f}",
            'Weight': f"{SCORE_WEIGHTS[key]*100:.0f}%",
            'Status': status.title(),
            'Interpretation': interp
        })

    components_df = pd.DataFrame(components_data)
    st.dataframe(components_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Risk and positive factors
    st.subheader("Factor Analysis")
    display_factors(health.risk_factors, health.positive_factors)

    # Scoring methodology
    with st.expander("Scoring Methodology"):
        st.markdown("""
        ### How the Health Score is Calculated

        The Token Health Score is a weighted composite of five key metrics:

        | Component | Weight | Description |
        |-----------|--------|-------------|
        | **Holder Count** | 20% | More holders = healthier, more established token |
        | **Concentration** | 25% | Lower concentration = more decentralized (based on Gini & Top-10) |
        | **Growth Trend** | 20% | Positive holder growth with low volatility = healthier |
        | **Whale Stability** | 20% | Stable whale holdings = less manipulation risk |
        | **Contract Ratio** | 15% | Higher EOA ratio = more real users vs bots |

        ### Grade Scale

        | Score Range | Grade | Risk Level |
        |-------------|-------|------------|
        | 95-100 | A+ | Low |
        | 90-94 | A | Low |
        | 85-89 | A- | Low |
        | 80-84 | B+ | Low |
        | 75-79 | B | Medium |
        | 70-74 | B- | Medium |
        | 65-69 | C+ | Medium |
        | 60-64 | C | Medium |
        | 55-59 | C- | High |
        | 50-54 | D+ | High |
        | 45-49 | D | High |
        | 40-44 | D- | High |
        | <40 | F | Critical |
        """)

    # Sidebar summary
    st.sidebar.markdown("---")
    st.sidebar.subheader("Health Summary")
    st.sidebar.metric("Overall Score", f"{health.overall_score:.1f}/100")
    st.sidebar.metric("Grade", health.health_grade)
    st.sidebar.metric("Risk Level", health.risk_level)
    st.sidebar.metric("Holders", f"{health.holder_count:,}")


if __name__ == "__main__":
    main()

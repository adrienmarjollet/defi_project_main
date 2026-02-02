"""
Suspicious Activity Detection Dashboard

This page provides comprehensive suspicious activity analysis for ERC-20 tokens:
- Wash trading detection (circular transfers)
- Concentration spike monitoring
- Coordinated wallet detection
- Dump pattern analysis
- Sybil cluster identification
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

from defi_library.blocks_scraping.dev.thegraph.suspicious_activity_queries import (
    SuspiciousActivityQueries,
    SuspiciousActivityReport,
    interpret_risk_level,
    get_risk_color,
    get_severity_color,
    get_activity_icon,
    ACTIVITY_WASH_TRADING,
    ACTIVITY_CONCENTRATION_SPIKE,
    ACTIVITY_COORDINATED_WALLETS,
    ACTIVITY_DUMP_PATTERN,
    ACTIVITY_SYBIL_CLUSTER,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)
from defi_library.blocks_scraping.dev.thegraph.graph_client import GraphClient

# Import utility functions
from utils.data_analysis import (
    prepare_export_data,
)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Suspicious Activity Detection",
    page_icon="🔍",
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

# Activity type display names
ACTIVITY_NAMES = {
    ACTIVITY_WASH_TRADING: "Wash Trading",
    ACTIVITY_CONCENTRATION_SPIKE: "Concentration Spike",
    ACTIVITY_COORDINATED_WALLETS: "Coordinated Wallets",
    ACTIVITY_DUMP_PATTERN: "Dump Pattern",
    ACTIVITY_SYBIL_CLUSTER: "Sybil Cluster",
}


def create_risk_gauge(risk_score: float, title: str = "Risk Score") -> go.Figure:
    """Create a gauge chart for the risk score."""
    # Determine color based on score
    if risk_score >= 70:
        color = "#dc3545"  # Red
    elif risk_score >= 50:
        color = "#fd7e14"  # Orange
    elif risk_score >= 30:
        color = "#ffc107"  # Yellow
    else:
        color = "#28a745"  # Green

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_score,
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
                {'range': [0, 30], 'color': 'rgba(40, 167, 69, 0.3)'},
                {'range': [30, 50], 'color': 'rgba(255, 193, 7, 0.3)'},
                {'range': [50, 70], 'color': 'rgba(253, 126, 20, 0.3)'},
                {'range': [70, 100], 'color': 'rgba(220, 53, 69, 0.3)'},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': risk_score
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def create_severity_breakdown_chart(report: dict) -> go.Figure:
    """Create a bar chart showing flag counts by severity."""
    severities = ['Critical', 'High', 'Medium', 'Low']
    counts = [
        report.get('critical_flags', 0),
        report.get('high_flags', 0),
        report.get('medium_flags', 0),
        report.get('low_flags', 0)
    ]
    colors = ['#dc3545', '#fd7e14', '#ffc107', '#17a2b8']

    fig = go.Figure(go.Bar(
        x=severities,
        y=counts,
        marker_color=colors,
        text=counts,
        textposition='auto',
    ))

    fig.update_layout(
        title="Flags by Severity",
        xaxis_title="Severity Level",
        yaxis_title="Count",
        height=300,
        margin=dict(l=40, r=40, t=50, b=40),
        template="plotly_white"
    )

    return fig


def create_activity_type_chart(activities: list) -> go.Figure:
    """Create a pie chart showing activity types."""
    if not activities:
        fig = go.Figure()
        fig.add_annotation(
            text="No suspicious activities detected",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=300)
        return fig

    type_counts = {}
    for activity in activities:
        act_type = activity.get('activity_type', 'unknown')
        display_name = ACTIVITY_NAMES.get(act_type, act_type)
        type_counts[display_name] = type_counts.get(display_name, 0) + 1

    fig = go.Figure(go.Pie(
        labels=list(type_counts.keys()),
        values=list(type_counts.values()),
        hole=0.4,
        marker_colors=px.colors.qualitative.Set2[:len(type_counts)]
    ))

    fig.update_layout(
        title="Activities by Type",
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_risk_level_indicator(risk_level: str) -> str:
    """Create HTML for risk level indicator."""
    color = get_risk_color(risk_level)
    return f"""
    <div style="background-color: {color}; color: white; padding: 15px 25px;
                border-radius: 8px; text-align: center; font-weight: bold; font-size: 20px;">
        Risk Level: {risk_level}
    </div>
    """


def display_activity_card(activity: dict, index: int):
    """Display a single suspicious activity as a card."""
    severity = activity.get('severity', 'unknown')
    activity_type = activity.get('activity_type', 'unknown')
    description = activity.get('description', 'No description')
    risk_score = activity.get('risk_score', 0)
    involved = activity.get('involved_addresses', [])
    evidence = activity.get('evidence', {})

    severity_color = get_severity_color(severity)
    icon = get_activity_icon(activity_type)
    type_name = ACTIVITY_NAMES.get(activity_type, activity_type)

    with st.container():
        st.markdown(f"""
        <div style="border-left: 4px solid {severity_color}; padding: 10px 15px;
                    margin: 10px 0; background-color: rgba(0,0,0,0.02); border-radius: 0 8px 8px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 18px; font-weight: bold;">{icon} {type_name}</span>
                <span style="background-color: {severity_color}; color: white; padding: 3px 10px;
                            border-radius: 4px; font-size: 12px; text-transform: uppercase;">
                    {severity}
                </span>
            </div>
            <p style="margin: 10px 0; color: #333;">{description}</p>
            <div style="font-size: 12px; color: #666;">
                Risk Contribution: <strong>{risk_score:.1f}</strong> points
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Show details in expander
        with st.expander(f"View Details"):
            if involved:
                st.markdown("**Involved Addresses:**")
                for addr in involved[:10]:  # Limit to 10 addresses
                    st.code(addr, language=None)
                if len(involved) > 10:
                    st.caption(f"... and {len(involved) - 10} more addresses")

            if evidence:
                st.markdown("**Evidence:**")
                st.json(evidence)


def generate_demo_report() -> dict:
    """Generate realistic demo report data."""
    np.random.seed(42)

    activities = [
        {
            'activity_type': ACTIVITY_CONCENTRATION_SPIKE,
            'severity': SEVERITY_HIGH,
            'description': 'Single wallet holds 18.5% of supply',
            'involved_addresses': ['0x1234...abcd'],
            'evidence': {'wallet_percentage': 18.5, 'top_10_concentration': 65.3},
            'risk_score': 18.5,
            'block_number': 18500000,
            'timestamp': int(datetime.now().timestamp())
        },
        {
            'activity_type': ACTIVITY_COORDINATED_WALLETS,
            'severity': SEVERITY_MEDIUM,
            'description': 'Potential coordinated wallets: 5 wallets with similar balances (8.2% total)',
            'involved_addresses': ['0xaaaa...1111', '0xbbbb...2222', '0xcccc...3333', '0xdddd...4444', '0xeeee...5555'],
            'evidence': {'cluster_size': 5, 'total_percentage': 8.2, 'detection_method': 'balance_similarity'},
            'risk_score': 10.0,
            'block_number': 18500000,
            'timestamp': int(datetime.now().timestamp())
        },
        {
            'activity_type': ACTIVITY_SYBIL_CLUSTER,
            'severity': SEVERITY_MEDIUM,
            'description': 'Potential Sybil attack: 8 wallets with identical balances (3.5% total)',
            'involved_addresses': ['0x1111...aaaa', '0x2222...bbbb', '0x3333...cccc', '0x4444...dddd',
                                   '0x5555...eeee', '0x6666...ffff', '0x7777...gggg', '0x8888...hhhh'],
            'evidence': {'cluster_size': 8, 'identical_balance': 43750.0, 'total_percentage': 3.5},
            'risk_score': 12.0,
            'block_number': 18500000,
            'timestamp': int(datetime.now().timestamp())
        },
        {
            'activity_type': ACTIVITY_DUMP_PATTERN,
            'severity': SEVERITY_LOW,
            'description': 'Some whale distribution detected',
            'involved_addresses': [],
            'evidence': {'distributing_whales': 3, 'total_whales': 8, 'distribution_ratio': 0.375},
            'risk_score': 7.5,
            'block_number': 18500000,
            'timestamp': int(datetime.now().timestamp())
        }
    ]

    total_risk = sum(a['risk_score'] for a in activities)

    return {
        'token_address': DEFAULT_TOKEN,
        'overall_risk_score': min(100, total_risk),
        'risk_level': 'Medium',
        'total_flags': len(activities),
        'critical_flags': sum(1 for a in activities if a['severity'] == SEVERITY_CRITICAL),
        'high_flags': sum(1 for a in activities if a['severity'] == SEVERITY_HIGH),
        'medium_flags': sum(1 for a in activities if a['severity'] == SEVERITY_MEDIUM),
        'low_flags': sum(1 for a in activities if a['severity'] == SEVERITY_LOW),
        'activities': activities,
        'summary': f"Risk Level: Medium (Score: {total_risk:.1f}/100)\nTotal flags: {len(activities)}\n- Concentration concerns: 1\n- Coordinated wallet groups: 1\n- Potential Sybil clusters: 1\n- Dump pattern signals: 1",
        'block_number': 18500000,
        'timestamp': int(datetime.now().timestamp())
    }


def main():
    """Main entry point for the Streamlit app."""
    st.title("Suspicious Activity Detection")
    st.markdown("""
    Comprehensive analysis to detect potential manipulation and scam patterns in token holder activity.
    This tool flags wash trading, concentration anomalies, coordinated wallets, dump patterns, and Sybil attacks.
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

    # Detection settings
    st.sidebar.subheader("Detection Settings")

    include_wash_trading = st.sidebar.checkbox("Wash Trading Detection", value=True)
    include_concentration = st.sidebar.checkbox("Concentration Analysis", value=True)
    include_coordinated = st.sidebar.checkbox("Coordinated Wallets", value=True)
    include_dump = st.sidebar.checkbox("Dump Pattern Detection", value=True)
    include_sybil = st.sidebar.checkbox("Sybil Cluster Detection", value=True)

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
        report = generate_demo_report()
        token_symbol = "DEMO"

        st.subheader("Sample Data (Demo Mode)")

        # Main risk display
        col1, col2 = st.columns([2, 1])

        with col1:
            fig_gauge = create_risk_gauge(report['overall_risk_score'])
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col2:
            st.markdown("### Risk Assessment")
            st.markdown(create_risk_level_indicator(report['risk_level']), unsafe_allow_html=True)
            st.metric("Total Flags", report['total_flags'])

        # Interpretation
        interpretation, severity = interpret_risk_level(report['risk_level'])
        if severity == "critical":
            st.error(f"**Assessment:** {interpretation}")
        elif severity == "high":
            st.warning(f"**Assessment:** {interpretation}")
        elif severity == "medium":
            st.info(f"**Assessment:** {interpretation}")
        else:
            st.success(f"**Assessment:** {interpretation}")

        st.markdown("---")

        # Charts row
        col1, col2 = st.columns(2)

        with col1:
            fig_severity = create_severity_breakdown_chart(report)
            st.plotly_chart(fig_severity, use_container_width=True)

        with col2:
            fig_types = create_activity_type_chart(report['activities'])
            st.plotly_chart(fig_types, use_container_width=True)

        st.markdown("---")

        # Activity feed
        st.subheader("Detected Activities")

        if report['activities']:
            # Filter controls
            severity_filter = st.multiselect(
                "Filter by Severity",
                options=['critical', 'high', 'medium', 'low'],
                default=['critical', 'high', 'medium', 'low']
            )

            filtered_activities = [
                a for a in report['activities']
                if a.get('severity') in severity_filter
            ]

            if filtered_activities:
                for i, activity in enumerate(filtered_activities):
                    display_activity_card(activity, i)
            else:
                st.info("No activities match the selected filters.")
        else:
            st.success("No suspicious activities detected. Token appears healthy.")

        st.markdown("---")

        # Summary
        st.subheader("Analysis Summary")
        st.text(report['summary'])

        # Detection methodology
        with st.expander("Detection Methodology"):
            st.markdown("""
            ### How Suspicious Activity is Detected

            This analysis uses multiple detection methods to identify potential manipulation:

            | Detection Type | Description | Severity Impact |
            |----------------|-------------|-----------------|
            | **Wash Trading** | Circular transfer patterns between small groups of wallets | High if >5 cycles |
            | **Concentration Spike** | Single wallets or top 10 holding excessive supply | High if >15% single wallet |
            | **Coordinated Wallets** | Wallets with similar balances or synchronized timing | Medium-High based on % |
            | **Dump Pattern** | Multiple whales distributing simultaneously | Medium-High |
            | **Sybil Cluster** | Multiple wallets with identical balances (potential fake holders) | Medium-High based on count |

            ### Risk Score Calculation

            The overall risk score (0-100) is calculated by summing individual activity risk contributions:
            - Each detected activity contributes based on its severity and scope
            - Multiple activities of the same type compound the risk
            - Critical flags significantly increase the overall score

            ### Risk Levels

            | Score Range | Level | Interpretation |
            |-------------|-------|----------------|
            | 0-29 | Low | No major red flags |
            | 30-49 | Medium | Some suspicious patterns |
            | 50-69 | High | Significant manipulation indicators |
            | 70-100 | Critical | Multiple severe red flags |
            """)

        st.stop()

    # Initialize queries
    try:
        client = GraphClient()
        queries = SuspiciousActivityQueries(subgraph_url=subgraph_url, client=client)
    except Exception as e:
        st.error(f"Failed to initialize The Graph client: {e}")
        st.stop()

    # Run analysis
    with st.spinner("Analyzing token for suspicious activity..."):
        try:
            report = queries.analyze_token(
                token_address,
                include_wash_trading=include_wash_trading,
                include_concentration=include_concentration,
                include_coordinated=include_coordinated,
                include_dump_patterns=include_dump,
                include_sybil=include_sybil
            )

            if not report:
                st.error(f"Could not analyze token: {token_address}")
                st.info("Make sure the token address is correct and the subgraph has indexed this token.")
                st.stop()

            # Get token info for symbol
            token_info = queries.erc20_queries.get_token_info(token_address)
            token_symbol = token_info.symbol if token_info else "TOKEN"

            st.success(f"Token: **{token_info.name if token_info else 'Unknown'}** ({token_symbol})")

            # Convert dataclass to dict for display
            report_dict = {
                'token_address': report.token_address,
                'overall_risk_score': report.overall_risk_score,
                'risk_level': report.risk_level,
                'total_flags': report.total_flags,
                'critical_flags': report.critical_flags,
                'high_flags': report.high_flags,
                'medium_flags': report.medium_flags,
                'low_flags': report.low_flags,
                'activities': [
                    {
                        'activity_type': a.activity_type,
                        'severity': a.severity,
                        'description': a.description,
                        'involved_addresses': a.involved_addresses,
                        'evidence': a.evidence,
                        'risk_score': a.risk_score,
                        'block_number': a.block_number,
                        'timestamp': a.timestamp
                    }
                    for a in report.activities
                ],
                'summary': report.summary,
                'block_number': report.block_number,
                'timestamp': report.timestamp
            }

        except Exception as e:
            st.error(f"Failed to analyze token: {e}")
            st.stop()

    # Main risk display
    col1, col2 = st.columns([2, 1])

    with col1:
        fig_gauge = create_risk_gauge(report_dict['overall_risk_score'])
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.markdown("### Risk Assessment")
        st.markdown(create_risk_level_indicator(report_dict['risk_level']), unsafe_allow_html=True)
        st.metric("Total Flags", report_dict['total_flags'])

    # Interpretation
    interpretation, severity = interpret_risk_level(report_dict['risk_level'])
    if severity == "critical":
        st.error(f"**Assessment:** {interpretation}")
    elif severity == "high":
        st.warning(f"**Assessment:** {interpretation}")
    elif severity == "medium":
        st.info(f"**Assessment:** {interpretation}")
    else:
        st.success(f"**Assessment:** {interpretation}")

    st.markdown("---")

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        fig_severity = create_severity_breakdown_chart(report_dict)
        st.plotly_chart(fig_severity, use_container_width=True)

    with col2:
        fig_types = create_activity_type_chart(report_dict['activities'])
        st.plotly_chart(fig_types, use_container_width=True)

    st.markdown("---")

    # Activity feed
    st.subheader("Detected Activities")

    if report_dict['activities']:
        # Filter controls
        severity_filter = st.multiselect(
            "Filter by Severity",
            options=['critical', 'high', 'medium', 'low'],
            default=['critical', 'high', 'medium', 'low']
        )

        filtered_activities = [
            a for a in report_dict['activities']
            if a.get('severity') in severity_filter
        ]

        if filtered_activities:
            for i, activity in enumerate(filtered_activities):
                display_activity_card(activity, i)
        else:
            st.info("No activities match the selected filters.")
    else:
        st.success("No suspicious activities detected. Token appears healthy.")

    st.markdown("---")

    # Summary
    st.subheader("Analysis Summary")
    st.text(report_dict['summary'])

    # Detection methodology
    with st.expander("Detection Methodology"):
        st.markdown("""
        ### How Suspicious Activity is Detected

        This analysis uses multiple detection methods to identify potential manipulation:

        | Detection Type | Description | Severity Impact |
        |----------------|-------------|-----------------|
        | **Wash Trading** | Circular transfer patterns between small groups of wallets | High if >5 cycles |
        | **Concentration Spike** | Single wallets or top 10 holding excessive supply | High if >15% single wallet |
        | **Coordinated Wallets** | Wallets with similar balances or synchronized timing | Medium-High based on % |
        | **Dump Pattern** | Multiple whales distributing simultaneously | Medium-High |
        | **Sybil Cluster** | Multiple wallets with identical balances (potential fake holders) | Medium-High based on count |

        ### Risk Score Calculation

        The overall risk score (0-100) is calculated by summing individual activity risk contributions:
        - Each detected activity contributes based on its severity and scope
        - Multiple activities of the same type compound the risk
        - Critical flags significantly increase the overall score

        ### Risk Levels

        | Score Range | Level | Interpretation |
        |-------------|-------|----------------|
        | 0-29 | Low | No major red flags |
        | 30-49 | Medium | Some suspicious patterns |
        | 50-69 | High | Significant manipulation indicators |
        | 70-100 | Critical | Multiple severe red flags |
        """)

    # Sidebar summary
    st.sidebar.markdown("---")
    st.sidebar.subheader("Risk Summary")
    st.sidebar.metric("Risk Score", f"{report_dict['overall_risk_score']:.1f}/100")
    st.sidebar.metric("Risk Level", report_dict['risk_level'])
    st.sidebar.metric("Total Flags", report_dict['total_flags'])

    if report_dict['critical_flags'] > 0:
        st.sidebar.error(f"Critical Flags: {report_dict['critical_flags']}")
    if report_dict['high_flags'] > 0:
        st.sidebar.warning(f"High Flags: {report_dict['high_flags']}")


if __name__ == "__main__":
    main()

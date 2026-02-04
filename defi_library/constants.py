"""
Consolidated Constants for DeFi Project

This module provides shared constants used across the application:
- Common token addresses
- Block interval constants
- Wallet type colors
- Severity levels
- Threshold values for tier classification
"""

from enum import Enum
from typing import Dict


# =============================================================================
# COMMON TOKEN ADDRESSES
# =============================================================================
# Well-known ERC-20 token addresses on Ethereum mainnet for quick selection

COMMON_TOKENS: Dict[str, str] = {
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "PEPE": "0x6982508145454Ce325dDbE47a25d4ec3d2311933",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "SHIB": "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",
    "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
}

# Default token address (WETH)
DEFAULT_TOKEN = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


# =============================================================================
# BLOCK INTERVAL CONSTANTS
# =============================================================================
# Ethereum block intervals (approximate, ~12 seconds per block)

BLOCKS_PER_HOUR = 300
BLOCKS_PER_DAY = 7200
BLOCKS_PER_WEEK = 50400
BLOCKS_PER_MONTH = 216000


# =============================================================================
# WALLET TYPE CLASSIFICATION
# =============================================================================

class WalletType(Enum):
    """Classification of wallet types."""
    EOA = "eoa"  # Externally Owned Account (regular user)
    CONTRACT = "contract"  # Smart contract
    EXCHANGE = "exchange"  # Known exchange wallet
    BRIDGE = "bridge"  # Bridge contract
    WHALE = "whale"  # Large holder (>1% of supply)
    UNKNOWN = "unknown"


# Wallet type colors for visualizations
WALLET_COLORS: Dict[str, str] = {
    "eoa": "#2ecc71",  # Green
    "contract": "#3498db",  # Blue
    "exchange": "#e67e22",  # Orange
    "bridge": "#9b59b6",  # Purple
    "whale": "#e74c3c",  # Red
    "unknown": "#95a5a6",  # Gray
}

# Wallet type colors by WalletType enum
WALLET_TYPE_COLORS: Dict[WalletType, str] = {
    WalletType.EOA: "#2ecc71",  # Green
    WalletType.CONTRACT: "#3498db",  # Blue
    WalletType.EXCHANGE: "#e67e22",  # Orange
    WalletType.BRIDGE: "#9b59b6",  # Purple
    WalletType.WHALE: "#e74c3c",  # Red
    WalletType.UNKNOWN: "#95a5a6",  # Gray
}


# =============================================================================
# SEVERITY LEVELS
# =============================================================================

SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

# Severity level colors for visualizations
SEVERITY_COLORS: Dict[str, str] = {
    "critical": "#dc3545",  # Red
    "high": "#fd7e14",  # Orange
    "medium": "#ffc107",  # Yellow
    "low": "#17a2b8",  # Light blue
}

# Risk level colors (capitalized keys)
RISK_COLORS: Dict[str, str] = {
    "Critical": "#dc3545",  # Red
    "High": "#fd7e14",  # Orange
    "Medium": "#ffc107",  # Yellow
    "Low": "#28a745",  # Green
}


# =============================================================================
# HEALTH SCORE COLORS
# =============================================================================

# Score-based color thresholds
SCORE_COLOR_THRESHOLDS = [
    (80, "#28a745"),  # Green - Excellent
    (60, "#5cb85c"),  # Light green - Good
    (50, "#ffc107"),  # Yellow - Fair
    (40, "#fd7e14"),  # Orange - Poor
    (0, "#dc3545"),   # Red - Critical
]

# Grade colors for health scores
GRADE_COLORS: Dict[str, str] = {
    "A": "#28a745",  # Green - Excellent (score >= 80)
    "B": "#5cb85c",  # Light green - Good (score >= 60)
    "C": "#ffc107",  # Yellow - Fair (score >= 40)
    "D": "#fd7e14",  # Orange - Poor (score >= 20)
    "F": "#dc3545",  # Red - Critical (score < 20)
}


# =============================================================================
# TIER CLASSIFICATION THRESHOLDS
# =============================================================================

# Holder tier thresholds (percentage of total supply)
TIER_THRESHOLDS = {
    "whale": 1.0,     # >= 1% of supply
    "dolphin": 0.1,   # >= 0.1% of supply
    "fish": 0.0,      # < 0.1% of supply
}

# Tier colors for visualizations
TIER_COLORS: Dict[str, str] = {
    "whale": "#e74c3c",    # Red
    "dolphin": "#3498db",  # Blue
    "fish": "#2ecc71",     # Green
}


# =============================================================================
# ACTIVITY TYPES
# =============================================================================

ACTIVITY_WASH_TRADING = "wash_trading"
ACTIVITY_CONCENTRATION_SPIKE = "concentration_spike"
ACTIVITY_COORDINATED_WALLETS = "coordinated_wallets"
ACTIVITY_DUMP_PATTERN = "dump_pattern"
ACTIVITY_SYBIL_CLUSTER = "sybil_cluster"
ACTIVITY_RAPID_ACCUMULATION = "rapid_accumulation"

# Activity type display names
ACTIVITY_NAMES: Dict[str, str] = {
    ACTIVITY_WASH_TRADING: "Wash Trading",
    ACTIVITY_CONCENTRATION_SPIKE: "Concentration Spike",
    ACTIVITY_COORDINATED_WALLETS: "Coordinated Wallets",
    ACTIVITY_DUMP_PATTERN: "Dump Pattern",
    ACTIVITY_SYBIL_CLUSTER: "Sybil Cluster",
    ACTIVITY_RAPID_ACCUMULATION: "Rapid Accumulation",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_score_color(score: float) -> str:
    """
    Get color code for score visualization.

    Args:
        score: Score value (0-100)

    Returns:
        Hex color code
    """
    for threshold, color in SCORE_COLOR_THRESHOLDS:
        if score >= threshold:
            return color
    return "#dc3545"  # Default to red


def get_grade_color(grade: str) -> str:
    """
    Get color code for grade visualization.

    Args:
        grade: Letter grade (A, B, C, D, F)

    Returns:
        Hex color code
    """
    return GRADE_COLORS.get(grade, "#6c757d")


def get_risk_color(risk_level: str) -> str:
    """
    Get color code for risk level visualization.

    Args:
        risk_level: Risk level string (Critical, High, Medium, Low)

    Returns:
        Hex color code
    """
    return RISK_COLORS.get(risk_level, "#6c757d")


def get_severity_color(severity: str) -> str:
    """
    Get color code for severity level visualization.

    Args:
        severity: Severity string (critical, high, medium, low)

    Returns:
        Hex color code
    """
    return SEVERITY_COLORS.get(severity, "#6c757d")


def get_wallet_type_color(wallet_type) -> str:
    """
    Get color for wallet type visualization.

    Args:
        wallet_type: WalletType enum value or string

    Returns:
        Hex color string
    """
    if isinstance(wallet_type, WalletType):
        return WALLET_TYPE_COLORS.get(wallet_type, "#95a5a6")
    return WALLET_COLORS.get(wallet_type, "#95a5a6")


def get_tier_color(tier: str) -> str:
    """
    Get color for holder tier visualization.

    Args:
        tier: Tier string (whale, dolphin, fish)

    Returns:
        Hex color string
    """
    return TIER_COLORS.get(tier, "#95a5a6")


def get_tier_from_percentage(percentage: float) -> str:
    """
    Get holder tier from percentage of supply.

    Args:
        percentage: Percentage of total supply

    Returns:
        Tier string: "whale", "dolphin", or "fish"
    """
    if percentage >= TIER_THRESHOLDS["whale"]:
        return "whale"
    elif percentage >= TIER_THRESHOLDS["dolphin"]:
        return "dolphin"
    else:
        return "fish"

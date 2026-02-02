"""
Whale Analysis Utilities for DeFi Analytics

This module provides functions for tracking and analyzing whale
(top holder) behavior, including accumulation patterns, stability,
and movement alerts.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .interpretation import interpret_pattern


def calculate_whale_concentration_change(
    history_df: pd.DataFrame,
    whale_addresses: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Calculate how whale concentration has changed over time.

    Args:
        history_df: DataFrame with whale balance history
        whale_addresses: Optional list of whale addresses to analyze

    Returns:
        Dictionary with concentration change metrics
    """
    if history_df.empty:
        return {
            "start_concentration": 0.0,
            "end_concentration": 0.0,
            "concentration_change": 0.0,
            "concentration_change_pct": 0.0
        }

    df = history_df.copy()

    if whale_addresses:
        df = df[df["address"].isin(whale_addresses)]

    if df.empty:
        return {
            "start_concentration": 0.0,
            "end_concentration": 0.0,
            "concentration_change": 0.0,
            "concentration_change_pct": 0.0
        }

    # Get first and last block data
    first_block = df["block_number"].min()
    last_block = df["block_number"].max()

    start_data = df[df["block_number"] == first_block]
    end_data = df[df["block_number"] == last_block]

    start_concentration = start_data["percentage"].sum()
    end_concentration = end_data["percentage"].sum()

    change = end_concentration - start_concentration
    change_pct = (change / start_concentration * 100) if start_concentration > 0 else 0

    return {
        "start_concentration": round(start_concentration, 2),
        "end_concentration": round(end_concentration, 2),
        "concentration_change": round(change, 2),
        "concentration_change_pct": round(change_pct, 2)
    }


def detect_whale_accumulation_pattern(
    history_df: pd.DataFrame,
    threshold_pct: float = 5.0
) -> Dict:
    """
    Detect accumulation/distribution patterns among whales.

    Args:
        history_df: DataFrame with whale balance history
        threshold_pct: Minimum change percentage to count as significant

    Returns:
        Dictionary with pattern analysis
    """
    if history_df.empty:
        return {
            "pattern": "unknown",
            "accumulating_whales": 0,
            "distributing_whales": 0,
            "stable_whales": 0,
            "total_whales": 0,
            "net_flow": 0.0
        }

    accumulating = 0
    distributing = 0
    stable = 0
    net_flow = 0.0

    for address in history_df["address"].unique():
        whale_data = history_df[history_df["address"] == address].sort_values("block_number")

        if len(whale_data) < 2:
            stable += 1
            continue

        start_balance = whale_data["balance"].iloc[0]
        end_balance = whale_data["balance"].iloc[-1]

        if start_balance > 0:
            change_pct = (end_balance - start_balance) / start_balance * 100
            net_flow += end_balance - start_balance

            if change_pct > threshold_pct:
                accumulating += 1
            elif change_pct < -threshold_pct:
                distributing += 1
            else:
                stable += 1
        else:
            if end_balance > 0:
                accumulating += 1
            else:
                stable += 1

    total = accumulating + distributing + stable

    # Determine overall pattern
    if total == 0:
        pattern = "unknown"
    elif accumulating > distributing * 2:
        pattern = "strong_accumulation"
    elif distributing > accumulating * 2:
        pattern = "strong_distribution"
    elif accumulating > distributing:
        pattern = "mild_accumulation"
    elif distributing > accumulating:
        pattern = "mild_distribution"
    else:
        pattern = "neutral"

    return {
        "pattern": pattern,
        "accumulating_whales": accumulating,
        "distributing_whales": distributing,
        "stable_whales": stable,
        "total_whales": total,
        "net_flow": round(net_flow, 4)
    }


def calculate_whale_stability_score(
    history_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Calculate a stability score for whale holdings.

    Higher score = more stable holdings (less movement).

    Args:
        history_df: DataFrame with whale balance history

    Returns:
        Dictionary with stability_score (0-100) and avg_volatility (percentage)
    """
    if history_df.empty:
        return {"stability_score": 0.0, "avg_volatility": 0.0}

    volatilities = []

    for address in history_df["address"].unique():
        whale_data = history_df[history_df["address"] == address].sort_values("block_number")

        if len(whale_data) < 2:
            continue

        balances = whale_data["balance"].values
        mean_balance = np.mean(balances)

        if mean_balance > 0:
            # Coefficient of variation as volatility measure
            volatility = np.std(balances) / mean_balance
            volatilities.append(volatility)

    if not volatilities:
        return {"stability_score": 0.0, "avg_volatility": 0.0}

    avg_volatility = np.mean(volatilities)

    # Stability score: inverse of volatility, scaled to 0-100
    # Lower volatility = higher stability
    stability_score = max(0, min(100, (1 - avg_volatility) * 100))

    return {
        "stability_score": round(stability_score, 2),
        "avg_volatility": round(avg_volatility * 100, 2),  # as percentage
    }


def prepare_stacked_area_data(
    history_df: pd.DataFrame,
    top_n: int = 10
) -> pd.DataFrame:
    """
    Prepare data for stacked area chart showing whale composition over time.

    Args:
        history_df: DataFrame with whale balance history
        top_n: Number of top whales to include individually

    Returns:
        DataFrame pivoted for stacked area chart
    """
    if history_df.empty:
        return pd.DataFrame()

    df = history_df.copy()

    # Get top N whales by average balance
    whale_avg_balances = df.groupby("address")["balance"].mean().sort_values(ascending=False)
    top_whales = whale_avg_balances.head(top_n).index.tolist()

    # Filter to only top whales
    df = df[df["address"].isin(top_whales)]

    # Pivot to wide format
    pivot_df = df.pivot_table(
        index="block_number",
        columns="address",
        values="percentage",
        aggfunc="first"
    ).fillna(0)

    # Sort columns by total holdings
    col_sums = pivot_df.sum()
    pivot_df = pivot_df[col_sums.sort_values(ascending=False).index]

    pivot_df = pivot_df.reset_index()

    return pivot_df


def calculate_whale_movement_alerts(
    history_df: pd.DataFrame,
    threshold_pct: float = 5.0
) -> List[Dict]:
    """
    Generate alerts for significant whale movements.

    Args:
        history_df: DataFrame with whale balance history
        threshold_pct: Minimum percentage change to trigger alert

    Returns:
        List of alert dictionaries
    """
    if history_df.empty:
        return []

    alerts = []

    for address in history_df["address"].unique():
        whale_data = history_df[history_df["address"] == address].sort_values("block_number")

        if len(whale_data) < 2:
            continue

        for i in range(1, len(whale_data)):
            prev = whale_data.iloc[i - 1]
            curr = whale_data.iloc[i]

            from_balance = prev["balance"]
            to_balance = curr["balance"]

            if from_balance > 0:
                change_pct = (to_balance - from_balance) / from_balance * 100

                if abs(change_pct) >= threshold_pct:
                    alert_type = "accumulation" if change_pct > 0 else "distribution"
                    severity = "high" if abs(change_pct) > 20 else "medium"

                    alerts.append({
                        "address": address,
                        "type": alert_type,
                        "from_balance": round(from_balance, 4),
                        "to_balance": round(to_balance, 4),
                        "change_pct": round(change_pct, 2),
                        "block_number": curr["block_number"],
                        "timestamp": curr.get("timestamp"),
                        "severity": severity
                    })

    # Sort by timestamp/block descending
    alerts.sort(key=lambda x: x.get("block_number", 0), reverse=True)

    return alerts


def interpret_whale_pattern(pattern: str) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of whale pattern.

    Args:
        pattern: Pattern string from detect_whale_accumulation_pattern

    Returns:
        Tuple of (interpretation, severity level)
    """
    return interpret_pattern(pattern, "whale_pattern")


# Alias functions for backwards compatibility
def analyze_whale_data(history_df: pd.DataFrame, threshold_pct: float = 5.0) -> Dict:
    """Alias for detect_whale_accumulation_pattern for backwards compatibility."""
    return detect_whale_accumulation_pattern(history_df, threshold_pct)


def generate_whale_summary(
    concentration_metrics: Dict,
    pattern_analysis: Dict,
    stability_metrics: Dict
) -> str:
    """
    Generate a text summary of whale analysis.

    Args:
        concentration_metrics: From calculate_whale_concentration_change
        pattern_analysis: From detect_whale_accumulation_pattern
        stability_metrics: From calculate_whale_stability_score

    Returns:
        Summary text string
    """
    pattern_interp, _ = interpret_whale_pattern(pattern_analysis.get("pattern", "unknown"))

    return (
        f"Whale Analysis Summary:\n"
        f"  - Total Whales Tracked: {pattern_analysis.get('total_whales', 0)}\n"
        f"  - Current Concentration: {concentration_metrics.get('end_concentration', 0):.1f}%\n"
        f"  - Concentration Change: {concentration_metrics.get('concentration_change', 0):+.2f}%\n"
        f"  - Accumulating: {pattern_analysis.get('accumulating_whales', 0)}\n"
        f"  - Distributing: {pattern_analysis.get('distributing_whales', 0)}\n"
        f"  - Stable: {pattern_analysis.get('stable_whales', 0)}\n"
        f"  - Stability Score: {stability_metrics.get('stability_score', 0):.0f}/100\n"
        f"  - Pattern: {pattern_interp}"
    )

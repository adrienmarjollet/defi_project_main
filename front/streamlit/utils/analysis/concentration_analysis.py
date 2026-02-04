"""
Concentration Analysis Utilities for DeFi Analytics

This module provides functions for analyzing holder concentration,
including Gini coefficient, HHI, and Lorenz curve calculations.
"""

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .interpretation import interpret_metric


def calculate_gini_coefficient(balances: np.ndarray) -> float:
    """
    Calculate Gini coefficient for a distribution of balances.

    The Gini coefficient measures inequality:
    - 0 = Perfect equality (everyone has the same balance)
    - 1 = Perfect inequality (one person has everything)

    Args:
        balances: Array of balance values

    Returns:
        Gini coefficient between 0 and 1
    """
    if len(balances) == 0:
        return 0.0

    # Filter out zero and negative balances
    balances = balances[balances > 0]
    if len(balances) == 0:
        return 0.0

    # Sort balances
    sorted_balances = np.sort(balances)
    n = len(sorted_balances)

    # Calculate cumulative sums
    cumsum = np.cumsum(sorted_balances)
    total = cumsum[-1]

    if total == 0:
        return 0.0

    # Gini formula: G = (2 * sum(i * x_i) - (n + 1) * sum(x_i)) / (n * sum(x_i))
    index_sum = np.sum((np.arange(1, n + 1) * sorted_balances))
    gini = (2 * index_sum - (n + 1) * total) / (n * total)

    return round(float(gini), 4)


def build_lorenz_curve(
    balances: np.ndarray,
    num_points: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build Lorenz curve data for visualization.

    The Lorenz curve shows the cumulative proportion of wealth
    held by the cumulative proportion of the population.

    Args:
        balances: Array of balance values
        num_points: Number of points for the curve

    Returns:
        Tuple of (population_percentiles, wealth_percentiles)
    """
    if len(balances) == 0:
        return np.array([0.0, 100.0]), np.array([0.0, 100.0])

    # Filter out zero balances
    balances = balances[balances > 0]
    if len(balances) == 0:
        return np.array([0.0, 100.0]), np.array([0.0, 100.0])

    # Sort balances in ascending order
    sorted_balances = np.sort(balances)
    n = len(sorted_balances)
    total = np.sum(sorted_balances)

    if total == 0:
        return np.array([0.0, 100.0]), np.array([0.0, 100.0])

    # Calculate cumulative proportions
    cumsum = np.cumsum(sorted_balances)

    # Create percentile points
    population_percentiles = [0.0]
    wealth_percentiles = [0.0]

    for i in range(1, num_points + 1):
        pct = i / num_points
        idx = int(pct * n) - 1
        idx = max(0, min(idx, n - 1))

        population_percentiles.append(pct * 100)
        wealth_percentiles.append((cumsum[idx] / total) * 100)

    return np.array(population_percentiles), np.array(wealth_percentiles)


def classify_holder_tiers(
    df: pd.DataFrame,
    balance_col: str = "balance",
    total_supply: Optional[float] = None
) -> Dict[str, int]:
    """
    Classify holders into tiers based on their percentage of supply.

    Tiers:
    - Whales: >1% of total supply
    - Dolphins: 0.1% - 1% of total supply
    - Fish: <0.1% of total supply

    Args:
        df: DataFrame with balance data
        balance_col: Name of the balance column
        total_supply: Total token supply (if None, calculated from sum)

    Returns:
        Dictionary with tier counts
    """
    if df.empty or balance_col not in df.columns:
        return {"whales": 0, "dolphins": 0, "fish": 0, "total": 0}

    if total_supply is None:
        total_supply = df[balance_col].sum()

    if total_supply == 0:
        return {"whales": 0, "dolphins": 0, "fish": 0, "total": len(df)}

    # Calculate percentages
    percentages = (df[balance_col] / total_supply) * 100

    whales = int((percentages >= 1.0).sum())
    dolphins = int(((percentages >= 0.1) & (percentages < 1.0)).sum())
    fish = int((percentages < 0.1).sum())

    return {
        "whales": whales,
        "dolphins": dolphins,
        "fish": fish,
        "total": len(df)
    }


def calculate_concentration_metrics(
    df: pd.DataFrame,
    balance_col: str = "balance"
) -> Dict[str, float]:
    """
    Calculate various concentration metrics for holder distribution.

    Args:
        df: DataFrame with balance data, sorted by balance descending
        balance_col: Name of the balance column

    Returns:
        Dictionary with concentration metrics
    """
    if df.empty or balance_col not in df.columns:
        return {
            "top_10_pct": 0.0,
            "top_50_pct": 0.0,
            "top_100_pct": 0.0,
            "gini": 0.0,
            "hhi": 0.0,
            "median_balance": 0.0,
            "mean_balance": 0.0,
        }

    balances = df[balance_col].values
    total = balances.sum()

    if total == 0:
        return {
            "top_10_pct": 0.0,
            "top_50_pct": 0.0,
            "top_100_pct": 0.0,
            "gini": 0.0,
            "hhi": 0.0,
            "median_balance": 0.0,
            "mean_balance": 0.0,
        }

    # Sort descending for top-N calculations
    sorted_balances = np.sort(balances)[::-1]
    percentages = (sorted_balances / total) * 100

    # Top-N concentrations
    top_10_pct = round(float(sorted_balances[:10].sum() / total * 100), 2)
    top_50_pct = round(float(sorted_balances[:50].sum() / total * 100), 2)
    top_100_pct = round(float(sorted_balances[:100].sum() / total * 100), 2)

    # Gini coefficient
    gini = calculate_gini_coefficient(balances)

    # Herfindahl-Hirschman Index (HHI)
    hhi = round(float(np.sum(percentages ** 2)), 2)

    return {
        "top_10_pct": top_10_pct,
        "top_50_pct": top_50_pct,
        "top_100_pct": top_100_pct,
        "gini": gini,
        "hhi": hhi,
        "median_balance": round(float(np.median(balances)), 6),
        "mean_balance": round(float(np.mean(balances)), 6),
    }


def interpret_gini_coefficient(gini: float) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of Gini coefficient.

    Args:
        gini: Gini coefficient value (0-1)

    Returns:
        Tuple of (interpretation, severity level)
    """
    return interpret_metric(gini, "gini")


def interpret_hhi(hhi: float) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of Herfindahl-Hirschman Index.

    Args:
        hhi: HHI value (0-10000)

    Returns:
        Tuple of (interpretation, severity level)
    """
    return interpret_metric(hhi, "hhi")


def create_distribution_histogram_data(
    balances: np.ndarray,
    num_bins: int = 50,
    log_scale: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create histogram data for balance distribution visualization.

    Args:
        balances: Array of balance values
        num_bins: Number of histogram bins
        log_scale: Whether to use log scale for bins

    Returns:
        Tuple of (bin_edges, counts)
    """
    if len(balances) == 0:
        return np.array([]), np.array([])

    # Filter out zero balances
    balances = balances[balances > 0]

    if len(balances) == 0:
        return np.array([]), np.array([])

    if log_scale:
        # Use log-spaced bins
        log_min = np.log10(balances.min())
        log_max = np.log10(balances.max())
        bins = np.logspace(log_min, log_max, num_bins + 1)
    else:
        bins = num_bins

    counts, bin_edges = np.histogram(balances, bins=bins)

    return bin_edges, counts


# Alias for backwards compatibility
def analyze_concentration_data(df: pd.DataFrame, balance_col: str = "balance") -> Dict:
    """Alias for calculate_concentration_metrics for backwards compatibility."""
    return calculate_concentration_metrics(df, balance_col)

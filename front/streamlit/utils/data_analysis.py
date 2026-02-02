"""
Data Analysis Utilities for DeFi Analytics

This module provides common data analysis functions for processing
blockchain and token metrics data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np


# ============================================================================
# Holder Count Analysis Utilities
# ============================================================================

def calculate_holder_growth_rate(
    df: pd.DataFrame,
    holder_count_col: str = "holder_count",
    period: str = "daily"
) -> pd.DataFrame:
    """
    Calculate holder count growth rate.

    Args:
        df: DataFrame with holder count data
        holder_count_col: Name of the column containing holder counts
        period: Growth period - "daily", "weekly", or "block"

    Returns:
        DataFrame with additional columns: growth_absolute, growth_rate
    """
    if df.empty:
        return df

    df = df.copy()
    df = df.sort_values("block_number" if "block_number" in df.columns else df.columns[0])

    # Calculate absolute growth (change from previous)
    df["growth_absolute"] = df[holder_count_col].diff()

    # Calculate percentage growth rate
    df["growth_rate"] = df[holder_count_col].pct_change() * 100

    # Add rolling averages for smoothing
    if len(df) >= 7:
        df["growth_rate_7d_avg"] = df["growth_rate"].rolling(window=7).mean()

    if len(df) >= 30:
        df["growth_rate_30d_avg"] = df["growth_rate"].rolling(window=30).mean()

    return df


def calculate_holder_growth_metrics(
    df: pd.DataFrame,
    holder_count_col: str = "holder_count"
) -> Dict:
    """
    Calculate summary growth metrics from holder count data.

    Args:
        df: DataFrame with holder count data
        holder_count_col: Name of the column containing holder counts

    Returns:
        Dictionary with growth metrics
    """
    if df.empty or len(df) < 2:
        return {
            "total_growth": 0,
            "total_growth_rate": 0,
            "avg_daily_growth": 0,
            "avg_daily_growth_rate": 0,
            "max_daily_growth": 0,
            "min_daily_growth": 0,
            "start_holders": 0,
            "end_holders": 0,
            "volatility": 0,
        }

    df = df.sort_values("block_number" if "block_number" in df.columns else df.columns[0])

    start_holders = df[holder_count_col].iloc[0]
    end_holders = df[holder_count_col].iloc[-1]

    total_growth = end_holders - start_holders
    total_growth_rate = (total_growth / start_holders * 100) if start_holders > 0 else 0

    # Calculate daily growth (approximate)
    growth_per_point = df[holder_count_col].diff().dropna()
    avg_growth = growth_per_point.mean() if len(growth_per_point) > 0 else 0

    # Calculate volatility (standard deviation of growth rate)
    growth_rates = df[holder_count_col].pct_change().dropna() * 100
    volatility = growth_rates.std() if len(growth_rates) > 0 else 0

    return {
        "total_growth": int(total_growth),
        "total_growth_rate": round(total_growth_rate, 2),
        "avg_daily_growth": round(avg_growth, 2),
        "avg_daily_growth_rate": round((avg_growth / start_holders * 100) if start_holders > 0 else 0, 2),
        "max_daily_growth": int(growth_per_point.max()) if len(growth_per_point) > 0 else 0,
        "min_daily_growth": int(growth_per_point.min()) if len(growth_per_point) > 0 else 0,
        "start_holders": int(start_holders),
        "end_holders": int(end_holders),
        "volatility": round(volatility, 2),
    }


def detect_holder_anomalies(
    df: pd.DataFrame,
    holder_count_col: str = "holder_count",
    threshold_std: float = 2.0
) -> pd.DataFrame:
    """
    Detect anomalous growth/decline periods in holder count.

    Identifies points where growth rate deviates significantly
    from the norm, which could indicate pump phases or
    artificial/organic growth events.

    Args:
        df: DataFrame with holder count data
        holder_count_col: Name of the column containing holder counts
        threshold_std: Number of standard deviations for anomaly detection

    Returns:
        DataFrame with anomaly flags
    """
    if df.empty or len(df) < 3:
        return df

    df = df.copy()
    df = df.sort_values("block_number" if "block_number" in df.columns else df.columns[0])

    df["growth"] = df[holder_count_col].diff()

    mean_growth = df["growth"].mean()
    std_growth = df["growth"].std()

    if std_growth > 0:
        df["anomaly_score"] = (df["growth"] - mean_growth) / std_growth
        df["is_anomaly"] = df["anomaly_score"].abs() > threshold_std
        df["anomaly_type"] = df.apply(
            lambda row: "pump" if row.get("is_anomaly") and row.get("anomaly_score", 0) > 0
            else ("decline" if row.get("is_anomaly") and row.get("anomaly_score", 0) < 0 else "normal"),
            axis=1
        )
    else:
        df["anomaly_score"] = 0
        df["is_anomaly"] = False
        df["anomaly_type"] = "normal"

    return df


def classify_growth_pattern(metrics: Dict) -> str:
    """
    Classify the growth pattern based on metrics.

    Args:
        metrics: Dictionary of growth metrics from calculate_holder_growth_metrics

    Returns:
        Classification string: "organic", "accelerating", "declining", "volatile", "stable"
    """
    growth_rate = metrics.get("avg_daily_growth_rate", 0)
    volatility = metrics.get("volatility", 0)
    total_growth = metrics.get("total_growth", 0)

    if volatility > 10:
        return "volatile"
    elif total_growth < 0:
        return "declining"
    elif growth_rate > 5:
        return "accelerating"
    elif growth_rate > 0 and growth_rate <= 5 and volatility < 5:
        return "organic"
    else:
        return "stable"


# ============================================================================
# Token Comparison Utilities
# ============================================================================

def compare_holder_growth(
    token_data: Dict[str, pd.DataFrame],
    normalize: bool = True
) -> pd.DataFrame:
    """
    Compare holder growth across multiple tokens.

    Args:
        token_data: Dictionary mapping token symbols to their holder count DataFrames
        normalize: If True, normalize holder counts to percentage of initial value

    Returns:
        DataFrame with comparison data
    """
    if not token_data:
        return pd.DataFrame()

    comparison_dfs = []

    for symbol, df in token_data.items():
        if df.empty:
            continue

        df = df.copy()
        df = df.sort_values("block_number" if "block_number" in df.columns else df.columns[0])

        if normalize:
            initial_count = df["holder_count"].iloc[0]
            df["holder_count_normalized"] = (df["holder_count"] / initial_count) * 100 if initial_count > 0 else 0

        df["token"] = symbol
        comparison_dfs.append(df)

    if not comparison_dfs:
        return pd.DataFrame()

    return pd.concat(comparison_dfs, ignore_index=True)


# ============================================================================
# Time Series Utilities
# ============================================================================

def resample_to_daily(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    value_col: str = "holder_count"
) -> pd.DataFrame:
    """
    Resample time series data to daily frequency.

    Args:
        df: DataFrame with timestamp and value columns
        timestamp_col: Name of the timestamp column
        value_col: Name of the value column to aggregate

    Returns:
        DataFrame with daily resampled data
    """
    if df.empty:
        return df

    df = df.copy()

    # Convert timestamp to datetime if needed
    if df[timestamp_col].dtype in ['int64', 'float64']:
        df["datetime"] = pd.to_datetime(df[timestamp_col], unit="s")
    else:
        df["datetime"] = pd.to_datetime(df[timestamp_col])

    df = df.set_index("datetime")

    # Resample to daily, taking the last value of each day
    daily = df[[value_col]].resample("D").last().dropna()
    daily = daily.reset_index()

    return daily


def calculate_moving_averages(
    df: pd.DataFrame,
    value_col: str = "holder_count",
    windows: List[int] = [7, 14, 30]
) -> pd.DataFrame:
    """
    Calculate moving averages for a time series.

    Args:
        df: DataFrame with value column
        value_col: Name of the value column
        windows: List of window sizes for moving averages

    Returns:
        DataFrame with moving average columns added
    """
    df = df.copy()

    for window in windows:
        if len(df) >= window:
            df[f"ma_{window}d"] = df[value_col].rolling(window=window).mean()

    return df


# ============================================================================
# Export Utilities
# ============================================================================

def prepare_export_data(
    df: pd.DataFrame,
    metrics: Dict,
    token_symbol: str
) -> Dict:
    """
    Prepare data for export (JSON/CSV).

    Args:
        df: DataFrame with holder count data
        metrics: Dictionary of growth metrics
        token_symbol: Token symbol

    Returns:
        Dictionary with export-ready data
    """
    return {
        "token_symbol": token_symbol,
        "generated_at": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "data_points": len(df),
        "time_series": df.to_dict(orient="records") if not df.empty else []
    }


# ============================================================================
# Holder Distribution Analysis Utilities
# ============================================================================

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
    if gini < 0.3:
        return "Low inequality - relatively even distribution", "good"
    elif gini < 0.5:
        return "Moderate inequality - some concentration", "moderate"
    elif gini < 0.7:
        return "High inequality - significant concentration", "warning"
    elif gini < 0.9:
        return "Very high inequality - heavy concentration", "high"
    else:
        return "Extreme inequality - near total concentration", "critical"


def interpret_hhi(hhi: float) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of Herfindahl-Hirschman Index.

    Args:
        hhi: HHI value (0-10000)

    Returns:
        Tuple of (interpretation, severity level)
    """
    if hhi < 1500:
        return "Competitive - well distributed among holders", "good"
    elif hhi < 2500:
        return "Moderately concentrated", "moderate"
    else:
        return "Highly concentrated - dominated by few holders", "warning"


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


def prepare_distribution_export_data(
    df: pd.DataFrame,
    metrics: Dict,
    tiers: Dict,
    token_symbol: str
) -> Dict:
    """
    Prepare distribution analysis data for export (JSON/CSV).

    Args:
        df: DataFrame with holder balance data
        metrics: Dictionary of concentration metrics
        tiers: Dictionary of holder tier counts
        token_symbol: Token symbol

    Returns:
        Dictionary with export-ready data
    """
    return {
        "token_symbol": token_symbol,
        "generated_at": datetime.utcnow().isoformat(),
        "concentration_metrics": metrics,
        "holder_tiers": tiers,
        "total_holders": len(df),
        "top_holders": df.head(100).to_dict(orient="records") if not df.empty else []
    }


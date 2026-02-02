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
# Generic Interpretation System
# ============================================================================

# Configuration for threshold-based interpretations
# Each metric type has a list of (threshold, message, severity) tuples
# evaluated in order - first matching threshold wins
INTERPRETATION_CONFIG = {
    "gini": [
        (0.3, "Low inequality - relatively even distribution", "good"),
        (0.5, "Moderate inequality - some concentration", "moderate"),
        (0.7, "High inequality - significant concentration", "warning"),
        (0.9, "Very high inequality - heavy concentration", "high"),
        (float('inf'), "Extreme inequality - near total concentration", "critical"),
    ],
    "hhi": [
        (1500, "Competitive - well distributed among holders", "good"),
        (2500, "Moderately concentrated", "moderate"),
        (float('inf'), "Highly concentrated - dominated by few holders", "warning"),
    ],
}

# Lookup-based interpretations (for categorical/pattern values)
PATTERN_INTERPRETATIONS = {
    "whale_pattern": {
        "strong_accumulation": ("Whales are heavily accumulating - strong bullish signal", "bullish"),
        "mild_accumulation": ("Whales showing net accumulation - mildly bullish", "mild_bullish"),
        "neutral": ("Balanced whale activity - no clear directional bias", "neutral"),
        "mild_distribution": ("Whales showing net distribution - mildly bearish", "mild_bearish"),
        "strong_distribution": ("Whales heavily distributing - potential sell pressure ahead", "bearish"),
        "unknown": ("Insufficient data to determine pattern", "unknown"),
    },
}
def interpret_metric(value: float, metric_type: str) -> Tuple[str, str]:
    """
    Generic threshold-based metric interpretation.

    Args:
        value: The metric value to interpret
        metric_type: Type of metric (must be in INTERPRETATION_CONFIG)

    Returns:
        Tuple of (interpretation message, severity level)
    """
    if metric_type not in INTERPRETATION_CONFIG:
        return f"Unknown metric type: {metric_type}", "unknown"

    for threshold, message, severity in INTERPRETATION_CONFIG[metric_type]:
        if value < threshold:
            return message, severity

    # Fallback (should not reach here with proper config)
    return "Unable to interpret", "unknown"
def interpret_pattern(pattern: str, pattern_type: str) -> Tuple[str, str]:
    """
    Generic pattern/category interpretation using lookup.

    Args:
        pattern: The pattern value to interpret
        pattern_type: Type of pattern (must be in PATTERN_INTERPRETATIONS)

    Returns:
        Tuple of (interpretation message, severity level)
    """
    if pattern_type not in PATTERN_INTERPRETATIONS:
        return f"Unknown pattern type: {pattern_type}", "unknown"

    return PATTERN_INTERPRETATIONS[pattern_type].get(
        pattern, ("Unknown pattern", "unknown")
    )
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
    data: Dict,
    export_type: str,
    token_symbol: str
) -> Dict:
    """
    Generic function to prepare data for export (JSON/CSV).

    Consolidates multiple export preparation functions into one.

    Args:
        data: Dictionary containing all relevant data for the export type.
              Expected keys vary by export_type:
              - "holder_count": df, metrics
              - "distribution": df, metrics, tiers
              - "whale": history_df, concentration_metrics, pattern_analysis, stability_metrics
              - "bubble_map": df, type_aggregation, tier_aggregation, diversity_metrics
              - "health_score": health_score, component_analysis, trend_metrics
        export_type: Type of export ("holder_count", "distribution", "whale",
                     "bubble_map", "health_score")
        token_symbol: Token symbol

    Returns:
        Dictionary with export-ready data
    """
    base = {
        "token_symbol": token_symbol,
        "generated_at": datetime.utcnow().isoformat(),
    }

    if export_type == "holder_count":
        df = data.get("df", pd.DataFrame())
        return {
            **base,
            "metrics": data.get("metrics", {}),
            "data_points": len(df),
            "time_series": df.to_dict(orient="records") if not df.empty else []
        }

    elif export_type == "distribution":
        df = data.get("df", pd.DataFrame())
        return {
            **base,
            "concentration_metrics": data.get("metrics", {}),
            "holder_tiers": data.get("tiers", {}),
            "total_holders": len(df),
            "top_holders": df.head(100).to_dict(orient="records") if not df.empty else []
        }

    elif export_type == "whale":
        history_df = data.get("history_df", pd.DataFrame())
        return {
            **base,
            "concentration_metrics": data.get("concentration_metrics", {}),
            "pattern_analysis": data.get("pattern_analysis", {}),
            "stability_metrics": data.get("stability_metrics", {}),
            "whale_count": len(history_df["address"].unique()) if not history_df.empty else 0,
            "data_points": len(history_df),
            "whale_history": history_df.to_dict(orient="records") if not history_df.empty else []
        }

    elif export_type == "bubble_map":
        df = data.get("df", pd.DataFrame())
        return {
            **base,
            "total_holders": len(df),
            "wallet_type_distribution": data.get("type_aggregation", {}),
            "tier_distribution": data.get("tier_aggregation", {}),
            "diversity_metrics": data.get("diversity_metrics", {}),
            "holders": df.to_dict(orient="records") if not df.empty else []
        }

    elif export_type == "health_score":
        health_score = data.get("health_score", {})
        return {
            **base,
            "overall_score": health_score.get("overall_score", 0),
            "health_grade": health_score.get("health_grade", "N/A"),
            "risk_level": health_score.get("risk_level", "Unknown"),
            "components": health_score.get("components", {}),
            "component_analysis": data.get("component_analysis", {}),
            "risk_factors": health_score.get("risk_factors", []),
            "positive_factors": health_score.get("positive_factors", []),
            "trend_metrics": data.get("trend_metrics", {}),
            "holder_count": health_score.get("holder_count", 0),
            "block_number": health_score.get("block_number", 0),
            "timestamp": health_score.get("timestamp", 0)
        }

    else:
        # Fallback for unknown types
        return {
            **base,
            "data": data
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
# ============================================================================
# Whale Tracking Utilities
# ============================================================================

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
) -> Dict[str, any]:
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
# ============================================================================
# Bubble Map Visualization Utilities
# ============================================================================

def calculate_bubble_sizes(
    balances: np.ndarray,
    method: str = "log",
    min_size: float = 5.0,
    max_size: float = 50.0
) -> np.ndarray:
    """
    Calculate bubble sizes from balances.

    Args:
        balances: Array of balance values
        method: Sizing method ("log", "sqrt", "linear")
        min_size: Minimum bubble size
        max_size: Maximum bubble size

    Returns:
        Array of bubble sizes
    """
    if len(balances) == 0:
        return np.array([])

    # Handle zero/negative values
    balances = np.clip(balances, 1e-18, None)

    if method == "log":
        sizes = np.log10(balances + 1)
    elif method == "sqrt":
        sizes = np.sqrt(balances)
    else:  # linear
        sizes = balances

    # Normalize to size range
    if sizes.max() > sizes.min():
        normalized = (sizes - sizes.min()) / (sizes.max() - sizes.min())
    else:
        normalized = np.ones_like(sizes) * 0.5

    return normalized * (max_size - min_size) + min_size
def aggregate_by_wallet_type(
    df: pd.DataFrame,
    balance_col: str = "balance",
    type_col: str = "wallet_type"
) -> Dict[str, Dict]:
    """
    Aggregate holder data by wallet type.

    Args:
        df: DataFrame with holder data
        balance_col: Name of balance column
        type_col: Name of wallet type column

    Returns:
        Dictionary with aggregated stats per wallet type
    """
    if df.empty or type_col not in df.columns:
        return {}

    total_balance = df[balance_col].sum()

    result = {}
    for wallet_type in df[type_col].unique():
        subset = df[df[type_col] == wallet_type]
        type_balance = subset[balance_col].sum()

        result[wallet_type] = {
            "count": len(subset),
            "total_balance": type_balance,
            "percentage": round(type_balance / total_balance * 100, 2) if total_balance > 0 else 0,
            "avg_balance": round(type_balance / len(subset), 4) if len(subset) > 0 else 0,
            "max_balance": subset[balance_col].max(),
            "min_balance": subset[balance_col].min()
        }

    return result
def aggregate_by_tier(
    df: pd.DataFrame,
    percentage_col: str = "percentage"
) -> Dict[str, Dict]:
    """
    Aggregate holder data by tier (whale/dolphin/fish).

    Args:
        df: DataFrame with holder data
        percentage_col: Name of percentage column

    Returns:
        Dictionary with aggregated stats per tier
    """
    if df.empty or percentage_col not in df.columns:
        return {}

    def get_tier(pct):
        if pct >= 1.0:
            return "whale"
        elif pct >= 0.1:
            return "dolphin"
        return "fish"

    df_copy = df.copy()
    df_copy["tier"] = df_copy[percentage_col].apply(get_tier)

    result = {}
    for tier in ["whale", "dolphin", "fish"]:
        subset = df_copy[df_copy["tier"] == tier]
        tier_pct = subset[percentage_col].sum()

        result[tier] = {
            "count": len(subset),
            "total_percentage": round(tier_pct, 2),
            "avg_percentage": round(tier_pct / len(subset), 4) if len(subset) > 0 else 0,
            "max_percentage": subset[percentage_col].max() if len(subset) > 0 else 0,
            "min_percentage": subset[percentage_col].min() if len(subset) > 0 else 0
        }

    return result
def calculate_holder_diversity_score(
    df: pd.DataFrame,
    type_col: str = "wallet_type",
    percentage_col: str = "percentage"
) -> Dict[str, float]:
    """
    Calculate diversity metrics for holder distribution.

    Args:
        df: DataFrame with holder data
        type_col: Name of wallet type column
        percentage_col: Name of percentage column

    Returns:
        Dictionary with diversity metrics
    """
    if df.empty:
        return {
            "type_diversity_score": 0.0,
            "tier_diversity_score": 0.0,
            "overall_diversity_score": 0.0,
            "eoa_dominance": 0.0
        }

    # Type diversity (Shannon entropy)
    type_counts = df[type_col].value_counts(normalize=True)
    type_entropy = -np.sum(type_counts * np.log2(type_counts + 1e-10))
    max_type_entropy = np.log2(len(type_counts)) if len(type_counts) > 1 else 1
    type_diversity = type_entropy / max_type_entropy if max_type_entropy > 0 else 0

    # Tier diversity
    def get_tier(pct):
        if pct >= 1.0:
            return "whale"
        elif pct >= 0.1:
            return "dolphin"
        return "fish"

    df_copy = df.copy()
    df_copy["tier"] = df_copy[percentage_col].apply(get_tier)

    tier_counts = df_copy["tier"].value_counts(normalize=True)
    tier_entropy = -np.sum(tier_counts * np.log2(tier_counts + 1e-10))
    max_tier_entropy = np.log2(3)  # 3 tiers
    tier_diversity = tier_entropy / max_tier_entropy if max_tier_entropy > 0 else 0

    # EOA dominance
    eoa_count = len(df[df[type_col] == "eoa"]) if "eoa" in df[type_col].values else 0
    eoa_dominance = eoa_count / len(df) * 100 if len(df) > 0 else 0

    # Overall diversity (weighted average)
    overall = (type_diversity * 0.4 + tier_diversity * 0.6) * 100

    return {
        "type_diversity_score": round(type_diversity * 100, 2),
        "tier_diversity_score": round(tier_diversity * 100, 2),
        "overall_diversity_score": round(overall, 2),
        "eoa_dominance": round(eoa_dominance, 2)
    }
# ============================================================================
# Token Health Score Utilities
# ============================================================================

def calculate_health_score_trend(
    history_df: pd.DataFrame,
    score_col: str = "overall_score"
) -> Dict[str, float]:
    """
    Calculate trend metrics for health score history.

    Args:
        history_df: DataFrame with historical health scores
        score_col: Name of the score column

    Returns:
        Dictionary with trend metrics
    """
    if history_df.empty or len(history_df) < 2:
        return {
            "trend_direction": "stable",
            "score_change": 0.0,
            "score_change_pct": 0.0,
            "avg_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "volatility": 0.0
        }

    df = history_df.copy()
    df = df.sort_values("timestamp" if "timestamp" in df.columns else df.columns[0])

    start_score = df[score_col].iloc[0]
    end_score = df[score_col].iloc[-1]

    score_change = end_score - start_score
    score_change_pct = (score_change / start_score * 100) if start_score > 0 else 0

    # Determine trend direction
    if score_change > 5:
        trend_direction = "improving"
    elif score_change < -5:
        trend_direction = "declining"
    else:
        trend_direction = "stable"

    # Calculate volatility
    volatility = df[score_col].std() if len(df) > 2 else 0

    return {
        "trend_direction": trend_direction,
        "score_change": round(score_change, 2),
        "score_change_pct": round(score_change_pct, 2),
        "avg_score": round(df[score_col].mean(), 2),
        "min_score": round(df[score_col].min(), 2),
        "max_score": round(df[score_col].max(), 2),
        "volatility": round(volatility, 2)
    }
def interpret_health_trend(trend_metrics: Dict) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of health score trend.

    Args:
        trend_metrics: Dictionary from calculate_health_score_trend

    Returns:
        Tuple of (interpretation, severity level)
    """
    direction = trend_metrics.get("trend_direction", "stable")
    change_pct = trend_metrics.get("score_change_pct", 0)
    volatility = trend_metrics.get("volatility", 0)

    if direction == "improving":
        if change_pct > 20:
            return "Significant improvement in token health", "positive"
        else:
            return "Token health is gradually improving", "positive"
    elif direction == "declining":
        if change_pct < -20:
            return "Significant decline in token health - review risk factors", "warning"
        else:
            return "Token health showing slight decline", "caution"
    else:
        if volatility > 10:
            return "Health score is stable but volatile", "caution"
        else:
            return "Token health remains stable", "neutral"
def calculate_component_contributions(
    components: Dict[str, float],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Dict]:
    """
    Calculate the contribution of each component to the overall score.

    Args:
        components: Dictionary of component scores
        weights: Dictionary of component weights (uses default if None)

    Returns:
        Dictionary with contribution analysis per component
    """
    if weights is None:
        weights = {
            "holder_count": 0.20,
            "concentration": 0.25,
            "growth_trend": 0.20,
            "whale_stability": 0.20,
            "contract_ratio": 0.15,
        }

    results = {}
    total_weighted_score = 0

    for key, weight in weights.items():
        score_key = f"{key}_score"
        score = components.get(score_key, 0)
        weighted_contribution = score * weight
        total_weighted_score += weighted_contribution

        results[key] = {
            "score": score,
            "weight": weight,
            "weighted_contribution": round(weighted_contribution, 2),
            "percentage_of_total": 0  # Will be calculated after
        }

    # Calculate percentage of total
    for key in results:
        if total_weighted_score > 0:
            results[key]["percentage_of_total"] = round(
                results[key]["weighted_contribution"] / total_weighted_score * 100, 2
            )

    return results
def identify_weakest_components(
    components: Dict[str, float],
    threshold: float = 60.0
) -> List[Dict]:
    """
    Identify components scoring below threshold that need improvement.

    Args:
        components: Dictionary of component scores
        threshold: Score threshold for identification

    Returns:
        List of weak components with improvement suggestions
    """
    weak_components = []

    component_suggestions = {
        "holder_count_score": {
            "name": "Holder Count",
            "suggestions": [
                "Increase marketing and community outreach",
                "Consider airdrops or incentive programs",
                "List on more exchanges"
            ]
        },
        "concentration_score": {
            "name": "Concentration",
            "suggestions": [
                "Encourage whale distribution through staking rewards",
                "Implement vesting schedules for large holders",
                "Increase liquidity mining incentives for smaller holders"
            ]
        },
        "growth_trend_score": {
            "name": "Growth Trend",
            "suggestions": [
                "Analyze and address causes of holder decline",
                "Improve utility and use cases",
                "Strengthen community engagement"
            ]
        },
        "whale_stability_score": {
            "name": "Whale Stability",
            "suggestions": [
                "Implement whale-friendly staking mechanisms",
                "Provide transparency on project developments",
                "Consider buyback programs during distribution periods"
            ]
        },
        "contract_ratio_score": {
            "name": "Contract Ratio",
            "suggestions": [
                "Focus on organic user acquisition",
                "Reduce reliance on bot/contract interactions",
                "Improve user experience for retail users"
            ]
        }
    }

    for key, score in components.items():
        if score < threshold and key in component_suggestions:
            weak_components.append({
                "component": component_suggestions[key]["name"],
                "score": score,
                "gap_to_threshold": round(threshold - score, 2),
                "suggestions": component_suggestions[key]["suggestions"]
            })

    # Sort by score (weakest first)
    weak_components.sort(key=lambda x: x["score"])

    return weak_components
def compare_health_scores(
    token_scores: Dict[str, Dict]
) -> pd.DataFrame:
    """
    Compare health scores across multiple tokens.

    Args:
        token_scores: Dictionary mapping token symbols to their health score data

    Returns:
        DataFrame with comparison data
    """
    if not token_scores:
        return pd.DataFrame()

    comparison_data = []

    for symbol, data in token_scores.items():
        comparison_data.append({
            "Token": symbol,
            "Overall Score": data.get("overall_score", 0),
            "Grade": data.get("health_grade", "N/A"),
            "Risk Level": data.get("risk_level", "Unknown"),
            "Holder Count": data.get("components", {}).get("holder_count_score", 0),
            "Concentration": data.get("components", {}).get("concentration_score", 0),
            "Growth Trend": data.get("components", {}).get("growth_trend_score", 0),
            "Whale Stability": data.get("components", {}).get("whale_stability_score", 0),
            "Contract Ratio": data.get("components", {}).get("contract_ratio_score", 0),
        })

    df = pd.DataFrame(comparison_data)
    df = df.sort_values("Overall Score", ascending=False)

    return df
def get_health_score_summary(
    health_score: Dict
) -> str:
    """
    Generate a text summary of the health score.

    Args:
        health_score: Health score data dictionary

    Returns:
        Summary text string
    """
    overall = health_score.get("overall_score", 0)
    grade = health_score.get("health_grade", "N/A")
    risk_level = health_score.get("risk_level", "Unknown")
    holder_count = health_score.get("holder_count", 0)

    components = health_score.get("components", {})
    risk_factors = health_score.get("risk_factors", [])
    positive_factors = health_score.get("positive_factors", [])

    summary_lines = [
        f"Token Health Score: {overall:.1f}/100 (Grade: {grade})",
        f"Risk Level: {risk_level}",
        f"Total Holders: {holder_count:,}",
        "",
        "Component Scores:",
    ]

    if components:
        summary_lines.extend([
            f"  - Holder Count: {components.get('holder_count_score', 0):.1f}",
            f"  - Concentration: {components.get('concentration_score', 0):.1f}",
            f"  - Growth Trend: {components.get('growth_trend_score', 0):.1f}",
            f"  - Whale Stability: {components.get('whale_stability_score', 0):.1f}",
            f"  - Contract Ratio: {components.get('contract_ratio_score', 0):.1f}",
        ])

    if risk_factors:
        summary_lines.append("")
        summary_lines.append("Risk Factors:")
        for factor in risk_factors[:5]:
            summary_lines.append(f"  - {factor}")

    if positive_factors:
        summary_lines.append("")
        summary_lines.append("Positive Indicators:")
        for factor in positive_factors[:5]:
            summary_lines.append(f"  - {factor}")

    return "\n".join(summary_lines)


# ============================================================================
# Suspicious Activity Detection Utilities
# ============================================================================

# Configuration for suspicious activity interpretation
SUSPICIOUS_ACTIVITY_CONFIG = {
    "risk_level": {
        "Critical": ("Critical risk - Multiple severe red flags detected. Exercise extreme caution.", "critical"),
        "High": ("High risk - Significant manipulation indicators present. Thorough due diligence recommended.", "high"),
        "Medium": ("Moderate risk - Some suspicious patterns detected. Additional investigation advised.", "medium"),
        "Low": ("Low risk - No major red flags detected. Standard due diligence recommended.", "low"),
    },
    "activity_type": {
        "wash_trading": ("Circular Transfer Pattern", "Tokens circulating between a small set of wallets, potentially inflating volume"),
        "concentration_spike": ("Concentration Anomaly", "Unusual concentration of tokens in single wallet or small group"),
        "coordinated_wallets": ("Coordinated Wallet Activity", "Multiple wallets showing synchronized behavior or similar patterns"),
        "dump_pattern": ("Distribution Pattern", "Large holders showing signs of coordinated selling"),
        "sybil_cluster": ("Potential Sybil Attack", "Multiple wallets with identical characteristics, possibly controlled by single entity"),
        "rapid_accumulation": ("Rapid Accumulation", "Unusually fast accumulation of tokens by single entity"),
    },
}


def interpret_suspicious_risk_level(risk_level: str) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of suspicious activity risk level.

    Args:
        risk_level: Risk level string ("Critical", "High", "Medium", "Low")

    Returns:
        Tuple of (interpretation message, severity level)
    """
    return SUSPICIOUS_ACTIVITY_CONFIG["risk_level"].get(
        risk_level, ("Unknown risk level", "unknown")
    )


def interpret_activity_type(activity_type: str) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of activity type.

    Args:
        activity_type: Activity type string

    Returns:
        Tuple of (display name, description)
    """
    return SUSPICIOUS_ACTIVITY_CONFIG["activity_type"].get(
        activity_type, (activity_type, "Unknown activity type")
    )


def calculate_suspicious_activity_metrics(
    activities: List[Dict]
) -> Dict[str, any]:
    """
    Calculate summary metrics from suspicious activity list.

    Args:
        activities: List of suspicious activity dictionaries

    Returns:
        Dictionary with summary metrics
    """
    if not activities:
        return {
            "total_activities": 0,
            "total_risk_score": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_type": {},
            "unique_addresses": 0,
            "most_common_type": None,
            "highest_severity": None,
        }

    # Count by severity
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in activities:
        severity = a.get("severity", "unknown")
        if severity in by_severity:
            by_severity[severity] += 1

    # Count by type
    by_type = {}
    for a in activities:
        act_type = a.get("activity_type", "unknown")
        by_type[act_type] = by_type.get(act_type, 0) + 1

    # Collect unique addresses
    all_addresses = set()
    for a in activities:
        addresses = a.get("involved_addresses", [])
        all_addresses.update(addresses)

    # Calculate total risk score
    total_risk = sum(a.get("risk_score", 0) for a in activities)

    # Find most common type
    most_common_type = max(by_type, key=by_type.get) if by_type else None

    # Find highest severity
    highest_severity = None
    for sev in ["critical", "high", "medium", "low"]:
        if by_severity[sev] > 0:
            highest_severity = sev
            break

    return {
        "total_activities": len(activities),
        "total_risk_score": round(total_risk, 2),
        "by_severity": by_severity,
        "by_type": by_type,
        "unique_addresses": len(all_addresses),
        "most_common_type": most_common_type,
        "highest_severity": highest_severity,
    }


def group_activities_by_address(
    activities: List[Dict]
) -> Dict[str, List[Dict]]:
    """
    Group suspicious activities by involved addresses.

    Useful for identifying wallets involved in multiple suspicious patterns.

    Args:
        activities: List of suspicious activity dictionaries

    Returns:
        Dictionary mapping addresses to their activities
    """
    address_activities = {}

    for activity in activities:
        addresses = activity.get("involved_addresses", [])
        for addr in addresses:
            if addr not in address_activities:
                address_activities[addr] = []
            address_activities[addr].append(activity)

    # Sort by number of activities (most suspicious first)
    sorted_addresses = dict(
        sorted(address_activities.items(), key=lambda x: len(x[1]), reverse=True)
    )

    return sorted_addresses


def calculate_address_risk_score(
    address: str,
    activities: List[Dict]
) -> Dict[str, any]:
    """
    Calculate risk score for a specific address based on its activities.

    Args:
        address: Wallet address
        activities: List of activities involving this address

    Returns:
        Dictionary with address risk metrics
    """
    if not activities:
        return {
            "address": address,
            "risk_score": 0,
            "activity_count": 0,
            "severity_breakdown": {},
            "activity_types": [],
        }

    total_risk = sum(a.get("risk_score", 0) for a in activities)
    severity_breakdown = {}
    activity_types = set()

    for a in activities:
        severity = a.get("severity", "unknown")
        severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
        activity_types.add(a.get("activity_type", "unknown"))

    return {
        "address": address,
        "risk_score": round(total_risk, 2),
        "activity_count": len(activities),
        "severity_breakdown": severity_breakdown,
        "activity_types": list(activity_types),
    }


def prepare_suspicious_activity_export_data(
    report: Dict,
    token_symbol: str
) -> Dict:
    """
    Prepare suspicious activity report for export.

    Args:
        report: Suspicious activity report dictionary
        token_symbol: Token symbol

    Returns:
        Dictionary with export-ready data
    """
    return {
        "token_symbol": token_symbol,
        "generated_at": datetime.utcnow().isoformat(),
        "token_address": report.get("token_address", ""),
        "overall_risk_score": report.get("overall_risk_score", 0),
        "risk_level": report.get("risk_level", "Unknown"),
        "total_flags": report.get("total_flags", 0),
        "severity_breakdown": {
            "critical": report.get("critical_flags", 0),
            "high": report.get("high_flags", 0),
            "medium": report.get("medium_flags", 0),
            "low": report.get("low_flags", 0),
        },
        "activities": report.get("activities", []),
        "summary": report.get("summary", ""),
        "block_number": report.get("block_number", 0),
        "timestamp": report.get("timestamp", 0),
    }


def filter_activities_by_severity(
    activities: List[Dict],
    min_severity: str = "low"
) -> List[Dict]:
    """
    Filter activities by minimum severity level.

    Args:
        activities: List of suspicious activity dictionaries
        min_severity: Minimum severity to include ("critical", "high", "medium", "low")

    Returns:
        Filtered list of activities
    """
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    min_level = severity_order.get(min_severity, 1)

    return [
        a for a in activities
        if severity_order.get(a.get("severity", "low"), 1) >= min_level
    ]


def filter_activities_by_type(
    activities: List[Dict],
    activity_types: List[str]
) -> List[Dict]:
    """
    Filter activities by type.

    Args:
        activities: List of suspicious activity dictionaries
        activity_types: List of activity types to include

    Returns:
        Filtered list of activities
    """
    return [
        a for a in activities
        if a.get("activity_type") in activity_types
    ]


def get_suspicious_activity_summary(
    report: Dict
) -> str:
    """
    Generate a text summary of the suspicious activity report.

    Args:
        report: Suspicious activity report dictionary

    Returns:
        Summary text string
    """
    risk_score = report.get("overall_risk_score", 0)
    risk_level = report.get("risk_level", "Unknown")
    total_flags = report.get("total_flags", 0)
    critical = report.get("critical_flags", 0)
    high = report.get("high_flags", 0)
    medium = report.get("medium_flags", 0)
    low = report.get("low_flags", 0)

    summary_lines = [
        f"Suspicious Activity Report",
        f"==========================",
        f"Risk Score: {risk_score:.1f}/100",
        f"Risk Level: {risk_level}",
        f"",
        f"Flag Summary:",
        f"  Total Flags: {total_flags}",
    ]

    if critical > 0:
        summary_lines.append(f"  - Critical: {critical}")
    if high > 0:
        summary_lines.append(f"  - High: {high}")
    if medium > 0:
        summary_lines.append(f"  - Medium: {medium}")
    if low > 0:
        summary_lines.append(f"  - Low: {low}")

    # Add interpretation
    interpretation, _ = interpret_suspicious_risk_level(risk_level)
    summary_lines.extend([
        "",
        "Assessment:",
        f"  {interpretation}"
    ])

    return "\n".join(summary_lines)


def calculate_risk_trend(
    historical_reports: List[Dict]
) -> Dict[str, any]:
    """
    Calculate risk trend from historical suspicious activity reports.

    Args:
        historical_reports: List of report dictionaries sorted by time

    Returns:
        Dictionary with trend metrics
    """
    if not historical_reports or len(historical_reports) < 2:
        return {
            "trend_direction": "stable",
            "risk_change": 0,
            "risk_change_pct": 0,
            "avg_risk": 0,
            "volatility": 0,
        }

    scores = [r.get("overall_risk_score", 0) for r in historical_reports]

    start_score = scores[0]
    end_score = scores[-1]
    risk_change = end_score - start_score
    risk_change_pct = (risk_change / start_score * 100) if start_score > 0 else 0

    # Determine trend
    if risk_change > 10:
        trend_direction = "increasing"
    elif risk_change < -10:
        trend_direction = "decreasing"
    else:
        trend_direction = "stable"

    return {
        "trend_direction": trend_direction,
        "risk_change": round(risk_change, 2),
        "risk_change_pct": round(risk_change_pct, 2),
        "avg_risk": round(np.mean(scores), 2),
        "volatility": round(np.std(scores), 2) if len(scores) > 2 else 0,
    }

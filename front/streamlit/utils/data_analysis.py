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


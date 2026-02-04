"""
Export Utilities for DeFi Analytics

This module provides functions for preparing and exporting
analysis data to various formats (JSON, CSV).
"""

from datetime import datetime
from typing import Dict

import pandas as pd


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


def export_to_csv(
    df: pd.DataFrame,
    filepath: str,
    include_index: bool = False
) -> bool:
    """
    Export DataFrame to CSV file.

    Args:
        df: DataFrame to export
        filepath: Path to save CSV file
        include_index: Whether to include the index in the CSV

    Returns:
        True if successful, False otherwise
    """
    try:
        df.to_csv(filepath, index=include_index)
        return True
    except Exception:
        return False


def prepare_health_score_export_data(
    data: Dict,
    token_symbol: str
) -> Dict:
    """
    Prepare health score data for export.

    This is a convenience wrapper around prepare_export_data.

    Args:
        data: Dictionary containing health score data
        token_symbol: Token symbol

    Returns:
        Dictionary with export-ready data
    """
    return prepare_export_data(data, "health_score", token_symbol)


def prepare_whale_export_data(
    data: Dict,
    token_symbol: str
) -> Dict:
    """
    Prepare whale tracking data for export.

    This is a convenience wrapper around prepare_export_data.

    Args:
        data: Dictionary containing whale tracking data
        token_symbol: Token symbol

    Returns:
        Dictionary with export-ready data
    """
    return prepare_export_data(data, "whale", token_symbol)


def prepare_distribution_export_data(
    data: Dict,
    token_symbol: str
) -> Dict:
    """
    Prepare distribution data for export.

    This is a convenience wrapper around prepare_export_data.

    Args:
        data: Dictionary containing distribution data
        token_symbol: Token symbol

    Returns:
        Dictionary with export-ready data
    """
    return prepare_export_data(data, "distribution", token_symbol)

"""
Token Health Score Utilities for DeFi Analytics

This module provides functions for analyzing token health scores,
including trend analysis, component breakdown, and summary generation.
"""

from typing import Dict, List, Optional, Tuple

import pandas as pd


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


# Alias for backwards compatibility
def analyze_health_score_data(health_score: Dict) -> Dict:
    """Alias that returns the health score with additional analysis."""
    return {
        **health_score,
        "summary": get_health_score_summary(health_score),
        "weak_components": identify_weakest_components(
            health_score.get("components", {})
        )
    }

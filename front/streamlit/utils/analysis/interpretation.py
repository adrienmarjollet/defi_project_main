"""
Generic Interpretation Utilities for DeFi Analytics

This module provides threshold-based and pattern-based interpretation
utilities for various metrics.
"""

from typing import Tuple


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

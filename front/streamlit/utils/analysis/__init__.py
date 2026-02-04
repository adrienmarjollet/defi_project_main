"""
Analysis Utilities for DeFi Analytics

This package provides modular analysis utilities for processing
blockchain and token metrics data.

Modules:
    - interpretation: Generic threshold and pattern interpretation
    - holder_analysis: Holder count analysis and growth metrics
    - concentration_analysis: Gini/HHI concentration metrics
    - whale_analysis: Whale tracking and behavior analysis
    - health_score: Token health score analysis
    - suspicious_activity: Suspicious activity detection
    - export: Data export utilities
"""

# Interpretation utilities
from .interpretation import (
    INTERPRETATION_CONFIG,
    PATTERN_INTERPRETATIONS,
    interpret_metric,
    interpret_pattern,
)

# Holder analysis utilities
from .holder_analysis import (
    calculate_holder_growth_rate,
    calculate_holder_growth_metrics,
    detect_holder_anomalies,
    classify_growth_pattern,
    compare_holder_growth,
    resample_to_daily,
    calculate_moving_averages,
    analyze_holder_count_data,
    generate_holder_count_summary,
)

# Concentration analysis utilities
from .concentration_analysis import (
    calculate_gini_coefficient,
    build_lorenz_curve,
    classify_holder_tiers,
    calculate_concentration_metrics,
    interpret_gini_coefficient,
    interpret_hhi,
    create_distribution_histogram_data,
    analyze_concentration_data,
)

# Whale analysis utilities
from .whale_analysis import (
    calculate_whale_concentration_change,
    detect_whale_accumulation_pattern,
    calculate_whale_stability_score,
    prepare_stacked_area_data,
    calculate_whale_movement_alerts,
    interpret_whale_pattern,
    analyze_whale_data,
    generate_whale_summary,
)

# Health score utilities
from .health_score import (
    calculate_health_score_trend,
    interpret_health_trend,
    calculate_component_contributions,
    identify_weakest_components,
    compare_health_scores,
    get_health_score_summary,
    analyze_health_score_data,
)

# Suspicious activity utilities
from .suspicious_activity import (
    SUSPICIOUS_ACTIVITY_CONFIG,
    interpret_suspicious_risk_level,
    interpret_activity_type,
    calculate_suspicious_activity_metrics,
    group_activities_by_address,
    calculate_address_risk_score,
    prepare_suspicious_activity_export_data,
    filter_activities_by_severity,
    filter_activities_by_type,
    get_suspicious_activity_summary,
    calculate_risk_trend,
    analyze_suspicious_data,
)

# Export utilities
from .export import (
    prepare_export_data,
    export_to_csv,
    prepare_health_score_export_data,
    prepare_whale_export_data,
    prepare_distribution_export_data,
)

__all__ = [
    # Interpretation
    "INTERPRETATION_CONFIG",
    "PATTERN_INTERPRETATIONS",
    "interpret_metric",
    "interpret_pattern",
    # Holder analysis
    "calculate_holder_growth_rate",
    "calculate_holder_growth_metrics",
    "detect_holder_anomalies",
    "classify_growth_pattern",
    "compare_holder_growth",
    "resample_to_daily",
    "calculate_moving_averages",
    "analyze_holder_count_data",
    "generate_holder_count_summary",
    # Concentration analysis
    "calculate_gini_coefficient",
    "build_lorenz_curve",
    "classify_holder_tiers",
    "calculate_concentration_metrics",
    "interpret_gini_coefficient",
    "interpret_hhi",
    "create_distribution_histogram_data",
    "analyze_concentration_data",
    # Whale analysis
    "calculate_whale_concentration_change",
    "detect_whale_accumulation_pattern",
    "calculate_whale_stability_score",
    "prepare_stacked_area_data",
    "calculate_whale_movement_alerts",
    "interpret_whale_pattern",
    "analyze_whale_data",
    "generate_whale_summary",
    # Health score
    "calculate_health_score_trend",
    "interpret_health_trend",
    "calculate_component_contributions",
    "identify_weakest_components",
    "compare_health_scores",
    "get_health_score_summary",
    "analyze_health_score_data",
    # Suspicious activity
    "SUSPICIOUS_ACTIVITY_CONFIG",
    "interpret_suspicious_risk_level",
    "interpret_activity_type",
    "calculate_suspicious_activity_metrics",
    "group_activities_by_address",
    "calculate_address_risk_score",
    "prepare_suspicious_activity_export_data",
    "filter_activities_by_severity",
    "filter_activities_by_type",
    "get_suspicious_activity_summary",
    "calculate_risk_trend",
    "analyze_suspicious_data",
    # Export
    "prepare_export_data",
    "export_to_csv",
    "prepare_health_score_export_data",
    "prepare_whale_export_data",
    "prepare_distribution_export_data",
]

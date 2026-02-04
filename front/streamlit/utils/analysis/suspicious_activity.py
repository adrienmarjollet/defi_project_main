"""
Suspicious Activity Detection Utilities for DeFi Analytics

This module provides functions for detecting and analyzing suspicious
activity in token holder data, including wash trading, Sybil attacks,
and coordinated wallet behavior.
"""

from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np


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
) -> Dict:
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
) -> Dict:
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
) -> Dict:
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


# Alias for backwards compatibility
def analyze_suspicious_data(report: Dict) -> Dict:
    """Alias that returns the report with additional analysis."""
    activities = report.get("activities", [])
    metrics = calculate_suspicious_activity_metrics(activities)

    return {
        **report,
        "metrics": metrics,
        "summary_text": get_suspicious_activity_summary(report),
        "address_groups": group_activities_by_address(activities)
    }

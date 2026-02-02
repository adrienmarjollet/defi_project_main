"""
Token Health Score Queries for ERC-20 Token Tracking

This module provides functionality to calculate a composite health score
for tokens based on various holder metrics.

Features:
- Composite health score from 0-100
- Component scores: holder count, concentration, growth trend, whale stability, contract ratio
- Health grade (A+, A, B, C, D, F) and risk level classification
- Historical health score tracking
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .graph_client import GraphClient
from .queries import ERC20Queries
from .holder_distribution_queries import HolderDistributionQueries
from .whale_tracking_queries import WhaleTrackingQueries
from .holder_count_queries import HolderCountQueries
from .bubble_map_queries import BubbleMapQueries

logger = logging.getLogger(__name__)

# Constants for scoring
BLOCKS_PER_DAY = 7200  # ~12 second blocks
BLOCKS_PER_WEEK = BLOCKS_PER_DAY * 7

# Scoring weights (must sum to 1.0)
SCORE_WEIGHTS = {
    "holder_count": 0.20,
    "concentration": 0.25,
    "growth_trend": 0.20,
    "whale_stability": 0.20,
    "contract_ratio": 0.15,
}


@dataclass
class HealthScoreComponents:
    """Individual component scores for the health score calculation."""
    holder_count_score: float  # 0-100, based on holder count
    concentration_score: float  # 0-100, inverse of concentration (higher = more decentralized)
    growth_trend_score: float  # 0-100, based on holder growth momentum
    whale_stability_score: float  # 0-100, based on whale holding stability
    contract_ratio_score: float  # 0-100, based on EOA vs contract ratio


@dataclass
class TokenHealthScore:
    """Complete token health score with all components and metadata."""
    overall_score: float  # 0-100, weighted average of components
    components: HealthScoreComponents
    health_grade: str  # A+, A, B, C, D, F
    risk_level: str  # "Low", "Medium", "High", "Critical"
    risk_factors: List[str]  # List of identified risk factors
    positive_factors: List[str]  # List of positive indicators
    holder_count: int
    total_supply: float
    block_number: int
    timestamp: int


class TokenHealthScoreQueries:
    """
    Queries for calculating token health scores.

    This class combines multiple metrics to produce a comprehensive
    health score for any ERC-20 token.

    Example usage:
        queries = TokenHealthScoreQueries(subgraph_url="https://api.studio.thegraph.com/query/.../erc20-tracker/v0.0.1")

        # Get health score
        health = queries.calculate_health_score(token_address)
        print(f"Health Score: {health.overall_score:.1f}/100 ({health.health_grade})")
        print(f"Risk Level: {health.risk_level}")
    """

    def __init__(
        self,
        subgraph_url: str,
        client: Optional[GraphClient] = None
    ):
        """
        Initialize TokenHealthScoreQueries.

        Args:
            subgraph_url: URL of the deployed erc20-tracker subgraph
            client: Optional GraphClient instance (creates new one if not provided)
        """
        self.subgraph_url = subgraph_url
        self.client = client or GraphClient()
        self.erc20_queries = ERC20Queries(subgraph_url=subgraph_url, client=self.client)
        self.distribution_queries = HolderDistributionQueries(subgraph_url=subgraph_url, client=self.client)
        self.whale_queries = WhaleTrackingQueries(subgraph_url=subgraph_url, client=self.client)
        self.holder_count_queries = HolderCountQueries(subgraph_url=subgraph_url, client=self.client)
        self.bubble_map_queries = BubbleMapQueries(subgraph_url=subgraph_url, client=self.client)

    def calculate_holder_count_score(
        self,
        holder_count: int
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate score based on holder count.

        More holders generally indicates a healthier, more decentralized token.

        Args:
            holder_count: Current number of unique holders

        Returns:
            Tuple of (score, risk_factors, positive_factors)
        """
        risk_factors = []
        positive_factors = []

        # Scoring tiers
        if holder_count >= 10000:
            score = 100.0
            positive_factors.append(f"Excellent holder count ({holder_count:,}+ holders)")
        elif holder_count >= 5000:
            score = 90.0
            positive_factors.append(f"Strong holder count ({holder_count:,} holders)")
        elif holder_count >= 1000:
            score = 75.0
            positive_factors.append(f"Good holder count ({holder_count:,} holders)")
        elif holder_count >= 500:
            score = 60.0
        elif holder_count >= 100:
            score = 40.0
            risk_factors.append(f"Low holder count ({holder_count} holders)")
        elif holder_count >= 50:
            score = 25.0
            risk_factors.append(f"Very low holder count ({holder_count} holders)")
        else:
            score = 10.0
            risk_factors.append(f"Critical: Extremely low holder count ({holder_count} holders)")

        return score, risk_factors, positive_factors

    def calculate_concentration_score(
        self,
        gini_coefficient: float,
        top_10_concentration: float,
        whale_count: int
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate score based on token concentration.

        Lower concentration = higher score (more decentralized is better).

        Args:
            gini_coefficient: Gini coefficient (0-1)
            top_10_concentration: Percentage held by top 10 holders
            whale_count: Number of whale holders (>1% of supply)

        Returns:
            Tuple of (score, risk_factors, positive_factors)
        """
        risk_factors = []
        positive_factors = []

        # Gini-based score (0 = equal, 1 = concentrated)
        # Invert so higher = better
        gini_score = (1 - gini_coefficient) * 100

        # Top 10 concentration penalty
        if top_10_concentration > 80:
            concentration_penalty = 40
            risk_factors.append(f"Extreme concentration: Top 10 hold {top_10_concentration:.1f}%")
        elif top_10_concentration > 60:
            concentration_penalty = 25
            risk_factors.append(f"High concentration: Top 10 hold {top_10_concentration:.1f}%")
        elif top_10_concentration > 40:
            concentration_penalty = 10
        elif top_10_concentration < 30:
            concentration_penalty = -10  # Bonus for low concentration
            positive_factors.append(f"Well distributed: Top 10 hold only {top_10_concentration:.1f}%")
        else:
            concentration_penalty = 0

        # Whale count adjustment
        if whale_count > 10:
            whale_penalty = 15
            risk_factors.append(f"Many whales ({whale_count} holders with >1%)")
        elif whale_count > 5:
            whale_penalty = 5
        elif whale_count <= 2:
            whale_penalty = -5  # Bonus
            positive_factors.append(f"Few whale holders ({whale_count})")
        else:
            whale_penalty = 0

        score = max(0, min(100, gini_score - concentration_penalty - whale_penalty))

        return score, risk_factors, positive_factors

    def calculate_growth_trend_score(
        self,
        growth_rate: float,
        volatility: float,
        holder_count: int
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate score based on holder growth trends.

        Positive growth with low volatility = higher score.

        Args:
            growth_rate: Percentage growth rate over period
            volatility: Standard deviation of growth
            holder_count: Current holder count (for context)

        Returns:
            Tuple of (score, risk_factors, positive_factors)
        """
        risk_factors = []
        positive_factors = []

        # Base score on growth rate
        if growth_rate > 20:
            base_score = 95.0
            positive_factors.append(f"Excellent growth: {growth_rate:.1f}%")
        elif growth_rate > 10:
            base_score = 85.0
            positive_factors.append(f"Strong growth: {growth_rate:.1f}%")
        elif growth_rate > 5:
            base_score = 75.0
            positive_factors.append(f"Healthy growth: {growth_rate:.1f}%")
        elif growth_rate > 0:
            base_score = 60.0
        elif growth_rate > -5:
            base_score = 45.0
            risk_factors.append(f"Slight decline: {growth_rate:.1f}%")
        elif growth_rate > -10:
            base_score = 30.0
            risk_factors.append(f"Declining holders: {growth_rate:.1f}%")
        else:
            base_score = 15.0
            risk_factors.append(f"Significant decline: {growth_rate:.1f}%")

        # Volatility penalty
        if volatility > 20:
            volatility_penalty = 25
            risk_factors.append("High growth volatility (unstable)")
        elif volatility > 10:
            volatility_penalty = 15
        elif volatility > 5:
            volatility_penalty = 5
        else:
            volatility_penalty = 0
            if growth_rate > 0:
                positive_factors.append("Stable growth pattern")

        score = max(0, min(100, base_score - volatility_penalty))

        return score, risk_factors, positive_factors

    def calculate_whale_stability_score(
        self,
        stability_score: float,
        accumulation_pattern: str,
        distributing_whales: int,
        total_whales: int
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate score based on whale behavior stability.

        Stable holdings with accumulation = higher score.

        Args:
            stability_score: Whale stability score (0-100)
            accumulation_pattern: Pattern string from whale analysis
            distributing_whales: Number of whales distributing
            total_whales: Total number of tracked whales

        Returns:
            Tuple of (score, risk_factors, positive_factors)
        """
        risk_factors = []
        positive_factors = []

        # Base score from stability
        base_score = stability_score

        # Pattern adjustment
        pattern_adjustments = {
            "strong_accumulation": 15,
            "mild_accumulation": 8,
            "neutral": 0,
            "mild_distribution": -10,
            "strong_distribution": -25,
            "unknown": 0
        }
        pattern_adjustment = pattern_adjustments.get(accumulation_pattern, 0)

        if accumulation_pattern == "strong_accumulation":
            positive_factors.append("Whales are accumulating")
        elif accumulation_pattern == "strong_distribution":
            risk_factors.append("Whales are distributing (potential sell pressure)")
        elif accumulation_pattern == "mild_distribution":
            risk_factors.append("Some whale distribution detected")

        # Distribution ratio penalty
        if total_whales > 0:
            distribution_ratio = distributing_whales / total_whales
            if distribution_ratio > 0.6:
                risk_factors.append(f"Many whales distributing ({distributing_whales}/{total_whales})")
                distribution_penalty = 15
            elif distribution_ratio > 0.4:
                distribution_penalty = 5
            else:
                distribution_penalty = 0
                if distribution_ratio < 0.2 and accumulation_pattern in ["strong_accumulation", "mild_accumulation"]:
                    positive_factors.append("Whales showing strong holding conviction")
        else:
            distribution_penalty = 0

        score = max(0, min(100, base_score + pattern_adjustment - distribution_penalty))

        return score, risk_factors, positive_factors

    def calculate_contract_ratio_score(
        self,
        eoa_percentage: float,
        contract_percentage: float,
        exchange_percentage: float = 0
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate score based on wallet type distribution.

        Higher EOA ratio = higher score (more real users).

        Args:
            eoa_percentage: Percentage of holdings by EOAs
            contract_percentage: Percentage of holdings by contracts
            exchange_percentage: Percentage of holdings on exchanges

        Returns:
            Tuple of (score, risk_factors, positive_factors)
        """
        risk_factors = []
        positive_factors = []

        # EOA dominance is generally positive
        if eoa_percentage >= 70:
            score = 90.0
            positive_factors.append(f"Strong EOA dominance ({eoa_percentage:.1f}%)")
        elif eoa_percentage >= 50:
            score = 75.0
            positive_factors.append(f"Healthy EOA ratio ({eoa_percentage:.1f}%)")
        elif eoa_percentage >= 30:
            score = 55.0
            risk_factors.append(f"Low EOA ratio ({eoa_percentage:.1f}%)")
        else:
            score = 35.0
            risk_factors.append(f"Very low EOA ratio ({eoa_percentage:.1f}%) - dominated by contracts")

        # High contract percentage might indicate bots or protocols
        if contract_percentage > 50:
            risk_factors.append(f"High contract holdings ({contract_percentage:.1f}%) - possible bot activity")
            score = max(20, score - 20)

        # High exchange percentage is a mixed signal
        if exchange_percentage > 40:
            risk_factors.append(f"High exchange holdings ({exchange_percentage:.1f}%) - potential sell pressure")
            score = max(20, score - 10)
        elif exchange_percentage < 10 and eoa_percentage > 50:
            positive_factors.append("Low exchange concentration - holders prefer self-custody")
            score = min(100, score + 5)

        return score, risk_factors, positive_factors

    def calculate_health_score(
        self,
        token_address: str,
        lookback_blocks: int = BLOCKS_PER_WEEK,
        max_holders: int = 1000
    ) -> Optional[TokenHealthScore]:
        """
        Calculate comprehensive health score for a token.

        This is the main entry point that combines all component scores
        into a single health assessment.

        Args:
            token_address: Token contract address
            lookback_blocks: Number of blocks to look back for trend analysis
            max_holders: Maximum holders to analyze

        Returns:
            TokenHealthScore dataclass or None if insufficient data
        """
        try:
            # Get token info
            token_info = self.erc20_queries.get_token_info(token_address)
            if not token_info:
                logger.warning(f"No token info found for {token_address}")
                return None

            total_supply = float(token_info.total_supply)
            holder_count = token_info.holder_count

            # Get current block
            current_block = self.client.get_latest_block_number(self.subgraph_url)
            if not current_block:
                current_block = 0
            timestamp = int(pd.Timestamp.now().timestamp())

            # Collect all risk and positive factors
            all_risk_factors = []
            all_positive_factors = []

            # 1. Holder Count Score
            holder_score, risk_f, pos_f = self.calculate_holder_count_score(holder_count)
            all_risk_factors.extend(risk_f)
            all_positive_factors.extend(pos_f)

            # 2. Concentration Score
            distribution_metrics = self.distribution_queries.get_distribution_metrics(
                token_address, limit=max_holders
            )
            if distribution_metrics:
                concentration_score, risk_f, pos_f = self.calculate_concentration_score(
                    distribution_metrics.gini_coefficient,
                    distribution_metrics.top_10_concentration,
                    distribution_metrics.whale_count
                )
            else:
                concentration_score = 50.0  # Neutral if no data
            all_risk_factors.extend(risk_f)
            all_positive_factors.extend(pos_f)

            # 3. Growth Trend Score
            try:
                from_block = max(0, current_block - lookback_blocks)
                holder_history = self.holder_count_queries.get_holder_count_history(
                    token_address,
                    from_block=from_block,
                    to_block=current_block,
                    interval_blocks=BLOCKS_PER_DAY
                )
                if not holder_history.empty and len(holder_history) >= 2:
                    start_count = holder_history["holder_count"].iloc[0]
                    end_count = holder_history["holder_count"].iloc[-1]
                    growth_rate = ((end_count - start_count) / start_count * 100) if start_count > 0 else 0
                    volatility = holder_history["holder_count"].pct_change().std() * 100 if len(holder_history) > 2 else 0
                else:
                    growth_rate = 0
                    volatility = 0
            except Exception as e:
                logger.warning(f"Could not get holder history: {e}")
                growth_rate = 0
                volatility = 0

            growth_score, risk_f, pos_f = self.calculate_growth_trend_score(
                growth_rate, volatility, holder_count
            )
            all_risk_factors.extend(risk_f)
            all_positive_factors.extend(pos_f)

            # 4. Whale Stability Score
            try:
                whale_analysis = self.whale_queries.analyze_whale_stability(token_address)
                whale_pattern = self.whale_queries.detect_accumulation_pattern(token_address)
                stability = whale_analysis.get("stability_score", 50)
                pattern = whale_pattern.get("pattern", "unknown")
                distributing = whale_pattern.get("distributing_whales", 0)
                total_whales = whale_pattern.get("total_whales", 0)
            except Exception as e:
                logger.warning(f"Could not get whale data: {e}")
                stability = 50
                pattern = "unknown"
                distributing = 0
                total_whales = 0

            whale_score, risk_f, pos_f = self.calculate_whale_stability_score(
                stability, pattern, distributing, total_whales
            )
            all_risk_factors.extend(risk_f)
            all_positive_factors.extend(pos_f)

            # 5. Contract Ratio Score
            try:
                holder_data = self.bubble_map_queries.get_holder_data_with_types(
                    token_address, limit=max_holders
                )
                if not holder_data.empty and "wallet_type" in holder_data.columns:
                    type_totals = holder_data.groupby("wallet_type")["percentage"].sum()
                    eoa_pct = type_totals.get("eoa", 0)
                    contract_pct = type_totals.get("contract", 0)
                    exchange_pct = type_totals.get("exchange", 0)
                else:
                    eoa_pct = 50  # Default neutral
                    contract_pct = 30
                    exchange_pct = 20
            except Exception as e:
                logger.warning(f"Could not get wallet type data: {e}")
                eoa_pct = 50
                contract_pct = 30
                exchange_pct = 20

            contract_score, risk_f, pos_f = self.calculate_contract_ratio_score(
                eoa_pct, contract_pct, exchange_pct
            )
            all_risk_factors.extend(risk_f)
            all_positive_factors.extend(pos_f)

            # Calculate weighted overall score
            overall_score = (
                holder_score * SCORE_WEIGHTS["holder_count"] +
                concentration_score * SCORE_WEIGHTS["concentration"] +
                growth_score * SCORE_WEIGHTS["growth_trend"] +
                whale_score * SCORE_WEIGHTS["whale_stability"] +
                contract_score * SCORE_WEIGHTS["contract_ratio"]
            )

            # Create components dataclass
            components = HealthScoreComponents(
                holder_count_score=round(holder_score, 2),
                concentration_score=round(concentration_score, 2),
                growth_trend_score=round(growth_score, 2),
                whale_stability_score=round(whale_score, 2),
                contract_ratio_score=round(contract_score, 2)
            )

            # Determine grade and risk level
            grade = self._score_to_grade(overall_score)
            risk_level = self._score_to_risk_level(overall_score)

            return TokenHealthScore(
                overall_score=round(overall_score, 2),
                components=components,
                health_grade=grade,
                risk_level=risk_level,
                risk_factors=all_risk_factors[:10],  # Limit to top 10
                positive_factors=all_positive_factors[:10],
                holder_count=holder_count,
                total_supply=total_supply,
                block_number=current_block,
                timestamp=timestamp
            )

        except Exception as e:
            logger.error(f"Error calculating health score for {token_address}: {e}")
            return None

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 55:
            return "C-"
        elif score >= 50:
            return "D+"
        elif score >= 45:
            return "D"
        elif score >= 40:
            return "D-"
        else:
            return "F"

    def _score_to_risk_level(self, score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= 80:
            return "Low"
        elif score >= 60:
            return "Medium"
        elif score >= 40:
            return "High"
        else:
            return "Critical"

    def get_health_score_history(
        self,
        token_address: str,
        from_block: int,
        to_block: int,
        interval_blocks: int = BLOCKS_PER_DAY
    ) -> pd.DataFrame:
        """
        Get historical health scores over a block range.

        Note: This is a simplified version that recalculates scores
        at each interval. For production, consider caching scores.

        Args:
            token_address: Token contract address
            from_block: Starting block number
            to_block: Ending block number
            interval_blocks: Blocks between samples

        Returns:
            DataFrame with historical health scores
        """
        scores = []
        current_block = from_block

        while current_block <= to_block:
            # For historical data, we use the current state as approximation
            # A more accurate approach would require historical snapshots
            health = self.calculate_health_score(token_address)

            if health:
                scores.append({
                    "block_number": current_block,
                    "timestamp": health.timestamp,
                    "overall_score": health.overall_score,
                    "holder_count_score": health.components.holder_count_score,
                    "concentration_score": health.components.concentration_score,
                    "growth_trend_score": health.components.growth_trend_score,
                    "whale_stability_score": health.components.whale_stability_score,
                    "contract_ratio_score": health.components.contract_ratio_score,
                    "health_grade": health.health_grade,
                    "risk_level": health.risk_level
                })

            current_block += interval_blocks

        return pd.DataFrame(scores)


def interpret_health_score(score: float) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of health score.

    Args:
        score: Health score (0-100)

    Returns:
        Tuple of (interpretation, severity level)
    """
    if score >= 80:
        return "Excellent token health - strong fundamentals across all metrics", "excellent"
    elif score >= 70:
        return "Good token health - solid metrics with minor areas for improvement", "good"
    elif score >= 60:
        return "Moderate token health - some concerns but generally acceptable", "moderate"
    elif score >= 50:
        return "Fair token health - several risk factors present", "fair"
    elif score >= 40:
        return "Poor token health - significant risks identified", "poor"
    else:
        return "Critical token health - major red flags present", "critical"


def interpret_component_score(component_name: str, score: float) -> Tuple[str, str]:
    """
    Provide interpretation for individual component scores.

    Args:
        component_name: Name of the component
        score: Component score (0-100)

    Returns:
        Tuple of (interpretation, status)
    """
    if score >= 80:
        status = "strong"
    elif score >= 60:
        status = "moderate"
    elif score >= 40:
        status = "weak"
    else:
        status = "critical"

    interpretations = {
        "holder_count": {
            "strong": "Large, established holder base",
            "moderate": "Growing holder base",
            "weak": "Limited holder base",
            "critical": "Very few holders - high risk"
        },
        "concentration": {
            "strong": "Well decentralized token distribution",
            "moderate": "Acceptable concentration levels",
            "weak": "Concentrated among few holders",
            "critical": "Extreme concentration - whale dominance"
        },
        "growth_trend": {
            "strong": "Strong positive growth momentum",
            "moderate": "Stable or growing holder base",
            "weak": "Declining or volatile holder growth",
            "critical": "Significant holder exodus"
        },
        "whale_stability": {
            "strong": "Whales showing strong holding conviction",
            "moderate": "Stable whale holdings",
            "weak": "Some whale distribution activity",
            "critical": "Whales actively distributing"
        },
        "contract_ratio": {
            "strong": "Healthy balance of real users (EOAs)",
            "moderate": "Acceptable wallet type distribution",
            "weak": "High contract/bot presence",
            "critical": "Dominated by contracts/bots"
        }
    }

    interp = interpretations.get(component_name, {}).get(status, f"{component_name}: {status}")
    return interp, status


def get_score_color(score: float) -> str:
    """
    Get color code for score visualization.

    Args:
        score: Score value (0-100)

    Returns:
        Hex color code
    """
    if score >= 80:
        return "#28a745"  # Green
    elif score >= 60:
        return "#5cb85c"  # Light green
    elif score >= 50:
        return "#ffc107"  # Yellow
    elif score >= 40:
        return "#fd7e14"  # Orange
    else:
        return "#dc3545"  # Red


def get_grade_color(grade: str) -> str:
    """
    Get color code for grade visualization.

    Args:
        grade: Letter grade (A+ to F)

    Returns:
        Hex color code
    """
    grade_colors = {
        "A+": "#28a745",
        "A": "#28a745",
        "A-": "#5cb85c",
        "B+": "#5cb85c",
        "B": "#8bc34a",
        "B-": "#8bc34a",
        "C+": "#ffc107",
        "C": "#ffc107",
        "C-": "#fd7e14",
        "D+": "#fd7e14",
        "D": "#dc3545",
        "D-": "#dc3545",
        "F": "#c82333"
    }
    return grade_colors.get(grade, "#6c757d")

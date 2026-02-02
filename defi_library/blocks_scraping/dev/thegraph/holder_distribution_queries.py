"""
Holder Distribution Analysis Queries for ERC-20 Token Tracking

This module provides functionality to analyze the shape of holder distribution
including Gini coefficient, holder tiers, and concentration metrics.

Features:
- Calculate Gini coefficient (inequality measure)
- Classify holders into tiers: Whales (>1%), Dolphins (0.1-1%), Fish (<0.1%)
- Generate distribution histograms with log scale
- Build Lorenz curve data for visualization
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .graph_client import GraphClient, raw_to_decimal
from .queries import ERC20Queries

logger = logging.getLogger(__name__)


@dataclass
class HolderTierCounts:
    """Holder counts by tier"""
    whales: int  # >1% of supply
    dolphins: int  # 0.1-1% of supply
    fish: int  # <0.1% of supply
    total: int


@dataclass
class DistributionMetrics:
    """Comprehensive distribution metrics"""
    gini_coefficient: float
    top_10_concentration: float
    top_50_concentration: float
    whale_count: int
    dolphin_count: int
    fish_count: int
    total_holders: int
    median_balance: float
    mean_balance: float
    max_balance: float
    herfindahl_index: float  # HHI - market concentration


@dataclass
class LorenzCurveData:
    """Data for Lorenz curve visualization"""
    population_percentiles: List[float]
    wealth_percentiles: List[float]


class HolderDistributionQueries:
    """
    Queries for analyzing holder distribution metrics.

    This class provides methods to calculate distribution statistics,
    Gini coefficient, holder tiers, and concentration metrics.

    Example usage:
        queries = HolderDistributionQueries(subgraph_url="https://api.studio.thegraph.com/query/.../erc20-tracker/v0.0.1")

        # Get distribution metrics
        metrics = queries.get_distribution_metrics(token_address)
        print(f"Gini coefficient: {metrics.gini_coefficient}")

        # Get holder tiers
        tiers = queries.get_holder_tiers(token_address)
        print(f"Whales: {tiers.whales}, Dolphins: {tiers.dolphins}, Fish: {tiers.fish}")
    """

    def __init__(
        self,
        subgraph_url: str,
        client: Optional[GraphClient] = None
    ):
        """
        Initialize HolderDistributionQueries.

        Args:
            subgraph_url: URL of the deployed erc20-tracker subgraph
            client: Optional GraphClient instance (creates new one if not provided)
        """
        self.subgraph_url = subgraph_url
        self.client = client or GraphClient()
        self.erc20_queries = ERC20Queries(subgraph_url=subgraph_url, client=self.client)

    def get_all_holder_balances(
        self,
        token_address: str,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Get all holder balances for a token.

        Args:
            token_address: Token contract address
            limit: Maximum number of holders to retrieve

        Returns:
            DataFrame with columns: account, balance, percentage
        """
        # Get token info for total supply
        token_info = self.erc20_queries.get_token_info(token_address)
        if not token_info:
            return pd.DataFrame(columns=["account", "balance", "percentage"])

        total_supply = float(token_info.total_supply)

        # Get all balances
        df = self.erc20_queries.get_token_balances(
            token_address=token_address,
            limit=limit
        )

        if df.empty:
            return pd.DataFrame(columns=["account", "balance", "percentage"])

        # Calculate percentage of total supply
        if total_supply > 0:
            df["percentage"] = (df["balance"] / total_supply) * 100
        else:
            df["percentage"] = 0.0

        return df[["account", "balance", "percentage"]]

    def calculate_gini_coefficient(self, balances: np.ndarray) -> float:
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

    def calculate_lorenz_curve(
        self,
        balances: np.ndarray,
        num_points: int = 100
    ) -> LorenzCurveData:
        """
        Calculate Lorenz curve data for visualization.

        The Lorenz curve shows the cumulative proportion of wealth
        held by the cumulative proportion of the population.

        Args:
            balances: Array of balance values
            num_points: Number of points for the curve

        Returns:
            LorenzCurveData with population and wealth percentiles
        """
        if len(balances) == 0:
            return LorenzCurveData(
                population_percentiles=[0.0, 100.0],
                wealth_percentiles=[0.0, 100.0]
            )

        # Filter out zero balances
        balances = balances[balances > 0]
        if len(balances) == 0:
            return LorenzCurveData(
                population_percentiles=[0.0, 100.0],
                wealth_percentiles=[0.0, 100.0]
            )

        # Sort balances in ascending order
        sorted_balances = np.sort(balances)
        n = len(sorted_balances)
        total = np.sum(sorted_balances)

        if total == 0:
            return LorenzCurveData(
                population_percentiles=[0.0, 100.0],
                wealth_percentiles=[0.0, 100.0]
            )

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

        return LorenzCurveData(
            population_percentiles=population_percentiles,
            wealth_percentiles=wealth_percentiles
        )

    def classify_holder_tiers(
        self,
        df: pd.DataFrame,
        whale_threshold: float = 1.0,
        dolphin_threshold: float = 0.1
    ) -> HolderTierCounts:
        """
        Classify holders into tiers based on their percentage of supply.

        Tiers:
        - Whales: >1% of total supply
        - Dolphins: 0.1% - 1% of total supply
        - Fish: <0.1% of total supply

        Args:
            df: DataFrame with 'percentage' column
            whale_threshold: Minimum percentage to be a whale (default 1.0%)
            dolphin_threshold: Minimum percentage to be a dolphin (default 0.1%)

        Returns:
            HolderTierCounts with counts for each tier
        """
        if df.empty or "percentage" not in df.columns:
            return HolderTierCounts(whales=0, dolphins=0, fish=0, total=0)

        whales = len(df[df["percentage"] >= whale_threshold])
        dolphins = len(df[(df["percentage"] >= dolphin_threshold) & (df["percentage"] < whale_threshold)])
        fish = len(df[df["percentage"] < dolphin_threshold])

        return HolderTierCounts(
            whales=whales,
            dolphins=dolphins,
            fish=fish,
            total=len(df)
        )

    def calculate_concentration_metrics(
        self,
        df: pd.DataFrame,
        top_n_list: List[int] = [10, 50, 100]
    ) -> Dict[str, float]:
        """
        Calculate concentration metrics for top N holders.

        Args:
            df: DataFrame with 'percentage' column, sorted by balance descending
            top_n_list: List of N values for top-N concentration

        Returns:
            Dictionary with concentration percentages
        """
        if df.empty or "percentage" not in df.columns:
            return {f"top_{n}_concentration": 0.0 for n in top_n_list}

        result = {}
        for n in top_n_list:
            top_n_pct = df["percentage"].head(n).sum()
            result[f"top_{n}_concentration"] = round(top_n_pct, 2)

        return result

    def calculate_herfindahl_index(self, percentages: np.ndarray) -> float:
        """
        Calculate Herfindahl-Hirschman Index (HHI) for market concentration.

        HHI = sum of squared market shares
        - 0-1500: Competitive market
        - 1500-2500: Moderately concentrated
        - 2500+: Highly concentrated

        Args:
            percentages: Array of percentage holdings

        Returns:
            HHI value (0-10000 scale)
        """
        if len(percentages) == 0:
            return 0.0

        # HHI uses market shares as percentages (0-100)
        # Square each share and sum
        hhi = np.sum(percentages ** 2)

        return round(float(hhi), 2)

    def get_distribution_metrics(
        self,
        token_address: str,
        limit: int = 1000
    ) -> Optional[DistributionMetrics]:
        """
        Get comprehensive distribution metrics for a token.

        Args:
            token_address: Token contract address
            limit: Maximum number of holders to analyze

        Returns:
            DistributionMetrics dataclass or None if no data
        """
        df = self.get_all_holder_balances(token_address, limit)

        if df.empty:
            return None

        balances = df["balance"].values
        percentages = df["percentage"].values

        # Calculate all metrics
        gini = self.calculate_gini_coefficient(balances)
        tiers = self.classify_holder_tiers(df)
        concentration = self.calculate_concentration_metrics(df, [10, 50])
        hhi = self.calculate_herfindahl_index(percentages)

        return DistributionMetrics(
            gini_coefficient=gini,
            top_10_concentration=concentration.get("top_10_concentration", 0.0),
            top_50_concentration=concentration.get("top_50_concentration", 0.0),
            whale_count=tiers.whales,
            dolphin_count=tiers.dolphins,
            fish_count=tiers.fish,
            total_holders=tiers.total,
            median_balance=float(np.median(balances)) if len(balances) > 0 else 0.0,
            mean_balance=float(np.mean(balances)) if len(balances) > 0 else 0.0,
            max_balance=float(np.max(balances)) if len(balances) > 0 else 0.0,
            herfindahl_index=hhi
        )

    def get_holder_tiers(
        self,
        token_address: str,
        limit: int = 1000
    ) -> HolderTierCounts:
        """
        Get holder tier counts for a token.

        Args:
            token_address: Token contract address
            limit: Maximum number of holders to analyze

        Returns:
            HolderTierCounts dataclass
        """
        df = self.get_all_holder_balances(token_address, limit)
        return self.classify_holder_tiers(df)

    def get_distribution_histogram_data(
        self,
        token_address: str,
        num_bins: int = 50,
        log_scale: bool = True,
        limit: int = 1000
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get histogram data for balance distribution.

        Args:
            token_address: Token contract address
            num_bins: Number of histogram bins
            log_scale: Whether to use log scale for bins
            limit: Maximum number of holders

        Returns:
            Tuple of (bin_edges, counts)
        """
        df = self.get_all_holder_balances(token_address, limit)

        if df.empty:
            return np.array([]), np.array([])

        balances = df["balance"].values
        balances = balances[balances > 0]  # Filter out zero balances

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

    def get_lorenz_curve_data(
        self,
        token_address: str,
        num_points: int = 100,
        limit: int = 1000
    ) -> LorenzCurveData:
        """
        Get Lorenz curve data for visualization.

        Args:
            token_address: Token contract address
            num_points: Number of points for the curve
            limit: Maximum number of holders

        Returns:
            LorenzCurveData for plotting
        """
        df = self.get_all_holder_balances(token_address, limit)

        if df.empty:
            return LorenzCurveData(
                population_percentiles=[0.0, 100.0],
                wealth_percentiles=[0.0, 100.0]
            )

        balances = df["balance"].values
        return self.calculate_lorenz_curve(balances, num_points)


def calculate_gini_from_balances(balances: pd.Series) -> float:
    """
    Utility function to calculate Gini coefficient from a pandas Series.

    Args:
        balances: Pandas Series of balance values

    Returns:
        Gini coefficient between 0 and 1
    """
    queries = HolderDistributionQueries.__new__(HolderDistributionQueries)
    return queries.calculate_gini_coefficient(balances.values)


def classify_holder_tier(percentage: float) -> str:
    """
    Classify a single holder into a tier based on percentage.

    Args:
        percentage: Percentage of total supply held

    Returns:
        Tier name: "whale", "dolphin", or "fish"
    """
    if percentage >= 1.0:
        return "whale"
    elif percentage >= 0.1:
        return "dolphin"
    else:
        return "fish"


def interpret_gini_coefficient(gini: float) -> str:
    """
    Provide human-readable interpretation of Gini coefficient.

    Args:
        gini: Gini coefficient value (0-1)

    Returns:
        Interpretation string
    """
    if gini < 0.3:
        return "Low inequality - relatively even distribution"
    elif gini < 0.5:
        return "Moderate inequality - some concentration"
    elif gini < 0.7:
        return "High inequality - significant concentration"
    elif gini < 0.9:
        return "Very high inequality - heavy concentration"
    else:
        return "Extreme inequality - near total concentration"


def interpret_hhi(hhi: float) -> str:
    """
    Provide human-readable interpretation of Herfindahl-Hirschman Index.

    Args:
        hhi: HHI value (0-10000)

    Returns:
        Interpretation string
    """
    if hhi < 1500:
        return "Competitive - well distributed among holders"
    elif hhi < 2500:
        return "Moderately concentrated"
    else:
        return "Highly concentrated - dominated by few holders"

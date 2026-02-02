"""
Suspicious Activity Detection Queries for ERC-20 Token Tracking

This module provides functionality to detect potential scam/manipulation patterns
in token holder activity.

Features:
- Circular transfer detection (wash trading)
- Sudden concentration changes
- Coordinated wallet detection (same funding source)
- Dump pattern detection
- Cluster analysis for split entities
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

import numpy as np
import pandas as pd

from .graph_client import GraphClient
from .queries import ERC20Queries
from .holder_distribution_queries import HolderDistributionQueries
from .whale_tracking_queries import WhaleTrackingQueries

logger = logging.getLogger(__name__)

# Constants
BLOCKS_PER_DAY = 7200  # ~12 second blocks
BLOCKS_PER_HOUR = 300

# Severity levels
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

# Activity types
ACTIVITY_WASH_TRADING = "wash_trading"
ACTIVITY_CONCENTRATION_SPIKE = "concentration_spike"
ACTIVITY_COORDINATED_WALLETS = "coordinated_wallets"
ACTIVITY_DUMP_PATTERN = "dump_pattern"
ACTIVITY_SYBIL_CLUSTER = "sybil_cluster"
ACTIVITY_RAPID_ACCUMULATION = "rapid_accumulation"


@dataclass
class SuspiciousActivity:
    """Represents a single suspicious activity detection."""
    activity_type: str  # Type of suspicious activity
    severity: str  # critical, high, medium, low
    description: str  # Human-readable description
    involved_addresses: List[str]  # Wallets involved
    evidence: Dict  # Supporting data/metrics
    block_number: int
    timestamp: int
    risk_score: float  # 0-100 contribution to overall risk


@dataclass
class SuspiciousActivityReport:
    """Complete suspicious activity report for a token."""
    token_address: str
    overall_risk_score: float  # 0-100
    risk_level: str  # "Low", "Medium", "High", "Critical"
    total_flags: int
    critical_flags: int
    high_flags: int
    medium_flags: int
    low_flags: int
    activities: List[SuspiciousActivity]
    summary: str
    block_number: int
    timestamp: int


@dataclass
class WalletCluster:
    """Represents a cluster of potentially related wallets."""
    cluster_id: int
    addresses: List[str]
    total_balance: float
    total_percentage: float
    connection_type: str  # "funding_source", "timing", "pattern"
    confidence: float  # 0-1 confidence score


class SuspiciousActivityQueries:
    """
    Queries for detecting suspicious activity patterns in token holder data.

    This class analyzes holder behavior to identify potential manipulation,
    wash trading, and coordinated activity.

    Example usage:
        queries = SuspiciousActivityQueries(subgraph_url="https://api.studio.thegraph.com/query/.../erc20-tracker/v0.0.1")

        # Get suspicious activity report
        report = queries.analyze_token(token_address)
        print(f"Risk Score: {report.overall_risk_score:.1f}/100")
        print(f"Risk Level: {report.risk_level}")
    """

    def __init__(
        self,
        subgraph_url: str,
        client: Optional[GraphClient] = None
    ):
        """
        Initialize SuspiciousActivityQueries.

        Args:
            subgraph_url: URL of the deployed erc20-tracker subgraph
            client: Optional GraphClient instance (creates new one if not provided)
        """
        self.subgraph_url = subgraph_url
        self.client = client or GraphClient()
        self.erc20_queries = ERC20Queries(subgraph_url=subgraph_url, client=self.client)
        self.distribution_queries = HolderDistributionQueries(subgraph_url=subgraph_url, client=self.client)
        self.whale_queries = WhaleTrackingQueries(subgraph_url=subgraph_url, client=self.client)

    def detect_wash_trading(
        self,
        token_address: str,
        lookback_blocks: int = BLOCKS_PER_DAY,
        min_cycle_count: int = 3
    ) -> List[SuspiciousActivity]:
        """
        Detect potential wash trading (circular transfers).

        Looks for patterns where tokens circulate between a small set of wallets,
        artificially inflating volume.

        Args:
            token_address: Token contract address
            lookback_blocks: Number of blocks to analyze
            min_cycle_count: Minimum cycles to flag as suspicious

        Returns:
            List of SuspiciousActivity for detected wash trading
        """
        activities = []

        try:
            # Get recent transfers
            transfers = self._get_recent_transfers(token_address, lookback_blocks)
            if transfers.empty:
                return activities

            # Build transfer graph
            transfer_graph = defaultdict(lambda: defaultdict(int))
            for _, row in transfers.iterrows():
                from_addr = row.get("from", "")
                to_addr = row.get("to", "")
                if from_addr and to_addr:
                    transfer_graph[from_addr][to_addr] += 1

            # Detect cycles
            cycles = self._find_transfer_cycles(transfer_graph, min_cycle_count)

            for cycle in cycles:
                cycle_count = min(
                    transfer_graph[cycle[i]][cycle[(i + 1) % len(cycle)]]
                    for i in range(len(cycle))
                )

                severity = SEVERITY_CRITICAL if cycle_count > 10 else (
                    SEVERITY_HIGH if cycle_count > 5 else SEVERITY_MEDIUM
                )

                risk_score = min(30, cycle_count * 3)

                activities.append(SuspiciousActivity(
                    activity_type=ACTIVITY_WASH_TRADING,
                    severity=severity,
                    description=f"Circular transfer pattern detected: {len(cycle)} wallets, {cycle_count}+ cycles",
                    involved_addresses=cycle,
                    evidence={
                        "cycle_length": len(cycle),
                        "cycle_count": cycle_count,
                        "transfer_graph_subset": {addr: dict(transfer_graph[addr]) for addr in cycle}
                    },
                    block_number=int(transfers["block_number"].max()) if "block_number" in transfers.columns else 0,
                    timestamp=int(transfers["timestamp"].max()) if "timestamp" in transfers.columns else 0,
                    risk_score=risk_score
                ))

        except Exception as e:
            logger.error(f"Error detecting wash trading: {e}")

        return activities

    def detect_concentration_spikes(
        self,
        token_address: str,
        lookback_blocks: int = BLOCKS_PER_DAY * 7,
        spike_threshold_pct: float = 10.0
    ) -> List[SuspiciousActivity]:
        """
        Detect sudden increases in token concentration.

        Args:
            token_address: Token contract address
            lookback_blocks: Number of blocks to analyze
            spike_threshold_pct: Percentage change threshold to flag

        Returns:
            List of SuspiciousActivity for concentration spikes
        """
        activities = []

        try:
            # Get concentration history
            current_block = self.client.get_latest_block_number(self.subgraph_url) or 0
            from_block = max(0, current_block - lookback_blocks)

            # Get top holder data at different points
            current_holders = self.distribution_queries.get_top_holders(
                token_address, limit=50
            )
            if current_holders.empty:
                return activities

            # Calculate current top 10 concentration
            current_top10_pct = current_holders.head(10)["percentage"].sum() if "percentage" in current_holders.columns else 0

            # Check for rapid accumulation by individual wallets
            for _, holder in current_holders.head(20).iterrows():
                percentage = holder.get("percentage", 0)

                # Flag if single wallet holds >15% (high concentration risk)
                if percentage > 15:
                    severity = SEVERITY_CRITICAL if percentage > 30 else (
                        SEVERITY_HIGH if percentage > 20 else SEVERITY_MEDIUM
                    )

                    activities.append(SuspiciousActivity(
                        activity_type=ACTIVITY_CONCENTRATION_SPIKE,
                        severity=severity,
                        description=f"Single wallet holds {percentage:.1f}% of supply",
                        involved_addresses=[holder.get("address", "unknown")],
                        evidence={
                            "wallet_percentage": percentage,
                            "top_10_concentration": current_top10_pct,
                            "wallet_balance": holder.get("balance", 0)
                        },
                        block_number=current_block,
                        timestamp=int(pd.Timestamp.now().timestamp()),
                        risk_score=min(25, percentage)
                    ))

            # Flag if top 10 hold >80%
            if current_top10_pct > 80:
                activities.append(SuspiciousActivity(
                    activity_type=ACTIVITY_CONCENTRATION_SPIKE,
                    severity=SEVERITY_HIGH,
                    description=f"Top 10 holders control {current_top10_pct:.1f}% of supply",
                    involved_addresses=current_holders.head(10)["address"].tolist() if "address" in current_holders.columns else [],
                    evidence={
                        "top_10_concentration": current_top10_pct,
                        "holder_count": len(current_holders)
                    },
                    block_number=current_block,
                    timestamp=int(pd.Timestamp.now().timestamp()),
                    risk_score=min(20, (current_top10_pct - 60) / 2)
                ))

        except Exception as e:
            logger.error(f"Error detecting concentration spikes: {e}")

        return activities

    def detect_coordinated_wallets(
        self,
        token_address: str,
        time_window_blocks: int = BLOCKS_PER_HOUR,
        min_cluster_size: int = 3
    ) -> List[SuspiciousActivity]:
        """
        Detect wallets that may be controlled by the same entity.

        Looks for:
        - Wallets funded from the same source
        - Wallets with synchronized transaction timing
        - Wallets with identical transaction patterns

        Args:
            token_address: Token contract address
            time_window_blocks: Block window for timing analysis
            min_cluster_size: Minimum wallets to form a suspicious cluster

        Returns:
            List of SuspiciousActivity for coordinated wallets
        """
        activities = []

        try:
            # Get holder data
            holders = self.distribution_queries.get_top_holders(token_address, limit=200)
            if holders.empty or len(holders) < min_cluster_size:
                return activities

            # Get transfer data for timing analysis
            transfers = self._get_recent_transfers(token_address, BLOCKS_PER_DAY * 3)

            # Cluster by similar balance patterns (potential Sybil)
            clusters = self._cluster_by_balance_similarity(holders, threshold=0.1)

            for cluster in clusters:
                if len(cluster) >= min_cluster_size:
                    cluster_addresses = [holders.iloc[i]["address"] for i in cluster if "address" in holders.columns]
                    total_pct = sum(holders.iloc[i]["percentage"] for i in cluster if "percentage" in holders.columns)

                    # Higher severity if cluster controls significant portion
                    severity = SEVERITY_CRITICAL if total_pct > 20 else (
                        SEVERITY_HIGH if total_pct > 10 else SEVERITY_MEDIUM
                    )

                    activities.append(SuspiciousActivity(
                        activity_type=ACTIVITY_COORDINATED_WALLETS,
                        severity=severity,
                        description=f"Potential coordinated wallets: {len(cluster)} wallets with similar balances ({total_pct:.1f}% total)",
                        involved_addresses=cluster_addresses,
                        evidence={
                            "cluster_size": len(cluster),
                            "total_percentage": total_pct,
                            "detection_method": "balance_similarity"
                        },
                        block_number=self.client.get_latest_block_number(self.subgraph_url) or 0,
                        timestamp=int(pd.Timestamp.now().timestamp()),
                        risk_score=min(25, total_pct)
                    ))

            # Cluster by synchronized timing
            if not transfers.empty:
                timing_clusters = self._cluster_by_timing(transfers, time_window_blocks)

                for cluster_addrs in timing_clusters:
                    if len(cluster_addrs) >= min_cluster_size:
                        # Calculate total holdings of this cluster
                        cluster_holdings = holders[holders["address"].isin(cluster_addrs)] if "address" in holders.columns else pd.DataFrame()
                        total_pct = cluster_holdings["percentage"].sum() if not cluster_holdings.empty and "percentage" in cluster_holdings.columns else 0

                        activities.append(SuspiciousActivity(
                            activity_type=ACTIVITY_COORDINATED_WALLETS,
                            severity=SEVERITY_MEDIUM,
                            description=f"Synchronized transaction timing: {len(cluster_addrs)} wallets",
                            involved_addresses=list(cluster_addrs),
                            evidence={
                                "cluster_size": len(cluster_addrs),
                                "total_percentage": total_pct,
                                "detection_method": "timing_synchronization"
                            },
                            block_number=self.client.get_latest_block_number(self.subgraph_url) or 0,
                            timestamp=int(pd.Timestamp.now().timestamp()),
                            risk_score=min(15, len(cluster_addrs) * 2)
                        ))

        except Exception as e:
            logger.error(f"Error detecting coordinated wallets: {e}")

        return activities

    def detect_dump_patterns(
        self,
        token_address: str,
        lookback_blocks: int = BLOCKS_PER_DAY * 7,
        dump_threshold_pct: float = 20.0
    ) -> List[SuspiciousActivity]:
        """
        Detect coordinated dump patterns among large holders.

        Args:
            token_address: Token contract address
            lookback_blocks: Number of blocks to analyze
            dump_threshold_pct: Percentage decrease to consider a dump

        Returns:
            List of SuspiciousActivity for dump patterns
        """
        activities = []

        try:
            # Analyze whale stability
            stability_data = self.whale_queries.analyze_whale_stability(token_address)
            pattern_data = self.whale_queries.detect_accumulation_pattern(token_address)

            if not pattern_data:
                return activities

            distributing_whales = pattern_data.get("distributing_whales", 0)
            total_whales = pattern_data.get("total_whales", 0)
            pattern = pattern_data.get("pattern", "unknown")

            # Flag if many whales are distributing
            if total_whales > 0 and distributing_whales / total_whales > 0.5:
                severity = SEVERITY_HIGH if distributing_whales / total_whales > 0.7 else SEVERITY_MEDIUM

                activities.append(SuspiciousActivity(
                    activity_type=ACTIVITY_DUMP_PATTERN,
                    severity=severity,
                    description=f"Coordinated distribution: {distributing_whales}/{total_whales} whales selling",
                    involved_addresses=[],  # Would need to get specific addresses
                    evidence={
                        "distributing_whales": distributing_whales,
                        "total_whales": total_whales,
                        "distribution_ratio": distributing_whales / total_whales,
                        "pattern": pattern,
                        "stability_score": stability_data.get("stability_score", 0)
                    },
                    block_number=self.client.get_latest_block_number(self.subgraph_url) or 0,
                    timestamp=int(pd.Timestamp.now().timestamp()),
                    risk_score=min(20, (distributing_whales / total_whales) * 25)
                ))

            # Flag strong distribution pattern
            if pattern == "strong_distribution":
                activities.append(SuspiciousActivity(
                    activity_type=ACTIVITY_DUMP_PATTERN,
                    severity=SEVERITY_HIGH,
                    description="Strong distribution pattern detected - significant sell pressure",
                    involved_addresses=[],
                    evidence={
                        "pattern": pattern,
                        "net_flow": pattern_data.get("net_flow", 0)
                    },
                    block_number=self.client.get_latest_block_number(self.subgraph_url) or 0,
                    timestamp=int(pd.Timestamp.now().timestamp()),
                    risk_score=15
                ))

        except Exception as e:
            logger.error(f"Error detecting dump patterns: {e}")

        return activities

    def detect_sybil_clusters(
        self,
        token_address: str,
        balance_similarity_threshold: float = 0.05,
        min_cluster_size: int = 5
    ) -> List[SuspiciousActivity]:
        """
        Detect potential Sybil attacks (single entity split across wallets).

        Uses clustering analysis to identify wallets that may be controlled
        by the same entity based on balance patterns and behavior.

        Args:
            token_address: Token contract address
            balance_similarity_threshold: Maximum difference ratio to consider similar
            min_cluster_size: Minimum wallets to form a Sybil cluster

        Returns:
            List of SuspiciousActivity for Sybil clusters
        """
        activities = []

        try:
            holders = self.distribution_queries.get_top_holders(token_address, limit=500)
            if holders.empty or len(holders) < min_cluster_size:
                return activities

            # Look for wallets with suspiciously similar balances
            if "balance" not in holders.columns:
                return activities

            balances = holders["balance"].values
            addresses = holders["address"].values if "address" in holders.columns else []

            # Find groups with nearly identical balances
            identical_groups = self._find_identical_balance_groups(
                balances, addresses, threshold=balance_similarity_threshold
            )

            for group_balance, group_addresses in identical_groups.items():
                if len(group_addresses) >= min_cluster_size:
                    group_holdings = holders[holders["address"].isin(group_addresses)]
                    total_pct = group_holdings["percentage"].sum() if "percentage" in group_holdings.columns else 0

                    severity = SEVERITY_CRITICAL if len(group_addresses) > 20 or total_pct > 15 else (
                        SEVERITY_HIGH if len(group_addresses) > 10 or total_pct > 10 else SEVERITY_MEDIUM
                    )

                    activities.append(SuspiciousActivity(
                        activity_type=ACTIVITY_SYBIL_CLUSTER,
                        severity=severity,
                        description=f"Potential Sybil attack: {len(group_addresses)} wallets with identical balances ({total_pct:.2f}% total)",
                        involved_addresses=group_addresses,
                        evidence={
                            "cluster_size": len(group_addresses),
                            "identical_balance": group_balance,
                            "total_percentage": total_pct,
                            "avg_balance_per_wallet": group_balance
                        },
                        block_number=self.client.get_latest_block_number(self.subgraph_url) or 0,
                        timestamp=int(pd.Timestamp.now().timestamp()),
                        risk_score=min(30, len(group_addresses) * 1.5 + total_pct)
                    ))

        except Exception as e:
            logger.error(f"Error detecting Sybil clusters: {e}")

        return activities

    def analyze_token(
        self,
        token_address: str,
        include_wash_trading: bool = True,
        include_concentration: bool = True,
        include_coordinated: bool = True,
        include_dump_patterns: bool = True,
        include_sybil: bool = True
    ) -> Optional[SuspiciousActivityReport]:
        """
        Perform comprehensive suspicious activity analysis for a token.

        This is the main entry point that combines all detection methods.

        Args:
            token_address: Token contract address
            include_wash_trading: Whether to check for wash trading
            include_concentration: Whether to check concentration spikes
            include_coordinated: Whether to check for coordinated wallets
            include_dump_patterns: Whether to check for dump patterns
            include_sybil: Whether to check for Sybil attacks

        Returns:
            SuspiciousActivityReport or None if analysis fails
        """
        try:
            all_activities = []
            current_block = self.client.get_latest_block_number(self.subgraph_url) or 0
            timestamp = int(pd.Timestamp.now().timestamp())

            # Run selected detections
            if include_wash_trading:
                all_activities.extend(self.detect_wash_trading(token_address))

            if include_concentration:
                all_activities.extend(self.detect_concentration_spikes(token_address))

            if include_coordinated:
                all_activities.extend(self.detect_coordinated_wallets(token_address))

            if include_dump_patterns:
                all_activities.extend(self.detect_dump_patterns(token_address))

            if include_sybil:
                all_activities.extend(self.detect_sybil_clusters(token_address))

            # Calculate overall risk score
            total_risk_score = sum(a.risk_score for a in all_activities)
            overall_risk_score = min(100, total_risk_score)

            # Count flags by severity
            critical_flags = sum(1 for a in all_activities if a.severity == SEVERITY_CRITICAL)
            high_flags = sum(1 for a in all_activities if a.severity == SEVERITY_HIGH)
            medium_flags = sum(1 for a in all_activities if a.severity == SEVERITY_MEDIUM)
            low_flags = sum(1 for a in all_activities if a.severity == SEVERITY_LOW)

            # Determine risk level
            if critical_flags > 0 or overall_risk_score >= 70:
                risk_level = "Critical"
            elif high_flags > 1 or overall_risk_score >= 50:
                risk_level = "High"
            elif high_flags > 0 or medium_flags > 2 or overall_risk_score >= 30:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            # Generate summary
            summary = self._generate_summary(all_activities, overall_risk_score, risk_level)

            return SuspiciousActivityReport(
                token_address=token_address,
                overall_risk_score=round(overall_risk_score, 2),
                risk_level=risk_level,
                total_flags=len(all_activities),
                critical_flags=critical_flags,
                high_flags=high_flags,
                medium_flags=medium_flags,
                low_flags=low_flags,
                activities=all_activities,
                summary=summary,
                block_number=current_block,
                timestamp=timestamp
            )

        except Exception as e:
            logger.error(f"Error analyzing token {token_address}: {e}")
            return None

    # Helper methods

    def _get_recent_transfers(
        self,
        token_address: str,
        lookback_blocks: int
    ) -> pd.DataFrame:
        """Get recent transfer events for analysis."""
        try:
            query = """
            query GetTransfers($token: String!, $minBlock: Int!) {
                transfers(
                    where: {token: $token, blockNumber_gte: $minBlock}
                    first: 1000
                    orderBy: blockNumber
                    orderDirection: desc
                ) {
                    from
                    to
                    value
                    blockNumber
                    timestamp
                }
            }
            """
            current_block = self.client.get_latest_block_number(self.subgraph_url) or 0
            min_block = max(0, current_block - lookback_blocks)

            result = self.client.execute_query(
                self.subgraph_url,
                query,
                {"token": token_address.lower(), "minBlock": min_block}
            )

            if result and "transfers" in result:
                return pd.DataFrame(result["transfers"])

        except Exception as e:
            logger.warning(f"Could not get transfers: {e}")

        return pd.DataFrame()

    def _find_transfer_cycles(
        self,
        graph: Dict,
        min_cycles: int
    ) -> List[List[str]]:
        """Find circular transfer patterns in the transfer graph."""
        cycles = []
        visited = set()

        def dfs(node: str, path: List[str], start: str):
            if len(path) > 5:  # Limit cycle length
                return

            for neighbor, count in graph[node].items():
                if count < min_cycles:
                    continue

                if neighbor == start and len(path) >= 2:
                    cycles.append(path[:])
                elif neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path, start)
                    path.pop()
                    visited.remove(neighbor)

        for node in graph:
            visited.add(node)
            dfs(node, [node], node)
            visited.clear()

        return cycles

    def _cluster_by_balance_similarity(
        self,
        holders: pd.DataFrame,
        threshold: float
    ) -> List[List[int]]:
        """Cluster holders by similar balance amounts."""
        if "balance" not in holders.columns or holders.empty:
            return []

        balances = holders["balance"].values
        n = len(balances)
        clusters = []
        visited = set()

        for i in range(n):
            if i in visited:
                continue

            cluster = [i]
            visited.add(i)

            for j in range(i + 1, n):
                if j in visited:
                    continue

                # Check if balances are similar
                if balances[i] > 0:
                    diff_ratio = abs(balances[j] - balances[i]) / balances[i]
                    if diff_ratio < threshold:
                        cluster.append(j)
                        visited.add(j)

            if len(cluster) >= 3:  # Minimum cluster size
                clusters.append(cluster)

        return clusters

    def _cluster_by_timing(
        self,
        transfers: pd.DataFrame,
        window_blocks: int
    ) -> List[Set[str]]:
        """Cluster addresses by synchronized transaction timing."""
        if transfers.empty or "block_number" not in transfers.columns:
            return []

        clusters = []
        address_blocks = defaultdict(list)

        # Group blocks by address
        for _, row in transfers.iterrows():
            from_addr = row.get("from", "")
            to_addr = row.get("to", "")
            block = row.get("block_number", 0)

            if from_addr:
                address_blocks[from_addr].append(block)
            if to_addr:
                address_blocks[to_addr].append(block)

        # Find addresses with overlapping transaction windows
        addresses = list(address_blocks.keys())
        n = len(addresses)

        for i in range(n):
            cluster = {addresses[i]}
            blocks_i = set(address_blocks[addresses[i]])

            for j in range(i + 1, n):
                blocks_j = set(address_blocks[addresses[j]])

                # Check for timing overlap within window
                for bi in blocks_i:
                    for bj in blocks_j:
                        if abs(bi - bj) <= window_blocks:
                            cluster.add(addresses[j])
                            break

            if len(cluster) >= 3:
                # Avoid duplicate clusters
                if not any(cluster.issubset(c) for c in clusters):
                    clusters.append(cluster)

        return clusters

    def _find_identical_balance_groups(
        self,
        balances: np.ndarray,
        addresses: List[str],
        threshold: float
    ) -> Dict[float, List[str]]:
        """Find groups of addresses with nearly identical balances."""
        groups = defaultdict(list)

        for balance, address in zip(balances, addresses):
            if balance <= 0:
                continue

            # Round to reduce floating point noise
            rounded = round(balance, 8)

            # Check existing groups
            matched = False
            for group_balance in list(groups.keys()):
                if group_balance > 0:
                    diff_ratio = abs(rounded - group_balance) / group_balance
                    if diff_ratio < threshold:
                        groups[group_balance].append(address)
                        matched = True
                        break

            if not matched:
                groups[rounded].append(address)

        # Filter to groups with multiple members
        return {k: v for k, v in groups.items() if len(v) >= 2}

    def _generate_summary(
        self,
        activities: List[SuspiciousActivity],
        risk_score: float,
        risk_level: str
    ) -> str:
        """Generate a human-readable summary of findings."""
        if not activities:
            return "No suspicious activity detected. Token appears to have healthy holder patterns."

        summary_parts = [f"Risk Level: {risk_level} (Score: {risk_score:.1f}/100)"]

        # Count by type
        type_counts = defaultdict(int)
        for a in activities:
            type_counts[a.activity_type] += 1

        summary_parts.append(f"Total flags: {len(activities)}")

        if type_counts.get(ACTIVITY_WASH_TRADING):
            summary_parts.append(f"- Wash trading patterns: {type_counts[ACTIVITY_WASH_TRADING]}")

        if type_counts.get(ACTIVITY_CONCENTRATION_SPIKE):
            summary_parts.append(f"- Concentration concerns: {type_counts[ACTIVITY_CONCENTRATION_SPIKE]}")

        if type_counts.get(ACTIVITY_COORDINATED_WALLETS):
            summary_parts.append(f"- Coordinated wallet groups: {type_counts[ACTIVITY_COORDINATED_WALLETS]}")

        if type_counts.get(ACTIVITY_DUMP_PATTERN):
            summary_parts.append(f"- Dump pattern signals: {type_counts[ACTIVITY_DUMP_PATTERN]}")

        if type_counts.get(ACTIVITY_SYBIL_CLUSTER):
            summary_parts.append(f"- Potential Sybil clusters: {type_counts[ACTIVITY_SYBIL_CLUSTER]}")

        return "\n".join(summary_parts)


# Module-level helper functions

def interpret_risk_level(risk_level: str) -> Tuple[str, str]:
    """
    Provide human-readable interpretation of risk level.

    Args:
        risk_level: Risk level string

    Returns:
        Tuple of (interpretation, severity)
    """
    interpretations = {
        "Critical": (
            "Critical risk - Multiple severe red flags detected. Exercise extreme caution.",
            "critical"
        ),
        "High": (
            "High risk - Significant manipulation indicators present. Thorough due diligence recommended.",
            "high"
        ),
        "Medium": (
            "Moderate risk - Some suspicious patterns detected. Additional investigation advised.",
            "medium"
        ),
        "Low": (
            "Low risk - No major red flags detected. Standard due diligence recommended.",
            "low"
        )
    }

    return interpretations.get(risk_level, ("Unknown risk level", "unknown"))


def get_risk_color(risk_level: str) -> str:
    """
    Get color code for risk level visualization.

    Args:
        risk_level: Risk level string

    Returns:
        Hex color code
    """
    colors = {
        "Critical": "#dc3545",  # Red
        "High": "#fd7e14",  # Orange
        "Medium": "#ffc107",  # Yellow
        "Low": "#28a745",  # Green
    }
    return colors.get(risk_level, "#6c757d")


def get_severity_color(severity: str) -> str:
    """
    Get color code for severity level visualization.

    Args:
        severity: Severity string

    Returns:
        Hex color code
    """
    colors = {
        "critical": "#dc3545",
        "high": "#fd7e14",
        "medium": "#ffc107",
        "low": "#17a2b8",
    }
    return colors.get(severity, "#6c757d")


def get_activity_icon(activity_type: str) -> str:
    """
    Get icon/emoji for activity type.

    Args:
        activity_type: Activity type string

    Returns:
        Icon string
    """
    icons = {
        ACTIVITY_WASH_TRADING: "🔄",
        ACTIVITY_CONCENTRATION_SPIKE: "📊",
        ACTIVITY_COORDINATED_WALLETS: "🔗",
        ACTIVITY_DUMP_PATTERN: "📉",
        ACTIVITY_SYBIL_CLUSTER: "👥",
        ACTIVITY_RAPID_ACCUMULATION: "📈",
    }
    return icons.get(activity_type, "⚠️")

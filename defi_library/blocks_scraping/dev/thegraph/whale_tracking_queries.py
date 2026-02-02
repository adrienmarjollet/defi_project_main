"""
Whale Tracking Queries for ERC-20 Token Tracking

This module provides functionality to track and analyze whale (top holder) behavior:
- Identify and track top N holders' balances over time
- Detect large movements (>5% of holdings)
- Alert system for significant whale activity
- Accumulation/distribution pattern analysis

Features:
- Track top 20-50 holders' balances across blocks
- Stacked area chart data for whale composition changes
- Individual whale balance sparklines
- Whale activity feed showing recent large movements
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .graph_client import GraphClient, raw_to_decimal
from .queries import ERC20Queries

logger = logging.getLogger(__name__)

# Block interval constants
BLOCKS_PER_HOUR = 300  # ~12 seconds per block
BLOCKS_PER_DAY = 7200
BLOCKS_PER_WEEK = 50400


@dataclass
class WhaleInfo:
    """Information about a whale (top holder)."""
    address: str
    balance: float
    percentage: float
    rank: int


@dataclass
class WhaleMovement:
    """Record of a whale's balance change."""
    address: str
    from_balance: float
    to_balance: float
    change_amount: float
    change_percentage: float
    block_number: int
    timestamp: int
    movement_type: str  # "accumulation", "distribution", "stable"


@dataclass
class WhaleSnapshot:
    """Snapshot of whale balances at a specific block."""
    block_number: int
    timestamp: int
    whale_balances: Dict[str, float]  # address -> balance
    total_whale_holdings: float
    whale_concentration: float  # % of supply held by tracked whales


@dataclass
class WhaleActivityEvent:
    """A significant whale activity event."""
    address: str
    event_type: str  # "large_buy", "large_sell", "new_whale", "exit"
    amount: float
    percentage_change: float
    block_number: int
    timestamp: int
    tx_hash: Optional[str] = None


class WhaleTrackingQueries:
    """
    Queries for tracking whale (top holder) behavior over time.

    This class provides methods to identify top holders, track their
    balance changes, and detect significant movements.

    Example usage:
        queries = WhaleTrackingQueries(subgraph_url="https://api.studio.thegraph.com/query/.../erc20-tracker/v0.0.1")

        # Get current top whales
        whales = queries.get_top_whales(token_address, limit=20)

        # Track whale balances over time
        history = queries.get_whale_balance_history(
            token_address,
            whale_addresses=[w.address for w in whales],
            from_block=18000000,
            to_block=18100000
        )

        # Detect large movements
        movements = queries.detect_whale_movements(history, threshold_pct=5.0)
    """

    def __init__(
        self,
        subgraph_url: str,
        client: Optional[GraphClient] = None
    ):
        """
        Initialize WhaleTrackingQueries.

        Args:
            subgraph_url: URL of the deployed erc20-tracker subgraph
            client: Optional GraphClient instance (creates new one if not provided)
        """
        self.subgraph_url = subgraph_url
        self.client = client or GraphClient()
        self.erc20_queries = ERC20Queries(subgraph_url=subgraph_url, client=self.client)

    def get_top_whales(
        self,
        token_address: str,
        limit: int = 20,
        min_percentage: float = 0.1
    ) -> List[WhaleInfo]:
        """
        Get top token holders (whales).

        Args:
            token_address: Token contract address
            limit: Number of top holders to return
            min_percentage: Minimum percentage of supply to qualify as whale

        Returns:
            List of WhaleInfo dataclasses
        """
        # Get token info for total supply
        token_info = self.erc20_queries.get_token_info(token_address)
        if not token_info:
            return []

        total_supply = float(token_info.total_supply)

        # Get top holders
        df = self.erc20_queries.get_top_holders(token_address, limit=limit)

        if df.empty:
            return []

        whales = []
        for idx, row in df.iterrows():
            balance = float(row["balance"])
            percentage = (balance / total_supply * 100) if total_supply > 0 else 0

            if percentage >= min_percentage:
                whales.append(WhaleInfo(
                    address=row["account"],
                    balance=balance,
                    percentage=round(percentage, 4),
                    rank=idx + 1
                ))

        return whales

    def get_whale_balance_at_block(
        self,
        token_address: str,
        whale_address: str,
        block_number: int
    ) -> Optional[float]:
        """
        Get a whale's balance at a specific block using time-travel query.

        Args:
            token_address: Token contract address
            whale_address: Whale's wallet address
            block_number: Block number to query

        Returns:
            Balance at that block or None if not found
        """
        query = """
        query GetBalanceAtBlock($token: String!, $account: String!, $block: Int!) {
            accountBalances(
                first: 1,
                where: { token: $token, account: $account },
                block: { number: $block }
            ) {
                balance
                token { decimals }
            }
        }
        """

        try:
            result = self.client.query(
                endpoint=self.subgraph_url,
                query=query,
                variables={
                    "token": token_address.lower(),
                    "account": whale_address.lower(),
                    "block": block_number
                }
            )

            balances = result.get("accountBalances", [])
            if balances:
                decimals = int(balances[0]["token"]["decimals"])
                return float(raw_to_decimal(balances[0]["balance"], decimals))
            return 0.0

        except Exception as e:
            logger.warning(f"Failed to get balance at block {block_number}: {e}")
            return None

    def get_whale_balance_history(
        self,
        token_address: str,
        whale_addresses: List[str],
        from_block: int,
        to_block: int,
        interval_blocks: int = BLOCKS_PER_DAY
    ) -> pd.DataFrame:
        """
        Get historical balance data for multiple whales.

        Args:
            token_address: Token contract address
            whale_addresses: List of whale addresses to track
            from_block: Starting block number
            to_block: Ending block number
            interval_blocks: Block interval for sampling

        Returns:
            DataFrame with columns: block_number, timestamp, address, balance, percentage
        """
        # Get token info for total supply
        token_info = self.erc20_queries.get_token_info(token_address)
        total_supply = float(token_info.total_supply) if token_info else 0

        records = []
        block_range = range(from_block, to_block + 1, interval_blocks)

        for block_num in block_range:
            # Estimate timestamp (rough approximation)
            # Ethereum: ~12 seconds per block
            blocks_from_reference = block_num - 18000000  # Reference: block 18M ~ Oct 2023
            timestamp = 1696118400 + (blocks_from_reference * 12)

            for address in whale_addresses:
                balance = self.get_whale_balance_at_block(
                    token_address, address, block_num
                )

                if balance is not None:
                    percentage = (balance / total_supply * 100) if total_supply > 0 else 0
                    records.append({
                        "block_number": block_num,
                        "timestamp": timestamp,
                        "address": address.lower(),
                        "balance": balance,
                        "percentage": round(percentage, 4)
                    })

        return pd.DataFrame(records)

    def get_whale_transfers(
        self,
        token_address: str,
        whale_addresses: List[str],
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get transfer events involving tracked whales.

        Args:
            token_address: Token contract address
            whale_addresses: List of whale addresses
            from_block: Starting block (optional)
            to_block: Ending block (optional)
            limit: Maximum transfers to return

        Returns:
            DataFrame with transfer records involving whales
        """
        all_transfers = []

        for address in whale_addresses:
            # Get transfers from this whale
            from_transfers = self.erc20_queries.get_transfers(
                token_address=token_address,
                from_address=address,
                from_block=from_block,
                to_block=to_block,
                limit=limit // len(whale_addresses) + 1
            )
            if not from_transfers.empty:
                from_transfers["whale_address"] = address
                from_transfers["direction"] = "out"
                all_transfers.append(from_transfers)

            # Get transfers to this whale
            to_transfers = self.erc20_queries.get_transfers(
                token_address=token_address,
                to_address=address,
                from_block=from_block,
                to_block=to_block,
                limit=limit // len(whale_addresses) + 1
            )
            if not to_transfers.empty:
                to_transfers["whale_address"] = address
                to_transfers["direction"] = "in"
                all_transfers.append(to_transfers)

        if not all_transfers:
            return pd.DataFrame()

        df = pd.concat(all_transfers, ignore_index=True)
        df = df.sort_values("block_number", ascending=False)
        return df.head(limit)

    def detect_whale_movements(
        self,
        history_df: pd.DataFrame,
        threshold_pct: float = 5.0
    ) -> List[WhaleMovement]:
        """
        Detect significant whale movements from balance history.

        Args:
            history_df: DataFrame from get_whale_balance_history
            threshold_pct: Minimum percentage change to flag as movement

        Returns:
            List of WhaleMovement dataclasses
        """
        if history_df.empty:
            return []

        movements = []

        for address in history_df["address"].unique():
            whale_data = history_df[history_df["address"] == address].sort_values("block_number")

            if len(whale_data) < 2:
                continue

            for i in range(1, len(whale_data)):
                prev = whale_data.iloc[i - 1]
                curr = whale_data.iloc[i]

                from_balance = prev["balance"]
                to_balance = curr["balance"]
                change = to_balance - from_balance

                if from_balance > 0:
                    change_pct = abs(change / from_balance * 100)
                else:
                    change_pct = 100 if to_balance > 0 else 0

                if change_pct >= threshold_pct:
                    movement_type = "accumulation" if change > 0 else "distribution"
                    movements.append(WhaleMovement(
                        address=address,
                        from_balance=from_balance,
                        to_balance=to_balance,
                        change_amount=change,
                        change_percentage=round(change_pct, 2),
                        block_number=curr["block_number"],
                        timestamp=curr["timestamp"],
                        movement_type=movement_type
                    ))

        # Sort by timestamp descending
        movements.sort(key=lambda x: x.timestamp, reverse=True)
        return movements

    def get_whale_activity_feed(
        self,
        token_address: str,
        whale_addresses: List[str],
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        min_amount_pct: float = 1.0,
        limit: int = 50
    ) -> List[WhaleActivityEvent]:
        """
        Get a feed of significant whale activity events.

        Args:
            token_address: Token contract address
            whale_addresses: List of whale addresses to track
            from_block: Starting block (optional)
            to_block: Ending block (optional)
            min_amount_pct: Minimum percentage of holdings for event
            limit: Maximum events to return

        Returns:
            List of WhaleActivityEvent dataclasses
        """
        transfers = self.get_whale_transfers(
            token_address=token_address,
            whale_addresses=whale_addresses,
            from_block=from_block,
            to_block=to_block,
            limit=limit * 2
        )

        if transfers.empty:
            return []

        # Get token info
        token_info = self.erc20_queries.get_token_info(token_address)
        total_supply = float(token_info.total_supply) if token_info else 0

        events = []

        for _, row in transfers.iterrows():
            amount = row["amount"]
            percentage = (amount / total_supply * 100) if total_supply > 0 else 0

            if percentage >= min_amount_pct:
                event_type = "large_buy" if row["direction"] == "in" else "large_sell"
                events.append(WhaleActivityEvent(
                    address=row["whale_address"],
                    event_type=event_type,
                    amount=amount,
                    percentage_change=round(percentage, 4),
                    block_number=row["block_number"],
                    timestamp=row["timestamp"],
                    tx_hash=row.get("tx_hash")
                ))

        # Sort by timestamp descending
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events[:limit]

    def calculate_whale_concentration(
        self,
        token_address: str,
        top_n: int = 10
    ) -> Dict[str, float]:
        """
        Calculate current whale concentration metrics.

        Args:
            token_address: Token contract address
            top_n: Number of top holders to include

        Returns:
            Dictionary with concentration metrics
        """
        whales = self.get_top_whales(token_address, limit=top_n)

        if not whales:
            return {
                "top_whale_percentage": 0.0,
                "total_whale_percentage": 0.0,
                "whale_count": 0,
                "avg_whale_holdings": 0.0
            }

        total_pct = sum(w.percentage for w in whales)
        top_whale_pct = whales[0].percentage if whales else 0

        return {
            "top_whale_percentage": round(top_whale_pct, 2),
            "total_whale_percentage": round(total_pct, 2),
            "whale_count": len(whales),
            "avg_whale_holdings": round(total_pct / len(whales), 2) if whales else 0.0
        }

    def analyze_whale_stability(
        self,
        history_df: pd.DataFrame,
        lookback_blocks: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Analyze whale holding stability over time.

        Args:
            history_df: DataFrame from get_whale_balance_history
            lookback_blocks: Number of blocks to analyze (None = all)

        Returns:
            Dictionary with stability metrics
        """
        if history_df.empty:
            return {
                "stability_score": 0.0,
                "avg_holding_change": 0.0,
                "volatile_whales": 0,
                "stable_whales": 0
            }

        if lookback_blocks:
            max_block = history_df["block_number"].max()
            history_df = history_df[history_df["block_number"] >= max_block - lookback_blocks]

        stability_scores = []
        volatile_count = 0
        stable_count = 0

        for address in history_df["address"].unique():
            whale_data = history_df[history_df["address"] == address].sort_values("block_number")

            if len(whale_data) < 2:
                continue

            # Calculate volatility as coefficient of variation
            mean_balance = whale_data["balance"].mean()
            std_balance = whale_data["balance"].std()

            if mean_balance > 0:
                cv = std_balance / mean_balance
                stability = max(0, 1 - cv)  # Higher = more stable
                stability_scores.append(stability)

                if stability > 0.9:
                    stable_count += 1
                elif stability < 0.5:
                    volatile_count += 1

        avg_stability = np.mean(stability_scores) if stability_scores else 0

        # Calculate average holding change
        changes = []
        for address in history_df["address"].unique():
            whale_data = history_df[history_df["address"] == address].sort_values("block_number")
            if len(whale_data) >= 2:
                start = whale_data["balance"].iloc[0]
                end = whale_data["balance"].iloc[-1]
                if start > 0:
                    changes.append((end - start) / start * 100)

        avg_change = np.mean(changes) if changes else 0

        return {
            "stability_score": round(avg_stability * 100, 2),
            "avg_holding_change": round(avg_change, 2),
            "volatile_whales": volatile_count,
            "stable_whales": stable_count
        }

    def get_accumulation_distribution_pattern(
        self,
        history_df: pd.DataFrame
    ) -> str:
        """
        Determine overall accumulation/distribution pattern.

        Args:
            history_df: DataFrame from get_whale_balance_history

        Returns:
            Pattern string: "accumulation", "distribution", "mixed", or "stable"
        """
        if history_df.empty:
            return "unknown"

        # Calculate net change for each whale
        net_changes = []

        for address in history_df["address"].unique():
            whale_data = history_df[history_df["address"] == address].sort_values("block_number")
            if len(whale_data) >= 2:
                start = whale_data["balance"].iloc[0]
                end = whale_data["balance"].iloc[-1]
                if start > 0:
                    net_changes.append((end - start) / start * 100)

        if not net_changes:
            return "unknown"

        avg_change = np.mean(net_changes)
        accumulating = sum(1 for c in net_changes if c > 5)
        distributing = sum(1 for c in net_changes if c < -5)
        total = len(net_changes)

        if accumulating > total * 0.6:
            return "accumulation"
        elif distributing > total * 0.6:
            return "distribution"
        elif abs(avg_change) < 5:
            return "stable"
        else:
            return "mixed"


def format_whale_address(address: str, length: int = 8) -> str:
    """
    Format whale address for display (shortened form).

    Args:
        address: Full Ethereum address
        length: Number of characters to show on each end

    Returns:
        Shortened address (e.g., "0x1234...5678")
    """
    if len(address) <= length * 2:
        return address
    return f"{address[:length]}...{address[-length:]}"


def interpret_whale_activity(movements: List[WhaleMovement]) -> str:
    """
    Provide interpretation of whale activity.

    Args:
        movements: List of whale movements

    Returns:
        Interpretation string
    """
    if not movements:
        return "No significant whale activity detected"

    accumulations = sum(1 for m in movements if m.movement_type == "accumulation")
    distributions = sum(1 for m in movements if m.movement_type == "distribution")

    total = len(movements)
    if accumulations > distributions * 2:
        return "Strong whale accumulation - bullish signal"
    elif distributions > accumulations * 2:
        return "Heavy whale distribution - potential sell pressure"
    elif total > 10:
        return "High whale activity - increased volatility expected"
    else:
        return "Moderate whale activity - mixed signals"

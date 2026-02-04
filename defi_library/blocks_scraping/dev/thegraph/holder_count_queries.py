"""
Holder Count Over Time Queries for ERC-20 Token Tracking

This module provides functionality to track unique holder count evolution
over time to detect growth/decline trends.

Features:
- Query holder count at different block intervals
- Store snapshots in time series
- Calculate holder growth rates (daily/weekly)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd

from .base_queries import (
    BaseQueries,
    BLOCKS_PER_DAY,
    BLOCKS_PER_WEEK,
    BLOCKS_PER_MONTH,
    normalize_address,
)
from .graph_client import GraphClient

logger = logging.getLogger(__name__)


@dataclass
class HolderCountRecord:
    """Holder count record at a specific point in time"""
    token_address: str
    holder_count: int
    block_number: int
    timestamp: int


@dataclass
class TokenInfoWithHolders:
    """Token metadata including holder count"""
    address: str
    name: str
    symbol: str
    decimals: int
    total_supply: str
    holder_count: int


class HolderCountQueries:
    """
    Queries for tracking holder count over time.

    This class provides methods to fetch holder count at different
    block heights and calculate growth metrics.

    Example usage:
        queries = HolderCountQueries(subgraph_url="https://api.studio.thegraph.com/query/.../erc20-tracker/v0.0.1")

        # Get current holder count
        info = queries.get_token_holder_info(token_address)
        print(f"Current holders: {info.holder_count}")

        # Get holder count history
        history = queries.get_holder_count_history(
            token_address="0x...",
            from_block=18000000,
            to_block=18100000,
            interval_blocks=7200  # Daily snapshots
        )
    """

    def __init__(
        self,
        subgraph_url: str,
        client: Optional[GraphClient] = None
    ):
        """
        Initialize HolderCountQueries.

        Args:
            subgraph_url: URL of the deployed erc20-tracker subgraph
            client: Optional GraphClient instance (creates new one if not provided)
        """
        self.subgraph_url = subgraph_url
        self.client = client or GraphClient()

    def get_token_holder_info(self, token_address: str) -> Optional[TokenInfoWithHolders]:
        """
        Get token metadata including current holder count.

        Args:
            token_address: Token contract address

        Returns:
            TokenInfoWithHolders dataclass or None if not found
        """
        query = """
        query GetTokenHolders($id: ID!) {
            token(id: $id) {
                id
                name
                symbol
                decimals
                totalSupply
                holderCount
            }
        }
        """

        result = self.client.query(
            endpoint=self.subgraph_url,
            query=query,
            variables={"id": normalize_address(token_address)}
        )

        token_data = result.get("token")
        if not token_data:
            return None

        return TokenInfoWithHolders(
            address=token_data["id"],
            name=token_data["name"],
            symbol=token_data["symbol"],
            decimals=int(token_data["decimals"]),
            total_supply=token_data["totalSupply"],
            holder_count=int(token_data["holderCount"])
        )

    def get_holder_count_at_block(
        self,
        token_address: str,
        block_number: int
    ) -> Optional[HolderCountRecord]:
        """
        Get holder count at a specific block number.

        Uses The Graph's time-travel query feature to fetch
        historical data at a specific block height.

        Args:
            token_address: Token contract address
            block_number: Block number to query at

        Returns:
            HolderCountRecord or None if not found
        """
        query = """
        query GetHolderCountAtBlock($id: ID!, $block: Int!) {
            token(id: $id, block: { number: $block }) {
                id
                holderCount
            }
        }
        """

        try:
            result = self.client.query(
                endpoint=self.subgraph_url,
                query=query,
                variables={
                    "id": normalize_address(token_address),
                    "block": block_number
                }
            )

            token_data = result.get("token")
            if not token_data:
                return None

            return HolderCountRecord(
                token_address=token_data["id"],
                holder_count=int(token_data["holderCount"]),
                block_number=block_number,
                timestamp=0  # Will be filled by caller if needed
            )
        except Exception as e:
            logger.warning(f"Failed to get holder count at block {block_number}: {e}")
            return None

    def get_holder_count_history(
        self,
        token_address: str,
        from_block: int,
        to_block: int,
        interval_blocks: int = BLOCKS_PER_DAY,
        include_timestamps: bool = True
    ) -> pd.DataFrame:
        """
        Get holder count history over a block range.

        Queries holder count at regular intervals between from_block
        and to_block to build a time series.

        Args:
            token_address: Token contract address
            from_block: Starting block number
            to_block: Ending block number
            interval_blocks: Number of blocks between each snapshot
            include_timestamps: Whether to fetch block timestamps

        Returns:
            DataFrame with columns: block_number, holder_count, timestamp (optional)
        """
        records = []
        current_block = from_block

        while current_block <= to_block:
            record = self.get_holder_count_at_block(token_address, current_block)
            if record:
                records.append({
                    "block_number": record.block_number,
                    "holder_count": record.holder_count,
                })
            current_block += interval_blocks

        if not records:
            return pd.DataFrame(columns=["block_number", "holder_count", "timestamp"])

        df = pd.DataFrame(records)

        # Fetch timestamps if requested
        if include_timestamps and not df.empty:
            df["timestamp"] = df["block_number"].apply(
                lambda b: self._get_block_timestamp(b)
            )
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

        return df

    def _get_block_timestamp(self, block_number: int) -> int:
        """
        Get timestamp for a block number.

        Uses Transfer events to get approximate timestamp.
        """
        query = """
        query GetBlockTimestamp($block: Int!) {
            transfers(
                first: 1,
                where: { blockNumber_gte: $block },
                orderBy: blockNumber,
                orderDirection: asc
            ) {
                timestamp
                blockNumber
            }
        }
        """

        try:
            result = self.client.query(
                endpoint=self.subgraph_url,
                query=query,
                variables={"block": block_number}
            )

            transfers = result.get("transfers", [])
            if transfers:
                return int(transfers[0]["timestamp"])
        except Exception as e:
            logger.warning(f"Failed to get timestamp for block {block_number}: {e}")

        # Estimate timestamp based on Ethereum block time (~12 seconds)
        # Using a reference point (block 18000000 ~ Oct 2023)
        reference_block = 18000000
        reference_timestamp = 1695902400  # Oct 2023
        estimated = reference_timestamp + (block_number - reference_block) * 12
        return estimated

    def get_holder_count_with_transfers(
        self,
        token_address: str,
        from_block: int,
        to_block: int,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Get holder count changes correlated with transfer events.

        This method uses transfer events to identify blocks where
        holder count might have changed, providing more accurate
        snapshots without needing to query every block.

        Args:
            token_address: Token contract address
            from_block: Starting block number
            to_block: Ending block number
            limit: Maximum number of transfer events to fetch

        Returns:
            DataFrame with holder count at each transfer block
        """
        # First, get transfer events to identify relevant blocks
        query = f"""
        query GetTransferBlocks($first: Int!) {{
            transfers(
                first: $first,
                where: {{
                    token: "{normalize_address(token_address)}",
                    blockNumber_gte: {from_block},
                    blockNumber_lte: {to_block}
                }},
                orderBy: blockNumber,
                orderDirection: asc
            ) {{
                blockNumber
                timestamp
            }}
        }}
        """

        result = self.client.query(
            endpoint=self.subgraph_url,
            query=query,
            variables={"first": limit}
        )

        transfers = result.get("transfers", [])

        if not transfers:
            return pd.DataFrame(columns=["block_number", "holder_count", "timestamp"])

        # Get unique blocks where transfers occurred
        unique_blocks = []
        seen_blocks = set()
        for t in transfers:
            block = int(t["blockNumber"])
            if block not in seen_blocks:
                seen_blocks.add(block)
                unique_blocks.append({
                    "block_number": block,
                    "timestamp": int(t["timestamp"])
                })

        # Query holder count at each unique block
        records = []
        for block_info in unique_blocks:
            record = self.get_holder_count_at_block(
                token_address,
                block_info["block_number"]
            )
            if record:
                records.append({
                    "block_number": block_info["block_number"],
                    "holder_count": record.holder_count,
                    "timestamp": block_info["timestamp"]
                })

        if not records:
            return pd.DataFrame(columns=["block_number", "holder_count", "timestamp"])

        df = pd.DataFrame(records)
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

        return df


def calculate_growth_rate(
    df: pd.DataFrame,
    period: str = "daily"
) -> pd.DataFrame:
    """
    Calculate holder count growth rate.

    Args:
        df: DataFrame with columns: block_number, holder_count, timestamp
        period: Growth period - "daily", "weekly", or "block"

    Returns:
        DataFrame with additional columns: growth_absolute, growth_rate
    """
    if df.empty:
        return df

    df = df.copy()
    df = df.sort_values("block_number")

    # Calculate absolute growth (change from previous)
    df["growth_absolute"] = df["holder_count"].diff()

    # Calculate percentage growth rate
    df["growth_rate"] = df["holder_count"].pct_change() * 100

    # Add rolling averages for smoothing
    if len(df) >= 7:
        df["growth_rate_7d_avg"] = df["growth_rate"].rolling(window=7).mean()

    return df


def calculate_growth_metrics(
    df: pd.DataFrame
) -> dict:
    """
    Calculate summary growth metrics from holder count data.

    Args:
        df: DataFrame with columns: block_number, holder_count, timestamp

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
        }

    df = df.sort_values("block_number")

    start_holders = df["holder_count"].iloc[0]
    end_holders = df["holder_count"].iloc[-1]

    total_growth = end_holders - start_holders
    total_growth_rate = (total_growth / start_holders * 100) if start_holders > 0 else 0

    # Calculate daily growth (approximate)
    growth_per_point = df["holder_count"].diff().dropna()
    avg_growth = growth_per_point.mean() if len(growth_per_point) > 0 else 0

    return {
        "total_growth": int(total_growth),
        "total_growth_rate": round(total_growth_rate, 2),
        "avg_daily_growth": round(avg_growth, 2),
        "avg_daily_growth_rate": round((avg_growth / start_holders * 100) if start_holders > 0 else 0, 2),
        "max_daily_growth": int(growth_per_point.max()) if len(growth_per_point) > 0 else 0,
        "min_daily_growth": int(growth_per_point.min()) if len(growth_per_point) > 0 else 0,
        "start_holders": int(start_holders),
        "end_holders": int(end_holders),
    }


def detect_growth_anomalies(
    df: pd.DataFrame,
    threshold_std: float = 2.0
) -> pd.DataFrame:
    """
    Detect anomalous growth/decline periods.

    Identifies points where growth rate deviates significantly
    from the norm, which could indicate pump phases or
    artificial/organic growth events.

    Args:
        df: DataFrame with holder count data
        threshold_std: Number of standard deviations for anomaly detection

    Returns:
        DataFrame with anomaly flags
    """
    if df.empty or len(df) < 3:
        return df

    df = df.copy()
    df = df.sort_values("block_number")

    df["growth"] = df["holder_count"].diff()

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

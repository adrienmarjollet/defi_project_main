"""
Base Queries Module for TheGraph Query Classes

This module provides common functionality shared across all TheGraph query classes:
- BaseQueries class with standard initialization
- Block time constants
- Address formatting utilities
- Holder tier classification
- Common data fetching patterns

All specialized query classes should inherit from BaseQueries to reduce duplication.
"""

import logging
from typing import List, Optional

import pandas as pd

from .graph_client import GraphClient, raw_to_decimal

# Import consolidated constants
from defi_library.constants import (
    BLOCKS_PER_HOUR,
    BLOCKS_PER_DAY,
    BLOCKS_PER_WEEK,
    BLOCKS_PER_MONTH,
    TIER_THRESHOLDS,
    get_tier_color,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Block Time Constants (re-exported from defi_library.constants)
# =============================================================================
# Ethereum mainnet approximate block times (~12 seconds per block)
BLOCKS_PER_MINUTE = 5  # Not in consolidated constants yet

# Holder Tier Thresholds (re-exported from defi_library.constants)
WHALE_THRESHOLD_PCT = TIER_THRESHOLDS["whale"]      # >1% of supply
DOLPHIN_THRESHOLD_PCT = TIER_THRESHOLDS["dolphin"]  # 0.1% - 1% of supply
# Fish: <0.1% of supply


# =============================================================================
# Address Formatting Utilities
# =============================================================================

def format_address(address: str, length: int = 6) -> str:
    """
    Format an Ethereum address for display (shortened form).

    Args:
        address: Full Ethereum address (42 characters with 0x prefix)
        length: Number of characters to show on each end (default 6)

    Returns:
        Shortened address (e.g., "0x1234...5678")

    Example:
        >>> format_address("0x742d35Cc6634C0532925a3b844Bc9e7595f5bEe1")
        '0x742d...bEe1'
    """
    if not address or len(address) <= length * 2 + 3:
        return address
    return f"{address[:length]}...{address[-length:]}"


def normalize_address(address: str) -> str:
    """
    Normalize an Ethereum address to lowercase for consistent comparisons.

    Args:
        address: Ethereum address in any case

    Returns:
        Lowercase address
    """
    return address.lower() if address else ""


def is_valid_address(address: str) -> bool:
    """
    Check if a string is a valid Ethereum address format.

    Args:
        address: String to validate

    Returns:
        True if valid Ethereum address format
    """
    if not address:
        return False
    if not address.startswith("0x"):
        return False
    if len(address) != 42:
        return False
    try:
        int(address, 16)
        return True
    except ValueError:
        return False


# =============================================================================
# Holder Tier Classification
# =============================================================================

def classify_holder_tier(
    percentage: float,
    whale_threshold: float = WHALE_THRESHOLD_PCT,
    dolphin_threshold: float = DOLPHIN_THRESHOLD_PCT
) -> str:
    """
    Classify a holder into a tier based on percentage of total supply.

    Tiers:
    - whale: >1% of supply (large holder with significant influence)
    - dolphin: 0.1% - 1% of supply (medium holder)
    - fish: <0.1% of supply (small holder)

    Args:
        percentage: Percentage of total supply held by the address
        whale_threshold: Minimum percentage to be classified as whale (default 1.0%)
        dolphin_threshold: Minimum percentage to be classified as dolphin (default 0.1%)

    Returns:
        Tier string: "whale", "dolphin", or "fish"

    Example:
        >>> classify_holder_tier(2.5)
        'whale'
        >>> classify_holder_tier(0.5)
        'dolphin'
        >>> classify_holder_tier(0.05)
        'fish'
    """
    if percentage >= whale_threshold:
        return "whale"
    elif percentage >= dolphin_threshold:
        return "dolphin"
    else:
        return "fish"


# get_tier_color is imported from defi_library.constants


# =============================================================================
# Base Queries Class
# =============================================================================

class BaseQueries:
    """
    Base class for all TheGraph query classes.

    Provides common initialization pattern and shared utilities for
    querying ERC-20 token data from The Graph subgraphs.

    All specialized query classes (WhaleTrackingQueries, HolderDistributionQueries,
    etc.) should inherit from this base class to reduce code duplication.

    Attributes:
        subgraph_url: URL of the deployed subgraph
        client: GraphClient instance for executing queries
    """

    def __init__(
        self,
        subgraph_url: str,
        client: Optional[GraphClient] = None
    ):
        """
        Initialize the base query class.

        Args:
            subgraph_url: URL of the deployed erc20-tracker subgraph
            client: Optional GraphClient instance (creates new one if not provided)
        """
        self.subgraph_url = subgraph_url
        self.client = client or GraphClient()

    def get_token_info(self, token_address: str) -> Optional[dict]:
        """
        Get basic token metadata.

        Args:
            token_address: Token contract address

        Returns:
            Dictionary with token info or None if not found
        """
        query = """
        query GetToken($id: ID!) {
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

        return result.get("token")

    def get_top_holders(
        self,
        token_address: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get top token holders by balance.

        This is a common operation used by multiple query classes.

        Args:
            token_address: Token contract address
            limit: Maximum number of holders to return

        Returns:
            DataFrame with columns: address, balance, percentage, rank
        """
        # First get token info for total supply
        token_info = self.get_token_info(token_address)
        if not token_info:
            return pd.DataFrame(columns=["address", "balance", "percentage", "rank"])

        total_supply = float(token_info.get("totalSupply", 0))
        decimals = int(token_info.get("decimals", 18))

        query = f"""
        query GetTopHolders($first: Int!) {{
            accountBalances(
                first: $first,
                where: {{ token: "{normalize_address(token_address)}" }},
                orderBy: balance,
                orderDirection: desc
            ) {{
                account {{ id }}
                balance
                blockNumber
            }}
        }}
        """

        result = self.client.query(
            endpoint=self.subgraph_url,
            query=query,
            variables={"first": limit}
        )

        balances = result.get("accountBalances", [])

        if not balances:
            return pd.DataFrame(columns=["address", "balance", "percentage", "rank"])

        records = []
        for idx, b in enumerate(balances):
            balance = float(raw_to_decimal(b["balance"], decimals))
            percentage = (balance / total_supply * 100) if total_supply > 0 else 0

            records.append({
                "address": b["account"]["id"],
                "balance": balance,
                "percentage": round(percentage, 4),
                "rank": idx + 1,
                "tier": classify_holder_tier(percentage),
            })

        return pd.DataFrame(records)

    def get_transfers(
        self,
        token_address: str,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Get transfer events for a token.

        Args:
            token_address: Token contract address
            from_address: Optional sender filter
            to_address: Optional receiver filter
            from_block: Starting block
            to_block: Ending block
            limit: Maximum results

        Returns:
            DataFrame with transfer records
        """
        where_parts = [f'token: "{normalize_address(token_address)}"']

        if from_address:
            where_parts.append(f'from: "{normalize_address(from_address)}"')
        if to_address:
            where_parts.append(f'to: "{normalize_address(to_address)}"')
        if from_block:
            where_parts.append(f"blockNumber_gte: {from_block}")
        if to_block:
            where_parts.append(f"blockNumber_lte: {to_block}")

        where_clause = ", ".join(where_parts)

        query = f"""
        query GetTransfers($first: Int!) {{
            transfers(
                first: $first,
                where: {{ {where_clause} }},
                orderBy: blockNumber,
                orderDirection: desc
            ) {{
                from {{ id }}
                to {{ id }}
                token {{ decimals symbol }}
                amount
                blockNumber
                timestamp
                transactionHash
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
            return pd.DataFrame(columns=["from", "to", "amount", "block_number", "timestamp", "tx_hash"])

        records = []
        for t in transfers:
            decimals = int(t["token"]["decimals"])
            records.append({
                "from": t["from"]["id"],
                "to": t["to"]["id"],
                "symbol": t["token"]["symbol"],
                "amount": float(raw_to_decimal(t["amount"], decimals)),
                "amount_raw": t["amount"],
                "block_number": int(t["blockNumber"]),
                "timestamp": int(t["timestamp"]),
                "tx_hash": t["transactionHash"],
            })

        return pd.DataFrame(records)

    def get_balance_at_block(
        self,
        token_address: str,
        account_address: str,
        block_number: int
    ) -> Optional[float]:
        """
        Get an account's balance at a specific block using time-travel query.

        Args:
            token_address: Token contract address
            account_address: Account address to query
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
                    "token": normalize_address(token_address),
                    "account": normalize_address(account_address),
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

    def estimate_timestamp(self, block_number: int, reference_block: int = 18000000, reference_timestamp: int = 1696118400) -> int:
        """
        Estimate timestamp for a block number based on average block time.

        Args:
            block_number: Block number to estimate timestamp for
            reference_block: Known reference block number (default: 18000000 ~ Oct 2023)
            reference_timestamp: Timestamp of reference block

        Returns:
            Estimated Unix timestamp
        """
        blocks_from_reference = block_number - reference_block
        # Ethereum: ~12 seconds per block
        return reference_timestamp + (blocks_from_reference * 12)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Constants
    "BLOCKS_PER_MINUTE",
    "BLOCKS_PER_HOUR",
    "BLOCKS_PER_DAY",
    "BLOCKS_PER_WEEK",
    "BLOCKS_PER_MONTH",
    "WHALE_THRESHOLD_PCT",
    "DOLPHIN_THRESHOLD_PCT",
    # Address utilities
    "format_address",
    "normalize_address",
    "is_valid_address",
    # Tier utilities
    "classify_holder_tier",
    "get_tier_color",
    # Base class
    "BaseQueries",
]

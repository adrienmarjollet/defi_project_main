"""
Pre-built GraphQL Queries for ERC-20 Token Tracking

These queries are designed to work with the erc20-tracker subgraph
and replicate the functionality previously provided by Cryo.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .graph_client import GraphClient, raw_to_decimal

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Token metadata"""
    address: str
    name: str
    symbol: str
    decimals: int
    total_supply: Decimal


@dataclass
class BalanceRecord:
    """Balance record for an account"""
    account: str
    token: str
    balance: Decimal
    block_number: int
    timestamp: int


class ERC20Queries:
    """
    Pre-built queries for ERC-20 token data.

    Replaces Cryo functionality with The Graph queries.

    Example usage:
        queries = ERC20Queries(subgraph_url="https://api.studio.thegraph.com/query/.../erc20-tracker/v0.0.1")

        # Get token balances
        balances = queries.get_token_balances(
            token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            addresses=["0x123...", "0x456..."]
        )

        # Get balance history
        history = queries.get_balance_snapshots(
            token_address="0x...",
            account_address="0x...",
            from_block=18000000,
            to_block=18100000
        )
    """

    def __init__(
        self,
        subgraph_url: str,
        client: Optional[GraphClient] = None
    ):
        """
        Initialize ERC20 queries.

        Args:
            subgraph_url: URL of the deployed erc20-tracker subgraph
            client: Optional GraphClient instance (creates new one if not provided)
        """
        self.subgraph_url = subgraph_url
        self.client = client or GraphClient()

    def get_token_info(self, token_address: str) -> Optional[TokenInfo]:
        """
        Get token metadata.

        Args:
            token_address: Token contract address

        Returns:
            TokenInfo dataclass or None if not found
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
            variables={"id": token_address.lower()}
        )

        token_data = result.get("token")
        if not token_data:
            return None

        return TokenInfo(
            address=token_data["id"],
            name=token_data["name"],
            symbol=token_data["symbol"],
            decimals=int(token_data["decimals"]),
            total_supply=raw_to_decimal(
                token_data["totalSupply"],
                int(token_data["decimals"])
            )
        )

    def get_token_balances(
        self,
        token_address: str,
        addresses: Optional[List[str]] = None,
        min_balance: Optional[str] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Get current token balances for accounts.

        Args:
            token_address: Token contract address
            addresses: Optional list of addresses to filter
            min_balance: Optional minimum balance filter (in raw units)
            limit: Maximum number of results

        Returns:
            DataFrame with columns: account, balance, balance_raw, block_number
        """
        # Build where clause
        where_parts = [f'token: "{token_address.lower()}"']
        if addresses:
            addr_list = ", ".join(f'"{a.lower()}"' for a in addresses)
            where_parts.append(f"account_in: [{addr_list}]")
        if min_balance:
            where_parts.append(f'balance_gt: "{min_balance}"')

        where_clause = ", ".join(where_parts)

        query = f"""
        query GetBalances($first: Int!) {{
            accountBalances(
                first: $first,
                where: {{ {where_clause} }},
                orderBy: balance,
                orderDirection: desc
            ) {{
                account {{ id }}
                token {{ id decimals symbol }}
                balance
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

        balances = result.get("accountBalances", [])

        if not balances:
            return pd.DataFrame(columns=["account", "token", "symbol", "balance", "balance_raw", "block_number"])

        # Convert to DataFrame
        records = []
        for b in balances:
            decimals = int(b["token"]["decimals"])
            records.append({
                "account": b["account"]["id"],
                "token": b["token"]["id"],
                "symbol": b["token"]["symbol"],
                "balance": float(raw_to_decimal(b["balance"], decimals)),
                "balance_raw": b["balance"],
                "block_number": int(b["blockNumber"]),
            })

        return pd.DataFrame(records)

    def get_balance_snapshots(
        self,
        token_address: str,
        account_address: str,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Get historical balance snapshots for an account.

        This replaces Cryo's fetch_erc20_balances for historical data.

        Args:
            token_address: Token contract address
            account_address: Account address
            from_block: Starting block number
            to_block: Ending block number
            limit: Maximum results per query

        Returns:
            DataFrame with columns: block_number, timestamp, balance
        """
        where_parts = [
            f'token: "{token_address.lower()}"',
            f'account: "{account_address.lower()}"'
        ]

        if from_block is not None:
            where_parts.append(f"blockNumber_gte: {from_block}")
        if to_block is not None:
            where_parts.append(f"blockNumber_lte: {to_block}")

        where_clause = ", ".join(where_parts)

        query = f"""
        query GetSnapshots($first: Int!) {{
            balanceSnapshots(
                first: $first,
                where: {{ {where_clause} }},
                orderBy: blockNumber,
                orderDirection: asc
            ) {{
                token {{ decimals }}
                balance
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

        snapshots = result.get("balanceSnapshots", [])

        if not snapshots:
            return pd.DataFrame(columns=["block_number", "timestamp", "balance"])

        records = []
        for s in snapshots:
            decimals = int(s["token"]["decimals"])
            records.append({
                "block_number": int(s["blockNumber"]),
                "timestamp": int(s["timestamp"]),
                "balance": float(raw_to_decimal(s["balance"], decimals)),
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
        where_parts = [f'token: "{token_address.lower()}"']

        if from_address:
            where_parts.append(f'from: "{from_address.lower()}"')
        if to_address:
            where_parts.append(f'to: "{to_address.lower()}"')
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

    def get_top_holders(
        self,
        token_address: str,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Get top token holders by balance.

        Args:
            token_address: Token contract address
            limit: Number of top holders to return

        Returns:
            DataFrame with holder addresses and balances
        """
        return self.get_token_balances(
            token_address=token_address,
            limit=limit
        )

    def get_pool_balances(
        self,
        pool_address: str,
        token0_address: str,
        token1_address: str,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Get liquidity pool reserve balances over time.

        This replaces Cryo's get_token_value_blocks functionality.

        Args:
            pool_address: Liquidity pool contract address
            token0_address: First token address
            token1_address: Second token address (e.g., WETH)
            from_block: Starting block
            to_block: Ending block

        Returns:
            DataFrame with pool balances and derived price
        """
        # Get snapshots for both tokens in the pool
        token0_snapshots = self.get_balance_snapshots(
            token_address=token0_address,
            account_address=pool_address,
            from_block=from_block,
            to_block=to_block
        )

        token1_snapshots = self.get_balance_snapshots(
            token_address=token1_address,
            account_address=pool_address,
            from_block=from_block,
            to_block=to_block
        )

        if token0_snapshots.empty or token1_snapshots.empty:
            return pd.DataFrame(columns=["block_number", "token0_balance", "token1_balance", "price"])

        # Merge on block number
        merged = pd.merge(
            token0_snapshots.rename(columns={"balance": "token0_balance"}),
            token1_snapshots.rename(columns={"balance": "token1_balance"}),
            on="block_number",
            how="inner",
            suffixes=("_0", "_1")
        )

        # Calculate price (token0 in terms of token1)
        merged["price"] = merged["token1_balance"] / merged["token0_balance"]

        return merged[["block_number", "token0_balance", "token1_balance", "price"]]


# Common subgraph endpoints for different chains
SUBGRAPH_ENDPOINTS = {
    "ethereum": {
        "erc20_tracker": "https://api.studio.thegraph.com/query/YOUR_ID/erc20-tracker-eth/version/latest",
    },
    "bsc": {
        "erc20_tracker": "https://api.studio.thegraph.com/query/YOUR_ID/erc20-tracker-bsc/version/latest",
    },
}


def create_erc20_queries(chain: str = "ethereum", subgraph_url: Optional[str] = None) -> ERC20Queries:
    """
    Factory function to create ERC20Queries for a specific chain.

    Args:
        chain: Chain name ("ethereum" or "bsc")
        subgraph_url: Optional custom subgraph URL (overrides default)

    Returns:
        Configured ERC20Queries instance
    """
    if subgraph_url:
        url = subgraph_url
    elif chain in SUBGRAPH_ENDPOINTS:
        url = SUBGRAPH_ENDPOINTS[chain]["erc20_tracker"]
    else:
        raise ValueError(f"Unknown chain: {chain}. Provide a custom subgraph_url.")

    return ERC20Queries(subgraph_url=url)

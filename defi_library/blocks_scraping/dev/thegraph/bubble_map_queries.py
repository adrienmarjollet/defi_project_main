"""
Bubble Map Visualization Queries for ERC-20 Token Tracking

This module provides functionality to generate interactive bubble map data:
- Fetch all holder balances with size proportional to holdings
- Classify wallet types: contracts, EOAs, exchanges
- Support for zoom levels (whales, medium holders, retail)
- Cluster detection for related wallets

Features:
- Plotly-ready data for scatter/bubble plots
- Wallet type classification using on-chain heuristics
- Known exchange address detection
- Force-directed graph data for transfer relationships
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .graph_client import GraphClient, raw_to_decimal
from .queries import ERC20Queries

logger = logging.getLogger(__name__)


class WalletType(Enum):
    """Classification of wallet types."""
    EOA = "eoa"  # Externally Owned Account (regular user)
    CONTRACT = "contract"  # Smart contract
    EXCHANGE = "exchange"  # Known exchange wallet
    BRIDGE = "bridge"  # Bridge contract
    WHALE = "whale"  # Large holder (>1% of supply)
    UNKNOWN = "unknown"


# Known exchange addresses (lowercase)
KNOWN_EXCHANGES: Dict[str, str] = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance",
    "0x56eddb7aa87536c09ccc2793473599fd21a8b17f": "Binance",
    "0x9696f59e4d72e237be84ffd425dcad154bf96976": "Binance",
    "0x4976a4a02f38326660d17bf34b431dc6e2eb2327": "Binance",
    "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance",
    "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8": "Binance",
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3": "Binance",
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": "Binance",
    "0xd551234ae421e3bcba99a0da6d736074f22192ff": "Binance",
    "0x564286362092d8e7936f0549571a803b203aaced": "Binance",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503": "Binance",
    "0xa090e606e30bd747d4e6245a1517ebe430f0057e": "Coinbase",
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase",
    "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": "Coinbase",
    "0x3cd751e6b0078be393132286c442345e5dc49699": "Coinbase",
    "0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511": "Coinbase",
    "0xeb2629a2734e272bcc07bda959863f316f4bd4cf": "Coinbase",
    "0xd688aea8f7d450909ade10c47faa95707b0682d9": "Coinbase",
    "0x02466e547bfdab679fc49e96bbfc62b9747d997c": "Coinbase",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX",
    "0x236f9f97e0e62388479bf9e5ba4889e46b0273c3": "OKX",
    "0xa7efae728d2936e78bda97dc267687568dd593f3": "OKX",
    "0x5041ed759dd4afc3a72b8192c143f72f4724081a": "OKX",
    "0x6262998ced04146fa42253a5c0af90ca02dfd2a3": "Crypto.com",
    "0x46340b20830761efd32832a74d7169b29feb9758": "Crypto.com",
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Kraken",
    "0xda9dfa130df4de4673b89022ee50ff26f6ea73cf": "Kraken",
    "0x2910543af39aba0cd09dbb2d50200b3e800a63d2": "Kraken",
    "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13": "Kraken",
    "0xe853c56864a2ebe4576a807d26fdc4a0ada51919": "Kraken",
    "0xae2d4617c862309a3d75a0ffb358c7a5009c673f": "Kraken",
    "0x53d284357ec70ce289d6d64134dfac8e511c8a3d": "Kraken",
    "0x2c8fbb630289363ac80705a1a61273f76fd5a161": "KuCoin",
    "0xd6216fc19db775df9774a6e33526131da7d19a2c": "KuCoin",
    "0xeb269732ab75a6fd61ea60b06fe994cd32a83549": "KuCoin",
    "0x738cf6903e6c4e699d1c2dd9ab8b67fcdb3121ea": "KuCoin",
    "0x88ff79eb2bc5850f27315415da8685282c7610f9": "KuCoin",
    "0xf16e9b0d03470827a95cdfd0cb8a8a3b46969b91": "KuCoin",
    "0x61189da79177950a7272c88c6058b96d4bcd6be2": "Huobi",
    "0x1062a747393198f70f71ec65a582423dba7e5ab3": "Huobi",
    "0x6748f50f686bfbca6fe8ad62b22228b87f31ff2b": "Huobi",
    "0xab5c66752a9e8167967685f1450532fb96d5d24f": "Huobi",
    "0xe93381fb4c4f14bda253907b18fad305d799241a": "Huobi",
    "0xfa4b5be3f2f84f56703c42eb22142744571a90ad": "Huobi",
    "0x46705dfff24256421a05d056c29e81bdc09723b8": "Huobi",
    "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c": "Gate.io",
    "0xd793281182a0e3e023116004778f45c29fc14f19": "Gate.io",
    "0xc882b111a75c0c657fc507c04fbfcd2cc984f071": "Gate.io",
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe": "Gate.io",
}

# Known bridge addresses
KNOWN_BRIDGES: Dict[str, str] = {
    "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf": "Polygon Bridge",
    "0xa0c68c638235ee32657e8f720a23cec1bfc77c77": "Polygon Bridge",
    "0x8484ef722627bf18ca5ae6bcf031c23e6e922b30": "Arbitrum Bridge",
    "0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f": "Arbitrum Bridge",
    "0xcee284f754e854890e311e3280b767f80797180d": "Arbitrum Bridge",
    "0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "Optimism Bridge",
    "0x467194771dae2967aef3ecbedd3bf9a310c76c65": "Optimism Bridge",
    "0x3154cf16ccdb4c6d922629664174b904d80f2c35": "Base Bridge",
    "0x49048044d57e1c92a77f79988d21fa8faf74e97e": "Base Bridge",
}


@dataclass
class HolderBubble:
    """Data for a single holder bubble in the visualization."""
    address: str
    balance: float
    percentage: float
    wallet_type: WalletType
    wallet_label: Optional[str]  # e.g., "Binance", "Uniswap V3"
    rank: int
    log_balance: float  # For better size scaling


@dataclass
class BubbleMapData:
    """Complete data for bubble map visualization."""
    holders: List[HolderBubble]
    total_supply: float
    token_symbol: str
    whale_count: int
    exchange_count: int
    contract_count: int
    eoa_count: int


class BubbleMapQueries:
    """
    Queries for generating bubble map visualization data.

    This class provides methods to fetch holder data and classify
    wallet types for interactive bubble visualizations.

    Example usage:
        queries = BubbleMapQueries(subgraph_url="https://api.studio.thegraph.com/query/.../erc20-tracker/v0.0.1")

        # Get bubble map data
        data = queries.get_bubble_map_data(token_address, limit=500)

        # Filter by holder tier
        whales = queries.filter_by_tier(data.holders, "whale")
    """

    def __init__(
        self,
        subgraph_url: str,
        client: Optional[GraphClient] = None
    ):
        """
        Initialize BubbleMapQueries.

        Args:
            subgraph_url: URL of the deployed erc20-tracker subgraph
            client: Optional GraphClient instance (creates new one if not provided)
        """
        self.subgraph_url = subgraph_url
        self.client = client or GraphClient()
        self.erc20_queries = ERC20Queries(subgraph_url=subgraph_url, client=self.client)

    def classify_wallet_type(
        self,
        address: str,
        percentage: float = 0.0,
        is_contract: Optional[bool] = None
    ) -> Tuple[WalletType, Optional[str]]:
        """
        Classify a wallet address into a type.

        Args:
            address: Wallet address (lowercase)
            percentage: Percentage of total supply held
            is_contract: Whether the address is a contract (if known)

        Returns:
            Tuple of (WalletType, optional label string)
        """
        addr_lower = address.lower()

        # Check known exchanges first
        if addr_lower in KNOWN_EXCHANGES:
            return WalletType.EXCHANGE, KNOWN_EXCHANGES[addr_lower]

        # Check known bridges
        if addr_lower in KNOWN_BRIDGES:
            return WalletType.BRIDGE, KNOWN_BRIDGES[addr_lower]

        # Check if it's a whale (>1% of supply)
        if percentage >= 1.0:
            return WalletType.WHALE, None

        # If we know it's a contract
        if is_contract is True:
            return WalletType.CONTRACT, None

        # Default to EOA (most addresses are EOAs)
        return WalletType.EOA, None

    def get_bubble_map_data(
        self,
        token_address: str,
        limit: int = 500,
        min_balance_pct: float = 0.0
    ) -> Optional[BubbleMapData]:
        """
        Get complete bubble map data for a token.

        Args:
            token_address: Token contract address
            limit: Maximum number of holders to include
            min_balance_pct: Minimum percentage of supply to include

        Returns:
            BubbleMapData or None if no data
        """
        # Get token info
        token_info = self.erc20_queries.get_token_info(token_address)
        if not token_info:
            return None

        total_supply = float(token_info.total_supply)
        token_symbol = token_info.symbol

        # Get holder balances
        df = self.erc20_queries.get_token_balances(
            token_address=token_address,
            limit=limit
        )

        if df.empty:
            return None

        # Calculate percentages
        df["percentage"] = (df["balance"] / total_supply * 100) if total_supply > 0 else 0

        # Filter by minimum percentage if specified
        if min_balance_pct > 0:
            df = df[df["percentage"] >= min_balance_pct]

        if df.empty:
            return None

        # Sort by balance and assign ranks
        df = df.sort_values("balance", ascending=False).reset_index(drop=True)
        df["rank"] = df.index + 1

        # Calculate log balance for better size scaling
        df["log_balance"] = np.log10(df["balance"].clip(lower=1e-18) + 1)

        # Classify wallet types and build holder bubbles
        holders = []
        whale_count = 0
        exchange_count = 0
        contract_count = 0
        eoa_count = 0

        for _, row in df.iterrows():
            wallet_type, label = self.classify_wallet_type(
                row["account"],
                row["percentage"]
            )

            holder = HolderBubble(
                address=row["account"],
                balance=row["balance"],
                percentage=row["percentage"],
                wallet_type=wallet_type,
                wallet_label=label,
                rank=row["rank"],
                log_balance=row["log_balance"]
            )
            holders.append(holder)

            # Count by type
            if wallet_type == WalletType.WHALE:
                whale_count += 1
            elif wallet_type == WalletType.EXCHANGE:
                exchange_count += 1
            elif wallet_type == WalletType.CONTRACT or wallet_type == WalletType.BRIDGE:
                contract_count += 1
            else:
                eoa_count += 1

        return BubbleMapData(
            holders=holders,
            total_supply=total_supply,
            token_symbol=token_symbol,
            whale_count=whale_count,
            exchange_count=exchange_count,
            contract_count=contract_count,
            eoa_count=eoa_count
        )

    def filter_by_tier(
        self,
        holders: List[HolderBubble],
        tier: str
    ) -> List[HolderBubble]:
        """
        Filter holders by tier (zoom level).

        Args:
            holders: List of HolderBubble objects
            tier: One of "whale" (>1%), "dolphin" (0.1-1%), "fish" (<0.1%), or "all"

        Returns:
            Filtered list of holders
        """
        if tier == "all":
            return holders

        tier_filters = {
            "whale": lambda h: h.percentage >= 1.0,
            "dolphin": lambda h: 0.1 <= h.percentage < 1.0,
            "fish": lambda h: h.percentage < 0.1,
        }

        filter_fn = tier_filters.get(tier)
        if filter_fn:
            return [h for h in holders if filter_fn(h)]
        return holders

    def filter_by_wallet_type(
        self,
        holders: List[HolderBubble],
        wallet_types: List[WalletType]
    ) -> List[HolderBubble]:
        """
        Filter holders by wallet type.

        Args:
            holders: List of HolderBubble objects
            wallet_types: List of WalletType to include

        Returns:
            Filtered list of holders
        """
        return [h for h in holders if h.wallet_type in wallet_types]

    def get_holder_transfers(
        self,
        token_address: str,
        holder_addresses: List[str],
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        limit: int = 500
    ) -> pd.DataFrame:
        """
        Get transfers between tracked holders for network graph.

        Args:
            token_address: Token contract address
            holder_addresses: List of holder addresses
            from_block: Starting block (optional)
            to_block: Ending block (optional)
            limit: Maximum transfers to return

        Returns:
            DataFrame with transfer records
        """
        holder_set = set(a.lower() for a in holder_addresses)

        # Get all transfers for the token
        transfers = self.erc20_queries.get_transfers(
            token_address=token_address,
            from_block=from_block,
            to_block=to_block,
            limit=limit * 2  # Get more to filter
        )

        if transfers.empty:
            return pd.DataFrame()

        # Filter to only transfers between tracked holders
        transfers["from_lower"] = transfers["from"].str.lower()
        transfers["to_lower"] = transfers["to"].str.lower()

        between_holders = transfers[
            (transfers["from_lower"].isin(holder_set)) &
            (transfers["to_lower"].isin(holder_set))
        ]

        return between_holders.head(limit)

    def build_network_edges(
        self,
        transfers_df: pd.DataFrame
    ) -> List[Dict]:
        """
        Build network edges from transfer data for force-directed graph.

        Args:
            transfers_df: DataFrame with transfer records

        Returns:
            List of edge dictionaries with source, target, weight
        """
        if transfers_df.empty:
            return []

        # Aggregate transfers between pairs
        edges = transfers_df.groupby(["from", "to"]).agg({
            "amount": ["sum", "count"]
        }).reset_index()

        edges.columns = ["source", "target", "total_amount", "transfer_count"]

        return edges.to_dict(orient="records")

    def to_dataframe(self, holders: List[HolderBubble]) -> pd.DataFrame:
        """
        Convert holder bubbles to DataFrame for visualization.

        Args:
            holders: List of HolderBubble objects

        Returns:
            DataFrame ready for Plotly
        """
        records = []
        for h in holders:
            records.append({
                "address": h.address,
                "short_address": format_address(h.address),
                "balance": h.balance,
                "percentage": h.percentage,
                "wallet_type": h.wallet_type.value,
                "wallet_label": h.wallet_label or h.wallet_type.value.upper(),
                "rank": h.rank,
                "log_balance": h.log_balance,
                "size": h.log_balance * 5 + 5,  # Scale for bubble size
            })
        return pd.DataFrame(records)


def format_address(address: str, length: int = 6) -> str:
    """
    Format address for display (shortened form).

    Args:
        address: Full Ethereum address
        length: Number of characters to show on each end

    Returns:
        Shortened address (e.g., "0x1234...5678")
    """
    if len(address) <= length * 2 + 3:
        return address
    return f"{address[:length]}...{address[-length:]}"


def get_wallet_type_color(wallet_type: WalletType) -> str:
    """
    Get color for wallet type visualization.

    Args:
        wallet_type: WalletType enum value

    Returns:
        Hex color string
    """
    colors = {
        WalletType.EOA: "#2ecc71",  # Green
        WalletType.CONTRACT: "#3498db",  # Blue
        WalletType.EXCHANGE: "#e67e22",  # Orange
        WalletType.BRIDGE: "#9b59b6",  # Purple
        WalletType.WHALE: "#e74c3c",  # Red
        WalletType.UNKNOWN: "#95a5a6",  # Gray
    }
    return colors.get(wallet_type, "#95a5a6")


def get_tier_from_percentage(percentage: float) -> str:
    """
    Get holder tier from percentage of supply.

    Args:
        percentage: Percentage of total supply

    Returns:
        Tier string: "whale", "dolphin", or "fish"
    """
    if percentage >= 1.0:
        return "whale"
    elif percentage >= 0.1:
        return "dolphin"
    else:
        return "fish"

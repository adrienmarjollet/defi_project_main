"""
Solana Queries Module

High-level query functions for Solana blockchain data.
Combines Helius API with solana-py for comprehensive data access.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .helius_client import (
    HeliusClient,
    HeliusNetwork,
    TokenBalance,
    TokenMetadata,
    Transaction,
    LAMPORTS_PER_SOL,
)

logger = logging.getLogger(__name__)


@dataclass
class WalletSummary:
    """Summary of a wallet's holdings"""
    address: str
    sol_balance: Decimal
    token_count: int
    tokens: List[TokenBalance]
    total_value_usd: Optional[Decimal] = None


@dataclass
class TokenHolderInfo:
    """Token holder information"""
    address: str
    balance: Decimal
    percentage: float
    rank: int


class SolanaQueries:
    """
    High-level query interface for Solana blockchain data.

    Provides convenient methods for common DeFi operations:
    - Wallet analysis
    - Token holder distribution
    - Transaction history
    - Token metadata

    Example usage:
        queries = SolanaQueries()

        # Get wallet summary
        summary = queries.get_wallet_summary("wallet_address")
        print(f"SOL: {summary.sol_balance}, Tokens: {summary.token_count}")

        # Get top token holders
        holders = queries.get_token_holders("token_mint", limit=100)

        # Get transaction history as DataFrame
        df = queries.get_transaction_history("wallet_address", limit=50)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        network: HeliusNetwork = HeliusNetwork.MAINNET,
    ):
        """
        Initialize Solana queries.

        Args:
            api_key: Helius API key (loads from env if not provided)
            network: Solana network to use
        """
        self.client = HeliusClient(api_key=api_key, network=network)
        self.network = network

    # ========== Wallet Analysis ==========

    def get_wallet_summary(self, address: str) -> WalletSummary:
        """
        Get complete wallet summary including SOL and all tokens.

        Args:
            address: Wallet address

        Returns:
            WalletSummary with all holdings
        """
        sol_balance = self.client.get_sol_balance(address)
        tokens = self.client.get_token_balances(address)

        return WalletSummary(
            address=address,
            sol_balance=sol_balance,
            token_count=len(tokens),
            tokens=tokens,
        )

    def get_wallet_balances_df(self, address: str) -> pd.DataFrame:
        """
        Get wallet token balances as a DataFrame.

        Args:
            address: Wallet address

        Returns:
            DataFrame with columns: mint, amount, decimals, ui_amount, symbol, name
        """
        tokens = self.client.get_token_balances(address)

        if not tokens:
            return pd.DataFrame(columns=["mint", "amount", "decimals", "ui_amount"])

        records = [
            {
                "mint": t.mint,
                "amount": t.amount,
                "decimals": t.decimals,
                "ui_amount": t.ui_amount,
                "symbol": t.symbol,
                "name": t.name,
            }
            for t in tokens
        ]

        df = pd.DataFrame(records)
        return df.sort_values("ui_amount", ascending=False)

    def get_multiple_wallet_balances(
        self,
        addresses: List[str],
        token_mint: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get balances for multiple wallets.

        Args:
            addresses: List of wallet addresses
            token_mint: Optional specific token to check (None = SOL)

        Returns:
            DataFrame with address and balance columns
        """
        records = []

        for addr in addresses:
            try:
                if token_mint:
                    balance_info = self.client.get_token_balance(addr, token_mint)
                    balance = balance_info.ui_amount if balance_info else 0
                else:
                    balance = float(self.client.get_sol_balance(addr))

                records.append({
                    "address": addr,
                    "balance": balance,
                })
            except Exception as e:
                logger.warning(f"Failed to get balance for {addr}: {e}")
                records.append({
                    "address": addr,
                    "balance": 0,
                })

        return pd.DataFrame(records)

    # ========== Token Analysis ==========

    def get_token_info(self, mint: str) -> Optional[TokenMetadata]:
        """
        Get token metadata.

        Args:
            mint: Token mint address

        Returns:
            TokenMetadata or None
        """
        return self.client.get_token_metadata(mint)

    def get_token_supply(self, mint: str) -> Dict[str, Any]:
        """
        Get token supply information.

        Args:
            mint: Token mint address

        Returns:
            Dict with amount, decimals, uiAmount
        """
        return self.client.get_token_supply(mint)

    def get_token_holders(
        self,
        mint: str,
        limit: int = 100,
    ) -> List[TokenHolderInfo]:
        """
        Get top token holders.

        Args:
            mint: Token mint address
            limit: Maximum holders to return

        Returns:
            List of TokenHolderInfo
        """
        # Get supply for percentage calculation
        supply_info = self.client.get_token_supply(mint)
        total_supply = float(supply_info.get("uiAmount", 0)) or 1

        # Get largest accounts
        accounts = self.client.get_token_largest_accounts(mint, limit=limit)

        holders = []
        for i, acc in enumerate(accounts, 1):
            ui_amount = acc["ui_amount"]
            holders.append(TokenHolderInfo(
                address=acc["address"],
                balance=Decimal(str(ui_amount)),
                percentage=(ui_amount / total_supply) * 100,
                rank=i,
            ))

        return holders

    def get_token_holders_df(self, mint: str, limit: int = 100) -> pd.DataFrame:
        """
        Get top token holders as DataFrame.

        Args:
            mint: Token mint address
            limit: Maximum holders to return

        Returns:
            DataFrame with rank, address, balance, percentage columns
        """
        holders = self.get_token_holders(mint, limit)

        if not holders:
            return pd.DataFrame(columns=["rank", "address", "balance", "percentage"])

        return pd.DataFrame([
            {
                "rank": h.rank,
                "address": h.address,
                "balance": float(h.balance),
                "percentage": h.percentage,
            }
            for h in holders
        ])

    def get_token_concentration(self, mint: str, top_n: int = 10) -> Dict[str, Any]:
        """
        Analyze token holder concentration.

        Args:
            mint: Token mint address
            top_n: Number of top holders to analyze

        Returns:
            Dict with concentration metrics
        """
        holders = self.get_token_holders(mint, limit=top_n)

        if not holders:
            return {
                "top_n": top_n,
                "total_percentage": 0,
                "holders": [],
            }

        total_pct = sum(h.percentage for h in holders)

        return {
            "top_n": top_n,
            "total_percentage": total_pct,
            "average_percentage": total_pct / len(holders),
            "largest_holder_percentage": holders[0].percentage if holders else 0,
            "holders": holders,
        }

    # ========== Transaction Analysis ==========

    def get_transaction_history(
        self,
        address: str,
        limit: int = 100,
        before: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get transaction history as DataFrame.

        Args:
            address: Wallet address
            limit: Maximum transactions
            before: Pagination cursor (signature)

        Returns:
            DataFrame with transaction data
        """
        txs = self.client.get_transactions(address, limit=limit, before=before)

        if not txs:
            return pd.DataFrame(columns=[
                "signature", "slot", "timestamp", "fee", "success", "type", "description"
            ])

        return pd.DataFrame([
            {
                "signature": tx.signature,
                "slot": tx.slot,
                "timestamp": tx.timestamp,
                "fee": tx.fee / LAMPORTS_PER_SOL,  # Convert to SOL
                "success": tx.success,
                "type": tx.type,
                "description": tx.description,
                "source": tx.source,
            }
            for tx in txs
        ])

    def get_transaction_types(self, address: str, limit: int = 500) -> Dict[str, int]:
        """
        Get transaction type distribution for an address.

        Args:
            address: Wallet address
            limit: Number of transactions to analyze

        Returns:
            Dict mapping transaction type to count
        """
        txs = self.client.get_transactions(address, limit=limit)

        type_counts: Dict[str, int] = {}
        for tx in txs:
            tx_type = tx.type
            type_counts[tx_type] = type_counts.get(tx_type, 0) + 1

        return dict(sorted(type_counts.items(), key=lambda x: -x[1]))

    # ========== Blockchain State ==========

    def get_current_slot(self) -> int:
        """Get current slot number."""
        return self.client.get_slot()

    def get_current_block_height(self) -> int:
        """Get current block height."""
        return self.client.get_block_height()

    def get_slot_timestamp(self, slot: int) -> Optional[int]:
        """
        Get timestamp for a slot.

        Args:
            slot: Slot number

        Returns:
            Unix timestamp or None
        """
        return self.client.get_block_time(slot)


# Well-known Solana tokens for reference
KNOWN_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",  # Wrapped SOL
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    "MSOL": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "JITOSOL": "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
}


def create_solana_queries(
    api_key: Optional[str] = None,
    network: str = "mainnet",
) -> SolanaQueries:
    """
    Factory function to create SolanaQueries.

    Args:
        api_key: Optional Helius API key
        network: "mainnet" or "devnet"

    Returns:
        Configured SolanaQueries instance
    """
    net = HeliusNetwork.MAINNET if network == "mainnet" else HeliusNetwork.DEVNET
    return SolanaQueries(api_key=api_key, network=net)


if __name__ == "__main__":
    # Test queries
    logging.basicConfig(level=logging.INFO)

    try:
        queries = SolanaQueries()

        # Test with a known active wallet
        test_wallet = "Ezrf3kUzKoAJ8T6XN38e59zF8HNc7VT6KTrPjKkLedyJ"

        print("Testing wallet summary...")
        summary = queries.get_wallet_summary(test_wallet)
        print(f"Wallet: {summary.address}")
        print(f"SOL Balance: {summary.sol_balance}")
        print(f"Token Count: {summary.token_count}")

        print("\nTesting token holders (BONK)...")
        holders = queries.get_token_holders(KNOWN_TOKENS["BONK"], limit=5)
        for h in holders:
            print(f"  #{h.rank}: {h.address[:8]}... - {h.percentage:.2f}%")

    except Exception as e:
        print(f"Test failed (expected if no API key): {e}")

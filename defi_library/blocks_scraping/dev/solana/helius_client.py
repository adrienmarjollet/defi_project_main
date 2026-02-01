"""
Helius API Client for Solana

Helius provides enhanced Solana RPC and DAS (Digital Asset Standard) APIs.
Free tier: 1M credits/month

Documentation: https://docs.helius.dev/
"""

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import requests

from config import HELIUS_API_KEY
from common.misc import find_project_root_path, load_env_variables

logger = logging.getLogger(__name__)

# Solana constants
LAMPORTS_PER_SOL = 1_000_000_000
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


class HeliusNetwork(Enum):
    """Supported Helius networks"""
    MAINNET = "mainnet"
    DEVNET = "devnet"


@dataclass
class TokenBalance:
    """SPL Token balance"""
    mint: str
    owner: str
    amount: int
    decimals: int
    ui_amount: float
    symbol: Optional[str] = None
    name: Optional[str] = None


@dataclass
class TokenMetadata:
    """Token metadata from Helius"""
    mint: str
    name: str
    symbol: str
    decimals: int
    supply: int
    uri: Optional[str] = None
    image: Optional[str] = None


@dataclass
class Transaction:
    """Parsed transaction"""
    signature: str
    slot: int
    timestamp: int
    fee: int
    success: bool
    type: str
    description: str
    source: Optional[str] = None


class HeliusClient:
    """
    Client for Helius Solana APIs.

    Provides access to:
    - Enhanced RPC (standard Solana RPC with better performance)
    - DAS API (Digital Asset Standard for NFTs and tokens)
    - Parsed transaction history
    - Webhooks (not implemented here)

    Free tier: 1,000,000 credits/month

    Example usage:
        client = HeliusClient()

        # Get SOL balance
        balance = client.get_sol_balance("wallet_address")

        # Get all token balances
        tokens = client.get_token_balances("wallet_address")

        # Get transaction history
        txs = client.get_transactions("wallet_address", limit=10)

        # Get token metadata
        metadata = client.get_token_metadata("token_mint_address")
    """

    # API endpoints
    MAINNET_RPC = "https://mainnet.helius-rpc.com"
    DEVNET_RPC = "https://devnet.helius-rpc.com"
    API_BASE = "https://api.helius.xyz"

    def __init__(
        self,
        api_key: Optional[str] = None,
        network: HeliusNetwork = HeliusNetwork.MAINNET,
    ):
        """
        Initialize Helius client.

        Args:
            api_key: Helius API key. If not provided, loads from environment.
            network: Network to connect to (mainnet or devnet)
        """
        self.root_path = find_project_root_path()

        if api_key:
            self._api_key = api_key
        else:
            try:
                self._api_key = load_env_variables(self.root_path, [HELIUS_API_KEY])[0]
            except Exception as e:
                raise ValueError(
                    "Helius API key not found. Set HELIUS_API_KEY in your .env file. "
                    "Get a free key at https://dev.helius.xyz/"
                ) from e

        self.network = network
        self._rpc_url = self._get_rpc_url()
        self._api_url = f"{self.API_BASE}/v0"

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
        })

        logger.info(f"Helius client initialized for {network.value}")

    def _get_rpc_url(self) -> str:
        """Get RPC URL with API key."""
        base = self.MAINNET_RPC if self.network == HeliusNetwork.MAINNET else self.DEVNET_RPC
        return f"{base}/?api-key={self._api_key}"

    def _rpc_request(
        self,
        method: str,
        params: Optional[List[Any]] = None,
        max_retries: int = 3,
    ) -> Any:
        """
        Make a JSON-RPC request to Helius.

        Args:
            method: RPC method name
            params: Method parameters
            max_retries: Number of retry attempts

        Returns:
            RPC result

        Raises:
            HeliusError: If request fails
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or [],
        }

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self._session.post(
                    self._rpc_url,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()

                data = response.json()

                if "error" in data:
                    raise HeliusError(f"RPC error: {data['error']}")

                return data.get("result")

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = 1.0 * (2 ** attempt)
                    logger.warning(
                        f"RPC request failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)

        raise HeliusError(f"RPC request failed after {max_retries + 1} attempts: {last_error}")

    def _api_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Any:
        """
        Make a REST API request to Helius.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters
            json_data: JSON body for POST requests
            max_retries: Number of retry attempts

        Returns:
            API response data
        """
        url = f"{self._api_url}/{endpoint}"

        # Add API key to params
        if params is None:
            params = {}
        params["api-key"] = self._api_key

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if method == "GET":
                    response = self._session.get(url, params=params, timeout=30)
                else:
                    response = self._session.post(url, params=params, json=json_data, timeout=30)

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = 1.0 * (2 ** attempt)
                    logger.warning(
                        f"API request failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)

        raise HeliusError(f"API request failed after {max_retries + 1} attempts: {last_error}")

    # ========== SOL Balance ==========

    def get_sol_balance(self, address: str) -> Decimal:
        """
        Get SOL balance for an address.

        Args:
            address: Wallet address

        Returns:
            Balance in SOL
        """
        result = self._rpc_request("getBalance", [address])
        lamports = result.get("value", 0)
        return Decimal(lamports) / Decimal(LAMPORTS_PER_SOL)

    def get_sol_balance_lamports(self, address: str) -> int:
        """
        Get SOL balance in lamports.

        Args:
            address: Wallet address

        Returns:
            Balance in lamports
        """
        result = self._rpc_request("getBalance", [address])
        return result.get("value", 0)

    # ========== Token Balances ==========

    def get_token_balances(
        self,
        owner: str,
        include_zero: bool = False,
    ) -> List[TokenBalance]:
        """
        Get all SPL token balances for an owner.

        Args:
            owner: Wallet address
            include_zero: Include tokens with zero balance

        Returns:
            List of TokenBalance objects
        """
        result = self._rpc_request(
            "getTokenAccountsByOwner",
            [
                owner,
                {"programId": SPL_TOKEN_PROGRAM_ID},
                {"encoding": "jsonParsed"}
            ]
        )

        balances = []
        for account in result.get("value", []):
            parsed = account["account"]["data"]["parsed"]["info"]
            amount = int(parsed["tokenAmount"]["amount"])

            if amount == 0 and not include_zero:
                continue

            balances.append(TokenBalance(
                mint=parsed["mint"],
                owner=parsed["owner"],
                amount=amount,
                decimals=parsed["tokenAmount"]["decimals"],
                ui_amount=float(parsed["tokenAmount"]["uiAmount"] or 0),
            ))

        return balances

    def get_token_balance(
        self,
        owner: str,
        mint: str,
    ) -> Optional[TokenBalance]:
        """
        Get balance of a specific token for an owner.

        Args:
            owner: Wallet address
            mint: Token mint address

        Returns:
            TokenBalance or None if not found
        """
        result = self._rpc_request(
            "getTokenAccountsByOwner",
            [
                owner,
                {"mint": mint},
                {"encoding": "jsonParsed"}
            ]
        )

        accounts = result.get("value", [])
        if not accounts:
            return None

        parsed = accounts[0]["account"]["data"]["parsed"]["info"]
        return TokenBalance(
            mint=parsed["mint"],
            owner=parsed["owner"],
            amount=int(parsed["tokenAmount"]["amount"]),
            decimals=parsed["tokenAmount"]["decimals"],
            ui_amount=float(parsed["tokenAmount"]["uiAmount"] or 0),
        )

    # ========== DAS API (Digital Asset Standard) ==========

    def get_assets_by_owner(
        self,
        owner: str,
        page: int = 1,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """
        Get all assets (tokens, NFTs) for an owner using DAS API.

        This is more comprehensive than getTokenAccountsByOwner.

        Args:
            owner: Wallet address
            page: Page number (1-indexed)
            limit: Results per page (max 1000)

        Returns:
            DAS API response with items and metadata
        """
        return self._api_request(
            "addresses/{}/balances".format(owner),
            method="GET",
            params={
                "page": page,
                "limit": limit,
            }
        )

    def get_token_metadata(self, mint: str) -> Optional[TokenMetadata]:
        """
        Get token metadata using DAS API.

        Args:
            mint: Token mint address

        Returns:
            TokenMetadata or None if not found
        """
        try:
            result = self._api_request(f"tokens/metadata", params={"mint": mint})

            if not result:
                return None

            return TokenMetadata(
                mint=result.get("mint", mint),
                name=result.get("name", "Unknown"),
                symbol=result.get("symbol", "???"),
                decimals=result.get("decimals", 0),
                supply=result.get("supply", 0),
                uri=result.get("uri"),
                image=result.get("image"),
            )
        except Exception as e:
            logger.warning(f"Failed to get token metadata for {mint}: {e}")
            return None

    # ========== Transactions ==========

    def get_transactions(
        self,
        address: str,
        limit: int = 100,
        before: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Get parsed transaction history for an address.

        Args:
            address: Wallet address
            limit: Maximum transactions to return
            before: Signature to paginate from

        Returns:
            List of Transaction objects
        """
        params = {"limit": limit}
        if before:
            params["before"] = before

        result = self._api_request(
            f"addresses/{address}/transactions",
            params=params
        )

        transactions = []
        for tx in result:
            transactions.append(Transaction(
                signature=tx.get("signature", ""),
                slot=tx.get("slot", 0),
                timestamp=tx.get("timestamp", 0),
                fee=tx.get("fee", 0),
                success=tx.get("success", True),
                type=tx.get("type", "UNKNOWN"),
                description=tx.get("description", ""),
                source=tx.get("source"),
            ))

        return transactions

    def get_transaction(self, signature: str) -> Dict[str, Any]:
        """
        Get a single parsed transaction.

        Args:
            signature: Transaction signature

        Returns:
            Parsed transaction data
        """
        return self._api_request(f"transactions/{signature}")

    # ========== Enhanced RPC Methods ==========

    def get_slot(self) -> int:
        """Get current slot number."""
        return self._rpc_request("getSlot")

    def get_block_height(self) -> int:
        """Get current block height."""
        return self._rpc_request("getBlockHeight")

    def get_block_time(self, slot: int) -> Optional[int]:
        """
        Get timestamp for a slot.

        Args:
            slot: Slot number

        Returns:
            Unix timestamp or None
        """
        return self._rpc_request("getBlockTime", [slot])

    def get_recent_blockhash(self) -> str:
        """Get recent blockhash for transactions."""
        result = self._rpc_request("getLatestBlockhash")
        return result["value"]["blockhash"]

    def get_token_supply(self, mint: str) -> Dict[str, Any]:
        """
        Get token supply information.

        Args:
            mint: Token mint address

        Returns:
            Supply info with amount, decimals, uiAmount
        """
        result = self._rpc_request("getTokenSupply", [mint])
        return result.get("value", {})

    def get_token_largest_accounts(self, mint: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get largest holders of a token.

        Args:
            mint: Token mint address
            limit: Maximum accounts to return

        Returns:
            List of {address, amount, decimals, uiAmount}
        """
        result = self._rpc_request("getTokenLargestAccounts", [mint])
        accounts = result.get("value", [])[:limit]

        return [
            {
                "address": acc["address"],
                "amount": int(acc["amount"]),
                "decimals": acc["decimals"],
                "ui_amount": float(acc["uiAmount"] or 0),
            }
            for acc in accounts
        ]


class HeliusError(Exception):
    """Raised when a Helius API request fails."""
    pass


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)

    try:
        client = HeliusClient()

        # Test basic RPC
        slot = client.get_slot()
        print(f"Current slot: {slot}")

        # Test with a known wallet (Solana Foundation)
        test_wallet = "Ezrf3kUzKoAJ8T6XN38e59zF8HNc7VT6KTrPjKkLedyJ"
        balance = client.get_sol_balance(test_wallet)
        print(f"Wallet balance: {balance} SOL")

    except Exception as e:
        print(f"Test failed (expected if no API key): {e}")

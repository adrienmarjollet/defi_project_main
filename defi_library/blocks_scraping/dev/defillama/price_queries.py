"""
DeFiLlama API client for free token price data.

DeFiLlama provides free, unlimited API access for DeFi data including:
- Current token prices across all chains
- Historical prices at specific timestamps
- TVL data for protocols
- Yields and stablecoin data

No API key required!

Usage:
    from defillama import DeFiLlamaClient

    # Synchronous usage
    client = DeFiLlamaClient()
    price = client.get_current_price("ethereum", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")

    # Async usage
    async with DeFiLlamaClient() as client:
        price = await client.get_current_price_async("ethereum", "0x...")
"""

import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Chain name mappings for DeFiLlama API
CHAIN_MAPPINGS = {
    "ethereum": "ethereum",
    "eth": "ethereum",
    "mainnet": "ethereum",
    "polygon": "polygon",
    "matic": "polygon",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "base": "base",
    "avalanche": "avax",
    "avax": "avax",
    "bsc": "bsc",
    "binance": "bsc",
    "fantom": "fantom",
    "gnosis": "gnosis",
    "xdai": "gnosis",
}


class DeFiLlamaClient:
    """
    Client for DeFiLlama's free price API.

    Provides both sync and async methods for fetching token prices.
    No API key required - completely free to use.
    """

    BASE_URL = "https://coins.llama.fi"
    PROTOCOLS_URL = "https://api.llama.fi"
    TIMEOUT = 30.0

    def __init__(self):
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=self.TIMEOUT)
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self.TIMEOUT)
        return self._async_client

    async def __aenter__(self) -> "DeFiLlamaClient":
        """Async context manager entry."""
        self._async_client = httpx.AsyncClient(timeout=self.TIMEOUT)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def close(self) -> None:
        """Close sync client."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    @staticmethod
    def _normalize_chain(chain: str) -> str:
        """Normalize chain name to DeFiLlama format."""
        return CHAIN_MAPPINGS.get(chain.lower(), chain.lower())

    @staticmethod
    def _normalize_address(address: str) -> str:
        """Normalize address to lowercase."""
        return address.lower()

    def _build_coin_id(self, chain: str, address: str) -> str:
        """Build DeFiLlama coin identifier."""
        chain = self._normalize_chain(chain)
        address = self._normalize_address(address)
        return f"{chain}:{address}"

    # ==================== Synchronous Methods ====================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_current_price(self, chain: str, address: str) -> Optional[float]:
        """
        Get current token price.

        Args:
            chain: Blockchain name (e.g., "ethereum", "polygon", "arbitrum")
            address: Token contract address

        Returns:
            Current price in USD, or None if not found
        """
        coin_id = self._build_coin_id(chain, address)
        url = f"{self.BASE_URL}/prices/current/{coin_id}"

        client = self._get_sync_client()
        response = client.get(url)
        response.raise_for_status()

        data = response.json()
        coin_data = data.get("coins", {}).get(coin_id)

        if coin_data:
            return coin_data.get("price")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_historical_price(
        self, chain: str, address: str, timestamp: int
    ) -> Optional[float]:
        """
        Get historical token price at a specific timestamp.

        Args:
            chain: Blockchain name
            address: Token contract address
            timestamp: Unix timestamp (seconds)

        Returns:
            Price in USD at that timestamp, or None if not found
        """
        coin_id = self._build_coin_id(chain, address)
        url = f"{self.BASE_URL}/prices/historical/{timestamp}/{coin_id}"

        client = self._get_sync_client()
        response = client.get(url)
        response.raise_for_status()

        data = response.json()
        coin_data = data.get("coins", {}).get(coin_id)

        if coin_data:
            return coin_data.get("price")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_prices_batch(
        self, coins: list[tuple[str, str]]
    ) -> dict[str, Optional[float]]:
        """
        Get current prices for multiple tokens in a single request.

        Args:
            coins: List of (chain, address) tuples

        Returns:
            Dict mapping "chain:address" to price (or None)
        """
        coin_ids = [self._build_coin_id(chain, addr) for chain, addr in coins]
        coins_param = ",".join(coin_ids)
        url = f"{self.BASE_URL}/prices/current/{coins_param}"

        client = self._get_sync_client()
        response = client.get(url)
        response.raise_for_status()

        data = response.json()
        coins_data = data.get("coins", {})

        return {
            coin_id: coins_data.get(coin_id, {}).get("price")
            for coin_id in coin_ids
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_token_info(self, chain: str, address: str) -> Optional[dict]:
        """
        Get detailed token information including price, symbol, and confidence.

        Args:
            chain: Blockchain name
            address: Token contract address

        Returns:
            Dict with token info or None if not found
        """
        coin_id = self._build_coin_id(chain, address)
        url = f"{self.BASE_URL}/prices/current/{coin_id}"

        client = self._get_sync_client()
        response = client.get(url)
        response.raise_for_status()

        data = response.json()
        return data.get("coins", {}).get(coin_id)

    # ==================== Async Methods ====================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    async def get_current_price_async(
        self, chain: str, address: str
    ) -> Optional[float]:
        """
        Get current token price (async).

        Args:
            chain: Blockchain name
            address: Token contract address

        Returns:
            Current price in USD, or None if not found
        """
        coin_id = self._build_coin_id(chain, address)
        url = f"{self.BASE_URL}/prices/current/{coin_id}"

        client = self._get_async_client()
        response = await client.get(url)
        response.raise_for_status()

        data = response.json()
        coin_data = data.get("coins", {}).get(coin_id)

        if coin_data:
            return coin_data.get("price")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    async def get_historical_price_async(
        self, chain: str, address: str, timestamp: int
    ) -> Optional[float]:
        """
        Get historical token price at a specific timestamp (async).

        Args:
            chain: Blockchain name
            address: Token contract address
            timestamp: Unix timestamp (seconds)

        Returns:
            Price in USD at that timestamp, or None if not found
        """
        coin_id = self._build_coin_id(chain, address)
        url = f"{self.BASE_URL}/prices/historical/{timestamp}/{coin_id}"

        client = self._get_async_client()
        response = await client.get(url)
        response.raise_for_status()

        data = response.json()
        coin_data = data.get("coins", {}).get(coin_id)

        if coin_data:
            return coin_data.get("price")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    async def get_prices_batch_async(
        self, coins: list[tuple[str, str]]
    ) -> dict[str, Optional[float]]:
        """
        Get current prices for multiple tokens (async).

        Args:
            coins: List of (chain, address) tuples

        Returns:
            Dict mapping "chain:address" to price (or None)
        """
        coin_ids = [self._build_coin_id(chain, addr) for chain, addr in coins]
        coins_param = ",".join(coin_ids)
        url = f"{self.BASE_URL}/prices/current/{coins_param}"

        client = self._get_async_client()
        response = await client.get(url)
        response.raise_for_status()

        data = response.json()
        coins_data = data.get("coins", {})

        return {
            coin_id: coins_data.get(coin_id, {}).get("price")
            for coin_id in coin_ids
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    print("Testing DeFiLlama API client")
    print("-" * 40)

    client = DeFiLlamaClient()

    # Test current price (WETH on Ethereum)
    weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    print(f"Fetching WETH price...")
    price = client.get_current_price("ethereum", weth_address)
    print(f"WETH price: ${price:.2f}" if price else "Price not found")

    # Test batch prices
    print("\nFetching batch prices...")
    coins = [
        ("ethereum", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),  # WETH
        ("ethereum", "0x6982508145454Ce325dDbE47a25d4ec3d2311933"),  # PEPE
    ]
    prices = client.get_prices_batch(coins)
    for coin_id, price in prices.items():
        print(f"  {coin_id}: ${price:.8f}" if price else f"  {coin_id}: Not found")

    # Test token info
    print("\nFetching token info...")
    info = client.get_token_info("ethereum", weth_address)
    if info:
        print(f"  Symbol: {info.get('symbol')}")
        print(f"  Price: ${info.get('price'):.2f}")
        print(f"  Confidence: {info.get('confidence')}")

    client.close()

    # Test async
    async def test_async():
        print("\nTesting async methods...")
        async with DeFiLlamaClient() as async_client:
            price = await async_client.get_current_price_async("ethereum", weth_address)
            print(f"WETH price (async): ${price:.2f}" if price else "Price not found")

    asyncio.run(test_async())
    print("\nAll tests completed!")

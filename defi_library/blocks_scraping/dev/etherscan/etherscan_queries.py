"""
Etherscan API client for Ethereum blockchain data.

Provides methods for querying contract ABIs, account balances,
token information, and block data from Etherscan.
"""

import logging
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import WETH_ADDRESS
from blocks_scraping.dev.web3.web3_queries import Web3Queries

logger = logging.getLogger(__name__)


class EtherscanError(Exception):
    """Custom exception for Etherscan API errors."""

    pass


class EtherScanQueries:
    """
    Client for Etherscan API queries.

    Provides methods to fetch contract data, account balances,
    and token information from Etherscan.
    """

    BASE_URL = "https://api.etherscan.io/api"
    CHAIN_ID = 1  # Ethereum mainnet

    def __init__(
        self,
        api_key: Optional[str] = None,
        rpc_url: Optional[str] = None,
    ):
        """
        Initialize EtherScan client.

        Args:
            api_key: Etherscan API key. If None, loads from environment.
            rpc_url: Ethereum RPC URL. If None, loads from environment.
        """
        # Load settings from environment if not provided
        if api_key is None or rpc_url is None:
            from common.misc import find_project_root_path, load_env_variables
            from config import ETHERSCAN_API_TOKEN, ETH_RPC_URL

            root_path = find_project_root_path()
            if api_key is None:
                api_key = load_env_variables(root_path, [ETHERSCAN_API_TOKEN])[0]
            if rpc_url is None:
                rpc_url = load_env_variables(root_path, [ETH_RPC_URL])[0]

        self._api_key = api_key
        self._rpc_url = rpc_url
        self._client = httpx.Client(timeout=30.0)
        self._web3_queries = Web3Queries(rpc_url)
        self._web3 = self._web3_queries.web3

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()

    def __enter__(self) -> "EtherScanQueries":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _make_request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Make a request to Etherscan API."""
        params["apikey"] = self._api_key
        response = self._client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()

    def _check_response(self, data: dict[str, Any], context: str) -> Any:
        """Check API response and raise on error."""
        if data.get("status") == "1":
            return data["result"]
        raise EtherscanError(f"{context}: {data.get('message', 'Unknown error')}")

    # ==================== API Credit ====================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_etherscan_credit(self) -> str:
        """Get Etherscan API credit/quota information."""
        params = {"module": "stats", "action": "ethsupply"}
        data = self._make_request(params)
        return self._check_response(data, "Error fetching Etherscan credit")

    # ==================== Contract Queries ====================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_contract_abi(self, address: str) -> str:
        """
        Fetch contract ABI from Etherscan.

        Args:
            address: Contract address

        Returns:
            Contract ABI as JSON string
        """
        params = {
            "chainid": self.CHAIN_ID,
            "module": "contract",
            "action": "getabi",
            "address": address,
        }
        data = self._make_request(params)
        return self._check_response(data, f"Error fetching ABI for {address}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_contract_creator_hash(self, address: str) -> list[dict[str, str]]:
        """
        Get contract creation information.

        Args:
            address: Contract address

        Returns:
            List with contract creator address and creation tx hash
        """
        params = {
            "chainid": self.CHAIN_ID,
            "module": "contract",
            "action": "getcontractcreation",
            "contractaddresses": address,
        }
        data = self._make_request(params)
        return self._check_response(data, f"Error fetching creator for {address}")

    # ==================== Block Queries ====================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_block_number_from_timestamp(self, timestamp: int) -> str:
        """
        Get block number for a given timestamp.

        Args:
            timestamp: Unix timestamp in seconds

        Returns:
            Block number as string
        """
        params = {
            "chainid": self.CHAIN_ID,
            "module": "block",
            "action": "getblocknobytime",
            "timestamp": timestamp,
            "closest": "before",
        }
        data = self._make_request(params)
        return self._check_response(
            data, f"Error fetching block for timestamp {timestamp}"
        )

    # ==================== Token Queries ====================

    def get_token_decimals(self, contract_address: str) -> int:
        """
        Get token decimals via Web3.

        Args:
            contract_address: Token contract address

        Returns:
            Number of decimals
        """
        abi = self.get_contract_abi(contract_address)
        contract = self._web3_queries.get_contract(contract_address, abi)
        return self._web3_queries.call_contract_function(contract, "decimals")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_eth_price(self) -> str:
        """
        Get current ETH price in USD.

        Returns:
            ETH price as string
        """
        params = {
            "chainid": self.CHAIN_ID,
            "module": "stats",
            "action": "ethprice",
        }
        data = self._make_request(params)
        result = self._check_response(data, "Error fetching ETH price")
        return result["ethusd"]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_eth_balance(self, address: str, fiat: bool = False) -> float:
        """
        Get ETH balance for an address.

        Args:
            address: Ethereum address
            fiat: If True, return balance in USD

        Returns:
            Balance in Wei or USD
        """
        params = {
            "chainid": self.CHAIN_ID,
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
        }
        data = self._make_request(params)
        result = self._check_response(data, f"Error fetching balance for {address}")
        balance = float(result)

        if fiat:
            eth_price = float(self.get_eth_price())
            return balance * eth_price
        return balance

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_eth_balances(
        self, addresses: list[str], fiat: bool = False
    ) -> dict[str, float]:
        """
        Get ETH balances for multiple addresses.

        Args:
            addresses: List of Ethereum addresses
            fiat: If True, return balances in USD

        Returns:
            Dict mapping address to balance
        """
        addresses_str = ",".join(addresses)
        params = {
            "chainid": self.CHAIN_ID,
            "module": "account",
            "action": "balancemulti",
            "address": addresses_str,
            "tag": "latest",
        }
        data = self._make_request(params)
        result = self._check_response(
            data, f"Error fetching balances for {len(addresses)} addresses"
        )

        balances = {
            item["account"]: float(item["balance"]) for item in result
        }

        if fiat:
            eth_price = float(self.get_eth_price())
            return {addr: bal * eth_price for addr, bal in balances.items()}
        return balances

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_erc20_balance_from_address(
        self, address: str, contract: str
    ) -> float:
        """
        Get ERC20 token balance for an address.

        Args:
            address: Wallet address
            contract: Token contract address

        Returns:
            Token balance (adjusted for decimals)
        """
        params = {
            "chainid": self.CHAIN_ID,
            "module": "account",
            "action": "tokenbalance",
            "contractaddress": contract,
            "address": address,
            "tag": "latest",
        }
        data = self._make_request(params)
        result = self._check_response(
            data, f"Error fetching token balance for {address}"
        )

        raw_balance = float(result)
        if contract == WETH_ADDRESS:
            return raw_balance

        token_decimals = self.get_token_decimals(contract)
        return raw_balance / (10**token_decimals)

    def get_token_value(
        self, pool_address: str, contract: str, fiat: bool = False
    ) -> float:
        """
        Calculate token value based on pool reserves.

        Args:
            pool_address: Liquidity pool address
            contract: Token contract address
            fiat: If True, return value in USD

        Returns:
            Token value in ETH or USD
        """
        weth_amount = self.get_erc20_balance_from_address(pool_address, WETH_ADDRESS)
        token_amount = self.get_erc20_balance_from_address(pool_address, contract)
        value_eth_per_token = float(weth_amount) / float(token_amount)

        if fiat:
            eth_price = float(self.get_eth_price())
            return value_eth_per_token * eth_price
        return value_eth_per_token

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    def get_token_total_supply(self, contract_address: str) -> float:
        """
        Get total supply of a token.

        Args:
            contract_address: Token contract address

        Returns:
            Total supply (adjusted for decimals)
        """
        params = {
            "chainid": self.CHAIN_ID,
            "module": "stats",
            "action": "tokensupply",
            "contractaddress": contract_address,
        }
        data = self._make_request(params)
        result = self._check_response(
            data, f"Error fetching total supply for {contract_address}"
        )

        raw_supply = float(result)
        decimals = self.get_token_decimals(contract_address)
        return raw_supply / (10**decimals)

    def get_token_diluted_marketcap(
        self, pool_address: str, contract_address: str
    ) -> float:
        """
        Calculate fully diluted market cap.

        Args:
            pool_address: Liquidity pool address for price
            contract_address: Token contract address

        Returns:
            Fully diluted market cap in USD
        """
        token_price = self.get_token_value(pool_address, contract_address, fiat=True)
        total_supply = self.get_token_total_supply(contract_address)
        return token_price * total_supply


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Testing EtherScanQueries")
    print("-" * 40)

    with EtherScanQueries() as client:
        # Test token value
        pool_pepe = "0xA43fe16908251ee70EF74718545e4FE6C5cCEc9f"
        pepe_address = "0x6982508145454Ce325dDbE47a25d4ec3d2311933"

        print("\nFetching PEPE token value...")
        token_value = client.get_token_value(pool_pepe, pepe_address)
        print(f"Token value (ETH): {token_value:.12f}")

        token_value_usd = client.get_token_value(pool_pepe, pepe_address, fiat=True)
        print(f"Token value (USD): ${token_value_usd:.12f}")

        print("\nFetching PEPE total supply...")
        total_supply = client.get_token_total_supply(pepe_address)
        print(f"Total supply: {total_supply:,.0f}")

        print("\nFetching PEPE diluted market cap...")
        mcap = client.get_token_diluted_marketcap(pool_pepe, pepe_address)
        print(f"Market cap: ${mcap:,.2f}")

    print("\nAll tests completed!")

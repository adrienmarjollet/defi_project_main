import sys
import time
import logging
import requests
from decimal import Decimal
from functools import wraps

# dev imports
from config import ETHERSCAN_API_TOKEN, ETH_RPC_URL, WETH_ADDRESS

from common.misc import find_project_root_path, load_env_variables

from blocks_scraping.dev.web3.web3_queries import Web3Queries

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


class EtherScanQueries:
    def __init__(self):
        self.root_path = find_project_root_path()
        self._ethscan_token = load_env_variables(self.root_path, [ETHERSCAN_API_TOKEN])[
            0
        ]

        self._eth_url_rpc = load_env_variables(self.root_path, [ETH_RPC_URL])[0]

        self._web3_queries = Web3Queries(self._eth_url_rpc)
        self._web3 = self._web3_queries.web3

    # related to your API key tier

    @retry_on_failure()
    def get_etherscan_credit(self):
        url = f"https://api.etherscan.io/api?module=stats&action=ethsupply&apikey={self._ethscan_token}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return data["result"]
        else:
            raise Exception(
                f"Error fetching Etherscan credit: {data['message']} via etherscan for get_etherscan_credit method"
            )

    ## CONTRACTS QUERIES

    @retry_on_failure()
    def get_contract_abi(self, address) -> str:
        url = f"https://api.etherscan.io/api?chainid=1&module=contract&action=getabi&address={address}&apikey={self._ethscan_token}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return data["result"]
        else:
            raise Exception(
                f"Error fetching ABI: {data['message']} for address: {address} via etherscan for get_contract_abi method"
            )

    @retry_on_failure()
    def get_contract_creator_hash(self, address):
        # TODO: this can be very useful, especially the creation tx hash
        url = (
            f"https://api.etherscan.io/api?chainid=1&module=contract&action=getcontractcreation"
            f"&contractaddresses={address}&apikey={self._ethscan_token}"
        )
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return data["result"]
        else:
            raise Exception(
                f"Error fetching contract creator hash: {data['message']} for address: {address} via etherscan for get_contract_creator_hash method"
            )

    # BLOCKS ENDPOINTS

    @retry_on_failure()
    def get_block_number_from_timestamp(self, timestamp: int):
        """Get the block number for a given timestamp (Unix in seconds)"""
        url = (
            f"https://api.etherscan.io/api?chainid=1&module=block&action=getblocknobytime"
            f"&timestamp={timestamp}&closest=before&apikey={self._ethscan_token}"
        )
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return data["result"]
        else:
            raise Exception(
                f"Error fetching block number: {data['message']} for timestamp: {timestamp} via etherscan for get_block_number_from_timestamp method"
            )

    #############
    # TOKENS
    #############

    def get_token_decimals(self, contract_address) -> int:
        # TODO improve the performance of this by including it in the database
        abi = self.get_contract_abi(contract_address)
        contract = self._web3_queries.get_contract(contract_address, abi)
        return self._web3_queries.call_contract_function(contract, "decimals")

    @retry_on_failure()
    def get_eth_price(self):
        url = f"https://api.etherscan.io/api?chainid=1&module=stats&action=ethprice&apikey={self._ethscan_token}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return data["result"]["ethusd"]
        else:
            raise Exception(
                f"Error fetching ETH price: {data['message']} via etherscan for get_eth_price method"
            )

    @retry_on_failure()
    def get_eth_balance(self, address, fiat=False):
        """
        Get the ETH balance for a given address.
        """
        url = f"https://api.etherscan.io/api?chainid=1&module=account&action=balance&address={address}&tag=latest&apikey={self._ethscan_token}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            if fiat:
                eth_price = Decimal(str(self.get_eth_price()))
                return Decimal(str(data["result"])) * eth_price
            else:
                return Decimal(str(data["result"]))

    @retry_on_failure()
    def get_eth_balances(self, addresses, fiat=False):
        # TODO: ADAPT THIS FUNCTION FOR A LIST OF ADDRESSES INSTEAD
        """
        Get the ETH balances for a list of addresses.
        """
        addresses_str = ",".join(addresses)
        url = (
            f"https://api.etherscan.io/api?chainid=1&module=account&action=balancemulti"
            f"&address={addresses_str}&tag=latest&apikey={self._ethscan_token}"
        )
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            balances = {
                address: Decimal(str(balance["balance"]))
                for address, balance in zip(addresses, data["result"])
            }
            if fiat:
                eth_price = Decimal(str(self.get_eth_price()))
                return {
                    address: balance * eth_price
                    for address, balance in balances.items()
                }
            else:
                return balances
        else:
            raise Exception(
                f"Error fetching balances: {data['message']} for addresses: {addresses} via etherscan for get_eth_balances method"
            )

    @retry_on_failure()
    def get_erc20_balance_from_address(self, address, contract):
        url = (
            f"https://api.etherscan.io/api?chainid=1&module=account&action=tokenbalance"
            f"&contractaddress={contract}&address={address}&tag=latest&apikey={self._ethscan_token}"
        )
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            if address == WETH_ADDRESS:
                return Decimal(str(data["result"]))
            else:
                token_decimal = self.get_token_decimals(address)
                return Decimal(str(data["result"])) / (
                    Decimal(10) ** token_decimal
                )  # check what is faster between web3 lib conversation and this one
        else:
            raise Exception(
                f"Error fetching balance: {data['message']} for address: {address} via etherscan for get_erc20_balance method"
            )

    def get_token_value(self, pool_address, contract, fiat=False):
        weth_amount = self.get_erc20_balance_from_address(pool_address, WETH_ADDRESS)
        # self.get_erc20_value(pool_address)
        print("weth_amount:", weth_amount)
        token_amount = self.get_erc20_balance_from_address(pool_address, contract)
        print("token_amount:", token_amount)
        # get price per eth
        value_eth_per_token = Decimal(str(weth_amount)) / Decimal(str(token_amount))
        if fiat:
            eth_price = Decimal(str(self.get_eth_price()))
            return value_eth_per_token * eth_price
        return value_eth_per_token

    @retry_on_failure()
    def get_token_total_supply(self, contract_address):
        """Get the total supply of a token"""
        url = f"https://api.etherscan.io/api?chainid=1&module=stats&action=tokensupply&contractaddress={contract_address}&apikey={self._ethscan_token}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return Decimal(str(data["result"])) / (
                Decimal(10) ** self.get_token_decimals(contract_address)
            )
        else:
            raise Exception(
                f"Error fetching total supply: {data['message']} for contract address: {contract_address} via etherscan for get_token_total_supply method"
            )

    def get_token_diluted_marketcap(self, pool_address, contract_address):
        token_price = self.get_token_value(pool_address, contract_address, fiat=True)
        total_supply = self.get_token_total_supply(contract_address)

        return token_price * total_supply

    ###########
    # LOGS  ###
    ###########

    # TODO   ADD LOGS QUERIES


if __name__ == "__main__":
    print("Testing the functions in etherscan_queries.py")
    ethscan_queries = EtherScanQueries()
    print("---------------------------------")
    print("get_token_value")
    pool_pepe = "0xA43fe16908251ee70EF74718545e4FE6C5cCEc9f"
    pepe_address = "0x6982508145454Ce325dDbE47a25d4ec3d2311933"
    token_value = ethscan_queries.get_token_value(pool_pepe, pepe_address)
    print("token_value:", token_value)
    token_value_usd = ethscan_queries.get_token_value(
        pool_pepe, pepe_address, fiat=True
    )
    print("token_value_usd:", token_value_usd)

    print("---------------------------------")
    print("token total supply")
    total_supply = ethscan_queries.get_token_total_supply(
        "0x6982508145454Ce325dDbE47a25d4ec3d2311933"
    )
    print("total_supply:", total_supply)
    print("---------------------------------")
    print("get_token_diluted_marketcap")
    diluted_marketcap = ethscan_queries.get_token_diluted_marketcap(
        "0xA43fe16908251ee70EF74718545e4FE6C5cCEc9f",
        "0x6982508145454Ce325dDbE47a25d4ec3d2311933",
    )
    print("diluted_marketcap:", diluted_marketcap)
    sys.exit()
    print("---------------------------------")
    print("get_contract_abi")
    abi = ethscan_queries.get_contract_abi(
        "0x6982508145454Ce325dDbE47a25d4ec3d2311933"
    )  # pepe on eth
    print("abi fetched OK" if abi else "abi not fetched KO")
    print("get_token_decimals")
    decimals = ethscan_queries.get_token_decimals(
        "0x6982508145454Ce325dDbE47a25d4ec3d2311933"
    )  # pepe on eth
    print("decimals:", decimals)
    print(type(decimals))
    sys.exit()
    print("---------------------------------")
    print("etherscan credit usage")
    credit = ethscan_queries.get_etherscan_credit()
    print("credit:", credit)
    print("get_erc20_balance")
    address = "0x6b175474e89094c44da98b954eedeac495271d0f"
    balance = ethscan_queries.get_erc20_balance(address)
    print("balance:", balance)
    print("---------------------------------")
    print("get_eth_price")
    eth_price = ethscan_queries.get_eth_price()
    print("eth_price:", eth_price)
    print("get_token_value")
    pool_address = "0x7C706586679Af2BA6D1A9fC2DA9C6aF59883fdD3"  # SPX/WETH POOL
    contract = "0xE0f63A424a4439cBE457D80E4f4b51aD25b2c56C"  # SPX TOKEN
    token_value = ethscan_queries.get_token_value(pool_address, contract)
    print("token_value:", token_value)

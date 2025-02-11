import requests

# dev imports
from config import ETHERSCAN_API_TOKEN, WETH_ADDRESS

from common.misc import find_project_root_path, load_env_variables


class EtherScanQueries:
    def __init__(self):
        print(ETHERSCAN_API_TOKEN)

        self.root_path = find_project_root_path()
        self._ethscan_token = load_env_variables(self.root_path, [ETHERSCAN_API_TOKEN])[
            0
        ]

        # self._web3_queries = Web3Queries(self._rpc_url)
        # self._web3 = self._web3_queries.web3

    ## CONTRACTS QUERIES

    def get_contract_abi(self, address):
        url = f"https://api.etherscan.io/api?chainid=1&module=contract&action=getabi&address={address}&apikey={self._ethscan_token}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return data["result"]
        else:
            raise Exception(
                f"Error fetching ABI: {data['message']} for address: {address} via etherscan for get_contract_abi method"
            )

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

    # TOKEN
    def get_erc20_balance_from_address(self, address, contract):
        url = (
            f"https://api.etherscan.io/api?chainid=1&module=account&action=tokenbalance"
            f"&contractaddress={contract}&address={address}&tag=latest&apikey={self._ethscan_token}"
        )
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return float(data["result"]) / 10**18
        else:
            raise Exception(
                f"Error fetching token balance: {data['message']} for address: {address} and contract: {contract} via etherscan for get_erc20_balance_from_address method"
            )

    # def get_token_value(self, pool_address, address, fiat=False):
    #     weth_amount = self.get_erc20_value(WETH_ADDRESS)
    #     # TODO

    #     return None

    def get_erc20_value(self, address, fiat=False):
        """
        Get the ERC20 token balance for a given address.
        """
        url = f"https://api.etherscan.io/api?chainid=1&module=account&action=balance&address={address}&tag=latest&apikey={self._ethscan_token}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            if address == WETH_ADDRESS:
                return float(data["result"])
            return (
                float(data["result"]) / 10**18
            )  # check what is faster between web3 lib conversation and this one
        else:
            raise Exception(
                f"Error fetching balance: {data['message']} for address: {address} via etherscan for get_erc20_balance method"
            )

    def get_erc20_balance(self, address):
        url = f"https://api.etherscan.io/api?chainid=1&module=account&action=balance&address={address}&tag=latest&apikey={self._ethscan_token}"
        response = requests.get(url)
        data = response.json()
        if data["status"] == "1":
            return data  # TODO
        else:
            raise Exception(
                f"Error fetching balance: {data['message']} for address: {address} via etherscan for get_erc20_balance method"
            )


if __name__ == "__main__":
    print("Testing the functions in etherscan_queries.py")
    print("---------------------------------")
    print("get_erc20_balance")
    ethscan_queries = EtherScanQueries()
    address = "0x6b175474e89094c44da98b954eedeac495271d0f"
    balance = ethscan_queries.get_erc20_balance(address)
    print("balance:", balance)
    print("---------------------------------")

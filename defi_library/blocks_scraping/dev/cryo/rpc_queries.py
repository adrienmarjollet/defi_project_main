import cryo

# typing modules
from typing import List

# dev imports
from config import ETH_RPC_URL, WETH_ADDRESS

from common.misc import find_project_root_path, load_env_variables

from blocks_scraping.dev.web3.web3_queries import Web3Queries

# TODO: improve init, dev fetch_erc20_balances method


class CryoTools:
    def __init__(self):
        self.root_path = find_project_root_path()
        self._rpc_url = load_env_variables(self.root_path, [ETH_RPC_URL])[0]
        self._web3_queries = Web3Queries(self._rpc_url)
        self._web3 = self._web3_queries.web3

    # TODO: adapt for multiple contract and make unittest for several cases
    # TODO generalizable it to several contracts ?
    # TODO: once this is done, unittest it.
    def fetch_erc20_balances(
        self,
        block_range: str,
        l_addresses: List[str],
        l_contracts: List[str],
        format="pandas",
        rps=250,
    ):
        """Fetch ERC-20 token balances for a given contract within a given block range
        Return a pandas DataFrame with the following columns:
        - chain_id
        - block_number, examples: "XX:YY/T"
        - erc20
        - address
        - balance_ether
        """

        # check that block_range is of the form "222:223"
        if ":" not in block_range:
            raise ValueError(f"block_range not valid: {block_range}")
        # check that address is a valid Ethereum address
        for address in l_addresses:
            if not self._web3.is_address(address):
                raise ValueError(f"{address} is not a valid Ethereum address")

        data = cryo.collect(  # loading this might lead to big peak memory due to many columns, check cryo to reduce the columns loaded
            "erc20_balances",
            blocks=[block_range],
            contract=l_contracts,
            address=l_addresses,
            rpc=self._rpc_url,
            output_format=format,
            hex=True,
            requests_per_second=rps,
        )

        # TODO: improve the data saving
        # TODO test cryo features for timestamps in UNIX
        # TODO handle errors
        # dtypes_erc20_balances = {'chain_id': 'UInt32', 'block_number': 'UInt64', 'erc20': 'string', 'address': 'string', 'balance_string': 'string', 'balance_f64': 'float64'}
        data = data[["chain_id", "block_number", "erc20", "address", "balance_string"]]
        # replace NaN values by 0 for column balance_string
        data["balance_string"] = data["balance_string"].fillna(0)

        # parse the balance_string column according to the contract
        decimal = self._web3_queries.get_token_decimals(l_contracts)
        print(f"decimal: {decimal} for contract {l_contracts}")

        if l_contracts == WETH_ADDRESS:  # WETH
            data["balance"] = (
                data["balance_string"]
                .apply(self._web3_queries.convert_balance_to_ether)
                .astype(float)
            )  # needs to be generalized for several contracts
        else:
            data["balance"] = data["balance_string"].astype("float64") / (10**decimal)
        # drop the balance_string column
        data = data.drop("balance_string", axis=1)
        return data
        # TODO: adapt it for several adresees and chec batches, if not -> write a method that does that effectively.

        # # parse the balance_string column according to the contract
        # decimal = self._web3_queries.get_token_decimals(contract)
        # print(f'decimal: {decimal} for contract {contract}')

        # if contract == WETH_ADDRESS: #WETH
        #     data['balance'] = data['balance_string'].apply(self._web3_queries.convert_balance_to_ether).astype(float)# needs to be generalized for several contracts
        # else:
        #     data['balance'] = data['balance_string'].astype('float64') / (10**decimal)
        # #drop the balance_string column
        # data = data.drop('balance_string', axis=1)
        # return data

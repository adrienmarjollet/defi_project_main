import logging
import sqlite3
import os
from web3 import Web3

# dev imports
from config import ABI_STANDARD_ERC20, ETH_RPC_URL

from common.misc import find_project_root_path, load_env_variables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: use sqlite with decorators for the functions ?


class Web3Queries:
    def __init__(self, provider_url=None):
        logger.info("Initializing Web3Queries")

        self.root_path = find_project_root_path()

        if provider_url is not None:
            logger.info(f"Using provided provider URL: {provider_url}")
            try:
                self.web3 = Web3(Web3.HTTPProvider(provider_url))
                if not self.web3.is_connected():
                    raise ConnectionError(
                        f"Unable to connect to Ethereum node at {provider_url}"
                    )
                logger.info("Successfully connected to Ethereum node")
            except Exception as e:
                logger.error(
                    f"An error occurred while connecting to the Ethereum node: {e}"
                )
                raise ConnectionError(
                    f"An error occurred while connecting to the Ethereum node: {e}"
                )
        else:
            logger.info("No provider URL provided, loading from environment variables")
            try:
                self._rpc_url = load_env_variables(self.root_path, [ETH_RPC_URL])[0]
                logger.info(
                    f"Using RPC URL from environment variables: {self._rpc_url}"
                )
            except Exception as e:
                logger.error(
                    f"An error occurred while loading environment variables: {e}"
                )
                raise ConnectionError(
                    f"An error occurred while connecting to the Ethereum node: {e}"
                )

        # Initialize SQLite database connection
        self.db_web3_path = os.path.join(
            self.root_path, "data/requests_data/web3/web3_database.db"
        )
        self.conn = sqlite3.connect(self.db_web3_path)
        # Create cache table if it doesn't exist
        self.create_cache_table()

    #################################
    # DB TABLE/ CACHING / GET CACHED
    #################################

    def create_cache_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS contract_cache (
                    contract_address TEXT PRIMARY KEY,
                    abi TEXT,
                    decimals INTEGER
                )
            """)

    def cache_data(self, table_name, data_dict):
        """Cache data in the database"""
        columns = ", ".join(data_dict.keys())
        placeholders = ", ".join("?" * len(data_dict))
        sql = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        with self.conn:
            self.conn.execute(sql, tuple(data_dict.values()))

    def get_cached_data(self, table_name, key_column, key_value):
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT * FROM {table_name} WHERE {key_column} = ?
        """,
            (key_value,),
        )
        row = cursor.fetchone()
        return row if row else None

    ################
    ## BALANCE QUERIES
    ################

    def convert_balance_to_ether(self, balance_str: str):
        """
        Convert balance from Wei to Ether, handling None values.
        """
        return (
            None
            if balance_str is None
            else self.web3.from_wei(int(balance_str), "ether")
        )

    def get_balance(self, address):
        return self.web3.eth.get_balance(address)

    ################
    ## CONTRACT QUERIES
    ################

    def get_contract(self, contract_address, abi):
        return self.web3.eth.contract(address=contract_address, abi=abi)

    ################
    ## BLOCK QUERIES
    ################

    def get_latest_block(self):
        return self.web3.eth.get_block("latest")

    def get_block_by_number(self, block_number):
        return self.web3.eth.get_block(block_number)

    def get_transaction_by_hash(self, tx_hash):
        return self.web3.eth.get_transaction(tx_hash)

    def get_token_name(self, contract_address):
        contract = self.get_contract(contract_address, ABI_STANDARD_ERC20)
        return self.call_contract_function(contract, "name")

    def get_token_decimals(self, contract_address):
        contract = self.get_contract(contract_address, ABI_STANDARD_ERC20)
        return self.call_contract_function(contract, "decimals")

    def call_contract_function(self, contract, function_name, *args):
        contract_function = contract.functions[function_name]
        return contract_function(*args).call()

    def send_contract_transaction(self, contract, function_name, transaction, *args):
        contract_function = contract.functions[function_name]
        return contract_function(*args).transact(transaction)

    def get_gas_price(self):
        return self.web3.eth.gas_price

    def estimate_gas(self, transaction):
        return self.web3.eth.estimate_gas(transaction)


if __name__ == "__main__":
    print("test of the methods")
    w3_queries = Web3Queries()
    print("test decimal")
    SPX_address = "0xE0f63A424a4439cBE457D80E4f4b51aD25b2c56C"
    # decimal_spx =

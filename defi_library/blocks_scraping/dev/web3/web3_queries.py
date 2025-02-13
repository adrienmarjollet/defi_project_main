import logging
import os
from web3 import Web3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, ContractCache

# dev imports
from config import ABI_STANDARD_ERC20, ETH_RPC_URL

from common.misc import find_project_root_path, load_env_variables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

        data_dir = os.path.join(self.root_path, "data", "requests_data", "web3")
        os.makedirs(data_dir, exist_ok=True)  # Create directory if it doesn't exist
        self.db_web3_path = os.path.join(data_dir, "web3_database.db")
        # DB connection
        self.engine = create_engine(
            f"sqlite:///{self.db_web3_path}", echo=True
        )  # Create a database engine, echo=True will print SQL queries
        Base.metadata.create_all(
            self.engine
        )  # Creates tables only if they don't exist. If the tables already exist, it does nothing
        Session = sessionmaker(bind=self.engine)  # Creates a session factory
        self.session = Session()  #  Creates a new session for database operations

    #################################
    # DB TABLE/ CACHING / GET CACHED
    #################################

    def cache_data(self, table_name, data_dict):
        """Cache data in the database using SQLAlchemy"""
        if table_name == "contract_cache":
            cache_entry = ContractCache(**data_dict)
            self.session.merge(cache_entry)
            self.session.commit()

    def get_cached_data(self, table_name, key_column, key_value):
        """Get cached data using SQLAlchemy"""
        if table_name == "contract_cache":
            result = (
                self.session.query(ContractCache)
                .filter(getattr(ContractCache, key_column) == key_value)
                .first()
            )
            return result.__dict__ if result else None

    def __del__(self):
        """Cleanup database connections"""
        if hasattr(self, "session"):
            self.session.close()

    def reset_tables(self):
        """Drop and recreate all tables"""
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        logger.warning("Database tables have been reset")

    def reset_all_tables(self):
        """Drop and recreate all tables after user confirmation"""
        confirmation = input("Type 'RESET' to confirm resetting the database tables: ")
        if confirmation == "RESET":
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)
            logger.warning("Database tables have been reset")
        else:
            logger.info("Reset operation cancelled by user")

    ################
    # WEB3 TOOLS
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

    ################
    ## BALANCE QUERIES
    ################

    def get_balance(self, address):
        return self.web3.eth.get_balance(address)

    ################
    ## GENERAL CONTRACT QUERIES
    ################

    def get_contract(self, contract_address, abi):
        return self.web3.eth.contract(address=contract_address, abi=abi)

    def call_contract_function(self, contract, function_name, *args):
        contract_function = contract.functions[function_name]
        return contract_function(*args).call()

    def get_token_decimals(self, contract_address, abi):
        """
        Get token decimals from cache or blockchain,
        and cache the result
        """
        # Try to get from cache first
        cached_data = self.get_cached_data(
            "contract_cache", "contract_address", contract_address
        )
        if cached_data and cached_data.get("decimals") is not None:
            logger.info(f"Found decimals in cache for contract {contract_address}")
            return cached_data["decimals"]

        # If not in cache, fetch from blockchain
        logger.info(
            f"Fetching decimals from blockchain for contract {contract_address}"
        )
        contract = self.get_contract(contract_address, abi or ABI_STANDARD_ERC20)
        decimals = int(self.call_contract_function(contract, "decimals"))

        # Cache the result
        self.cache_data(
            "contract_cache",
            {
                "contract_address": contract_address,
                "abi": abi or ABI_STANDARD_ERC20,
                "decimals": decimals,
            },
        )

        return decimals

    # def get_token_name(self, contract_address, abi = None):
    #     contract = self.get_contract(contract_address, abi or ABI_STANDARD_ERC20)
    #     return self.call_contract_function(contract, "name")

    def get_token_name(self, contract_address, abi=None):
        """
        Get token name from cache or blockchain,
        and cache the result
        """
        # Try to get from cache first
        cached_data = self.get_cached_data(
            "contract_cache", "contract_address", contract_address
        )
        if cached_data and cached_data.get("name") is not None:
            logger.info(f"Found name in cache for contract {contract_address}")
            return cached_data["name"]

        # If not in cache, fetch from blockchain
        logger.info(f"Fetching name from blockchain for contract {contract_address}")
        contract = self.get_contract(contract_address, abi or ABI_STANDARD_ERC20)
        name = self.call_contract_function(contract, "name")

        # Cache the result
        self.cache_data(
            "contract_cache",
            {
                "contract_address": contract_address,
                "abi": abi or ABI_STANDARD_ERC20,
                "name": name,
            },
        )

        return name

    # def send_contract_transaction(self, contract, function_name, transaction, *args):
    #     contract_function = contract.functions[function_name]
    #     return contract_function(*args).transact(transaction)

    ################
    ## BLOCK QUERIES
    ################

    def get_latest_block(self):
        return self.web3.eth.get_block("latest")

    def get_block_by_number(self, block_number):
        return self.web3.eth.get_block(block_number)

    def get_transaction_by_hash(self, tx_hash):
        return self.web3.eth.get_transaction(tx_hash)

    # def get_token_name(self, contract_address):
    #     contract = self.get_contract(contract_address, ABI_STANDARD_ERC20)
    #     return self.call_contract_function(contract, "name")

    # def get_gas_price(self):
    #     return self.web3.eth.gas_price

    # def estimate_gas(self, transaction):
    #     return self.web3.eth.estimate_gas(transaction)


if __name__ == "__main__":
    print("test of the methods")
    w3_queries = Web3Queries()
    print("test decimal")
    SPX_address = "0xE0f63A424a4439cBE457D80E4f4b51aD25b2c56C"
    # TEST HERE IF NEEDED:

import logging
import os
import requests
from web3 import Web3

from collections import defaultdict
from decimal import Decimal
from typing import Optional, Any, Dict, List

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
            # logger.info(f"Using provided provider URL: {provider_url}")
            try:
                self.web3 = Web3(Web3.HTTPProvider(provider_url))
                if not self.web3.is_connected():
                    raise ConnectionError("Unable to connect to Ethereum node.")
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

    def convert_balance_to_ether(self, balance_str: str) -> Optional[Decimal]:
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

    def get_balance(self, address: str) -> int:
        return self.web3.eth.get_balance(address)

    ################
    ## GENERAL CONTRACT QUERIES
    ################

    def get_contract(self, contract_address: str, abi: list) -> Any:
        return self.web3.eth.contract(address=contract_address, abi=abi)

    def call_contract_function(self, contract: Any, function_name: str, *args) -> Any:
        contract_function = contract.functions[function_name]
        return contract_function(*args).call()

    def get_token_decimals(self, contract_address: str, abi: Optional[list] = None) -> int:
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

    def get_token_name(self, contract_address: str, abi: Optional[list] = None) -> str:
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

    ################
    ## BLOCK QUERIES
    ################

    def get_latest_block(self) -> dict:
        return self.web3.eth.get_block("latest")

    def get_block_by_number(self, block_number: int) -> dict:
        return self.web3.eth.get_block(block_number)

    def get_transaction_by_hash(self, tx_hash: str) -> dict:
        return self.web3.eth.get_transaction(tx_hash)

    #############
    ## EXPLO TO GET HOLDERS
    #############

    def get_rpc_response(self, method: str, params: Optional[list] = None) -> dict:
        url = self._rpc_url
        params = params or []
        data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=data)
        return response.json()

    def get_contract_transfers(self, address: str, decimals: int = 18, from_block: Optional[str] = None) -> list:
        """Get logs of Transfer events of a contract"""
        from_block = from_block or "0x0"
        transfer_hash = (
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        )
        params = [
            {"address": address, "fromBlock": from_block, "topics": [transfer_hash]}
        ]
        logs = self.get_rpc_response("eth_getLogs", params)["result"]
        decimals_factor = Decimal("10") ** Decimal("-{}".format(decimals))
        for log in logs:
            log["amount"] = Decimal(str(int(log["data"], 16))) * decimals_factor
            log["from"] = log["topics"][1][0:2] + log["topics"][1][26:]
            log["to"] = log["topics"][2][0:2] + log["topics"][2][26:]
        return logs

    @staticmethod
    def get_balances(transfers: list) -> dict:
        balances = defaultdict(Decimal)
        for t in transfers:
            balances[t["from"]] -= t["amount"]
            balances[t["to"]] += t["amount"]
        bottom_limit = Decimal("0.00000000001")
        balances = {k: balances[k] for k in balances if balances[k] > bottom_limit}
        return balances

    def get_balances_list(self, transfers: list) -> list:
        balances = self.get_balances(transfers)
        balances = [{"address": a, "amount": b} for a, b in balances.items()]
        balances = sorted(balances, key=lambda b: -abs(b["amount"]))
        return balances


if __name__ == "__main__":
    print("test of the methods")
    w3_queries = Web3Queries()
    print("test decimal")
    SPX_address = "0xE0f63A424a4439cBE457D80E4f4b51aD25b2c56C"
    # TEST HERE IF NEEDED:

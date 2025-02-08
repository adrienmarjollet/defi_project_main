from web3 import Web3

# dev imports
from config import ABI_STANDARD_ERC20


class Web3Queries:
    def __init__(self, provider_url):
        try:
            self.web3 = Web3(Web3.HTTPProvider(provider_url))
            if not self.web3.is_connected():
                raise ConnectionError(
                    f"Unable to connect to Ethereum node at {provider_url}"
                )
        except Exception as e:
            raise ConnectionError(
                f"An error occurred while connecting to the Ethereum node: {e}"
            )

    def convert_balance_to_ether(self, balance_str: str):
        """
        Convert balance from Wei to Ether, handling None values.
        """
        return (
            None
            if balance_str is None
            else self.web3.from_wei(int(balance_str), "ether")
        )

    # TODO check the rest of the methods
    def get_latest_block(self):
        return self.web3.eth.get_block("latest")

    def get_block_by_number(self, block_number):
        return self.web3.eth.get_block(block_number)

    def get_transaction_by_hash(self, tx_hash):
        return self.web3.eth.get_transaction(tx_hash)

    def get_balance(self, address):
        return self.web3.eth.get_balance(address)

    def send_transaction(self, transaction):
        return self.web3.eth.send_transaction(transaction)

    def get_contract(self, contract_address, abi):
        return self.web3.eth.contract(address=contract_address, abi=abi)

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

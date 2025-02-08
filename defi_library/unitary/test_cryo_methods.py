import unittest

from unittest.mock import patch

from unittest.mock import MagicMock
from web3 import Web3


from blocks_scraping.dev.cryo.rpc_queries import CryoTools


class TestCryoTools(unittest.TestCase):
    def test_convert_balance_to_ether(self):
        # Test conversion of balance from Wei to Ether
        balance_str = str(10**18)  # 1 Ether in Wei
        result = CryoTools.convert_balance_to_ether(balance_str)
        self.assertEqual(result, Web3.from_wei(1000000000000000000, "ether"))

        # Test handling of None value
        result = CryoTools.convert_balance_to_ether(None)
        self.assertIsNone(result)

    @patch("defi_library.blocks_scraping.dev.cryo.rpc_queries.cryo.collect")
    def test_fetch_erc20_balances(self, mock_cryo_collect):
        # Mock the cryo.collect function to return a dummy DataFrame
        mock_data = MagicMock()
        mock_data[
            ["chain_id", "block_number", "erc20", "address", "balance_string"]
        ] = [
            {
                "chain_id": 1,
                "block_number": 123456,
                "erc20": "0xToken",
                "address": "0xAddress",
                "balance_string": "1000000000000000000",
            }
        ]
        mock_cryo_collect.return_value = mock_data

        # Initialize CryoTools with a dummy RPC URL
        rpc_url = "http://dummy-rpc-url"
        cryo_tools = CryoTools(rpc_url)

        # Call fetch_erc20_balances and assert the result
        block_range = "1000000:1000100"
        address = "0xAddress"
        contract = "0xToken"
        result = cryo_tools.fetch_erc20_balances(block_range, address, contract)

        # Assert that the result is a DataFrame with the expected columns and values
        self.assertEqual(result["chain_id"][0], 1)
        self.assertEqual(result["block_number"][0], 123456)
        self.assertEqual(result["erc20"][0], "0xToken")
        self.assertEqual(result["address"][0], "0xAddress")
        self.assertEqual(
            result["balance_ether"][0], Web3.from_wei(1000000000000000000, "ether")
        )


if __name__ == "__main__":
    unittest.main()

"""Unit tests for EtherScanQueries class."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, Mock
from decimal import Decimal
import importlib.util

# Add the defi_library path to enable imports
DEFI_LIBRARY_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEFI_LIBRARY_PATH)

# Mock the dependencies before importing the module
sys.modules['dotenv'] = MagicMock()
sys.modules['web3'] = MagicMock()

# Mock config module
mock_config = MagicMock()
mock_config.ETHERSCAN_API_TOKEN = 'ETHERSCAN_API_TOKEN'
mock_config.ETH_RPC_URL = 'ETH_RPC_URL'
mock_config.WETH_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
sys.modules['config'] = mock_config

# Mock common.misc module
mock_misc = MagicMock()
mock_misc.find_project_root_path = MagicMock(return_value='/fake/path')
mock_misc.load_env_variables = MagicMock(return_value=['fake_api_key'])
sys.modules['common'] = MagicMock()
sys.modules['common.misc'] = mock_misc

# Mock blocks_scraping.dev.web3.web3_queries module
mock_web3_queries_module = MagicMock()
mock_web3_queries_module.Web3Queries = MagicMock(return_value=MagicMock())
sys.modules['blocks_scraping.dev.web3.web3_queries'] = mock_web3_queries_module

# Load the etherscan_queries module directly from file
etherscan_module_path = os.path.join(
    DEFI_LIBRARY_PATH,
    'blocks_scraping', 'dev', 'etherscan', 'etherscan_queries.py'
)
spec = importlib.util.spec_from_file_location("etherscan_queries", etherscan_module_path)
etherscan_module = importlib.util.module_from_spec(spec)
sys.modules['etherscan_queries'] = etherscan_module
spec.loader.exec_module(etherscan_module)


class TestEtherScanQueries(unittest.TestCase):
    """Test cases for EtherScanQueries methods."""

    def setUp(self):
        """Set up test fixtures with proper mocking."""
        # Reset the mocks for each test
        mock_misc.find_project_root_path.return_value = '/fake/path'
        mock_misc.load_env_variables.return_value = ['fake_api_key']

        # Mock time.sleep to speed up tests with retry decorator
        self.patcher_sleep = patch.object(etherscan_module.time, 'sleep')
        self.mock_sleep = self.patcher_sleep.start()

        # Create a fresh instance for each test
        self.etherscan = etherscan_module.EtherScanQueries()
        self.test_address = '0x6982508145454Ce325dDbE47a25d4ec3d2311933'

    def tearDown(self):
        """Clean up patches."""
        self.patcher_sleep.stop()

    def test_initialization(self):
        """Test that EtherScanQueries initializes correctly with mocked dependencies."""
        mock_misc.find_project_root_path.assert_called()
        self.assertEqual(self.etherscan.root_path, '/fake/path')
        self.assertEqual(self.etherscan._ethscan_token, 'fake_api_key')

    @patch.object(etherscan_module.requests, 'get')
    def test_get_contract_abi_success(self, mock_get):
        """Test get_contract_abi returns ABI when API call succeeds."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': '[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}]}]'
        }
        mock_get.return_value = mock_response

        result = self.etherscan.get_contract_abi(self.test_address)

        self.assertIn('constant', result)
        self.assertIn('name', result)
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        self.assertIn(self.test_address, call_url)
        self.assertIn('module=contract', call_url)
        self.assertIn('action=getabi', call_url)

    @patch.object(etherscan_module.requests, 'get')
    def test_get_contract_abi_error(self, mock_get):
        """Test get_contract_abi raises exception when API returns error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '0',
            'message': 'NOTOK',
            'result': 'Contract source code not verified'
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.etherscan.get_contract_abi(self.test_address)

        self.assertIn('Error fetching ABI', str(context.exception))
        self.assertIn(self.test_address, str(context.exception))

    @patch.object(etherscan_module.requests, 'get')
    def test_get_eth_price_success(self, mock_get):
        """Test get_eth_price returns price when API call succeeds."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': {
                'ethbtc': '0.05432',
                'ethbtc_timestamp': '1234567890',
                'ethusd': '3250.42',
                'ethusd_timestamp': '1234567890'
            }
        }
        mock_get.return_value = mock_response

        result = self.etherscan.get_eth_price()

        self.assertEqual(result, '3250.42')
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        self.assertIn('module=stats', call_url)
        self.assertIn('action=ethprice', call_url)

    @patch.object(etherscan_module.requests, 'get')
    def test_get_eth_price_error(self, mock_get):
        """Test get_eth_price raises exception when API returns error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '0',
            'message': 'NOTOK',
            'result': 'Error'
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.etherscan.get_eth_price()

        self.assertIn('Error fetching ETH price', str(context.exception))

    @patch.object(etherscan_module.requests, 'get')
    def test_get_eth_balance_success(self, mock_get):
        """Test get_eth_balance returns balance as Decimal when API call succeeds."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': '1000000000000000000'  # 1 ETH in wei
        }
        mock_get.return_value = mock_response

        result = self.etherscan.get_eth_balance(self.test_address)

        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal('1000000000000000000'))
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        self.assertIn(self.test_address, call_url)
        self.assertIn('module=account', call_url)
        self.assertIn('action=balance', call_url)

    @patch.object(etherscan_module.requests, 'get')
    def test_get_eth_balance_with_fiat(self, mock_get):
        """Test get_eth_balance returns fiat value when fiat=True."""
        # First call returns balance, second call returns ETH price
        mock_response_balance = MagicMock()
        mock_response_balance.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': '1000000000000000000'  # 1 ETH in wei
        }

        mock_response_price = MagicMock()
        mock_response_price.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': {
                'ethusd': '3000.00'
            }
        }

        mock_get.side_effect = [mock_response_balance, mock_response_price]

        result = self.etherscan.get_eth_balance(self.test_address, fiat=True)

        self.assertIsInstance(result, Decimal)
        # 1 ETH in wei * 3000 USD = 3000000000000000000000
        expected = Decimal('1000000000000000000') * Decimal('3000.00')
        self.assertEqual(result, expected)

    @patch.object(etherscan_module.requests, 'get')
    def test_get_block_number_from_timestamp_success(self, mock_get):
        """Test get_block_number_from_timestamp returns block number on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': '18500000'
        }
        mock_get.return_value = mock_response

        timestamp = 1699000000
        result = self.etherscan.get_block_number_from_timestamp(timestamp)

        self.assertEqual(result, '18500000')
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        self.assertIn(str(timestamp), call_url)
        self.assertIn('module=block', call_url)
        self.assertIn('action=getblocknobytime', call_url)

    @patch.object(etherscan_module.requests, 'get')
    def test_get_block_number_from_timestamp_error(self, mock_get):
        """Test get_block_number_from_timestamp raises exception on error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '0',
            'message': 'NOTOK',
            'result': 'Error'
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.etherscan.get_block_number_from_timestamp(1699000000)

        self.assertIn('Error fetching block number', str(context.exception))

    @patch.object(etherscan_module.requests, 'get')
    def test_get_contract_creator_hash_success(self, mock_get):
        """Test get_contract_creator_hash returns creator info on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': [{
                'contractAddress': self.test_address,
                'contractCreator': '0x1234567890abcdef1234567890abcdef12345678',
                'txHash': '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890'
            }]
        }
        mock_get.return_value = mock_response

        result = self.etherscan.get_contract_creator_hash(self.test_address)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn('contractCreator', result[0])
        self.assertIn('txHash', result[0])

    @patch.object(etherscan_module.requests, 'get')
    def test_get_etherscan_credit_success(self, mock_get):
        """Test get_etherscan_credit returns result on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': '120000000000000000000000000'
        }
        mock_get.return_value = mock_response

        result = self.etherscan.get_etherscan_credit()

        self.assertEqual(result, '120000000000000000000000000')
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        self.assertIn('module=stats', call_url)
        self.assertIn('action=ethsupply', call_url)

    @patch.object(etherscan_module.requests, 'get')
    def test_get_eth_balances_success(self, mock_get):
        """Test get_eth_balances returns balances dict for multiple addresses."""
        addresses = [
            '0x1234567890abcdef1234567890abcdef12345678',
            '0xabcdef1234567890abcdef1234567890abcdef12'
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': [
                {'account': addresses[0], 'balance': '1000000000000000000'},
                {'account': addresses[1], 'balance': '2000000000000000000'}
            ]
        }
        mock_get.return_value = mock_response

        result = self.etherscan.get_eth_balances(addresses)

        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[addresses[0]], Decimal('1000000000000000000'))
        self.assertEqual(result[addresses[1]], Decimal('2000000000000000000'))

    @patch.object(etherscan_module.requests, 'get')
    def test_get_eth_balances_error(self, mock_get):
        """Test get_eth_balances raises exception on API error."""
        addresses = ['0x1234567890abcdef1234567890abcdef12345678']
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '0',
            'message': 'NOTOK',
            'result': 'Error'
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.etherscan.get_eth_balances(addresses)

        self.assertIn('Error fetching balances', str(context.exception))


class TestRetryDecorator(unittest.TestCase):
    """Test cases for the retry_on_failure decorator."""

    def setUp(self):
        """Set up test fixtures with proper mocking."""
        mock_misc.find_project_root_path.return_value = '/fake/path'
        mock_misc.load_env_variables.return_value = ['fake_api_key']

        self.patcher_sleep = patch.object(etherscan_module.time, 'sleep')
        self.mock_sleep = self.patcher_sleep.start()

        self.etherscan = etherscan_module.EtherScanQueries()

    def tearDown(self):
        """Clean up patches."""
        self.patcher_sleep.stop()

    @patch.object(etherscan_module.requests, 'get')
    def test_retry_on_transient_failure(self, mock_get):
        """Test that retry decorator retries on failure and eventually succeeds."""
        # First two calls fail, third succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.json.side_effect = Exception('Connection error')

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': {
                'ethusd': '3250.00'
            }
        }

        mock_get.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ]

        # This should succeed after retries
        result = self.etherscan.get_eth_price()
        self.assertEqual(result, '3250.00')
        self.assertEqual(mock_get.call_count, 3)

    @patch.object(etherscan_module.requests, 'get')
    def test_retry_exhausted_raises_exception(self, mock_get):
        """Test that retry decorator raises exception after max retries."""
        mock_response_fail = MagicMock()
        mock_response_fail.json.side_effect = Exception('Persistent connection error')
        mock_get.return_value = mock_response_fail

        with self.assertRaises(Exception) as context:
            self.etherscan.get_eth_price()

        self.assertIn('Persistent connection error', str(context.exception))
        # Default is 3 retries + 1 initial = 4 total calls
        self.assertEqual(mock_get.call_count, 4)


if __name__ == '__main__':
    unittest.main()

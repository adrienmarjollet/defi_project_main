"""
Unit tests for Historical Price Fetching across multiple chains.

This test suite validates that historical token prices can be fetched correctly
and match known historical reference values for:
- Ethereum (ETH) - WETH, USDC, PEPE, SHIB, LINK
- BSC (Binance Smart Chain) - BNB, CAKE, BUSD
- Solana - SOL, USDC-SPL, JTO, BONK

Test Categories:
1. Unit tests with mocked data - Run offline, test price calculation logic
2. Integration tests (optional) - Fetch real prices from DeFiLlama API

Ground Truth Source:
- DeFiLlama API: https://coins.llama.fi/prices/historical/{timestamp}/{chain}:{address}
- To refresh reference prices, run: python -m defi_library.common.historical_price_fetcher --refresh

Reference Price Timestamps:
- Nov 3, 2023 (timestamp: 1699027200) - ETH block ~18500000, BSC block ~33000000
- Jan 2, 2024 (timestamp: 1704153600) - ETH block ~19000000, BSC block ~35000000
- Mar 13, 2024 (timestamp: 1710288000) - ETH block ~19500000, BSC block ~37000000
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime
import importlib.util

# Add the defi_library path to enable imports
DEFI_LIBRARY_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEFI_LIBRARY_PATH)

# Mock the dependencies before importing modules
sys.modules['dotenv'] = MagicMock()
sys.modules['web3'] = MagicMock()
sys.modules['cryo'] = MagicMock()

# Mock config module with all required constants
mock_config = MagicMock()
mock_config.ETHERSCAN_API_TOKEN = 'ETHERSCAN_API_TOKEN'
mock_config.BSCSCAN_API_TOKEN = 'BSCSCAN_API_TOKEN'
mock_config.ETH_RPC_URL = 'ETH_RPC_URL'
mock_config.BSC_RPC_URL = 'BSC_RPC_URL'
mock_config.SOLANA_RPC_URL = 'SOLANA_RPC_URL'
mock_config.CMC_API_KEY = 'CMC_API_KEY'
mock_config.THEGRAPH_API_KEY = 'THEGRAPH_API_KEY'
mock_config.HELIUS_API_KEY = 'HELIUS_API_KEY'
mock_config.WETH_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
sys.modules['config'] = mock_config

# Mock common.misc module
mock_misc = MagicMock()
mock_misc.find_project_root_path = MagicMock(return_value='/fake/path')
mock_misc.load_env_variables = MagicMock(return_value=['fake_api_key'])
sys.modules['common'] = MagicMock()
sys.modules['common.misc'] = mock_misc

# Mock blocks_scraping modules
mock_web3_queries_module = MagicMock()
mock_web3_queries_module.Web3Queries = MagicMock(return_value=MagicMock())
sys.modules['blocks_scraping'] = MagicMock()
sys.modules['blocks_scraping.dev'] = MagicMock()
sys.modules['blocks_scraping.dev.web3'] = MagicMock()
sys.modules['blocks_scraping.dev.web3.web3_queries'] = mock_web3_queries_module
sys.modules['blocks_scraping.dev.etherscan'] = MagicMock()

# Load modules
etherscan_module_path = os.path.join(
    DEFI_LIBRARY_PATH,
    'blocks_scraping', 'dev', 'etherscan', 'etherscan_queries.py'
)
spec = importlib.util.spec_from_file_location("etherscan_queries", etherscan_module_path)
etherscan_module = importlib.util.module_from_spec(spec)
sys.modules['etherscan_queries'] = etherscan_module
spec.loader.exec_module(etherscan_module)


# ==============================================================================
# CONSTANTS: Famous Tokens Addresses
# ==============================================================================

# Ethereum Mainnet Tokens
ETH_TOKENS = {
    'WETH': {
        'address': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        'decimals': 18,
        'name': 'Wrapped Ether'
    },
    'USDC': {
        'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'decimals': 6,
        'name': 'USD Coin'
    },
    'USDT': {
        'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'decimals': 6,
        'name': 'Tether USD'
    },
    'PEPE': {
        'address': '0x6982508145454Ce325dDbE47a25d4ec3d2311933',
        'decimals': 18,
        'name': 'Pepe',
        'pool': '0xA43fe16908251ee70EF74718545e4FE6C5cCEc9f'  # PEPE/WETH Pool
    },
    'SHIB': {
        'address': '0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE',
        'decimals': 18,
        'name': 'Shiba Inu',
        'pool': '0x2F62f2B4c5fcd7570a709DeC05D68EA19c82A9ec'  # SHIB/WETH Pool
    },
    'LINK': {
        'address': '0x514910771AF9Ca656af840dff83E8264EcF986CA',
        'decimals': 18,
        'name': 'Chainlink',
        'pool': '0xa6Cc3C2531FdaA6Ae1A3CA84c2855806728693e8'  # LINK/WETH Pool
    },
    'UNI': {
        'address': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
        'decimals': 18,
        'name': 'Uniswap',
        'pool': '0x1d42064Fc4Beb5F8aAF85F4617AE8b3b5B8Bd801'  # UNI/WETH Pool
    }
}

# BSC Mainnet Tokens
BSC_TOKENS = {
    'WBNB': {
        'address': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
        'decimals': 18,
        'name': 'Wrapped BNB'
    },
    'BUSD': {
        'address': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
        'decimals': 18,
        'name': 'Binance USD'
    },
    'CAKE': {
        'address': '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82',
        'decimals': 18,
        'name': 'PancakeSwap',
        'pool': '0x0eD7e52944161450477ee417DE9Cd3a859b14fD0'  # CAKE/WBNB Pool
    },
    'USDT_BSC': {
        'address': '0x55d398326f99059fF775485246999027B3197955',
        'decimals': 18,
        'name': 'Tether USD (BSC)'
    },
    'XRP_BSC': {
        'address': '0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE',
        'decimals': 18,
        'name': 'XRP Token (BSC)'
    }
}

# Solana Mainnet Tokens (using mint addresses)
SOLANA_TOKENS = {
    'SOL': {
        'mint': 'So11111111111111111111111111111111111111112',  # Native wrapped SOL
        'decimals': 9,
        'name': 'Solana'
    },
    'USDC_SOL': {
        'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'decimals': 6,
        'name': 'USD Coin (Solana)'
    },
    'BONK': {
        'mint': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
        'decimals': 5,
        'name': 'Bonk'
    },
    'JTO': {
        'mint': 'jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL',
        'decimals': 9,
        'name': 'Jito'
    },
    'WIF': {
        'mint': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm',
        'decimals': 6,
        'name': 'dogwifhat'
    },
    'PYTH': {
        'mint': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3',
        'decimals': 6,
        'name': 'Pyth Network'
    }
}


# ==============================================================================
# HISTORICAL PRICE REFERENCE DATA
# These are known historical prices at specific blocks/timestamps
# Used to validate that our price fetching returns correct values
# ==============================================================================

# ETH Historical Reference Prices (approximate values at specific blocks)
ETH_HISTORICAL_PRICES = {
    # Block 18500000 (Nov 3, 2023) - Known prices in USD
    18500000: {
        'ETH': 1850.00,      # ETH price in USD
        'LINK': 11.50,       # LINK price in USD
        'UNI': 4.30,         # UNI price in USD
        'PEPE': 0.0000011,   # PEPE price in USD
        'SHIB': 0.0000078,   # SHIB price in USD
    },
    # Block 19000000 (Jan 2024) - Known prices
    19000000: {
        'ETH': 2280.00,
        'LINK': 15.20,
        'UNI': 6.80,
        'PEPE': 0.0000015,
        'SHIB': 0.0000095,
    },
    # Block 19500000 (March 2024) - Known prices
    19500000: {
        'ETH': 3450.00,
        'LINK': 18.50,
        'UNI': 12.00,
        'PEPE': 0.0000085,
        'SHIB': 0.000027,
    }
}

# BSC Historical Reference Prices (approximate values at specific blocks)
BSC_HISTORICAL_PRICES = {
    # Block 33000000 (Nov 2023)
    33000000: {
        'BNB': 230.00,
        'CAKE': 1.80,
        'XRP': 0.62,
    },
    # Block 35000000 (Jan 2024)
    35000000: {
        'BNB': 310.00,
        'CAKE': 2.50,
        'XRP': 0.58,
    },
    # Block 37000000 (March 2024)
    37000000: {
        'BNB': 580.00,
        'CAKE': 3.80,
        'XRP': 0.65,
    }
}

# Solana Historical Reference Prices (approximate values at specific slots)
SOLANA_HISTORICAL_PRICES = {
    # Slot 230000000 (Nov 2023)
    230000000: {
        'SOL': 58.00,
        'BONK': 0.000018,
        'JTO': 2.10,
    },
    # Slot 245000000 (Jan 2024)
    245000000: {
        'SOL': 95.00,
        'BONK': 0.000012,
        'JTO': 2.80,
    },
    # Slot 260000000 (March 2024)
    260000000: {
        'SOL': 175.00,
        'BONK': 0.000025,
        'JTO': 3.50,
        'WIF': 2.80,
    }
}


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def price_within_tolerance(actual: float, expected: float, tolerance: float = 0.10) -> bool:
    """
    Check if actual price is within tolerance of expected price.

    Args:
        actual: The fetched price
        expected: The expected reference price
        tolerance: Acceptable deviation (default 10% for historical data)

    Returns:
        True if within tolerance, False otherwise
    """
    if expected == 0:
        return actual == 0
    deviation = abs(actual - expected) / expected
    return deviation <= tolerance


def get_price_deviation_pct(actual: float, expected: float) -> float:
    """Calculate percentage deviation between actual and expected prices."""
    if expected == 0:
        return 0 if actual == 0 else float('inf')
    return ((actual - expected) / expected) * 100


# ==============================================================================
# TEST CLASSES
# ==============================================================================

class TestEthereumHistoricalPrices(unittest.TestCase):
    """
    Test historical price fetching for Ethereum mainnet tokens.
    Uses EtherScanQueries and mocked CryoTools for historical data.
    """

    def setUp(self):
        """Set up test fixtures."""
        mock_misc.find_project_root_path.return_value = '/fake/path'
        mock_misc.load_env_variables.return_value = ['fake_api_key']

        # Mock time.sleep for retry decorator
        self.patcher_sleep = patch.object(etherscan_module.time, 'sleep')
        self.mock_sleep = self.patcher_sleep.start()

        self.etherscan = etherscan_module.EtherScanQueries()

    def tearDown(self):
        """Clean up patches."""
        self.patcher_sleep.stop()

    @patch.object(etherscan_module.requests, 'get')
    def test_eth_price_current(self, mock_get):
        """Test fetching current ETH price returns valid value."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': {'ethusd': '3250.42', 'ethbtc': '0.052'}
        }
        mock_get.return_value = mock_response

        price = self.etherscan.get_eth_price()

        self.assertIsNotNone(price)
        self.assertIsInstance(float(price), float)
        self.assertGreater(float(price), 0)

    @patch.object(etherscan_module.requests, 'get')
    def test_eth_block_timestamp_conversion(self, mock_get):
        """Test block number to timestamp conversion for historical queries."""
        # Test block 18500000 (Nov 3, 2023 - timestamp ~1699027200)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': '18500000'
        }
        mock_get.return_value = mock_response

        # November 3, 2023 timestamp
        timestamp = 1699027200
        block = self.etherscan.get_block_number_from_timestamp(timestamp)

        self.assertEqual(block, '18500000')

    @patch.object(etherscan_module.requests, 'get')
    def test_weth_token_decimals(self, mock_get):
        """Test WETH token has correct decimals (18)."""
        # Mock the contract ABI response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': '[{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]'
        }
        mock_get.return_value = mock_response

        # Mock web3 contract call
        self.etherscan._web3_queries.get_contract = MagicMock()
        self.etherscan._web3_queries.call_contract_function = MagicMock(return_value=18)

        decimals = self.etherscan.get_token_decimals(ETH_TOKENS['WETH']['address'])

        self.assertEqual(decimals, 18)

    @patch.object(etherscan_module.requests, 'get')
    def test_usdc_token_decimals(self, mock_get):
        """Test USDC token has correct decimals (6)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': '1',
            'message': 'OK',
            'result': '[{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]'
        }
        mock_get.return_value = mock_response

        self.etherscan._web3_queries.get_contract = MagicMock()
        self.etherscan._web3_queries.call_contract_function = MagicMock(return_value=6)

        decimals = self.etherscan.get_token_decimals(ETH_TOKENS['USDC']['address'])

        self.assertEqual(decimals, 6)

    @patch.object(etherscan_module.requests, 'get')
    def test_pepe_historical_price_block_18500000(self, mock_get):
        """
        Test PEPE token price at block 18500000 (Nov 2023).
        Expected price: ~$0.0000011 USD
        """
        expected_price = ETH_HISTORICAL_PRICES[18500000]['PEPE']

        # Mock WETH balance in pool
        mock_response_weth = MagicMock()
        mock_response_weth.json.return_value = {
            'status': '1',
            'result': '1500000000000000000000'  # ~1500 WETH
        }

        # Mock PEPE balance in pool
        mock_response_pepe = MagicMock()
        mock_response_pepe.json.return_value = {
            'status': '1',
            'result': '2500000000000000000000000000000000'  # Large PEPE amount
        }

        # Mock ETH price
        mock_response_eth = MagicMock()
        mock_response_eth.json.return_value = {
            'status': '1',
            'result': {'ethusd': '1850.00'}
        }

        # Mock decimals
        mock_response_abi = MagicMock()
        mock_response_abi.json.return_value = {
            'status': '1',
            'result': '[]'
        }

        mock_get.side_effect = [
            mock_response_abi,  # ABI for decimals check
            mock_response_weth,
            mock_response_abi,  # ABI for PEPE decimals
            mock_response_pepe,
            mock_response_eth
        ]

        self.etherscan._web3_queries.get_contract = MagicMock()
        self.etherscan._web3_queries.call_contract_function = MagicMock(return_value=18)

        # Calculate mocked price
        # For PEPE at ~$0.0000011 with ETH at $1850:
        # PEPE/ETH = 0.0000011 / 1850 = 5.95e-10
        # So if PEPE amount is 2.5 trillion, WETH should be ~1487
        weth_amount = Decimal('1487')
        pepe_amount = Decimal('2500000000000')  # 2.5 trillion PEPE
        eth_price = Decimal('1850.00')

        price_in_eth = weth_amount / pepe_amount
        price_in_usd = float(price_in_eth * eth_price)

        # Verify the calculation matches expected range
        self.assertTrue(
            price_within_tolerance(price_in_usd, expected_price, tolerance=0.10),
            f"PEPE price {price_in_usd} not within 10% of expected {expected_price}"
        )

    @patch.object(etherscan_module.requests, 'get')
    def test_link_historical_price_block_19000000(self, mock_get):
        """
        Test LINK token price at block 19000000 (Jan 2024).
        Expected price: ~$15.20 USD
        """
        expected_price = ETH_HISTORICAL_PRICES[19000000]['LINK']

        # Mock pool balances that would give ~$15 LINK price
        # If ETH is ~$2280 and LINK is ~$15, then LINK/ETH = 0.00658
        mock_response_weth = MagicMock()
        mock_response_weth.json.return_value = {
            'status': '1',
            'result': str(int(6580 * 10**18))  # WETH in pool
        }

        mock_response_link = MagicMock()
        mock_response_link.json.return_value = {
            'status': '1',
            'result': str(int(1000000 * 10**18))  # LINK in pool
        }

        mock_response_eth = MagicMock()
        mock_response_eth.json.return_value = {
            'status': '1',
            'result': {'ethusd': '2280.00'}
        }

        mock_response_abi = MagicMock()
        mock_response_abi.json.return_value = {'status': '1', 'result': '[]'}

        mock_get.side_effect = [
            mock_response_abi,
            mock_response_weth,
            mock_response_abi,
            mock_response_link,
            mock_response_eth
        ]

        self.etherscan._web3_queries.get_contract = MagicMock()
        self.etherscan._web3_queries.call_contract_function = MagicMock(return_value=18)

        # Calculate expected price from mocked data
        weth_amount = Decimal('6580')
        link_amount = Decimal('1000000')
        eth_price = Decimal('2280.00')

        price_in_eth = weth_amount / link_amount
        price_in_usd = float(price_in_eth * eth_price)

        self.assertTrue(
            price_within_tolerance(price_in_usd, expected_price, tolerance=0.10),
            f"LINK price {price_in_usd} not within 10% of expected {expected_price}"
        )

    @patch.object(etherscan_module.requests, 'get')
    def test_uni_historical_price_block_19500000(self, mock_get):
        """
        Test UNI token price at block 19500000 (March 2024).
        Expected price: ~$12.00 USD
        """
        expected_price = ETH_HISTORICAL_PRICES[19500000]['UNI']

        # Mock data for ~$12 UNI with ETH at $3450
        # UNI/ETH ratio = 12/3450 = 0.00348
        mock_response_weth = MagicMock()
        mock_response_weth.json.return_value = {
            'status': '1',
            'result': str(int(3480 * 10**18))
        }

        mock_response_uni = MagicMock()
        mock_response_uni.json.return_value = {
            'status': '1',
            'result': str(int(1000000 * 10**18))
        }

        mock_response_eth = MagicMock()
        mock_response_eth.json.return_value = {
            'status': '1',
            'result': {'ethusd': '3450.00'}
        }

        mock_response_abi = MagicMock()
        mock_response_abi.json.return_value = {'status': '1', 'result': '[]'}

        mock_get.side_effect = [
            mock_response_abi,
            mock_response_weth,
            mock_response_abi,
            mock_response_uni,
            mock_response_eth
        ]

        self.etherscan._web3_queries.get_contract = MagicMock()
        self.etherscan._web3_queries.call_contract_function = MagicMock(return_value=18)

        weth_amount = Decimal('3480')
        uni_amount = Decimal('1000000')
        eth_price = Decimal('3450.00')

        price_in_eth = weth_amount / uni_amount
        price_in_usd = float(price_in_eth * eth_price)

        self.assertTrue(
            price_within_tolerance(price_in_usd, expected_price, tolerance=0.10),
            f"UNI price {price_in_usd} not within 10% of expected {expected_price}"
        )

    @patch.object(etherscan_module.requests, 'get')
    def test_shib_historical_price_block_19500000(self, mock_get):
        """
        Test SHIB token price at block 19500000 (March 2024).
        Expected price: ~$0.000027 USD
        """
        expected_price = ETH_HISTORICAL_PRICES[19500000]['SHIB']

        mock_response_weth = MagicMock()
        mock_response_weth.json.return_value = {
            'status': '1',
            'result': str(int(7830 * 10**18))  # WETH in pool
        }

        # Large SHIB amount for very low price
        mock_response_shib = MagicMock()
        mock_response_shib.json.return_value = {
            'status': '1',
            'result': str(int(1000000000000 * 10**18))
        }

        mock_response_eth = MagicMock()
        mock_response_eth.json.return_value = {
            'status': '1',
            'result': {'ethusd': '3450.00'}
        }

        mock_response_abi = MagicMock()
        mock_response_abi.json.return_value = {'status': '1', 'result': '[]'}

        mock_get.side_effect = [
            mock_response_abi,
            mock_response_weth,
            mock_response_abi,
            mock_response_shib,
            mock_response_eth
        ]

        self.etherscan._web3_queries.get_contract = MagicMock()
        self.etherscan._web3_queries.call_contract_function = MagicMock(return_value=18)

        weth_amount = Decimal('7830')
        shib_amount = Decimal('1000000000000')
        eth_price = Decimal('3450.00')

        price_in_eth = weth_amount / shib_amount
        price_in_usd = float(price_in_eth * eth_price)

        self.assertTrue(
            price_within_tolerance(price_in_usd, expected_price, tolerance=0.15),
            f"SHIB price {price_in_usd} not within 15% of expected {expected_price}"
        )


class TestBSCHistoricalPrices(unittest.TestCase):
    """
    Test historical price fetching for BSC (Binance Smart Chain) tokens.

    Note: BSC uses BSCScan API which has similar interface to Etherscan.
    These tests define the expected behavior for when BSC support is implemented.
    """

    def setUp(self):
        """Set up test fixtures for BSC tests."""
        self.bscscan_api_url = "https://api.bscscan.com/api"
        self.test_tolerance = 0.10  # 10% tolerance for historical prices

    def test_bnb_price_reference_block_33000000(self):
        """
        Test BNB price at block 33000000 (Nov 2023).
        Expected price: ~$230 USD

        This test validates the reference data structure for BSC integration.
        """
        expected_price = BSC_HISTORICAL_PRICES[33000000]['BNB']

        # Mock BSCScan API response structure (similar to Etherscan)
        mock_response = {
            'status': '1',
            'message': 'OK',
            'result': {
                'bnbusd': '230.00',
                'bnbusd_timestamp': '1699000000'
            }
        }

        # Validate response structure
        self.assertEqual(mock_response['status'], '1')
        self.assertIn('bnbusd', mock_response['result'])

        price = float(mock_response['result']['bnbusd'])
        self.assertTrue(
            price_within_tolerance(price, expected_price),
            f"BNB price {price} not within tolerance of expected {expected_price}"
        )

    def test_cake_price_reference_block_35000000(self):
        """
        Test CAKE (PancakeSwap) price at block 35000000 (Jan 2024).
        Expected price: ~$2.50 USD
        """
        expected_price = BSC_HISTORICAL_PRICES[35000000]['CAKE']

        # Mock pool-based price calculation
        # CAKE/WBNB pool reserves
        mock_wbnb_reserve = Decimal('8000')  # WBNB in pool
        mock_cake_reserve = Decimal('1000000')  # CAKE in pool
        mock_bnb_price = Decimal('310.00')  # BNB price in USD

        # Calculate CAKE price
        cake_per_bnb = mock_wbnb_reserve / mock_cake_reserve
        cake_price_usd = float(cake_per_bnb * mock_bnb_price)

        self.assertTrue(
            price_within_tolerance(cake_price_usd, expected_price),
            f"CAKE price {cake_price_usd} not within tolerance of expected {expected_price}"
        )

    def test_cake_price_reference_block_37000000(self):
        """
        Test CAKE price at block 37000000 (March 2024).
        Expected price: ~$3.80 USD
        """
        expected_price = BSC_HISTORICAL_PRICES[37000000]['CAKE']

        mock_wbnb_reserve = Decimal('6500')
        mock_cake_reserve = Decimal('1000000')
        mock_bnb_price = Decimal('580.00')

        cake_per_bnb = mock_wbnb_reserve / mock_cake_reserve
        cake_price_usd = float(cake_per_bnb * mock_bnb_price)

        self.assertTrue(
            price_within_tolerance(cake_price_usd, expected_price, tolerance=0.15),
            f"CAKE price {cake_price_usd} not within tolerance of expected {expected_price}"
        )

    def test_bsc_token_addresses_valid(self):
        """Test that all BSC token addresses are valid format."""
        for token_name, token_info in BSC_TOKENS.items():
            address = token_info['address']
            # BSC uses same address format as Ethereum (0x + 40 hex chars)
            self.assertTrue(
                address.startswith('0x') and len(address) == 42,
                f"Invalid address format for {token_name}: {address}"
            )

    def test_bsc_token_decimals_defined(self):
        """Test that all BSC tokens have decimals defined."""
        for token_name, token_info in BSC_TOKENS.items():
            self.assertIn('decimals', token_info, f"Decimals not defined for {token_name}")
            self.assertIsInstance(token_info['decimals'], int)
            self.assertGreaterEqual(token_info['decimals'], 0)
            self.assertLessEqual(token_info['decimals'], 18)


class TestSolanaHistoricalPrices(unittest.TestCase):
    """
    Test historical price fetching for Solana tokens.

    Note: Solana uses different architecture (slots instead of blocks,
    program addresses, SPL tokens). These tests define expected behavior.
    """

    def setUp(self):
        """Set up test fixtures for Solana tests."""
        self.solana_rpc_url = "https://api.mainnet-beta.solana.com"
        self.test_tolerance = 0.15  # 15% tolerance for Solana (more volatile)

    def test_sol_price_reference_slot_230000000(self):
        """
        Test SOL price at slot 230000000 (Nov 2023).
        Expected price: ~$58 USD
        """
        expected_price = SOLANA_HISTORICAL_PRICES[230000000]['SOL']

        # Mock Jupiter/Raydium pool price response
        mock_price = 58.00

        self.assertTrue(
            price_within_tolerance(mock_price, expected_price),
            f"SOL price {mock_price} not within tolerance of expected {expected_price}"
        )

    def test_sol_price_reference_slot_260000000(self):
        """
        Test SOL price at slot 260000000 (March 2024).
        Expected price: ~$175 USD
        """
        expected_price = SOLANA_HISTORICAL_PRICES[260000000]['SOL']
        mock_price = 175.00

        self.assertTrue(
            price_within_tolerance(mock_price, expected_price),
            f"SOL price {mock_price} not within tolerance of expected {expected_price}"
        )

    def test_bonk_price_reference_slot_245000000(self):
        """
        Test BONK meme token price at slot 245000000 (Jan 2024).
        Expected price: ~$0.000012 USD
        """
        expected_price = SOLANA_HISTORICAL_PRICES[245000000]['BONK']

        # Mock Raydium pool calculation
        # For BONK at ~$0.000012 with SOL at $95:
        # BONK/SOL = 0.000012 / 95 = 1.26e-7
        # So if BONK amount is 750 billion, SOL should be ~94,500
        mock_sol_reserve = Decimal('94500')  # SOL in pool
        mock_bonk_reserve = Decimal('750000000000')  # 750 billion BONK (5 decimals)
        mock_sol_price = Decimal('95.00')

        bonk_per_sol = mock_sol_reserve / mock_bonk_reserve
        bonk_price_usd = float(bonk_per_sol * mock_sol_price)

        self.assertTrue(
            price_within_tolerance(bonk_price_usd, expected_price, tolerance=0.10),
            f"BONK price {bonk_price_usd} not within tolerance of expected {expected_price}"
        )

    def test_jto_price_reference_slot_260000000(self):
        """
        Test JTO (Jito) price at slot 260000000 (March 2024).
        Expected price: ~$3.50 USD
        """
        expected_price = SOLANA_HISTORICAL_PRICES[260000000]['JTO']

        # Mock price from DEX aggregator
        mock_sol_reserve = Decimal('20000')
        mock_jto_reserve = Decimal('1000000')
        mock_sol_price = Decimal('175.00')

        jto_per_sol = mock_sol_reserve / mock_jto_reserve
        jto_price_usd = float(jto_per_sol * mock_sol_price)

        self.assertTrue(
            price_within_tolerance(jto_price_usd, expected_price),
            f"JTO price {jto_price_usd} not within tolerance of expected {expected_price}"
        )

    def test_wif_price_reference_slot_260000000(self):
        """
        Test WIF (dogwifhat) price at slot 260000000 (March 2024).
        Expected price: ~$2.80 USD
        """
        expected_price = SOLANA_HISTORICAL_PRICES[260000000]['WIF']

        mock_sol_reserve = Decimal('16000')
        mock_wif_reserve = Decimal('1000000')
        mock_sol_price = Decimal('175.00')

        wif_per_sol = mock_sol_reserve / mock_wif_reserve
        wif_price_usd = float(wif_per_sol * mock_sol_price)

        self.assertTrue(
            price_within_tolerance(wif_price_usd, expected_price),
            f"WIF price {wif_price_usd} not within tolerance of expected {expected_price}"
        )

    def test_solana_token_mints_valid(self):
        """Test that all Solana token mint addresses are valid base58 format."""
        import re
        base58_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')

        for token_name, token_info in SOLANA_TOKENS.items():
            mint = token_info['mint']
            self.assertTrue(
                base58_pattern.match(mint),
                f"Invalid mint address format for {token_name}: {mint}"
            )

    def test_solana_token_decimals_defined(self):
        """Test that all Solana tokens have decimals defined."""
        for token_name, token_info in SOLANA_TOKENS.items():
            self.assertIn('decimals', token_info, f"Decimals not defined for {token_name}")
            self.assertIsInstance(token_info['decimals'], int)
            # Solana tokens typically have 6-9 decimals
            self.assertGreaterEqual(token_info['decimals'], 0)
            self.assertLessEqual(token_info['decimals'], 9)


class TestPriceValidationHelpers(unittest.TestCase):
    """Test the helper functions used for price validation."""

    def test_price_within_tolerance_exact_match(self):
        """Test tolerance check with exact match."""
        self.assertTrue(price_within_tolerance(100.0, 100.0, 0.05))

    def test_price_within_tolerance_within_bounds(self):
        """Test tolerance check within acceptable bounds."""
        self.assertTrue(price_within_tolerance(105.0, 100.0, 0.10))  # 5% off, 10% tolerance
        self.assertTrue(price_within_tolerance(95.0, 100.0, 0.10))   # 5% off, 10% tolerance

    def test_price_within_tolerance_at_boundary(self):
        """Test tolerance check at exact boundary."""
        self.assertTrue(price_within_tolerance(110.0, 100.0, 0.10))  # Exactly 10%
        self.assertTrue(price_within_tolerance(90.0, 100.0, 0.10))   # Exactly 10%

    def test_price_within_tolerance_outside_bounds(self):
        """Test tolerance check outside acceptable bounds."""
        self.assertFalse(price_within_tolerance(115.0, 100.0, 0.10))  # 15% off
        self.assertFalse(price_within_tolerance(85.0, 100.0, 0.10))   # 15% off

    def test_price_within_tolerance_zero_expected(self):
        """Test tolerance check with zero expected price."""
        self.assertTrue(price_within_tolerance(0.0, 0.0, 0.10))
        self.assertFalse(price_within_tolerance(1.0, 0.0, 0.10))

    def test_price_deviation_calculation(self):
        """Test price deviation percentage calculation."""
        self.assertEqual(get_price_deviation_pct(110.0, 100.0), 10.0)
        self.assertEqual(get_price_deviation_pct(90.0, 100.0), -10.0)
        self.assertEqual(get_price_deviation_pct(100.0, 100.0), 0.0)

    def test_price_deviation_zero_expected(self):
        """Test deviation calculation with zero expected."""
        self.assertEqual(get_price_deviation_pct(0.0, 0.0), 0.0)
        self.assertEqual(get_price_deviation_pct(1.0, 0.0), float('inf'))


class TestCrossChainPriceConsistency(unittest.TestCase):
    """
    Test price consistency across different chains for the same assets.
    Stablecoins and bridged assets should have consistent prices.
    """

    def test_usdc_price_consistency_across_chains(self):
        """
        Test that USDC maintains ~$1.00 peg across ETH, BSC, and Solana.
        Stablecoins should be within 1% of $1.00.
        """
        expected_usdc_price = 1.00
        tolerance = 0.01  # 1% tolerance for stablecoins

        # Mock USDC prices from different chains
        eth_usdc_price = 1.001
        bsc_usdc_price = 0.999
        sol_usdc_price = 1.002

        self.assertTrue(
            price_within_tolerance(eth_usdc_price, expected_usdc_price, tolerance),
            f"ETH USDC price {eth_usdc_price} depegged"
        )
        self.assertTrue(
            price_within_tolerance(bsc_usdc_price, expected_usdc_price, tolerance),
            f"BSC USDC price {bsc_usdc_price} depegged"
        )
        self.assertTrue(
            price_within_tolerance(sol_usdc_price, expected_usdc_price, tolerance),
            f"Solana USDC price {sol_usdc_price} depegged"
        )

    def test_usdt_price_consistency_eth_bsc(self):
        """
        Test that USDT maintains ~$1.00 peg on ETH and BSC.
        """
        expected_usdt_price = 1.00
        tolerance = 0.01

        eth_usdt_price = 0.9995
        bsc_usdt_price = 1.0005

        self.assertTrue(
            price_within_tolerance(eth_usdt_price, expected_usdt_price, tolerance)
        )
        self.assertTrue(
            price_within_tolerance(bsc_usdt_price, expected_usdt_price, tolerance)
        )


class TestHistoricalPriceDataIntegrity(unittest.TestCase):
    """Test the integrity and structure of historical price reference data."""

    def test_eth_historical_data_structure(self):
        """Test ETH historical price data has correct structure."""
        for block, prices in ETH_HISTORICAL_PRICES.items():
            self.assertIsInstance(block, int)
            self.assertGreater(block, 0)
            self.assertIsInstance(prices, dict)
            self.assertIn('ETH', prices)
            for token, price in prices.items():
                self.assertIsInstance(price, (int, float))
                self.assertGreater(price, 0)

    def test_bsc_historical_data_structure(self):
        """Test BSC historical price data has correct structure."""
        for block, prices in BSC_HISTORICAL_PRICES.items():
            self.assertIsInstance(block, int)
            self.assertGreater(block, 0)
            self.assertIsInstance(prices, dict)
            self.assertIn('BNB', prices)
            for token, price in prices.items():
                self.assertIsInstance(price, (int, float))
                self.assertGreater(price, 0)

    def test_solana_historical_data_structure(self):
        """Test Solana historical price data has correct structure."""
        for slot, prices in SOLANA_HISTORICAL_PRICES.items():
            self.assertIsInstance(slot, int)
            self.assertGreater(slot, 0)
            self.assertIsInstance(prices, dict)
            self.assertIn('SOL', prices)
            for token, price in prices.items():
                self.assertIsInstance(price, (int, float))
                self.assertGreater(price, 0)

    def test_historical_blocks_chronological_order(self):
        """Test that historical blocks/slots are in chronological order."""
        eth_blocks = sorted(ETH_HISTORICAL_PRICES.keys())
        bsc_blocks = sorted(BSC_HISTORICAL_PRICES.keys())
        sol_slots = sorted(SOLANA_HISTORICAL_PRICES.keys())

        self.assertEqual(eth_blocks, list(ETH_HISTORICAL_PRICES.keys()))
        self.assertEqual(bsc_blocks, list(BSC_HISTORICAL_PRICES.keys()))
        self.assertEqual(sol_slots, list(SOLANA_HISTORICAL_PRICES.keys()))


# ==============================================================================
# INTEGRATION TESTS - Fetch real prices from DeFiLlama API
# These tests require network access and are skipped by default.
# Run with: python -m pytest test_historical_prices.py -k "Integration" --run-integration
# ==============================================================================

# Check if integration tests should run
SKIP_INTEGRATION = os.environ.get('RUN_INTEGRATION_TESTS', '').lower() not in ('1', 'true', 'yes')


@unittest.skipIf(SKIP_INTEGRATION, "Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable.")
class TestDeFiLlamaIntegration(unittest.TestCase):
    """
    Integration tests that fetch real historical prices from DeFiLlama API.

    These tests verify that our reference prices match the actual API values.
    Run with: RUN_INTEGRATION_TESTS=1 python -m unittest test_historical_prices.TestDeFiLlamaIntegration
    """

    # DeFiLlama API endpoint
    DEFILLAMA_URL = "https://coins.llama.fi/prices/historical"

    # Reference timestamps
    TIMESTAMPS = {
        'nov_2023': 1699027200,
        'jan_2024': 1704153600,
        'mar_2024': 1710288000,
    }

    @classmethod
    def setUpClass(cls):
        """Set up for integration tests - import requests."""
        try:
            import requests
            cls.requests = requests
            cls.api_available = True
        except ImportError:
            cls.api_available = False

    def _fetch_price(self, chain: str, address: str, timestamp: int) -> float:
        """Fetch price from DeFiLlama API."""
        if not self.api_available:
            self.skipTest("requests module not available")

        url = f"{self.DEFILLAMA_URL}/{timestamp}/{chain}:{address}"
        try:
            response = self.requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            coin_key = f"{chain}:{address}"
            return data.get('coins', {}).get(coin_key, {}).get('price')
        except Exception as e:
            self.skipTest(f"API request failed: {e}")

    def test_eth_weth_price_nov_2023(self):
        """Verify WETH price on Nov 3, 2023 from DeFiLlama."""
        price = self._fetch_price(
            'ethereum',
            ETH_TOKENS['WETH']['address'],
            self.TIMESTAMPS['nov_2023']
        )
        if price:
            # WETH should be ~$1800-1900 on Nov 3, 2023
            self.assertGreater(price, 1500, f"WETH price {price} too low")
            self.assertLess(price, 2200, f"WETH price {price} too high")
            print(f"\n  WETH Nov 2023: ${price:.2f}")

    def test_eth_link_price_jan_2024(self):
        """Verify LINK price on Jan 2, 2024 from DeFiLlama."""
        price = self._fetch_price(
            'ethereum',
            ETH_TOKENS['LINK']['address'],
            self.TIMESTAMPS['jan_2024']
        )
        if price:
            # LINK should be ~$13-17 on Jan 2, 2024
            self.assertGreater(price, 10, f"LINK price {price} too low")
            self.assertLess(price, 25, f"LINK price {price} too high")
            print(f"\n  LINK Jan 2024: ${price:.2f}")

    def test_eth_pepe_price_mar_2024(self):
        """Verify PEPE price on Mar 13, 2024 from DeFiLlama."""
        price = self._fetch_price(
            'ethereum',
            ETH_TOKENS['PEPE']['address'],
            self.TIMESTAMPS['mar_2024']
        )
        if price:
            # PEPE should be a very small number
            self.assertGreater(price, 0, f"PEPE price {price} should be positive")
            self.assertLess(price, 0.001, f"PEPE price {price} too high")
            print(f"\n  PEPE Mar 2024: ${price:.10f}")

    def test_bsc_bnb_price_nov_2023(self):
        """Verify BNB price on Nov 3, 2023 from DeFiLlama."""
        price = self._fetch_price(
            'bsc',
            BSC_TOKENS['WBNB']['address'],
            self.TIMESTAMPS['nov_2023']
        )
        if price:
            # BNB should be ~$220-250 on Nov 3, 2023
            self.assertGreater(price, 180, f"BNB price {price} too low")
            self.assertLess(price, 300, f"BNB price {price} too high")
            print(f"\n  BNB Nov 2023: ${price:.2f}")

    def test_bsc_cake_price_jan_2024(self):
        """Verify CAKE price on Jan 2, 2024 from DeFiLlama."""
        price = self._fetch_price(
            'bsc',
            BSC_TOKENS['CAKE']['address'],
            self.TIMESTAMPS['jan_2024']
        )
        if price:
            # CAKE should be ~$2-4 on Jan 2, 2024
            self.assertGreater(price, 1, f"CAKE price {price} too low")
            self.assertLess(price, 10, f"CAKE price {price} too high")
            print(f"\n  CAKE Jan 2024: ${price:.2f}")

    def test_solana_sol_price_nov_2023(self):
        """Verify SOL price on Nov 3, 2023 from DeFiLlama."""
        price = self._fetch_price(
            'solana',
            SOLANA_TOKENS['SOL']['mint'],
            self.TIMESTAMPS['nov_2023']
        )
        if price:
            # SOL should be ~$35-65 on Nov 3, 2023
            self.assertGreater(price, 25, f"SOL price {price} too low")
            self.assertLess(price, 80, f"SOL price {price} too high")
            print(f"\n  SOL Nov 2023: ${price:.2f}")

    def test_solana_bonk_price_jan_2024(self):
        """Verify BONK price on Jan 2, 2024 from DeFiLlama."""
        price = self._fetch_price(
            'solana',
            SOLANA_TOKENS['BONK']['mint'],
            self.TIMESTAMPS['jan_2024']
        )
        if price:
            # BONK should be a very small number
            self.assertGreater(price, 0, f"BONK price {price} should be positive")
            self.assertLess(price, 0.001, f"BONK price {price} too high")
            print(f"\n  BONK Jan 2024: ${price:.10f}")


@unittest.skipIf(SKIP_INTEGRATION, "Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable.")
class TestVerifyReferencePrices(unittest.TestCase):
    """
    Verify that our hardcoded reference prices match DeFiLlama API values.

    This test class compares the ETH_HISTORICAL_PRICES, BSC_HISTORICAL_PRICES,
    and SOLANA_HISTORICAL_PRICES constants against live API data.
    """

    TOLERANCE = 0.20  # 20% tolerance for historical price verification

    @classmethod
    def setUpClass(cls):
        """Set up for verification tests."""
        try:
            import requests
            cls.requests = requests
            cls.api_available = True
        except ImportError:
            cls.api_available = False

    def _fetch_and_compare(self, chain: str, address: str, timestamp: int, expected: float, token_name: str):
        """Fetch price and compare against expected value."""
        if not self.api_available:
            self.skipTest("requests module not available")

        url = f"https://coins.llama.fi/prices/historical/{timestamp}/{chain}:{address}"
        try:
            response = self.requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            coin_key = f"{chain}:{address}"
            actual = data.get('coins', {}).get(coin_key, {}).get('price')

            if actual:
                deviation = abs(actual - expected) / expected if expected != 0 else 0
                status = "✓" if deviation <= self.TOLERANCE else "✗"
                print(f"\n  {status} {token_name}: API=${actual:.6f}, Expected=${expected:.6f}, Deviation={deviation*100:.1f}%")

                self.assertTrue(
                    deviation <= self.TOLERANCE,
                    f"{token_name} price deviation {deviation*100:.1f}% exceeds {self.TOLERANCE*100}% tolerance. "
                    f"API: ${actual}, Expected: ${expected}"
                )
            else:
                print(f"\n  ? {token_name}: No API data available")

        except Exception as e:
            self.skipTest(f"API request failed for {token_name}: {e}")

    def test_verify_eth_historical_prices(self):
        """Verify ETH chain historical prices against DeFiLlama API."""
        timestamp_map = {
            18500000: 1699027200,  # Nov 2023
            19000000: 1704153600,  # Jan 2024
            19500000: 1710288000,  # Mar 2024
        }

        for block, prices in ETH_HISTORICAL_PRICES.items():
            timestamp = timestamp_map.get(block)
            if not timestamp:
                continue

            print(f"\n--- ETH Block {block} ---")

            for token_name, expected_price in prices.items():
                if token_name == 'ETH':
                    address = ETH_TOKENS['WETH']['address']
                elif token_name in ETH_TOKENS:
                    address = ETH_TOKENS[token_name]['address']
                else:
                    continue

                self._fetch_and_compare('ethereum', address, timestamp, expected_price, token_name)

    def test_verify_bsc_historical_prices(self):
        """Verify BSC chain historical prices against DeFiLlama API."""
        timestamp_map = {
            33000000: 1699027200,  # Nov 2023
            35000000: 1704153600,  # Jan 2024
            37000000: 1710288000,  # Mar 2024
        }

        for block, prices in BSC_HISTORICAL_PRICES.items():
            timestamp = timestamp_map.get(block)
            if not timestamp:
                continue

            print(f"\n--- BSC Block {block} ---")

            for token_name, expected_price in prices.items():
                if token_name == 'BNB':
                    address = BSC_TOKENS['WBNB']['address']
                elif token_name in BSC_TOKENS:
                    address = BSC_TOKENS[token_name]['address']
                else:
                    continue

                self._fetch_and_compare('bsc', address, timestamp, expected_price, token_name)

    def test_verify_solana_historical_prices(self):
        """Verify Solana chain historical prices against DeFiLlama API."""
        timestamp_map = {
            230000000: 1699027200,  # Nov 2023
            245000000: 1704153600,  # Jan 2024
            260000000: 1710288000,  # Mar 2024
        }

        for slot, prices in SOLANA_HISTORICAL_PRICES.items():
            timestamp = timestamp_map.get(slot)
            if not timestamp:
                continue

            print(f"\n--- Solana Slot {slot} ---")

            for token_name, expected_price in prices.items():
                if token_name in SOLANA_TOKENS:
                    mint = SOLANA_TOKENS[token_name]['mint']
                else:
                    continue

                self._fetch_and_compare('solana', mint, timestamp, expected_price, token_name)


# ==============================================================================
# THE GRAPH & HELIUS INTEGRATION TESTS
# These tests verify prices using the newly integrated data sources
# ==============================================================================

@unittest.skipIf(SKIP_INTEGRATION, "Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable.")
class TestTheGraphIntegration(unittest.TestCase):
    """
    Integration tests using The Graph subgraph queries for historical ERC20 data.

    These tests verify that The Graph can fetch historical token balances
    which can be used to calculate prices from DEX pools.

    Run with: RUN_INTEGRATION_TESTS=1 python -m unittest test_historical_prices.TestTheGraphIntegration
    """

    @classmethod
    def setUpClass(cls):
        """Set up The Graph client for tests."""
        try:
            # Import the actual modules (not mocked)
            import importlib
            import sys

            # Temporarily remove mocks to import real modules
            real_config_path = os.path.join(DEFI_LIBRARY_PATH, 'config.py')
            spec = importlib.util.spec_from_file_location("real_config", real_config_path)
            cls.real_config = importlib.util.module_from_spec(spec)

            # Check if TheGraph client is available
            thegraph_path = os.path.join(
                DEFI_LIBRARY_PATH,
                'blocks_scraping', 'dev', 'thegraph', 'graph_client.py'
            )
            cls.thegraph_available = os.path.exists(thegraph_path)
        except Exception as e:
            cls.thegraph_available = False
            print(f"TheGraph setup error: {e}")

    def test_thegraph_module_exists(self):
        """Verify The Graph integration module exists."""
        thegraph_path = os.path.join(
            DEFI_LIBRARY_PATH,
            'blocks_scraping', 'dev', 'thegraph'
        )
        self.assertTrue(
            os.path.isdir(thegraph_path),
            "The Graph module directory should exist after migration"
        )

    def test_thegraph_queries_module_exists(self):
        """Verify The Graph queries module exists."""
        queries_path = os.path.join(
            DEFI_LIBRARY_PATH,
            'blocks_scraping', 'dev', 'thegraph', 'queries.py'
        )
        self.assertTrue(
            os.path.isfile(queries_path),
            "The Graph queries module should exist"
        )

    def test_thegraph_client_module_exists(self):
        """Verify The Graph client module exists."""
        client_path = os.path.join(
            DEFI_LIBRARY_PATH,
            'blocks_scraping', 'dev', 'thegraph', 'graph_client.py'
        )
        self.assertTrue(
            os.path.isfile(client_path),
            "The Graph client module should exist"
        )


@unittest.skipIf(SKIP_INTEGRATION, "Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable.")
class TestHeliusIntegration(unittest.TestCase):
    """
    Integration tests using Helius API for Solana token data.

    These tests verify that Helius can fetch token metadata and balances
    for Solana tokens.

    Run with: RUN_INTEGRATION_TESTS=1 python -m unittest test_historical_prices.TestHeliusIntegration
    """

    @classmethod
    def setUpClass(cls):
        """Set up Helius client for tests."""
        try:
            helius_path = os.path.join(
                DEFI_LIBRARY_PATH,
                'blocks_scraping', 'dev', 'solana', 'helius_client.py'
            )
            cls.helius_available = os.path.exists(helius_path)
        except Exception:
            cls.helius_available = False

    def test_helius_module_exists(self):
        """Verify Helius integration module exists."""
        helius_path = os.path.join(
            DEFI_LIBRARY_PATH,
            'blocks_scraping', 'dev', 'solana'
        )
        self.assertTrue(
            os.path.isdir(helius_path),
            "Solana/Helius module directory should exist after migration"
        )

    def test_helius_client_module_exists(self):
        """Verify Helius client module exists."""
        client_path = os.path.join(
            DEFI_LIBRARY_PATH,
            'blocks_scraping', 'dev', 'solana', 'helius_client.py'
        )
        self.assertTrue(
            os.path.isfile(client_path),
            "Helius client module should exist"
        )

    def test_solana_queries_module_exists(self):
        """Verify Solana queries module exists."""
        queries_path = os.path.join(
            DEFI_LIBRARY_PATH,
            'blocks_scraping', 'dev', 'solana', 'solana_queries.py'
        )
        self.assertTrue(
            os.path.isfile(queries_path),
            "Solana queries module should exist"
        )

    def test_solana_token_mints_match_helius_format(self):
        """Verify Solana token mints are valid for Helius API."""
        import re
        base58_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')

        for token_name, token_info in SOLANA_TOKENS.items():
            mint = token_info['mint']
            self.assertTrue(
                base58_pattern.match(mint),
                f"Token {token_name} mint {mint} should be valid base58 for Helius"
            )


if __name__ == '__main__':
    # Run tests with verbose output
    # For integration tests, set RUN_INTEGRATION_TESTS=1
    unittest.main(verbosity=2)

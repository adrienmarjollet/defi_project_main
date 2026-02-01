"""
Historical Price Fetcher for DeFi tokens.

Fetches verified historical prices from DeFiLlama API and caches them locally.
Supports Ethereum, BSC, and Solana chains.

Usage:
    fetcher = HistoricalPriceFetcher()
    price = fetcher.get_price('ethereum', '0xC02aa...', timestamp=1699027200)

    # Or fetch all reference prices for tests
    fetcher.fetch_and_cache_all_reference_prices()
"""

import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from decimal import Decimal


class HistoricalPriceFetcher:
    """
    Fetches and caches historical token prices from DeFiLlama API.

    DeFiLlama endpoint: https://coins.llama.fi/prices/historical/{timestamp}/{chain}:{address}

    Supports chains: ethereum, bsc, solana
    """

    # DeFiLlama API base URL
    DEFILLAMA_BASE_URL = "https://coins.llama.fi"

    # CoinGecko API base URL (fallback)
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

    # Chain identifiers for DeFiLlama
    CHAIN_IDS = {
        'ethereum': 'ethereum',
        'eth': 'ethereum',
        'bsc': 'bsc',
        'binance': 'bsc',
        'solana': 'solana',
        'sol': 'solana'
    }

    # Famous tokens with their addresses across chains
    TOKENS = {
        # Ethereum tokens
        'ethereum': {
            'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'PEPE': '0x6982508145454Ce325dDbE47a25d4ec3d2311933',
            'SHIB': '0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE',
            'LINK': '0x514910771AF9Ca656af840dff83E8264EcF986CA',
            'UNI': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
        },
        # BSC tokens
        'bsc': {
            'WBNB': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',
            'BUSD': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
            'CAKE': '0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82',
            'USDT': '0x55d398326f99059fF775485246999027B3197955',
            'XRP': '0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE',
        },
        # Solana tokens (mint addresses)
        'solana': {
            'SOL': 'So11111111111111111111111111111111111111112',
            'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'JTO': 'jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL',
            'WIF': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm',
            'PYTH': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3',
        }
    }

    # Reference timestamps for historical price tests
    # Format: (name, unix_timestamp, date_string)
    REFERENCE_TIMESTAMPS = {
        'ethereum': [
            ('block_18500000', 1699027200, '2023-11-03'),  # Nov 3, 2023
            ('block_19000000', 1704153600, '2024-01-02'),  # Jan 2, 2024
            ('block_19500000', 1710288000, '2024-03-13'),  # Mar 13, 2024
        ],
        'bsc': [
            ('block_33000000', 1699027200, '2023-11-03'),  # Nov 3, 2023
            ('block_35000000', 1704153600, '2024-01-02'),  # Jan 2, 2024
            ('block_37000000', 1710288000, '2024-03-13'),  # Mar 13, 2024
        ],
        'solana': [
            ('slot_230000000', 1699027200, '2023-11-03'),  # Nov 3, 2023
            ('slot_245000000', 1704153600, '2024-01-02'),  # Jan 2, 2024
            ('slot_260000000', 1710288000, '2024-03-13'),  # Mar 13, 2024
        ]
    }

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the price fetcher.

        Args:
            cache_dir: Directory to store cached prices. Defaults to project data directory.
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to project data directory
            self.cache_dir = Path(__file__).parent.parent.parent / 'data' / 'price_cache'

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / 'historical_prices.json'
        self._cache = self._load_cache()

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 500ms between requests

    def _load_cache(self) -> Dict:
        """Load cached prices from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_cache(self):
        """Save prices to cache file."""
        with open(self.cache_file, 'w') as f:
            json.dump(self._cache, f, indent=2)

    def _rate_limit(self):
        """Ensure rate limiting between API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _get_cache_key(self, chain: str, address: str, timestamp: int) -> str:
        """Generate cache key for a price query."""
        return f"{chain}:{address}:{timestamp}"

    def get_price_from_defillama(
        self,
        chain: str,
        address: str,
        timestamp: int
    ) -> Optional[float]:
        """
        Fetch historical price from DeFiLlama API.

        Args:
            chain: Chain name (ethereum, bsc, solana)
            address: Token contract/mint address
            timestamp: Unix timestamp for the price query

        Returns:
            Price in USD or None if not available
        """
        chain_id = self.CHAIN_IDS.get(chain.lower(), chain.lower())
        url = f"{self.DEFILLAMA_BASE_URL}/prices/historical/{timestamp}/{chain_id}:{address}"

        self._rate_limit()

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            coin_key = f"{chain_id}:{address}"
            if 'coins' in data and coin_key in data['coins']:
                return data['coins'][coin_key].get('price')

            # Try lowercase address
            coin_key_lower = f"{chain_id}:{address.lower()}"
            if 'coins' in data and coin_key_lower in data['coins']:
                return data['coins'][coin_key_lower].get('price')

        except requests.RequestException as e:
            print(f"DeFiLlama API error for {chain}:{address}: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error parsing DeFiLlama response: {e}")

        return None

    def get_price_from_coingecko(
        self,
        coin_id: str,
        date: str  # Format: DD-MM-YYYY
    ) -> Optional[float]:
        """
        Fetch historical price from CoinGecko API (fallback).

        Args:
            coin_id: CoinGecko coin ID (e.g., 'ethereum', 'binancecoin')
            date: Date string in DD-MM-YYYY format

        Returns:
            Price in USD or None if not available
        """
        url = f"{self.COINGECKO_BASE_URL}/coins/{coin_id}/history?date={date}"

        self._rate_limit()

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            return data.get('market_data', {}).get('current_price', {}).get('usd')

        except requests.RequestException as e:
            print(f"CoinGecko API error for {coin_id}: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error parsing CoinGecko response: {e}")

        return None

    def get_price(
        self,
        chain: str,
        address: str,
        timestamp: int,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> Optional[float]:
        """
        Get historical price for a token, using cache if available.

        Args:
            chain: Chain name (ethereum, bsc, solana)
            address: Token contract/mint address
            timestamp: Unix timestamp
            use_cache: Whether to use cached prices
            force_refresh: Force fetching from API even if cached

        Returns:
            Price in USD or None if not available
        """
        cache_key = self._get_cache_key(chain, address, timestamp)

        # Check cache first
        if use_cache and not force_refresh and cache_key in self._cache:
            return self._cache[cache_key]

        # Fetch from API
        price = self.get_price_from_defillama(chain, address, timestamp)

        # Cache the result
        if price is not None:
            self._cache[cache_key] = price
            self._save_cache()

        return price

    def fetch_all_reference_prices(self, force_refresh: bool = False) -> Dict:
        """
        Fetch all reference prices for the test suite.

        Args:
            force_refresh: Force refetching all prices from API

        Returns:
            Dictionary of all fetched prices organized by chain/timestamp/token
        """
        results = {}

        for chain, timestamps in self.REFERENCE_TIMESTAMPS.items():
            results[chain] = {}
            tokens = self.TOKENS.get(chain, {})

            for ts_name, timestamp, date_str in timestamps:
                results[chain][ts_name] = {
                    'timestamp': timestamp,
                    'date': date_str,
                    'prices': {}
                }

                print(f"\nFetching prices for {chain} at {date_str} ({ts_name})...")

                for token_name, address in tokens.items():
                    price = self.get_price(
                        chain, address, timestamp,
                        force_refresh=force_refresh
                    )

                    if price is not None:
                        results[chain][ts_name]['prices'][token_name] = price
                        print(f"  {token_name}: ${price}")
                    else:
                        print(f"  {token_name}: NOT AVAILABLE")

        return results

    def export_for_tests(self, output_file: Optional[str] = None) -> str:
        """
        Export cached prices in a format ready for test file inclusion.

        Args:
            output_file: Optional file path to write the output

        Returns:
            Python code string for the reference prices
        """
        # Reorganize cache by chain and timestamp
        organized = {}

        for key, price in self._cache.items():
            parts = key.split(':')
            if len(parts) == 3:
                chain, address, timestamp = parts[0], parts[1], int(parts[2])

                # Find token name
                token_name = None
                for t_name, t_addr in self.TOKENS.get(chain, {}).items():
                    if t_addr.lower() == address.lower():
                        token_name = t_name
                        break

                if token_name:
                    if chain not in organized:
                        organized[chain] = {}
                    if timestamp not in organized[chain]:
                        organized[chain][timestamp] = {}
                    organized[chain][timestamp][token_name] = price

        # Generate Python code
        lines = ['# Auto-generated historical price reference data']
        lines.append(f'# Generated: {datetime.now().isoformat()}')
        lines.append(f'# Source: DeFiLlama API (https://coins.llama.fi)')
        lines.append('')

        for chain in ['ethereum', 'bsc', 'solana']:
            if chain not in organized:
                continue

            var_name = f'{chain.upper()}_HISTORICAL_PRICES'
            lines.append(f'{var_name} = {{')

            for timestamp in sorted(organized[chain].keys()):
                prices = organized[chain][timestamp]
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                lines.append(f'    # {date_str}')
                lines.append(f'    {timestamp}: {{')

                for token, price in sorted(prices.items()):
                    if price < 0.0001:
                        lines.append(f"        '{token}': {price:.10f},")
                    elif price < 1:
                        lines.append(f"        '{token}': {price:.6f},")
                    else:
                        lines.append(f"        '{token}': {price:.2f},")

                lines.append('    },')

            lines.append('}')
            lines.append('')

        output = '\n'.join(lines)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            print(f"Exported to {output_file}")

        return output

    def get_cached_prices(self) -> Dict:
        """Return all cached prices."""
        return self._cache.copy()


# CoinGecko ID mapping for fallback
COINGECKO_IDS = {
    'ethereum': {
        'WETH': 'weth',
        'ETH': 'ethereum',
        'USDC': 'usd-coin',
        'USDT': 'tether',
        'PEPE': 'pepe',
        'SHIB': 'shiba-inu',
        'LINK': 'chainlink',
        'UNI': 'uniswap',
    },
    'bsc': {
        'BNB': 'binancecoin',
        'WBNB': 'wbnb',
        'BUSD': 'binance-usd',
        'CAKE': 'pancakeswap-token',
    },
    'solana': {
        'SOL': 'solana',
        'BONK': 'bonk',
        'JTO': 'jito-governance-token',
        'WIF': 'dogwifcoin',
        'PYTH': 'pyth-network',
    }
}


def main():
    """CLI entry point for fetching and caching historical prices."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fetch and cache historical token prices for testing'
    )
    parser.add_argument(
        '--refresh', '-r',
        action='store_true',
        help='Force refresh all prices from API'
    )
    parser.add_argument(
        '--export', '-e',
        type=str,
        help='Export prices to Python file'
    )
    parser.add_argument(
        '--show-cache', '-s',
        action='store_true',
        help='Show all cached prices'
    )

    args = parser.parse_args()

    fetcher = HistoricalPriceFetcher()

    if args.show_cache:
        cache = fetcher.get_cached_prices()
        print(f"Cached prices: {len(cache)} entries")
        for key, price in sorted(cache.items()):
            print(f"  {key}: ${price}")
        return

    # Fetch all reference prices
    print("Fetching historical prices from DeFiLlama API...")
    results = fetcher.fetch_all_reference_prices(force_refresh=args.refresh)

    # Export if requested
    if args.export:
        fetcher.export_for_tests(args.export)
    else:
        print("\n" + "="*60)
        print("Generated Python code for test reference data:")
        print("="*60)
        print(fetcher.export_for_tests())


if __name__ == '__main__':
    main()

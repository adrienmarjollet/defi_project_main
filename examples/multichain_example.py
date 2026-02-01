#!/usr/bin/env python3
"""
Multi-Chain DeFi Analytics Example

This script demonstrates how to use the new integrations:
- The Graph for ETH/BSC (EVM chains)
- Helius for Solana

Before running:
1. Copy .env.example to .env
2. Fill in your API keys
3. Run: poetry install
4. Run: python examples/multichain_example.py
"""

import sys
from pathlib import Path

# Add defi_library to path
sys.path.insert(0, str(Path(__file__).parent.parent / "defi_library"))

from decimal import Decimal

# EVM imports
from blocks_scraping.dev.thegraph import GraphClient, ERC20Queries
from blocks_scraping.dev.web3.web3_queries import Web3Queries

# Solana imports
from blocks_scraping.dev.solana import HeliusClient, SolanaQueries
from blocks_scraping.dev.solana.solana_queries import KNOWN_TOKENS


def example_ethereum_queries():
    """Example: Query Ethereum data via The Graph"""
    print("\n" + "=" * 60)
    print("ETHEREUM EXAMPLES (The Graph)")
    print("=" * 60)

    try:
        # Initialize Graph client
        client = GraphClient()

        # Query Uniswap V3 pools
        print("\n1. Top Uniswap V3 Pools by TVL:")
        result = client.query(
            endpoint="uniswap_v3_eth",
            query="""
            {
                pools(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc) {
                    id
                    token0 { symbol }
                    token1 { symbol }
                    totalValueLockedUSD
                    volumeUSD
                }
            }
            """
        )

        for pool in result.get("pools", []):
            tvl = float(pool["totalValueLockedUSD"])
            print(f"   {pool['token0']['symbol']}/{pool['token1']['symbol']}: ${tvl:,.0f} TVL")

    except Exception as e:
        print(f"   [Skipped - API key required] {e}")

    # Direct Web3 queries still work
    print("\n2. Direct RPC Queries (Web3.py):")
    try:
        w3 = Web3Queries()
        latest_block = w3.get_latest_block()
        print(f"   Latest block: {latest_block['number']}")
        print(f"   Timestamp: {latest_block['timestamp']}")
    except Exception as e:
        print(f"   [Skipped - RPC required] {e}")


def example_bsc_queries():
    """Example: Query BSC data via The Graph"""
    print("\n" + "=" * 60)
    print("BSC EXAMPLES (The Graph)")
    print("=" * 60)

    try:
        client = GraphClient()

        # Query PancakeSwap V3 pools on BSC
        print("\n1. Top PancakeSwap V3 Pools:")
        result = client.query(
            endpoint="pancakeswap_v3_bsc",
            query="""
            {
                pools(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc) {
                    id
                    token0 { symbol }
                    token1 { symbol }
                    totalValueLockedUSD
                }
            }
            """
        )

        for pool in result.get("pools", []):
            tvl = float(pool["totalValueLockedUSD"])
            print(f"   {pool['token0']['symbol']}/{pool['token1']['symbol']}: ${tvl:,.0f} TVL")

    except Exception as e:
        print(f"   [Skipped - API key required] {e}")


def example_solana_queries():
    """Example: Query Solana data via Helius"""
    print("\n" + "=" * 60)
    print("SOLANA EXAMPLES (Helius)")
    print("=" * 60)

    try:
        # Initialize Solana queries
        queries = SolanaQueries()

        # Current blockchain state
        print("\n1. Blockchain State:")
        slot = queries.get_current_slot()
        height = queries.get_current_block_height()
        print(f"   Current slot: {slot:,}")
        print(f"   Block height: {height:,}")

        # Example wallet analysis
        print("\n2. Wallet Analysis (Solana Foundation):")
        test_wallet = "Ezrf3kUzKoAJ8T6XN38e59zF8HNc7VT6KTrPjKkLedyJ"
        summary = queries.get_wallet_summary(test_wallet)
        print(f"   Address: {summary.address[:16]}...")
        print(f"   SOL Balance: {summary.sol_balance:.4f} SOL")
        print(f"   Token Count: {summary.token_count}")

        # Token holder analysis
        print("\n3. Token Holder Analysis (BONK):")
        bonk_mint = KNOWN_TOKENS["BONK"]
        concentration = queries.get_token_concentration(bonk_mint, top_n=5)
        print(f"   Top 5 holders control: {concentration['total_percentage']:.2f}%")
        print(f"   Largest holder: {concentration['largest_holder_percentage']:.2f}%")

        # Get holders as DataFrame
        print("\n4. Top BONK Holders:")
        holders_df = queries.get_token_holders_df(bonk_mint, limit=5)
        if not holders_df.empty:
            for _, row in holders_df.iterrows():
                print(f"   #{int(row['rank'])}: {row['address'][:12]}... ({row['percentage']:.2f}%)")

    except Exception as e:
        print(f"   [Skipped - Helius API key required] {e}")


def example_custom_subgraph():
    """Example: Using your own deployed subgraph"""
    print("\n" + "=" * 60)
    print("CUSTOM SUBGRAPH EXAMPLE")
    print("=" * 60)

    print("""
    To use your own deployed subgraph:

    1. Deploy the ERC-20 tracker subgraph:
       cd defi_library/subgraphs/erc20-tracker
       npm install
       graph auth --studio YOUR_DEPLOY_KEY
       graph deploy --studio erc20-tracker-eth

    2. Query your subgraph:

       from blocks_scraping.dev.thegraph import ERC20Queries

       queries = ERC20Queries(
           subgraph_url="https://api.studio.thegraph.com/query/YOUR_ID/erc20-tracker-eth/v0.0.1"
       )

       # Get token balances
       balances = queries.get_token_balances(
           token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
           limit=100
       )

       # Get historical snapshots
       history = queries.get_balance_snapshots(
           token_address="0x...",
           account_address="0x...",
           from_block=18000000,
           to_block=18100000
       )

       # Get pool balances for price calculation
       pool_data = queries.get_pool_balances(
           pool_address="0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",  # USDC/ETH
           token0_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
           token1_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
       )
    """)


def main():
    print("=" * 60)
    print("  MULTI-CHAIN DEFI ANALYTICS DEMO")
    print("  Supports: Ethereum, BSC, Solana")
    print("=" * 60)

    # Run examples
    example_ethereum_queries()
    example_bsc_queries()
    example_solana_queries()
    example_custom_subgraph()

    print("\n" + "=" * 60)
    print("  MIGRATION COMPLETE!")
    print("=" * 60)
    print("""
    Summary of changes:
    - Cryo replaced with The Graph (ETH/BSC)
    - Solana support added via Helius
    - Monthly cost: 0-20 EUR (within budget)

    Next steps:
    1. Set up your API keys in .env
    2. Deploy the ERC-20 subgraph (optional, for custom tracking)
    3. Start building!

    See MIGRATION_PLAN.md for full documentation.
    """)


if __name__ == "__main__":
    main()

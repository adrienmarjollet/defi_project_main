import os
import time
from dotenv import load_dotenv
import cryo
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from web3 import Web3

# Constants
ETH_RPC_VAR = "ETH_RPC"
LOOKBACK_BLOCKS = 7200 # Approx a day in the past
CONTRACT_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2' # WETH
WALLET_ADDRESS = '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852'   # WETH-USDT pool Uniswap V2

# Initialize environment variables and Web3
load_dotenv()
eth_rpc = os.getenv(ETH_RPC_VAR)
w3 = Web3(Web3.HTTPProvider(eth_rpc))

def check_eth_rpc_connection(eth_rpc):
    """Check connection to Ethereum RPC."""
    if not eth_rpc:
        raise ValueError(f"Environment variable {ETH_RPC_VAR} not found")
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to Ethereum node.")

def get_block_range(lookback_blocks):
    """Determine the range of blocks to fetch."""
    latest_block = w3.eth.block_number
    start_block = max(0, latest_block - lookback_blocks)
    return f"{start_block}:{latest_block}"

def fetch_erc20_balances(block_range):
    """Fetch ERC-20 token balances within a given block range."""
    return cryo.collect(
        "erc20_balances",
        blocks=[block_range],
        contract=[CONTRACT_ADDRESS],
        address=[WALLET_ADDRESS],
        rpc=eth_rpc,
        output_format="pandas",
        hex=True,
        requests_per_second=900 # Adapt the RPS to your endpoint
    )

def convert_balance_to_ether(balance_str):
    """Convert balance from Wei to Ether, handling None values."""
    return None if balance_str is None else Web3.from_wei(int(balance_str), 'ether')

def plot_balance_change_over_time(data):
    """Plot the balance change over time on a chart."""
    plt.figure(figsize=(12, 6))
    plt.plot(data['block_number'], data['balance_ether'], marker='o')

    # Set axis labels and chart title with contract and address
    plt.xlabel("Block Number")
    plt.ylabel("Balance (Ether)")
    plt.title(f"ERC-20 Token Balance Change for {CONTRACT_ADDRESS}\nWallet {WALLET_ADDRESS}")

    # Manually set the x-axis ticks based on the block range
    block_numbers = data['block_number']
    tick_spacing = (block_numbers.max() - block_numbers.min()) // 10  # for example, 10 evenly spaced ticks
    ticks = range(int(block_numbers.min()), int(block_numbers.max()), int(tick_spacing))
    plt.xticks(ticks, [f"{tick:,.0f}" for tick in ticks])

    # Format the y-axis to show balances rounded to 4 decimal places
    plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.4f}'))

    # Add grid, tighten layout, and display the plot
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    """Main function to fetch and plot ERC-20 token balance changes."""
    check_eth_rpc_connection(eth_rpc)
    block_range = get_block_range(LOOKBACK_BLOCKS)

    # Start timing the data fetch
    start_time = time.time()

    # Fetch the data
    data = fetch_erc20_balances(block_range)

    # End timing the data fetch
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Data fetched in {elapsed_time:.2f} seconds.")

    if data.empty:
        print("No data available for plotting.")
        return
    
    # Prepare data for plotting
    data = data[['block_number', 'erc20', 'address', 'balance_string']]
    data['balance_ether'] = data['balance_string'].apply(convert_balance_to_ether)
    data = data[data['balance_ether'].notnull()]  # Filter out rows with None values

    # Print data summary to the console
    print("\nData summary:")
    print(f"Block rage: {block_range}")
    print(f"Start balance in Ether: {data.iloc[0]['balance_ether']}")
    print(f"End balance in Ether: {data.iloc[-1]['balance_ether']}")

    # Plot the balance changes over time
    plot_balance_change_over_time(data)

if __name__ == "__main__":
    main()
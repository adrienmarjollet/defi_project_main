import os
import time
from dotenv import load_dotenv
import cryo
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from web3 import Web3
import streamlit as st
import plotly.graph_objs as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Holders statistics", page_icon="📈")

# Constants
LOOKBACK_BLOCKS = 100 # Approx a day in the past
CONTRACT_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2' # WETH
WALLET_ADDRESS = '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852'   # WETH-USDT pool Uniswap V2

CONTRACT_ADDRESS = '0x6982508145454ce325ddbe47a25d4ec3d2311933' # PEPE
WALLET_ADDRESS = '0x1c06c36a559bbe99adece16eb7a63c5e997b2ef3'   # pepe whale
WALLET_ADDRESS = '0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852'   # WETH-USDT pool Uniswap V2
#TODO: fix it to display balance of any token

#TODO add manual selection from a choice of tokens in a dic in a SQL data base 


class EthRPC():
    def __init__(self):
        # load_dotenv()
        self.eth_rpc = os.getenv(ETH_RPC_VAR)
        self.w3 = Web3(Web3.HTTPProvider(self.eth_rpc))
        self.check_eth_rpc_connection()

    def check_eth_rpc_connection(self):
        """Check connection to Ethereum RPC."""
        if not self.eth_rpc:
            raise ValueError(f"Environment variable {ETH_RPC_VAR} not found")
        if not (self.w3).is_connected():
            raise ConnectionError("Failed to connect to Ethereum node.")

    def get_block_range(self,lookback_blocks):
        """Determine the range of blocks to fetch."""
        latest_block = (self.w3).eth.block_number
        start_block = max(0, latest_block - lookback_blocks)
        return f"{start_block}:{latest_block}"

    def fetch_erc20_balances(self,block_range):
        """Fetch ERC-20 token balances within a given block range."""
        return cryo.collect(
            "erc20_balances",
            blocks=[block_range],
            contract=[CONTRACT_ADDRESS],
            address=[WALLET_ADDRESS],
            rpc=self.eth_rpc,
            output_format="pandas",
            hex=True,
            requests_per_second=100)# Adapt the RPS to your endpoint)

    @staticmethod
    def convert_balance_to_ether(balance_str):
        """Convert balance from Wei to Ether, handling None values."""
        return None if balance_str is None else Web3.from_wei(int(balance_str), 'ether')

    def plot_balance_change_over_time(self,data):
        """Plot the balance change over time on a chart."""
        # Set the title of the Streamlit app
        st.title(f"ERC-20 Token Balance Change for {CONTRACT_ADDRESS}")
        st.subheader(f"Wallet {WALLET_ADDRESS}")

        # Create a figure
        fig = go.Figure()

        # Add a trace for the balance data
        fig.add_trace(go.Scatter(
            x=data['block_number'],
            y=data['balance_ether'],
            mode='lines+markers',
            marker=dict(symbol='circle', size=8),
            name='Balance'
        ))

        # Set axis labels and chart title
        fig.update_layout(
            xaxis_title="Block Number",
            yaxis_title="Balance (Ether)",
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(int(data['block_number'].min()), int(data['block_number'].max()), (data['block_number'].max() - data['block_number'].min()) // 10)),
                ticktext=[f"{tick:,.0f}" for tick in range(int(data['block_number'].min()), int(data['block_number'].max()), (data['block_number'].max() - data['block_number'].min()) // 10)]
            ),
            yaxis=dict(
                tickformat=".4f"  # Format y-axis ticks to 4 decimal places
            ),
            template="plotly_white"  # Use a clean theme
        )

        # Add grid
        fig.update_xaxes(showgrid=True)
        fig.update_yaxes(showgrid=True)

        # Display the plot in Streamlit
        st.plotly_chart(fig)

if __name__ == "__main__":

    ETH_RPC_VAR = "ETH_RPC"
    eth_rpc = os.getenv(ETH_RPC_VAR)
    w3 = Web3(Web3.HTTPProvider(eth_rpc))

    # initialize a new instance of the class
    rpc = EthRPC()     

    block_range = rpc.get_block_range(LOOKBACK_BLOCKS)
    # Fetch the data
    data = rpc.fetch_erc20_balances(block_range)

    if data.empty:
        st.write("No data available for plotting.")
        st.stop()

    # Prepare data for plotting
    data = data[['block_number', 'erc20', 'address', 'balance_string']]
    data['balance_ether'] = data['balance_string'].apply(rpc.convert_balance_to_ether)
    data = data[data['balance_ether'].notnull()]  # Filter out rows with None values

    # Plot the balance changes over time
    rpc.plot_balance_change_over_time(data)

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             

import os
from dotenv import load_dotenv
import cryo
from web3 import Web3
import streamlit as st
import plotly.graph_objs as go

# Import shared utilities
from utils.streamlit_config import (
    configure_page,
    setup_sidebar_header,
    COMMON_TOKENS,
)
from utils.components import token_selector

# Load environment variables
load_dotenv()

configure_page(page_title="Holders statistics", page_icon="📈", layout="centered")

# Environment variable name
ETH_RPC_VAR = "ETH_RPC_URL"

# Default values (can be overridden via UI)
DEFAULT_CONTRACT = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
DEFAULT_WALLET = "0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852"    # WETH-USDT pool Uniswap V2
DEFAULT_LOOKBACK = 100

# Sidebar configuration
setup_sidebar_header()

CONTRACT_ADDRESS = st.sidebar.text_input(
    "Token Contract Address",
    value=DEFAULT_CONTRACT,
    help="ERC-20 token contract address to analyze"
)

WALLET_ADDRESS = st.sidebar.text_input(
    "Wallet/Pool Address",
    value=DEFAULT_WALLET,
    help="Wallet or pool address to track balance"
)

LOOKBACK_BLOCKS = st.sidebar.slider(
    "Lookback Blocks",
    min_value=10,
    max_value=7200,
    value=DEFAULT_LOOKBACK,
    step=10,
    help="Number of blocks to look back (100 blocks ~ 20 minutes)"
)

# Quick token selection using shared component logic
selected_token = st.sidebar.selectbox(
    "Quick Select Token",
    options=["Custom"] + list(COMMON_TOKENS.keys()),
    help="Select a common token or use custom address above"
)

if selected_token != "Custom":
    CONTRACT_ADDRESS = COMMON_TOKENS[selected_token]


class EthRPC:
    def __init__(self):
        self.eth_rpc = os.getenv(ETH_RPC_VAR)
        self.w3 = Web3(Web3.HTTPProvider(self.eth_rpc))
        self.check_eth_rpc_connection()

    def check_eth_rpc_connection(self):
        """Check connection to Ethereum RPC."""
        if not self.eth_rpc:
            raise ValueError(f"Environment variable {ETH_RPC_VAR} not found")
        if not (self.w3).is_connected():
            raise ConnectionError("Failed to connect to Ethereum node.")

    def get_block_range(self, lookback_blocks):
        """Determine the range of blocks to fetch."""
        latest_block = (self.w3).eth.block_number
        start_block = max(0, latest_block - lookback_blocks)
        return f"{start_block}:{latest_block}"

    def fetch_erc20_balances(self, block_range, contract_address, wallet_address):
        """Fetch ERC-20 token balances within a given block range."""
        return cryo.collect(
            "erc20_balances",
            blocks=[block_range],
            contract=[contract_address],
            address=[wallet_address],
            rpc=self.eth_rpc,
            output_format="pandas",
            hex=True,
            requests_per_second=100)  # Adapt the RPS to your endpoint

    @staticmethod
    def convert_balance_to_ether(balance_str):
        """Convert balance from Wei to Ether, handling None values."""
        return None if balance_str is None else Web3.from_wei(int(balance_str), 'ether')

    def plot_balance_change_over_time(self, data, contract_address, wallet_address):
        """Plot the balance change over time on a chart."""
        # Set the title of the Streamlit app
        st.title(f"ERC-20 Token Balance Change for {contract_address}")
        st.subheader(f"Wallet {wallet_address}")

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


def main():
    """Main entry point for the Streamlit app."""
    try:
        rpc = EthRPC()
    except (ValueError, ConnectionError) as e:
        st.error(f"Connection Error: {e}")
        st.info(f"Please ensure the {ETH_RPC_VAR} environment variable is set correctly.")
        st.stop()

    block_range = rpc.get_block_range(LOOKBACK_BLOCKS)

    with st.spinner("Fetching balance data..."):
        data = rpc.fetch_erc20_balances(block_range, CONTRACT_ADDRESS, WALLET_ADDRESS)

    if data.empty:
        st.warning("No data available for the selected parameters.")
        st.info("Try adjusting the contract address, wallet address, or lookback period.")
        st.stop()

    # Prepare data for plotting
    data = data[["block_number", "erc20", "address", "balance_string"]]
    data["balance_ether"] = data["balance_string"].apply(rpc.convert_balance_to_ether)
    data = data[data["balance_ether"].notnull()]

    if data.empty:
        st.warning("No valid balance data found after processing.")
        st.stop()

    # Display summary stats
    st.sidebar.markdown("---")
    st.sidebar.subheader("Summary")
    st.sidebar.metric("Data Points", len(data))
    st.sidebar.metric("Latest Balance", f"{data['balance_ether'].iloc[-1]:.4f}")

    # Plot the balance changes over time
    rpc.plot_balance_change_over_time(data, CONTRACT_ADDRESS, WALLET_ADDRESS)


if __name__ == "__main__":
    main()

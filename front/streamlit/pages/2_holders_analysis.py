import os
import cryo
from web3 import Web3
import streamlit as st
import plotly.graph_objs as go

st.set_page_config(page_title="Holders statistics", page_icon="📈")

# Environment variable for RPC endpoint
ETH_RPC_VAR = "ETH_RPC" 


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

if __name__ == "__main__":

    # Sidebar configuration
    st.sidebar.header("Configuration")
    CONTRACT_ADDRESS = st.sidebar.text_input(
        "Token Contract Address",
        value="0x6982508145454ce325ddbe47a25d4ec3d2311933",
        help="ERC-20 token contract address (default: PEPE)"
    )
    WALLET_ADDRESS = st.sidebar.text_input(
        "Wallet/Pool Address",
        value="0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852",
        help="Address to track - wallet or liquidity pool (default: WETH-USDT Uniswap V2 pool)"
    )
    LOOKBACK_BLOCKS = st.sidebar.slider(
        "Lookback Blocks",
        min_value=10,
        max_value=1000,
        value=100,
        help="Number of blocks to look back (approx 100 blocks = 1 day)"
    )

    # Initialize RPC connection
    eth_rpc = os.getenv(ETH_RPC_VAR)
    w3 = Web3(Web3.HTTPProvider(eth_rpc))

    # Initialize a new instance of the class
    rpc = EthRPC()

    block_range = rpc.get_block_range(LOOKBACK_BLOCKS)
    # Fetch the data
    data = rpc.fetch_erc20_balances(block_range, CONTRACT_ADDRESS, WALLET_ADDRESS)

    if data.empty:
        st.write("No data available for plotting.")
        st.stop()

    # Prepare data for plotting
    data = data[['block_number', 'erc20', 'address', 'balance_string']]
    data['balance_ether'] = data['balance_string'].apply(rpc.convert_balance_to_ether)
    data = data[data['balance_ether'].notnull()]  # Filter out rows with None values

    # Plot the balance changes over time
    rpc.plot_balance_change_over_time(data, CONTRACT_ADDRESS, WALLET_ADDRESS)

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             

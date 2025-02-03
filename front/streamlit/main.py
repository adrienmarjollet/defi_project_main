import os
import time
from dotenv import load_dotenv
import cryo
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from web3 import Web3
import streamlit as st

st.set_page_config(page_title="Ethereum Token Analyzer", page_icon="🔍", layout="wide")

# Initialize environment variables and Web3 
load_dotenv()
#TODO: put in a config file later
ETH_RPC_VAR = "ETH_RPC"
eth_rpc = os.getenv(ETH_RPC_VAR)
w3 = Web3(Web3.HTTPProvider(eth_rpc))

# ADD all init from chainstack code ?                       


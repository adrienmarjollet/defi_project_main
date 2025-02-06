import os
import cryo
from dotenv import load_dotenv
from web3 import Web3

# dev imports
from python.dev.common.misc import find_project_root_path, load_env_variables



class cryo_tools:

    def __init__(self):
        
        try:
            self.root_path = find_project_root_path()
        except FileNotFoundError as e:    
            raise FileNotFoundError(f'Could not find the project root path: {e}')
        
    # def load_env_variables(self):
    #     dotenv_path = os.path.join(self.root_path, 'env_variables', '.env')
    #     load_dotenv(dotenv_path)
        
    #     # Retrieve the Ethereum RPC URL from environment variables
    #     ETH_RPC_NAME = "ETH_RPC"
    #     self.eth_rpc = os.getenv(ETH_RPC_NAME)
    #     # check that the RPC URL is set
    #     if self.eth_rpc is None:
    #         raise ValueError("ETH_RPC is not set in the .env file")
    #     else:
    #         print(f'Env variable {ETH_RPC_NAME} loaded.')    


        









# Find the project root path
root_path = find_project_root_path()



# Load the environment variables
dotenv_path = os.path.join(parent_dir, 'env_variables', '.env')
load_dotenv(dotenv_path)

# Retrieve the Ethereum RPC URL from environment variables
ETH_RPC_NAME = "ETH_RPC"
eth_rpc = os.getenv(ETH_RPC_NAME)
# check that the RPC URL is set
if eth_rpc is None:
    raise ValueError("ETH_RPC is not set in the .env file")
else:
    print(f'Env variable {ETH_RPC_NAME} loaded.')

# TEST OF THE RPC URL WITH web3
web3 = Web3(Web3.HTTPProvider(eth_rpc))
if web3.is_connected():
    print("Connected to Ethereum node")
else:
    raise ValueError("Could not connect to Ethereum node")

# test a simple cryo query
try:
    data = cryo.collect("blocks", blocks=["21782280:21782281"], rpc=eth_rpc, output_format="pandas", hex=True)
    print('Cryo (collect) query successful')
except Exception as e:    
    print(f'cryo query failed: {e}')
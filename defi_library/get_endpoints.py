import requests
import os
import logging
from dotenv import load_dotenv
from web3 import Web3
from typing import Optional, Dict, Any

# Load environment variables
load_dotenv()

# Constants
CHAINSTACK_API_KEY = os.getenv('CHAINSTACK_API_KEY')
OUTPUT_FILE_NAME = 'rpc.env'

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_chainstack_data(api_key: str) -> Optional[Dict[str, Any]]:
    """Fetch data from Chainstack API."""
    url = "https://api.chainstack.com/v1/nodes/"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Fetched {len(data.get('results', []))} items from Chainstack.")
        return data
    except requests.RequestException as e:
        logging.error(f"Failed to fetch data from Chainstack: {e}")
        return None

def process_chainstack_item(item: Dict[str, Any]) -> Dict[str, str]:
    """Process a single item from Chainstack data."""
    logging.debug(f"Processing item: {item['name']} with ID {item['id']}")
    return {
        'id': item['id'],
        'name': item['name'],
        'details': item['details'],
        'http_endpoint': item['details'].get('https_endpoint'),
        'auth_key': item['details'].get('auth_key'),
        'configuration': item['configuration'],
        'client': item['configuration'].get('client')
    }

def connect_to_web3(reconstructed_endpoint: str) -> bool:
    """Connect to a Web3 endpoint."""
    logging.debug(f"Attempting to connect to Web3 endpoint: {reconstructed_endpoint}")
    try:
        w3 = Web3(Web3.HTTPProvider(reconstructed_endpoint))
        if w3.is_connected():
            chain_id = w3.eth.chain_id
            logging.info(f"Connected to {reconstructed_endpoint} with chain ID: {chain_id}")
            return True
        else:
            logging.warning(f"Failed to connect to {reconstructed_endpoint}")
    except Exception as e:
        logging.error(f"An error occurred while connecting to {reconstructed_endpoint}: {e}")
    return False

def sanitize_name(name: str) -> str:
    """Sanitize the endpoint name for use as an environment variable key."""
    return name.replace(" ", "_").replace("-", "_").replace("/", "_").upper()


def create_env_file(endpoint_info_dict: Dict[str, Dict[str, str]], filename: str = OUTPUT_FILE_NAME) -> None:
    """Create a .env file from the endpoint info dictionary."""
    logging.info(f"Preparing to write {len(endpoint_info_dict)} endpoints to .env file.")
    with open(filename, 'w') as file:
        for endpoint, info in endpoint_info_dict.items():
            sanitized_name = sanitize_name(info['name'])
            file.write(f'{sanitized_name}_URL="{endpoint}"\n')
        logging.info(f".env file created successfully at {filename}.")

def main() -> None:
    """Main function to orchestrate the process."""
    logging.info("Starting main process.")
    if not CHAINSTACK_API_KEY:
        logging.error("Chainstack API key not found.")
        return

    json_data = fetch_chainstack_data(CHAINSTACK_API_KEY)
    if not json_data:
        return

    endpoint_info_dict = {}
    for item in json_data.get('results', []):
        data = process_chainstack_item(item)
        reconstructed_endpoint = f"{data['http_endpoint']}/{data['auth_key']}"
        if connect_to_web3(reconstructed_endpoint):
            endpoint_info_dict[reconstructed_endpoint] = {'name': data['name']}

    if endpoint_info_dict:
        create_env_file(endpoint_info_dict)
    else:
        logging.info("No endpoint information to write to .env file.")
    logging.info("Main process completed.")

if __name__ == "__main__":
    main()

"""Shared Web3 connection manager for the DeFi project."""
import logging
from typing import Optional

from web3 import Web3

from config import ETH_RPC_URL
from common.misc import find_project_root_path, load_env_variables

logger = logging.getLogger(__name__)

# Module-level connection cache
_web3_instance: Optional[Web3] = None
_rpc_url: Optional[str] = None


def get_web3(provider_url: Optional[str] = None) -> Web3:
    """
    Get a Web3 connection instance.

    Uses a cached connection if available, or creates a new one.

    Args:
        provider_url: Optional RPC URL. If not provided, loads from environment.

    Returns:
        Connected Web3 instance.

    Raises:
        ConnectionError: If connection to Ethereum node fails.
    """
    global _web3_instance, _rpc_url

    # Return cached instance if no new URL provided and we have a connection
    if _web3_instance is not None and provider_url is None:
        return _web3_instance

    # Determine RPC URL
    if provider_url:
        url = provider_url
    else:
        root_path = find_project_root_path()
        url = load_env_variables(root_path, [ETH_RPC_URL])[0]

    # Create new connection
    web3 = Web3(Web3.HTTPProvider(url))

    if not web3.is_connected():
        raise ConnectionError(f"Failed to connect to Ethereum node at {url}")

    logger.info("Successfully connected to Ethereum node")

    # Cache the connection
    _web3_instance = web3
    _rpc_url = url

    return web3


def get_rpc_url() -> Optional[str]:
    """Get the current RPC URL."""
    return _rpc_url


def reset_connection():
    """Reset the cached connection (useful for testing)."""
    global _web3_instance, _rpc_url
    _web3_instance = None
    _rpc_url = None

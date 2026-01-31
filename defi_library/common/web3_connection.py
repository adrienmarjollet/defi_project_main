"""Shared Web3 connection manager for the DeFi project."""
import logging
from web3 import Web3

from config import ETH_RPC_URL
from common.misc import find_project_root_path, load_env_variables

logger = logging.getLogger(__name__)


class Web3ConnectionManager:
    """Singleton class to manage Web3 connections."""

    _instance = None
    _web3 = None
    _rpc_url = None

    def __new__(cls, provider_url: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(provider_url)
        return cls._instance

    def _initialize(self, provider_url: str = None):
        """Initialize the Web3 connection."""
        if provider_url:
            self._rpc_url = provider_url
        else:
            root_path = find_project_root_path()
            self._rpc_url = load_env_variables(root_path, [ETH_RPC_URL])[0]

        self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))

        if not self._web3.is_connected():
            raise ConnectionError(f"Failed to connect to Ethereum node at {self._rpc_url}")

        logger.info("Successfully connected to Ethereum node")

    @property
    def web3(self) -> Web3:
        """Get the Web3 instance."""
        return self._web3

    @property
    def rpc_url(self) -> str:
        """Get the RPC URL."""
        return self._rpc_url

    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
        cls._web3 = None
        cls._rpc_url = None

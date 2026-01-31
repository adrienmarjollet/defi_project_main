"""
The Graph Integration Module

Provides GraphQL client for querying indexed blockchain data from The Graph protocol.
Supports Ethereum, BSC, and other EVM-compatible chains.
"""

from .graph_client import GraphClient
from .queries import ERC20Queries

__all__ = ["GraphClient", "ERC20Queries"]

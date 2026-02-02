"""
The Graph Integration Module

Provides GraphQL client for querying indexed blockchain data from The Graph protocol.
Supports Ethereum, BSC, and other EVM-compatible chains.

Modules:
- graph_client: Core GraphQL client for The Graph protocol
- base_queries: Common base class and utilities for all query classes
- queries: ERC-20 token queries
- whale_tracking_queries: Whale (top holder) tracking and analysis
- holder_count_queries: Holder count history and growth metrics
- holder_distribution_queries: Distribution analysis (Gini, tiers, concentration)
- bubble_map_queries: Bubble map visualization data
- token_health_score_queries: Composite health score calculation
- suspicious_activity_queries: Manipulation and scam pattern detection
"""

from .graph_client import GraphClient
from .queries import ERC20Queries
from .base_queries import (
    BaseQueries,
    BLOCKS_PER_MINUTE,
    BLOCKS_PER_HOUR,
    BLOCKS_PER_DAY,
    BLOCKS_PER_WEEK,
    BLOCKS_PER_MONTH,
    format_address,
    normalize_address,
    classify_holder_tier,
)

__all__ = [
    # Core client
    "GraphClient",
    # Base class and utilities
    "BaseQueries",
    "format_address",
    "normalize_address",
    "classify_holder_tier",
    # Constants
    "BLOCKS_PER_MINUTE",
    "BLOCKS_PER_HOUR",
    "BLOCKS_PER_DAY",
    "BLOCKS_PER_WEEK",
    "BLOCKS_PER_MONTH",
    # Query classes
    "ERC20Queries",
]

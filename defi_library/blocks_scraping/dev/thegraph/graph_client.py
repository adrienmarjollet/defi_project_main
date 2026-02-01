"""
The Graph Protocol Client

A Python client for querying The Graph subgraphs.
Supports both hosted service (Subgraph Studio) and self-hosted Graph nodes.
"""

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import requests

from config import THEGRAPH_API_KEY
from common.misc import find_project_root_path, load_env_variables

logger = logging.getLogger(__name__)


@dataclass
class SubgraphEndpoint:
    """Configuration for a subgraph endpoint"""
    name: str
    url: str
    chain: str
    is_self_hosted: bool = False


# Pre-configured public subgraph endpoints (free to query)
PUBLIC_SUBGRAPHS = {
    # Uniswap V3 subgraphs (official)
    "uniswap_v3_eth": SubgraphEndpoint(
        name="Uniswap V3 Ethereum",
        url="https://gateway.thegraph.com/api/{api_key}/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
        chain="ethereum"
    ),
    "uniswap_v3_bsc": SubgraphEndpoint(
        name="Uniswap V3 BSC",
        url="https://gateway.thegraph.com/api/{api_key}/subgraphs/id/F85MNzUGYqgSHSHRGgeVMNsdnW1KtZSVgFULumXRZTw2",
        chain="bsc"
    ),
    # PancakeSwap (BSC)
    "pancakeswap_v3_bsc": SubgraphEndpoint(
        name="PancakeSwap V3 BSC",
        url="https://gateway.thegraph.com/api/{api_key}/subgraphs/id/Hv1GncLY5docZoGtXjo4kwbTvxm3MAhVZqBZE4sUT9eZ",
        chain="bsc"
    ),
}


class GraphClient:
    """
    Client for querying The Graph protocol subgraphs.

    Supports:
    - Subgraph Studio (hosted, free tier)
    - Self-hosted Graph nodes
    - Decentralized network (requires GRT)

    Example usage:
        client = GraphClient()

        # Query a public subgraph
        result = client.query(
            endpoint="uniswap_v3_eth",
            query='''
                { pools(first: 10) { id token0 { symbol } token1 { symbol } } }
            '''
        )

        # Query a custom subgraph URL
        result = client.query(
            endpoint="https://api.studio.thegraph.com/query/12345/my-subgraph/v0.0.1",
            query="{ tokens(first: 10) { id name symbol } }"
        )
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Graph client.

        Args:
            api_key: Optional API key for The Graph Gateway.
                     If not provided, will try to load from environment.
        """
        self.root_path = find_project_root_path()

        if api_key:
            self._api_key = api_key
        else:
            try:
                self._api_key = load_env_variables(self.root_path, [THEGRAPH_API_KEY])[0]
            except Exception:
                self._api_key = None
                logger.warning(
                    "No Graph API key found. Some subgraphs may not be accessible. "
                    "Set THEGRAPH_API_KEY in your .env file."
                )

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
        })

    def _get_endpoint_url(self, endpoint: Union[str, SubgraphEndpoint]) -> str:
        """Resolve endpoint to a URL."""
        if isinstance(endpoint, SubgraphEndpoint):
            url = endpoint.url
        elif endpoint in PUBLIC_SUBGRAPHS:
            url = PUBLIC_SUBGRAPHS[endpoint].url
        else:
            # Assume it's a direct URL
            url = endpoint

        # Replace API key placeholder if present
        if "{api_key}" in url:
            if not self._api_key:
                raise ValueError(
                    f"Endpoint {endpoint} requires an API key. "
                    "Set THEGRAPH_API_KEY in your environment."
                )
            url = url.replace("{api_key}", self._api_key)

        return url

    def query(
        self,
        endpoint: Union[str, SubgraphEndpoint],
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query against a subgraph.

        Args:
            endpoint: Subgraph endpoint (name from PUBLIC_SUBGRAPHS, URL, or SubgraphEndpoint)
            query: GraphQL query string
            variables: Optional variables for the query
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            Query result as a dictionary

        Raises:
            GraphQueryError: If the query fails after all retries
        """
        url = self._get_endpoint_url(endpoint)

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self._session.post(url, json=payload, timeout=30)
                response.raise_for_status()

                data = response.json()

                if "errors" in data:
                    error_msg = "; ".join(e.get("message", str(e)) for e in data["errors"])
                    raise GraphQueryError(f"GraphQL errors: {error_msg}")

                return data.get("data", {})

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Query failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Query failed after {max_retries + 1} attempts: {e}")

        raise GraphQueryError(f"Query failed after {max_retries + 1} attempts: {last_error}")

    def paginated_query(
        self,
        endpoint: Union[str, SubgraphEndpoint],
        query_template: str,
        entity_name: str,
        page_size: int = 1000,
        max_pages: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a paginated query to fetch all results.

        The Graph limits results to 1000 items per query.
        This method handles pagination automatically.

        Args:
            endpoint: Subgraph endpoint
            query_template: Query with {skip} and {first} placeholders
            entity_name: Name of the entity being queried (for extraction)
            page_size: Number of items per page (max 1000)
            max_pages: Maximum number of pages to fetch (None for all)
            variables: Additional variables for the query

        Returns:
            List of all results

        Example:
            results = client.paginated_query(
                endpoint="uniswap_v3_eth",
                query_template='''
                    query($skip: Int!, $first: Int!) {
                        pools(skip: $skip, first: $first, orderBy: totalValueLockedUSD, orderDirection: desc) {
                            id
                            token0 { symbol }
                            token1 { symbol }
                        }
                    }
                ''',
                entity_name="pools",
                page_size=1000
            )
        """
        all_results = []
        skip = 0
        page = 0

        while True:
            if max_pages and page >= max_pages:
                break

            query_vars = {"skip": skip, "first": page_size}
            if variables:
                query_vars.update(variables)

            result = self.query(endpoint, query_template, query_vars)

            items = result.get(entity_name, [])
            if not items:
                break

            all_results.extend(items)

            if len(items) < page_size:
                # Last page
                break

            skip += page_size
            page += 1

            logger.debug(f"Fetched page {page}, total items: {len(all_results)}")

        return all_results

    def query_to_dataframe(
        self,
        endpoint: Union[str, SubgraphEndpoint],
        query: str,
        entity_name: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Execute a query and return results as a pandas DataFrame.

        Args:
            endpoint: Subgraph endpoint
            query: GraphQL query string
            entity_name: Name of the entity to extract from results
            variables: Optional query variables

        Returns:
            pandas DataFrame with query results
        """
        result = self.query(endpoint, query, variables)
        items = result.get(entity_name, [])

        if not items:
            return pd.DataFrame()

        return pd.DataFrame(items)


class GraphQueryError(Exception):
    """Raised when a Graph query fails."""
    pass


# Utility functions for common conversions
def wei_to_ether(wei_value: Union[str, int]) -> Decimal:
    """Convert Wei to Ether."""
    return Decimal(str(wei_value)) / Decimal("10") ** 18


def raw_to_decimal(raw_value: Union[str, int], decimals: int) -> Decimal:
    """Convert raw token amount to decimal representation."""
    return Decimal(str(raw_value)) / Decimal("10") ** decimals


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)

    client = GraphClient()

    # Test with a public Uniswap subgraph (if API key is set)
    try:
        result = client.query(
            endpoint="uniswap_v3_eth",
            query="""
            {
                pools(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc) {
                    id
                    token0 { symbol }
                    token1 { symbol }
                    totalValueLockedUSD
                }
            }
            """
        )
        print("Top 5 Uniswap V3 pools by TVL:")
        for pool in result.get("pools", []):
            print(f"  {pool['token0']['symbol']}/{pool['token1']['symbol']}: ${float(pool['totalValueLockedUSD']):,.0f}")
    except Exception as e:
        print(f"Query failed (expected if no API key): {e}")

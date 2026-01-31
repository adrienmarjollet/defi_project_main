"""Utility functions for unit conversions in the DeFi project."""
from decimal import Decimal
from typing import Optional, Union
from web3 import Web3


def wei_to_ether(balance: Union[str, int, None]) -> Optional[Decimal]:
    """
    Convert balance from Wei to Ether with proper precision.

    Args:
        balance: Balance in Wei as string, int, or None

    Returns:
        Balance in Ether as Decimal, or None if input is None
    """
    if balance is None:
        return None
    return Decimal(str(Web3.from_wei(int(balance), 'ether')))


def wei_to_ether_float(balance: Union[str, int, None]) -> Optional[float]:
    """
    Convert balance from Wei to Ether, returning float for compatibility.

    Args:
        balance: Balance in Wei as string, int, or None

    Returns:
        Balance in Ether as float, or None if input is None
    """
    result = wei_to_ether(balance)
    return float(result) if result is not None else None


def token_units_to_decimal(balance: Union[str, int], decimals: int) -> Decimal:
    """
    Convert token balance from smallest units to decimal representation.

    Args:
        balance: Token balance in smallest units
        decimals: Number of decimals for the token

    Returns:
        Balance as Decimal
    """
    return Decimal(str(balance)) / (Decimal(10) ** decimals)

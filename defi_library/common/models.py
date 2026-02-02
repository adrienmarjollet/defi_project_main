"""Database models for DeFi analytics tracking."""

from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .db_config import DATABASE_URI

Base = declarative_base()


class ERC20Balance(Base):
    """Model for tracking ERC20 token balances."""
    __tablename__ = "erc20_balances"
    id = Column(Integer, primary_key=True)
    chain_id = Column(Integer)
    block_number = Column(Integer)
    erc20 = Column(String)
    address = Column(String)
    balance = Column(Float)


class HolderCountSnapshot(Base):
    """
    Model for storing historical holder count snapshots.

    Used to track unique holder count evolution over time
    for detecting growth/decline trends.
    """
    __tablename__ = "holder_count_snapshots"

    id = Column(Integer, primary_key=True)
    token_address = Column(String(42), nullable=False, index=True)
    holder_count = Column(Integer, nullable=False)
    block_number = Column(Integer, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    chain_id = Column(Integer, default=1)  # 1 = Ethereum mainnet
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_holder_snapshots_token_block', 'token_address', 'block_number'),
        Index('ix_holder_snapshots_token_timestamp', 'token_address', 'timestamp'),
    )


class HolderDistributionSnapshot(Base):
    """
    Model for storing holder distribution analysis snapshots.

    Used to track distribution metrics over time including
    Gini coefficient, holder tiers, and concentration metrics.
    """
    __tablename__ = "holder_distribution_snapshots"

    id = Column(Integer, primary_key=True)
    token_address = Column(String(42), nullable=False, index=True)
    gini_coefficient = Column(Float, nullable=False)
    top_10_concentration = Column(Float, nullable=False)
    top_50_concentration = Column(Float, nullable=False)
    whale_count = Column(Integer, nullable=False)  # >1% of supply
    dolphin_count = Column(Integer, nullable=False)  # 0.1-1% of supply
    fish_count = Column(Integer, nullable=False)  # <0.1% of supply
    total_holders = Column(Integer, nullable=False)
    herfindahl_index = Column(Float, nullable=True)  # HHI
    block_number = Column(Integer, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    chain_id = Column(Integer, default=1)  # 1 = Ethereum mainnet
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_distribution_snapshots_token_block', 'token_address', 'block_number'),
        Index('ix_distribution_snapshots_token_timestamp', 'token_address', 'timestamp'),
    )


engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()


def create_tables():
    Base.metadata.create_all(engine)

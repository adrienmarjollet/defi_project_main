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


class WhaleTrackingSnapshot(Base):
    """
    Model for storing whale (top holder) tracking snapshots.

    Used to track individual whale balances over time for
    monitoring accumulation/distribution patterns and large movements.
    """
    __tablename__ = "whale_tracking_snapshots"

    id = Column(Integer, primary_key=True)
    token_address = Column(String(42), nullable=False, index=True)
    whale_address = Column(String(42), nullable=False, index=True)
    balance = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)  # % of total supply
    rank = Column(Integer, nullable=True)  # Rank among holders at this snapshot
    block_number = Column(Integer, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    chain_id = Column(Integer, default=1)  # 1 = Ethereum mainnet
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('ix_whale_snapshots_token_block', 'token_address', 'block_number'),
        Index('ix_whale_snapshots_token_whale', 'token_address', 'whale_address'),
        Index('ix_whale_snapshots_token_whale_timestamp', 'token_address', 'whale_address', 'timestamp'),
    )


class TokenHealthScoreSnapshot(Base):
    """
    Model for storing token health score snapshots.

    Used to track composite health scores over time including
    component scores for holder count, concentration, growth trend,
    whale stability, and contract ratio.
    """
    __tablename__ = "token_health_score_snapshots"

    id = Column(Integer, primary_key=True)
    token_address = Column(String(42), nullable=False, index=True)
    overall_score = Column(Float, nullable=False)  # 0-100
    holder_count_score = Column(Float, nullable=False)  # Component scores
    concentration_score = Column(Float, nullable=False)
    growth_trend_score = Column(Float, nullable=False)
    whale_stability_score = Column(Float, nullable=False)
    contract_ratio_score = Column(Float, nullable=False)
    health_grade = Column(String(1), nullable=False)  # A, B, C, D, F
    risk_level = Column(String(10), nullable=False)  # Low, Medium, High, Critical
    holder_count = Column(Integer, nullable=True)
    block_number = Column(Integer, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    chain_id = Column(Integer, default=1)  # 1 = Ethereum mainnet
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('ix_health_snapshots_token_block', 'token_address', 'block_number'),
        Index('ix_health_snapshots_token_timestamp', 'token_address', 'timestamp'),
    )


class SuspiciousActivitySnapshot(Base):
    """
    Model for storing suspicious activity detection snapshots.

    Used to track detected manipulation patterns and red flags
    including wash trading, concentration spikes, coordinated wallets,
    dump patterns, and Sybil cluster detection.
    """
    __tablename__ = "suspicious_activity_snapshots"

    id = Column(Integer, primary_key=True)
    token_address = Column(String(42), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)  # wash_trading, concentration_spike, etc.
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    description = Column(String(500), nullable=True)
    involved_addresses = Column(String(2000), nullable=True)  # JSON array of addresses
    evidence = Column(String(2000), nullable=True)  # JSON evidence data
    risk_score = Column(Float, nullable=False)  # 0-100 contribution to overall risk
    block_number = Column(Integer, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    chain_id = Column(Integer, default=1)  # 1 = Ethereum mainnet
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('ix_suspicious_activity_token_block', 'token_address', 'block_number'),
        Index('ix_suspicious_activity_token_timestamp', 'token_address', 'timestamp'),
        Index('ix_suspicious_activity_token_type', 'token_address', 'activity_type'),
    )


engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()


def create_tables():
    Base.metadata.create_all(engine)

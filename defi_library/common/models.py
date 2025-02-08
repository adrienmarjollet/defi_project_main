""" " This module contains the database models for the ERC20Balance table."""

from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .db_config import DATABASE_URI

Base = declarative_base()


class ERC20Balance(Base):
    __tablename__ = "erc20_balances"
    id = Column(Integer, primary_key=True)
    chain_id = Column(Integer)
    block_number = Column(Integer)
    erc20 = Column(String)
    address = Column(String)
    balance = Column(Float)


engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()


def create_tables():
    Base.metadata.create_all(engine)

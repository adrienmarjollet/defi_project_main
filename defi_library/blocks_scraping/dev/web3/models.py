from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ContractCache(Base):
    __tablename__ = "contract_cache"

    contract_address = Column(
        String(66), primary_key=True
    )  # Ethereum addresses are 42 chars
    abi = Column(String)
    decimals = Column(Integer)
    name = Column(String(50))  # Add reasonable length limit
    # TODO: add symbol,


# class Token(Base):
#     __tablename__ = 'tokens'

#     address = Column(String, primary_key=True)
#     name = Column(String)
#     symbol = Column(String)
#     total_supply = Column(Float)
#     # Reference to ContractCache
#     contract_data = relationship("ContractCache", backref="token")

# class Transaction(Base):
#     __tablename__ = 'transactions'

#     tx_hash = Column(String, primary_key=True)
#     from_address = Column(String)
#     to_address = Column(String)
#     value = Column(Float)
#     timestamp = Column(DateTime)
#     # Foreign key to Token
#     token_address = Column(String, ForeignKey('tokens.address'))
#     token = relationship("Token", backref="transactions")

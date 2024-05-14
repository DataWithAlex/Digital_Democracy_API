from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, BIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()

class BillRequest(BaseModel):
    url: str
    lan: str  # Language field

class Bill(Base):
    __tablename__ = 'bill'

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    govId = Column(String(10))
    billTextPath = Column(String(255))
    history = Column(String(255))  # New history column
    webflow_link = Column(String(255))


class BillMeta(Base):
    __tablename__ = 'bill_meta'

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    billId = Column(BIGINT, ForeignKey('bill.id'))
    type = Column(Enum('Pro', 'Con', 'Summary', name='meta_type'))
    text = Column(Text)
    language = Column(String(2))

    # Relationship to link back to the bill
    bill = relationship("Bill")


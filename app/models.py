from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, BIGINT, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel as PydanticBaseModel
import datetime

Base = declarative_base()

# Pydantic models for request validation
class BillRequest(PydanticBaseModel):
    url: str
    lan: str  # Language field

class FormRequest(PydanticBaseModel):
    name: str
    email: str
    member_organization: str
    year: str
    legislation_type: str
    session: str
    bill_number: str
    bill_type: str
    support: str

# SQLAlchemy models
class Bill(Base):
    __tablename__ = 'bill'

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    govId = Column(String(10))
    billTextPath = Column(String(255))
    history = Column(String(255))  # New history column
    webflow_link = Column(String(255))
    webflow_item_id = Column(String(255))  # New webflow item ID column

class BillMeta(Base):
    __tablename__ = 'bill_meta'

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    billId = Column(BIGINT, ForeignKey('bill.id'))
    type = Column(Enum('Pro', 'Con', 'Summary', name='meta_type'))
    text = Column(Text)
    language = Column(String(2))

    # Relationship to link back to the bill
    bill = relationship("Bill")

class FormData(Base):
    __tablename__ = 'form_data'

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(255))
    email = Column(String(255))
    member_organization = Column(String(255))
    year = Column(String(4))
    legislation_type = Column(String(50))
    session = Column(String(10))
    bill_number = Column(String(50))
    bill_type = Column(String(50))
    support = Column(String(10))
    govId = Column(String(50))
    created_at = Column(DateTime, default=datetime.datetime.now)

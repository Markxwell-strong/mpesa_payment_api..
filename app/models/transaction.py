from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, func
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    account_reference = Column(String(100), nullable=True, index=True)
    transaction_description = Column(String(250), nullable=True)

    merchant_request_id = Column(String(100), nullable=True)
    checkout_request_id = Column(String(100), unique=True, nullable=True, index=True)
    mpesa_receipt_number = Column(String(50), unique=True, nullable=True, index=True)

    result_code = Column(Integer, nullable=True)
    result_description = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

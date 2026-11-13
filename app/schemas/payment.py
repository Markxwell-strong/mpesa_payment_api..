from pydantic import BaseModel, Field, ConfigDict


class PaymentRequest(BaseModel):
    phone_number: str = Field(pattern=r"^254(?:7|1)\d{8}$")
    amount: int = Field(gt=0)
    account_reference: str = Field(min_length=1, max_length=100)
    transaction_description: str = Field(min_length=1, max_length=250)


class PaymentResponse(BaseModel):
    transaction_id: int
    status: str
    message: str


class MpesaCallback(BaseModel):
    Body: dict


class ReversalRequestBody(BaseModel):
    transaction_id: int = Field(gt=0)
    amount: int = Field(gt=0)
    remarks: str = Field(min_length=1, max_length=100)
    occasion: str | None = Field(default=None, max_length=100)


class ReversalResponse(BaseModel):
    reversal_id: int
    status: str
    message: str


class ReversalCallback(BaseModel):
    Result: dict


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    phone_number: str
    amount: float
    account_reference: str | None
    mpesa_receipt_number: str | None
    status: str

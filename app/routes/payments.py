from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.security import verify_api_key
from app.database import get_db
from app.config import settings
from app.models.transaction import Transaction
from app.models.reversal import ReversalRequest
from app.schemas.payment import (
    PaymentRequest, PaymentResponse, MpesaCallback,
    ReversalRequestBody, ReversalResponse, ReversalCallback,
)
from app.services.payment_services import create_payment_transaction
from app.services.reversal_service import request_reversal

router = APIRouter(prefix="/api/v1/payment", tags=["Payment"])


@router.post("/stkpush", response_model=PaymentResponse)
async def stk_push(
    payment: PaymentRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    if not settings.daraja_callback_url:
        raise HTTPException(status_code=500, detail="Payment callback URL is not configured")
    try:
        result = await create_payment_transaction(
            db=db,
            phone_number=payment.phone_number,
            amount=payment.amount,
            callback_url=settings.daraja_callback_url,
            account_reference=payment.account_reference,
            transaction_description=payment.transaction_description,
        )
        return PaymentResponse(
            transaction_id=result["transaction_id"],
            status=result["status"],
            message="STK Push request submitted. Awaiting payment confirmation.",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to initiate M-Pesa payment") from exc


@router.post("/callback")
async def mpesa_callback(callback: MpesaCallback, db: Session = Depends(get_db)):
    try:
        stk = callback.Body.get("stkCallback", {})
        checkout_id = stk.get("CheckoutRequestID")
        result_code = stk.get("ResultCode")
        if not checkout_id or result_code is None:
            raise HTTPException(status_code=400, detail="Invalid callback data")

        transaction = (
            db.query(Transaction)
            .filter(Transaction.checkout_request_id == checkout_id)
            .with_for_update()
            .first()
        )
        if not transaction:
            return {"ResultCode": 0, "ResultDesc": "Accepted"}

        if transaction.status in ("completed", "failed"):
            return {"ResultCode": 0, "ResultDesc": "Already processed"}

        transaction.result_code = int(result_code)
        transaction.result_description = stk.get("ResultDesc", "")
        if int(result_code) == 0:
            items = stk.get("CallbackMetadata", {}).get("Item", [])
            details = {item.get("Name"): item.get("Value") for item in items if isinstance(item, dict)}
            try:
                amount_ok = Decimal(str(details.get("Amount"))) == Decimal(str(transaction.amount))
            except (InvalidOperation, TypeError):
                amount_ok = False
            phone_ok = str(details.get("PhoneNumber", "")) == transaction.phone_number
            receipt = details.get("MpesaReceiptNumber")
            if receipt and amount_ok and phone_ok:
                transaction.mpesa_receipt_number = str(receipt)
                transaction.status = "completed"
            else:
                transaction.status = "failed"
                transaction.result_description = "Callback details did not match the pending transaction"
        else:
            transaction.status = "failed"

        db.commit()
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Callback processing failed") from exc


@router.get("/transaction/{transaction_id}")
def get_payment_status(
    transaction_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        "transaction_id": transaction.id,
        "phone_number": transaction.phone_number,
        "amount": transaction.amount,
        "account_reference": transaction.account_reference,
        "mpesa_receipt_number": transaction.mpesa_receipt_number,
        "status": transaction.status,
        "result_description": transaction.result_description,
        "created_at": transaction.created_at.isoformat(),
    }


@router.get("/")
def get_all_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    phone_number: str | None = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    query = db.query(Transaction)
    if status:
        query = query.filter(Transaction.status == status)
    if phone_number:
        query = query.filter(Transaction.phone_number == phone_number)
    rows = query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "transaction_id": row.id,
            "phone_number": row.phone_number,
            "amount": row.amount,
            "account_reference": row.account_reference,
            "mpesa_receipt_number": row.mpesa_receipt_number,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/reversal", response_model=ReversalResponse)
async def create_reversal(
    body: ReversalRequestBody,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    transaction = db.query(Transaction).filter(Transaction.id == body.transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Original transaction not found")
    if transaction.status != "completed":
        raise HTTPException(status_code=409, detail="Only completed payments can be reversed")
    try:
        reversal, _ = await request_reversal(
            db, transaction, body.amount, body.remarks, body.occasion
        )
        return ReversalResponse(
            reversal_id=reversal.id,
            status=reversal.status,
            message="Reversal request submitted to Safaricom",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to submit reversal request") from exc


@router.post("/reversal/result")
async def reversal_result(callback: ReversalCallback, db: Session = Depends(get_db)):
    result = callback.Result
    originator_id = result.get("OriginatorConversationID")
    conversation_id = result.get("ConversationID")
    code = result.get("ResultCode")
    description = result.get("ResultDesc", "")
    if code is None:
        raise HTTPException(status_code=400, detail="Invalid reversal result callback")

    reversal = None
    if originator_id:
        reversal = db.query(ReversalRequest).filter(
            ReversalRequest.originator_conversation_id == originator_id
        ).first()
    if not reversal and conversation_id:
        reversal = db.query(ReversalRequest).filter(
            ReversalRequest.conversation_id == conversation_id
        ).first()
    if reversal:
        reversal.result_code = int(code)
        reversal.result_description = description
        reversal.status = "completed" if int(code) == 0 else "failed"
        db.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/reversal/timeout")
async def reversal_timeout(callback: dict, db: Session = Depends(get_db)):
    result = callback.get("Result", callback)
    originator_id = result.get("OriginatorConversationID")
    conversation_id = result.get("ConversationID")
    reversal = None
    if originator_id:
        reversal = db.query(ReversalRequest).filter(
            ReversalRequest.originator_conversation_id == originator_id
        ).first()
    if not reversal and conversation_id:
        reversal = db.query(ReversalRequest).filter(
            ReversalRequest.conversation_id == conversation_id
        ).first()
    if reversal and reversal.status not in ("completed", "failed"):
        reversal.status = "timeout"
        reversal.result_description = "Safaricom reversal request timed out"
        db.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.get("/reversal/{reversal_id}")
def get_reversal_status(
    reversal_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    reversal = db.query(ReversalRequest).filter(ReversalRequest.id == reversal_id).first()
    if not reversal:
        raise HTTPException(status_code=404, detail="Reversal not found")
    return {
        "reversal_id": reversal.id,
        "transaction_id": reversal.transaction_id,
        "original_receipt_number": reversal.original_receipt_number,
        "amount": reversal.amount,
        "status": reversal.status,
        "result_code": reversal.result_code,
        "result_description": reversal.result_description,
        "created_at": reversal.created_at.isoformat(),
    }

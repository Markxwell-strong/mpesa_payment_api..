import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reversal import ReversalRequest
from app.models.transaction import Transaction
from app.services.daraja_auth import daraja_base_url, get_access_token


async def request_reversal(
    db: Session,
    transaction: Transaction,
    amount: int,
    remarks: str,
    occasion: str | None,
):
    required = (
        settings.daraja_initiator_name,
        settings.daraja_security_credential,
        settings.daraja_reversal_result_url,
        settings.daraja_reversal_timeout_url,
    )
    if not all(required):
        raise ValueError("Reversal credentials and callback URLs are not fully configured")
    if not transaction.mpesa_receipt_number:
        raise ValueError("Transaction has no confirmed M-Pesa receipt number")
    if amount <= 0 or amount > transaction.amount:
        raise ValueError("Reversal amount must be positive and no greater than the original payment")

    record = ReversalRequest(
        transaction_id=transaction.id,
        original_receipt_number=transaction.mpesa_receipt_number,
        amount=amount,
        remarks=remarks,
        occasion=occasion,
        status="requested",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    payload = {
        "Initiator": settings.daraja_initiator_name,
        "SecurityCredential": settings.daraja_security_credential,
        "CommandID": "TransactionReversal",
        "TransactionID": transaction.mpesa_receipt_number,
        "Amount": amount,
        "ReceiverParty": settings.daraja_shortcode,
        "RecieverIdentifierType": "11",
        "ResultURL": settings.daraja_reversal_result_url,
        "QueueTimeOutURL": settings.daraja_reversal_timeout_url,
        "Remarks": remarks,
        "Occasion": occasion or "Customer refund",
    }

    try:
        token = await get_access_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{daraja_base_url()}/mpesa/reversal/v1/request",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()

        record.originator_conversation_id = data.get("OriginatorConversationID")
        record.conversation_id = data.get("ConversationID")
        record.result_description = data.get("ResponseDescription")
        record.status = "submitted"
        db.commit()
        db.refresh(record)
        return record, data
    except Exception:
        db.rollback()
        failed = db.query(ReversalRequest).filter(ReversalRequest.id == record.id).first()
        if failed:
            failed.status = "request_failed"
            failed.result_description = "Reversal request submission failed"
            db.commit()
        raise

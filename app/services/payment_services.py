from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.services.stk_push import initiate_stk_push


async def create_payment_transaction(
    db: Session,
    phone_number: str,
    amount: int,
    callback_url: str,
    account_reference: str,
    transaction_description: str,
):
    transaction = Transaction(
        phone_number=phone_number,
        amount=amount,
        account_reference=account_reference,
        transaction_description=transaction_description,
        status="pending",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    transaction_id = transaction.id

    try:
        response = await initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            callback_url=callback_url,
            account_reference=account_reference,
            transaction_description=transaction_description,
        )
        transaction.merchant_request_id = response.get("MerchantRequestID")
        transaction.checkout_request_id = response.get("CheckoutRequestID")
        if response.get("ResponseCode") not in (None, "0", 0):
            transaction.status = "request_failed"
            transaction.result_description = response.get("ResponseDescription", "STK request rejected")
        db.commit()
        db.refresh(transaction)
        return {
            "transaction_id": transaction.id,
            "status": transaction.status,
            "safaricom_response": response,
        }
    except Exception:
        db.rollback()
        failed = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if failed:
            failed.status = "request_failed"
            failed.result_description = "STK Push request could not be submitted"
            db.commit()
        raise

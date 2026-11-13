from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction
from app.security import verify_api_key

router = APIRouter(prefix="/api/v1/reconciliation", tags=["Reconciliation"])


@router.get("/summary")
def reconciliation_summary(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    rows = (
        db.query(Transaction.status, func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0))
        .group_by(Transaction.status)
        .all()
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "statuses": [
            {"status": status, "transaction_count": count, "total_amount": str(total)}
            for status, count, total in rows
        ],
    }

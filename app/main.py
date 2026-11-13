import logging
from fastapi import FastAPI
from app.config import settings
from app.database import Base, engine
from app.models import Transaction, ReversalRequest
from app.routes.payments import router as payments_router
from app.routes.reconciliation import router as reconciliation_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Reusable M-Pesa payment API built with FastAPI and Daraja.",
)

app.include_router(payments_router)
app.include_router(reconciliation_router)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {"message": "M-Pesa Payment API is running", "environment": settings.environment}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

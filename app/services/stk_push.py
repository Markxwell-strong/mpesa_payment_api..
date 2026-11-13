import base64
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx

from app.config import settings
from app.services.daraja_auth import daraja_base_url, get_access_token


async def initiate_stk_push(
    phone_number: str,
    amount: int,
    callback_url: str,
    account_reference: str,
    transaction_description: str,
):
    if amount <= 0:
        raise ValueError("Amount must be greater than zero")
    if not callback_url.startswith("https://"):
        raise ValueError("Callback URL must use HTTPS")
    if not settings.daraja_shortcode or not settings.daraja_passkey:
        raise ValueError("Daraja shortcode or passkey is not configured")

    timestamp = datetime.now(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")
    shortcode = settings.daraja_shortcode
    password = base64.b64encode(
        f"{shortcode}{settings.daraja_passkey}{timestamp}".encode()
    ).decode()

    token = await get_access_token()
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_description,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{daraja_base_url()}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

import httpx
from app.config import settings


def daraja_base_url() -> str:
    return (
        "https://sandbox.safaricom.co.ke"
        if settings.daraja_env.lower() == "sandbox"
        else "https://api.safaricom.co.ke"
    )


async def get_access_token() -> str:
    if not settings.daraja_consumer_key or not settings.daraja_consumer_secret:
        raise ValueError("Daraja consumer credentials are not configured")

    url = f"{daraja_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            url,
            auth=(settings.daraja_consumer_key, settings.daraja_consumer_secret),
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError("Daraja did not return an access token")
        return token

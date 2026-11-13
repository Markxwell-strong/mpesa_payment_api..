# M-Pesa Payment API

A reusable REST API built with FastAPI, PostgreSQL, SQLAlchemy and Safaricom Daraja.

## Features

- STK Push initiation
- STK callback processing and transaction status
- API-key-protected payment and transaction endpoints
- Transaction history filtering and pagination
- Reversal request endpoint and reversal callback handlers
- Basic transaction reconciliation summary
- Health endpoint and application logging

## Important status

This is a project starter, not a verified production payment gateway. STK Push and reversal requests require valid Daraja credentials and an accessible HTTPS callback URL. Reversal functionality also requires the relevant Safaricom product/permissions and valid initiator/security credentials. A successful API submission is not proof that a payment or reversal completed; use the callback/status endpoints.

## 1. Requirements

- Python 3.10+
- PostgreSQL
- Safaricom Daraja app credentials
- Public HTTPS URL for callbacks (a tunnel can be used during development)

## 2. Setup (Windows CMD)

```bat
cd path\\to\\mpesa_payment_api
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

Create a PostgreSQL database named `mpesa_db`, then copy `.env.example` to `.env` and fill in your own values.

```bat
copy .env.example .env
```

Do not share or commit `.env`. Do not paste API secrets into chat or screenshots.

## 3. Initialize database

```bat
python -m app.init_db
```

Tables are also created when the application starts. For future schema changes, use a migration tool such as Alembic rather than relying on `create_all`.

## 4. Run

```bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/docs`.

## 5. Start a public callback tunnel

In a second terminal:

```bat
cloudflared tunnel --url http://127.0.0.1:8000
```

Copy the HTTPS hostname into the callback URL settings in `.env`, then restart the API. Quick Tunnel URLs can change when restarted.

## 6. Authentication

Protected endpoints require the `X-API-KEY` header. In Swagger, click **Authorize** and enter the value configured as `API_KEY`.

Safaricom callback endpoints are intentionally not protected by this API key because Daraja does not send that custom header. Before production, implement and validate a robust callback authenticity strategy and network/security controls.

## 7. Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | Health check |
| POST | `/api/v1/payment/stkpush` | Request STK Push |
| POST | `/api/v1/payment/callback` | STK callback |
| GET | `/api/v1/payment/transaction/{transaction_id}` | Read transaction |
| GET | `/api/v1/payment/` | List/filter transactions |
| POST | `/api/v1/payment/reversal` | Submit a reversal request |
| POST | `/api/v1/payment/reversal/result` | Reversal result callback |
| POST | `/api/v1/payment/reversal/timeout` | Reversal timeout callback |
| GET | `/api/v1/payment/reversal/{reversal_id}` | Read reversal status |
| GET | `/api/v1/reconciliation/summary` | Totals grouped by payment status |

## 8. Example STK Push body

```json
{
  "phone_number": "2547XXXXXXXX",
  "amount": 1,
  "account_reference": "ORDER-1001",
  "transaction_description": "Payment for order 1001"
}
```

Use an MSISDN and shortcode supported by the selected Daraja environment. Never assume the sandbox MSISDN will produce a real prompt on a personal phone.

## 9. Reversal configuration

The reversal route expects the initiator name and encrypted security credential supplied/configured for the applicable Daraja reversal product. The credential is not the consumer secret, passkey, or API key. Configure the result and timeout URLs as publicly reachable HTTPS endpoints. Confirm reversal access and test credentials with Safaricom before attempting reversal calls.

## 10. Known next steps before production

- Verify STK Push end-to-end with Safaricom.
- Verify callbacks against actual Daraja payloads.
- Verify reversal permissions, payload and callback formats with Safaricom.
- Add database migrations (Alembic).
- Add request idempotency and rate limiting.
- Add callback authentication/verification and audit logging.
- Add role-based merchant/admin access instead of one shared API key.
- Add automated tests and deployment configuration.
- Review privacy, retention, monitoring, backups and operational security.

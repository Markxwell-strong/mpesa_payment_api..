from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "M-Pesa Payment API"
    environment: str = "development"
    database_url: str

    daraja_env: str = "sandbox"
    daraja_consumer_key: str = ""
    daraja_consumer_secret: str = ""
    daraja_shortcode: str = ""
    daraja_passkey: str = ""
    daraja_callback_url: str = ""

    # Reversal API credentials are separate from STK Push credentials.
    daraja_initiator_name: str = ""
    daraja_security_credential: str = ""
    daraja_reversal_result_url: str = ""
    daraja_reversal_timeout_url: str = ""

    api_key: str
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

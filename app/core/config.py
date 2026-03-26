from typing import List
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# pydantic v2 moved BaseSettings into a separate package; support environments
try:
    from pydantic import BaseSettings, Field


    class Settings(BaseSettings):
        app_name: str = Field("DigiCloset", env="APP_NAME")
        debug: bool = Field(False, env="DEBUG")
        redis_required: bool = Field(False, env="REDIS_REQUIRED")
        dev_shop_domain: str = Field("local-dev.myshopify.com", env="DEV_SHOP_DOMAIN")
        dev_access_token: str = Field("local-dev-token", env="DEV_ACCESS_TOKEN")
        dev_auto_activate_billing: bool = Field(True, env="DEV_AUTO_ACTIVATE_BILLING")

        shopify_api_key: str = Field("", env="SHOPIFY_API_KEY")
        shopify_api_secret: str = Field("", env="SHOPIFY_API_SECRET")
        shopify_api_version: str = Field("2024-01", env="SHOPIFY_API_VERSION")
        app_url: str = Field("", env="APP_URL")

        allowed_origins: List[str] = Field(default_factory=list)

        request_timeout: float = Field(15.0, env="REQUEST_TIMEOUT")
        ai_inference_timeout: float = Field(10.0, env="AI_INFERENCE_TIMEOUT")

        class Config:
            env_file = ".env"


    settings = Settings()
except Exception:
    # Fallback for environments without BaseSettings available
    class Settings:
        app_name: str = os.getenv("APP_NAME", "DigiCloset")
        debug: bool = os.getenv("DEBUG", "False") in ("1", "true", "True")
        redis_required: bool = os.getenv("REDIS_REQUIRED", "False") in ("1", "true", "True")
        dev_shop_domain: str = os.getenv("DEV_SHOP_DOMAIN", "local-dev.myshopify.com")
        dev_access_token: str = os.getenv("DEV_ACCESS_TOKEN", "local-dev-token")
        dev_auto_activate_billing: bool = os.getenv("DEV_AUTO_ACTIVATE_BILLING", "True") in ("1", "true", "True")
        shopify_api_key: str = os.getenv("SHOPIFY_API_KEY", "")
        shopify_api_secret: str = os.getenv("SHOPIFY_API_SECRET", "")
        shopify_api_version: str = os.getenv("SHOPIFY_API_VERSION", "2024-01")
        allowed_origins: List[str] = [o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o]
        request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "15"))
        ai_inference_timeout: float = float(os.getenv("AI_INFERENCE_TIMEOUT", "10"))
        app_url: str = os.getenv("APP_URL", "")


    settings = Settings()

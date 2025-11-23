import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://dc_user:dc_pass@localhost/digicloset")
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minio")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minio123")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "CHANGE_ME")
    JWT_ALGORITHM: str = "HS256"

settings = Settings()

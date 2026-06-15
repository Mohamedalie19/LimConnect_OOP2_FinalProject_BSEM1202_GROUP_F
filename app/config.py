# app/config.py
# ─────────────────────────────────────────────────────────────────────────────
# PURPOSE:
#   Loads all environment variables from the .env file and exposes
#   them as a validated, typed Settings object used across the app.
#
# WHY pydantic-settings:
#   It automatically reads from .env, validates types (e.g. int for
#   ACCESS_TOKEN_EXPIRE_MINUTES), and raises clear errors if anything
#   is missing — far safer than reading os.environ manually.
# ─────────────────────────────────────────────────────────────────────────────

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    # Full PostgreSQL connection string
    # Format: postgresql://user:password@host:port/dbname
    DATABASE_URL: str

    # ── JWT ───────────────────────────────────────────────────────────────────
    # Secret key used to sign JWT tokens — must be long and random in production
    SECRET_KEY: str

    # Hashing algorithm for JWT — HS256 is the standard symmetric choice
    ALGORITHM: str = "HS256"

    # How long an access token stays valid (in minutes)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        # Tell pydantic-settings where to read variables from
        env_file = ".env"


# ── Singleton instance ────────────────────────────────────────────────────────
# Import this object in any file that needs environment values:
#   from app.config import settings
#   print(settings.SECRET_KEY)
settings = Settings()
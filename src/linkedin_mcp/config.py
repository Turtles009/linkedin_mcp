from datetime import date
from pathlib import Path

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LINKEDIN_")
    client_secret: SecretStr = Field(min_length=1)
    client_id: str = Field(min_length=1)
    redirect_uri: HttpUrl
    version: str = Field(pattern=r"^(20)\d{2}(0[1-9]|1[0-2])$")
    token_path: Path


def version_age_warning(version: str, today: date) -> str | None:
    version_year = int(version[:4])
    version_month = int(version[4:])
    total_version_months  = version_year * 12 + version_month

    total_today_months = today.year * 12 + today.month

    difference = total_today_months - total_version_months

    if difference >= 12:
        return "API version 12 months old may already be retired, please update to ensure proper functionality."
    elif difference >= 11:
        return "API version is old, please update to maintain proper functionality."
    elif difference < 0:
        raise ValueError("Future versions not supported yet.")
    return None

"""
Configuración centralizada de la aplicación.

Optimizaciones:
- Validación más estricta de configuración
- Configuraciones de rate limiting y timeouts
- Mejor tipado
"""
import os
import logging
import sys
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env desde la raíz del proyecto (un nivel arriba de /server)
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    """Configuración de la aplicación usando Pydantic Settings."""

    # API
    app_name: str = "AXIS Prospector API"
    app_version: str = "1.1.0"
    debug: bool = False
    api_key: str = Field(
        default="",
        description="API Key para proteger endpoints",
        validation_alias="PROSPECTOR_API_KEY"
    )
    api_key_header: str = Field(default="x-api-key", description="Header para API Key")
    request_cooldown_secs: int = Field(
        default=20,
        ge=5,
        le=300,
        validation_alias="REQUEST_COOLDOWN_SECS"
    )

    # Apify
    apify_token: str = Field(default="", description="Token de API de Apify")
    apify_timeout_secs: int = Field(default=300, ge=60, le=600)

    # Supabase
    supabase_url: str = Field(default="", description="URL del proyecto Supabase")
    supabase_key: str = Field(default="", description="API Key de Supabase")
    supabase_password: str = ""

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=30, ge=1, le=100)
    
    # Scraping
    max_leads_per_request: int = Field(default=100, ge=1, le=500)
    batch_size: int = Field(default=50, ge=10, le=200)
    audit_retry_attempts: int = Field(
        default=2,
        ge=1,
        le=5,
        validation_alias="AUDIT_RETRY_ATTEMPTS"
    )
    audit_retry_backoff_secs: float = Field(
        default=1.5,
        ge=0.5,
        le=10,
        validation_alias="AUDIT_RETRY_BACKOFF_SECS"
    )

    # Logging
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    @field_validator('apify_token', 'supabase_url', 'supabase_key')
    @classmethod
    def validate_not_placeholder(cls, v: str) -> str:
        """Verifica que no sean valores placeholder."""
        placeholders = {'your-token-here', 'xxx', 'placeholder', ''}
        if v.lower() in placeholders:
            return ""
        return v

    model_config = {
        "env_file": str(ROOT_DIR / ".env"),
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Obtiene la configuración cacheada."""
    return Settings()


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configura el logging de la aplicación.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    settings = get_settings()
    log_level = level or settings.log_level
    
    # Formato con colores para terminal
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Handler para stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.handlers = [handler]
    
    # Reducir verbosidad de librerías externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apify_client").setLevel(logging.WARNING)


def validate_environment() -> None:
    """Valida que las variables de entorno requeridas estén configuradas."""
    settings = get_settings()
    missing = []

    if not settings.apify_token:
        missing.append("APIFY_TOKEN")
    if not settings.supabase_url:
        missing.append("SUPABASE_URL")
    if not settings.supabase_key:
        missing.append("SUPABASE_KEY")

    if missing:
        raise ValueError(
            f"❌ Variables de entorno faltantes: {', '.join(missing)}. "
            "Revisa tu archivo .env"
        )

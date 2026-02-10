"""
Excepciones personalizadas para la aplicación.
"""
from typing import Optional


class SierraProspectorError(Exception):
    """Excepción base para errores de la aplicación."""

    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class ScraperError(SierraProspectorError):
    """Error durante el proceso de scraping."""
    pass


class ApifyConnectionError(ScraperError):
    """Error de conexión con la API de Apify."""
    pass


class ApifyTimeoutError(ScraperError):
    """Timeout esperando respuesta de Apify."""
    pass


class DatabaseError(SierraProspectorError):
    """Error de base de datos."""
    pass


class SupabaseConnectionError(DatabaseError):
    """Error de conexión con Supabase."""
    pass


class LeadNotFoundError(DatabaseError):
    """Lead no encontrado en la base de datos."""
    pass


class RateLimitExceededError(SierraProspectorError):
    """Límite de requests excedido."""
    pass


class ValidationError(SierraProspectorError):
    """Error de validación de datos."""
    pass

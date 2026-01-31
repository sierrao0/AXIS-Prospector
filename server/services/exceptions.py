"""
Excepciones personalizadas para la aplicación.
"""
from typing import Optional


class AXISProspectorError(Exception):
    """Excepción base para errores de la aplicación."""

    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class ScraperError(AXISProspectorError):
    """Error durante el proceso de scraping."""
    pass


class ApifyConnectionError(ScraperError):
    """Error de conexión con la API de Apify."""
    pass


class ApifyTimeoutError(ScraperError):
    """Timeout esperando respuesta de Apify."""
    pass


class DatabaseError(AXISProspectorError):
    """Error de base de datos."""
    pass


class SupabaseConnectionError(DatabaseError):
    """Error de conexión con Supabase."""
    pass


class LeadNotFoundError(DatabaseError):
    """Lead no encontrado en la base de datos."""
    pass


class RateLimitExceededError(AXISProspectorError):
    """Límite de requests excedido."""
    pass


class ValidationError(AXISProspectorError):
    """Error de validación de datos."""
    pass

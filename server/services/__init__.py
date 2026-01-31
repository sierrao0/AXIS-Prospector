"""
Servicios de la aplicación AXIS Prospector.

Módulos:
- scraper: Extracción de leads desde Google Maps via Apify
- database: Operaciones CRUD con Supabase
- exceptions: Excepciones personalizadas
"""

from services.scraper import get_scraper_service, cleanup_scraper
from services.database import get_database_service, cleanup_database
from services.exceptions import (
    AXISProspectorError,
    ScraperError,
    ApifyConnectionError,
    ApifyTimeoutError,
    DatabaseError,
    SupabaseConnectionError,
    LeadNotFoundError,
)

__all__ = [
    # Factories
    "get_scraper_service",
    "get_database_service",
    # Cleanup
    "cleanup_scraper",
    "cleanup_database",
    # Exceptions
    "AXISProspectorError",
    "ScraperError",
    "ApifyConnectionError",
    "ApifyTimeoutError",
    "DatabaseError",
    "SupabaseConnectionError",
    "LeadNotFoundError",
]

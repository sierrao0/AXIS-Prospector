"""
Servicio de extracción de leads usando Apify.

Optimizaciones:
- Async/await para operaciones I/O
- Retry con backoff exponencial
- Mejor manejo de errores
- Filtros configurables
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import List, Dict, Any, Optional, Set

from apify_client import ApifyClient
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from config import get_settings
from services.exceptions import ApifyConnectionError, ApifyTimeoutError, ScraperError

logger = logging.getLogger(__name__)

# ThreadPool para ejecutar operaciones sync de Apify en async
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="apify_worker")

# Dominios de redes sociales para filtro 80/20
SOCIAL_MEDIA_DOMAINS: Set[str] = {
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "linkedin.com",
    "wa.me",
    "linktr.ee",
}


class ScraperService:
    """Servicio para extraer leads de Google Maps via Apify."""

    def __init__(self):
        settings = get_settings()
        if not settings.apify_token:
            raise ValueError("APIFY_TOKEN no configurado")
        
        self.client = ApifyClient(settings.apify_token)
        self.actor_id = "compass/crawler-google-places"
        self._is_initialized = True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _ejecutar_actor_sync(self, run_input: Dict[str, Any]) -> str:
        """
        Ejecuta el actor de Apify de forma síncrona (con retry).
        
        Returns:
            Dataset ID del resultado
        """
        try:
            run = self.client.actor(self.actor_id).call(
                run_input=run_input,
                timeout_secs=300,  # 5 minutos máximo
            )
            return run["defaultDatasetId"]
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                raise ApifyTimeoutError(f"Timeout ejecutando Apify: {e}")
            elif "connection" in error_msg or "network" in error_msg:
                raise ApifyConnectionError(f"Error de conexión con Apify: {e}")
            raise ScraperError(f"Error ejecutando Apify: {e}")

    async def extraer_leads(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Extrae leads de Google Maps de forma asíncrona.
        
        Args:
            query: Término de búsqueda (ej: "Restaurantes en Bogotá")
            max_results: Número máximo de resultados
            
        Returns:
            Lista de leads filtrados (sin web o con redes sociales)
        """
        logger.info(f"🔍 Iniciando búsqueda: '{query}' (max: {max_results})")

        run_input = {
            "searchStringsArray": [query],
            "maxCrawledPlacesPerSearch": max_results,
            "language": "es",
        }

        # Ejecutar actor en thread pool para no bloquear el event loop
        loop = asyncio.get_event_loop()
        try:
            dataset_id = await loop.run_in_executor(
                _executor,
                partial(self._ejecutar_actor_sync, run_input)
            )
            logger.info(f"✅ Apify ejecutado. Dataset: {dataset_id}")
        except (ApifyConnectionError, ApifyTimeoutError):
            raise
        except Exception as e:
            logger.error(f"❌ Error ejecutando Apify: {e}")
            raise ScraperError(f"Error inesperado: {e}")

        # Procesar resultados en thread pool
        leads_encontrados = await loop.run_in_executor(
            _executor,
            partial(self._procesar_dataset, dataset_id)
        )

        logger.info(f"📊 Leads encontrados: {len(leads_encontrados)}")
        return leads_encontrados

    def _procesar_dataset(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Procesa el dataset de Apify y filtra leads."""
        leads = []
        for item in self.client.dataset(dataset_id).iterate_items():
            lead = self._filtrar_lead(item)
            if lead:
                leads.append(lead)
        return leads

    def _filtrar_lead(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Aplica filtro 80/20: Solo leads sin web o con redes sociales.
        
        Args:
            item: Datos crudos de Apify
            
        Returns:
            Lead formateado o None si no pasa el filtro
        """
        website = item.get("website") or ""
        website_lower = website.lower()

        # Filtro: Solo si no tienen web o usan redes sociales
        es_lead_valido = (
            not website or
            any(domain in website_lower for domain in SOCIAL_MEDIA_DOMAINS)
        )

        if es_lead_valido:
            # Determinar estado basado en indicadores de calidad
            rating = item.get("totalScore") or 0
            reviews = item.get("reviewsCount") or 0
            
            if not website:
                status = "caliente"  # Sin web = Máxima prioridad
            elif rating >= 4.0 and reviews >= 10:
                status = "caliente"  # Buena reputación pero sin web propia
            else:
                status = "tibio"

            return {
                "name": item.get("title"),
                "website": website or None,
                "phone": item.get("phone"),
                "rating": rating if rating else None,
                "reviews_count": reviews if reviews else None,
                "location": item.get("address"),
                "category": item.get("categoryName"),
                "status": status,
            }
        return None


# Instancia singleton del servicio (lazy initialization)
_scraper_service: Optional[ScraperService] = None


def get_scraper_service() -> ScraperService:
    """Factory para obtener el servicio de scraping."""
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service


async def cleanup_scraper() -> None:
    """Limpia recursos del scraper (llamar en shutdown)."""
    _executor.shutdown(wait=False)

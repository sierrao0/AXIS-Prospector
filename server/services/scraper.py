"""
Servicio de extracción de leads usando Apify.

🎯 THE HUNTER - Fase 1: Extracción de Leads

Estrategia de filtrado:
- ANTES: Solo leads sin web o con redes sociales (80/20 muy agresivo)
- AHORA: Todos los leads pasan, el scoring decide la prioridad

El Deep Audit y The Hunter Logic determinarán la calidad del lead,
no el filtro de extracción.
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

# Dominios de redes sociales (para clasificación, no filtrado)
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
        """Procesa el dataset de Apify y formatea leads, eliminando duplicados locales."""
        leads = []
        seen_websites: Set[str] = set()

        for item in self.client.dataset(dataset_id).iterate_items():
            lead = self._formatear_lead(item)
            if lead:
                # Deduplicación local (dentro del mismo batch de búsqueda)
                website = lead.get("website")
                if website:
                    if website in seen_websites:
                        continue
                    seen_websites.add(website)
                
                leads.append(lead)
        return leads

    def _formatear_lead(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        🎯 THE HUNTER - Formatea un lead de Apify.
        
        CAMBIO IMPORTANTE: Ya no filtramos aquí. TODOS los leads pasan.
        El Deep Audit y The Hunter Logic determinarán la prioridad.
        
        Clasificación inicial por status:
        - 'caliente': Sin web O web es solo red social (MÁXIMA OPORTUNIDAD)
        - 'tibio': Tiene web propia pero necesita evaluación
        - 'frío': Casos edge
        
        Args:
            item: Datos crudos de Apify
            
        Returns:
            Lead formateado (nunca None, todos pasan)
        """
        website = item.get("website") or ""
        website_lower = website.lower()
        
        # Clasificar el tipo de presencia web
        has_website = bool(website)
        is_social_only = has_website and any(
            domain in website_lower for domain in SOCIAL_MEDIA_DOMAINS
        )
        has_real_website = has_website and not is_social_only
        
        # Datos de reputación
        rating = item.get("totalScore") or 0
        reviews = item.get("reviewsCount") or 0
        
        # Determinar status inicial basado en presencia digital
        if not has_website:
            # 🎯 Sin web = MÁXIMA OPORTUNIDAD para The Architect
            status = "caliente"
            logger.debug(f"🎯 Lead sin web: {item.get('title')} - OPPORTUNITY")
        elif is_social_only:
            # Solo red social = Necesita web propia
            status = "caliente"
            logger.debug(f"📱 Lead solo social: {item.get('title')} - OPPORTUNITY")
        elif rating >= 4.0 and reviews >= 50:
            # Negocio establecido con web = Candidato para optimización
            status = "tibio"
        else:
            # Tiene web, evaluación pendiente
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

"""
Servicio de análisis de sitios web usando Playwright.

Analiza sitios web de leads para detectar webs obsoletas basándose en:
- Contenido del header (muy corto = obsoleta)
- Presencia de meta tags SEO básicas
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from services.exceptions import AXISProspectorError

logger = logging.getLogger(__name__)

# Configuración de análisis
MIN_HEADER_TEXT_LENGTH = 20  # Caracteres mínimos en header para considerar web válida
REQUIRED_META_TAGS = {"description", "viewport"}  # Meta tags mínimas esperadas
PAGE_TIMEOUT_MS = 15000  # 15 segundos máximo por página


class WebAnalysisError(AXISProspectorError):
    """Error durante el análisis de sitio web."""
    pass


@dataclass
class AnalysisResult:
    """Resultado del análisis de un sitio web."""
    url: str
    es_obsoleta: bool
    header_text: str
    header_length: int
    meta_tags_encontradas: List[str]
    meta_tags_faltantes: List[str]
    motivo: Optional[str] = None
    error: Optional[str] = None


class WebAnalyzerService:
    """Servicio para analizar sitios web de leads usando Playwright."""

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._playwright = None
        self._is_initialized = False

    async def _inicializar_browser(self) -> None:
        """Inicializa el browser de Playwright de forma lazy."""
        if not self._is_initialized:
            logger.info("🌐 Inicializando Playwright browser...")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            self._is_initialized = True
            logger.info("✅ Playwright browser inicializado")

    async def _obtener_pagina(self) -> Page:
        """Obtiene una nueva página del browser."""
        await self._inicializar_browser()
        context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        return await context.new_page()

    async def analizar_sitio(self, url: str) -> AnalysisResult:
        """
        Analiza un sitio web para determinar si es obsoleto.
        
        Criterios de web obsoleta:
        1. Header con texto muy corto (< 20 caracteres)
        2. Ausencia de meta tags SEO básicas (description, viewport)
        
        Args:
            url: URL del sitio web a analizar
            
        Returns:
            AnalysisResult con el diagnóstico del sitio
        """
        logger.info(f"🔍 Analizando sitio: {url}")
        
        # Asegurar que la URL tenga protocolo
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        page = None
        try:
            page = await self._obtener_pagina()
            
            # Navegar a la página con timeout
            await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            
            # Extraer contenido del header
            header_text = await self._extraer_header_text(page)
            header_length = len(header_text.strip())
            
            # Extraer meta tags
            meta_tags = await self._extraer_meta_tags(page)
            meta_tags_faltantes = list(REQUIRED_META_TAGS - set(meta_tags))
            
            # Determinar si es obsoleta
            es_obsoleta, motivo = self._evaluar_obsolescencia(
                header_length, 
                meta_tags, 
                meta_tags_faltantes
            )
            
            resultado = AnalysisResult(
                url=url,
                es_obsoleta=es_obsoleta,
                header_text=header_text[:100],  # Truncar para logs
                header_length=header_length,
                meta_tags_encontradas=meta_tags,
                meta_tags_faltantes=meta_tags_faltantes,
                motivo=motivo
            )
            
            emoji = "⚠️" if es_obsoleta else "✅"
            logger.info(f"{emoji} {url}: {'Web Obsoleta' if es_obsoleta else 'Web OK'} - {motivo}")
            
            return resultado

        except PlaywrightTimeout:
            logger.warning(f"⏱️ Timeout analizando {url}")
            return AnalysisResult(
                url=url,
                es_obsoleta=True,
                header_text="",
                header_length=0,
                meta_tags_encontradas=[],
                meta_tags_faltantes=list(REQUIRED_META_TAGS),
                motivo="Timeout - sitio no responde",
                error="timeout"
            )
        except Exception as e:
            logger.error(f"❌ Error analizando {url}: {e}")
            return AnalysisResult(
                url=url,
                es_obsoleta=True,
                header_text="",
                header_length=0,
                meta_tags_encontradas=[],
                meta_tags_faltantes=list(REQUIRED_META_TAGS),
                motivo=f"Error de conexión: {str(e)[:50]}",
                error=str(e)
            )
        finally:
            if page:
                await page.context.close()

    async def _extraer_header_text(self, page: Page) -> str:
        """Extrae el innerText del header de la página."""
        try:
            # Intentar múltiples selectores de header
            selectores = ["header", "[role='banner']", "nav", ".header", "#header"]
            
            for selector in selectores:
                elemento = await page.query_selector(selector)
                if elemento:
                    texto = await elemento.inner_text()
                    if texto.strip():
                        return texto.strip()
            
            # Fallback: primeros elementos del body
            body_text = await page.evaluate("""
                () => {
                    const body = document.body;
                    if (!body) return '';
                    const children = Array.from(body.children).slice(0, 3);
                    return children.map(el => el.innerText || '').join(' ').slice(0, 500);
                }
            """)
            return body_text.strip()
            
        except Exception as e:
            logger.debug(f"Error extrayendo header: {e}")
            return ""

    async def _extraer_meta_tags(self, page: Page) -> List[str]:
        """Extrae los nombres de las meta tags presentes."""
        try:
            meta_tags = await page.evaluate("""
                () => {
                    const metas = document.querySelectorAll('meta[name], meta[property]');
                    return Array.from(metas).map(m => 
                        (m.getAttribute('name') || m.getAttribute('property') || '').toLowerCase()
                    ).filter(Boolean);
                }
            """)
            return meta_tags
        except Exception as e:
            logger.debug(f"Error extrayendo meta tags: {e}")
            return []

    def _evaluar_obsolescencia(
        self, 
        header_length: int, 
        meta_tags: List[str],
        meta_tags_faltantes: List[str]
    ) -> tuple[bool, str]:
        """
        Evalúa si un sitio es obsoleto basándose en los criterios.
        
        Returns:
            Tupla (es_obsoleta, motivo)
        """
        razones = []
        
        # Criterio 1: Header muy corto
        if header_length < MIN_HEADER_TEXT_LENGTH:
            razones.append(f"Header corto ({header_length} chars)")
        
        # Criterio 2: Faltan meta tags SEO
        if meta_tags_faltantes:
            razones.append(f"Sin meta tags: {', '.join(meta_tags_faltantes)}")
        
        if razones:
            return True, " | ".join(razones)
        
        return False, "Web con estructura válida"

    async def analizar_leads_con_web(
        self, 
        leads: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Analiza todos los leads que tienen sitio web.
        
        Args:
            leads: Lista de leads a analizar
            max_concurrent: Máximo de análisis concurrentes
            
        Returns:
            Lista de leads con campo 'web_obsoleta' actualizado
        """
        leads_con_web = [lead for lead in leads if lead.get("website")]
        
        if not leads_con_web:
            logger.info("📋 No hay leads con sitio web para analizar")
            return leads

        logger.info(f"🌐 Analizando {len(leads_con_web)} sitios web...")
        
        # Semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analizar_con_semaforo(lead: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                resultado = await self.analizar_sitio(lead["website"])
                lead["web_obsoleta"] = resultado.es_obsoleta
                lead["web_analisis_motivo"] = resultado.motivo
                
                # Si es obsoleta, promover a "caliente"
                if resultado.es_obsoleta and lead.get("status") != "caliente":
                    lead["status"] = "caliente"
                    logger.info(f"📌 Lead '{lead.get('name')}' promovido a 'caliente' por web obsoleta")
                
                return lead
        
        # Procesar leads con web
        tareas = [analizar_con_semaforo(lead) for lead in leads_con_web]
        leads_analizados = await asyncio.gather(*tareas)
        
        # Crear mapa de leads analizados
        analizados_map = {lead.get("website"): lead for lead in leads_analizados}
        
        # Actualizar lista original
        for i, lead in enumerate(leads):
            if lead.get("website") in analizados_map:
                leads[i] = analizados_map[lead["website"]]
        
        webs_obsoletas = sum(1 for lead in leads if lead.get("web_obsoleta"))
        logger.info(f"✅ Análisis completado: {webs_obsoletas}/{len(leads_con_web)} webs obsoletas")
        
        return leads

    async def cleanup(self) -> None:
        """Cierra el browser y libera recursos."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._is_initialized = False
        logger.info("✅ Playwright browser cerrado")


# Singleton del servicio
_analyzer_service: Optional[WebAnalyzerService] = None


def get_analyzer_service() -> WebAnalyzerService:
    """Factory para obtener el servicio de análisis."""
    global _analyzer_service
    if _analyzer_service is None:
        _analyzer_service = WebAnalyzerService()
    return _analyzer_service


async def cleanup_analyzer() -> None:
    """Limpia recursos del analyzer (llamar en shutdown)."""
    global _analyzer_service
    if _analyzer_service:
        await _analyzer_service.cleanup()
        _analyzer_service = None

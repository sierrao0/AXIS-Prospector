"""
Deep Audit Engine - Servicio de análisis profundo de sitios web.

Phase 1: The Hunter
- SSL certificate validation
- Email extraction (with contact page crawling)
- Technology detection (CMS, frameworks, e-commerce)
- Social links extraction
- AI Score calculation

Optimizations:
- Single browser instance with multiple contexts (memory efficient)
- playwright-stealth for bot evasion
- Semaphore-limited concurrency (M4 optimized)
- Deep crawl for contact pages
"""
from __future__ import annotations

import asyncio
import re
import ssl
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

import aiohttp
from playwright.async_api import (
    async_playwright, 
    Browser, 
    Page, 
    BrowserContext,
    TimeoutError as PlaywrightTimeout,
    Playwright
)
from playwright_stealth import Stealth

from schemas import (
    AuditResult, 
    TechStack, 
    SocialLinks, 
    LeadSchema,
    AuditStatus,
    calculate_ai_score
)
from services.exceptions import SierraProspectorError

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Concurrency: 8 contexts on M4, adjust based on hardware
CONTEXT_SEMAPHORE = asyncio.Semaphore(8)

# Timeouts
PAGE_TIMEOUT_MS = 15000  # 15 seconds per page
SSL_TIMEOUT_SECONDS = 10

# Regex patterns
EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# Contact page patterns for deep crawl
CONTACT_PAGE_PATTERNS = re.compile(
    r'(contact|contacto|kontakt|nosotros|about|sobre|info|empresa|company|'
    r'acerca|quienes-somos|who-we-are|get-in-touch|reach-us)',
    re.IGNORECASE
)

# Social media domains mapping
SOCIAL_DOMAINS = {
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "instagram.com": "instagram",
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "tiktok.com": "tiktok",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "wa.me": "whatsapp",
    "api.whatsapp.com": "whatsapp",
}

# Technology signatures for detection
TECH_SIGNATURES: Dict[str, Dict[str, List[str]]] = {
    "cms": {
        "wordpress": ["/wp-content/", "/wp-includes/", "wp-json", "WordPress"],
        "wix": ["wix.com", "wixsite.com", "_wix", "X-Wix"],
        "shopify": ["cdn.shopify.com", "Shopify.theme", "myshopify.com"],
        "squarespace": ["squarespace.com", "static.squarespace"],
        "webflow": ["webflow.com", "wf-asset"],
        "ghost": ["ghost.io", "Ghost"],
        "drupal": ["drupal", "/sites/default/"],
        "joomla": ["joomla", "/components/com_"],
    },
    "framework": {
        "react": ["react", "__REACT", "data-reactroot", "_next/static"],
        "nextjs": ["/_next/", "__NEXT_DATA__", "next/dist"],
        "vue": ["__vue__", "vue.js", "Vue.js", "v-cloak"],
        "nuxt": ["__nuxt", "_nuxt/"],
        "angular": ["ng-", "angular", "ng-version"],
        "svelte": ["svelte", "__svelte"],
        "astro": ["astro"],
    },
    "ecommerce": {
        "woocommerce": ["woocommerce", "wc-"],
        "magento": ["magento", "mage"],
        "prestashop": ["prestashop", "PrestaShop"],
        "bigcommerce": ["bigcommerce"],
    },
    "analytics": {
        "google_analytics": ["google-analytics", "gtag", "ga.js", "analytics.js", "G-", "UA-"],
        "facebook_pixel": ["fbq(", "facebook.com/tr"],
        "hotjar": ["hotjar", "hj("],
        "clarity": ["clarity.ms"],
    }
}

# Emails to exclude (common false positives)
EXCLUDED_EMAIL_PATTERNS = [
    r".*@example\.com$",
    r".*@test\.com$",
    r".*@placeholder\.",
    r".*@sentry\.",
    r".*@wix\.",
    r"^privacy@",
    r"^noreply@",
    r"^no-reply@",
]


# =============================================================================
# EXCEPTIONS
# =============================================================================

class WebAnalysisError(SierraProspectorError):
    """Error durante el análisis de sitio web."""
    pass


# =============================================================================
# DEEP AUDIT SERVICE
# =============================================================================

class DeepAuditService:
    """
    Servicio de auditoría profunda para sitios web.
    
    Usa un single browser instance con múltiples contexts para eficiencia.
    Implementa stealth mode para evadir detección de bots.
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._stealth: Stealth = Stealth()  # Stealth instance for bot evasion
        self._is_initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Inicializa el browser de Playwright (thread-safe)."""
        async with self._lock:
            if not self._is_initialized:
                logger.info("🌐 Inicializando Playwright browser con stealth...")
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )
                self._is_initialized = True
                logger.info("✅ Deep Audit Engine inicializado (8 contexts max)")

    async def _get_context(self) -> BrowserContext:
        """Crea un nuevo context con configuración stealth."""
        await self.initialize()
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="es-ES",
            timezone_id="America/Bogota",
        )
        # Apply stealth evasions to context
        await self._stealth.apply_stealth_async(context)
        return context

    # -------------------------------------------------------------------------
    # SSL VALIDATION
    # -------------------------------------------------------------------------
    
    async def check_ssl(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica si el certificado SSL del sitio es válido.
        
        Returns:
            Tuple (is_valid, error_message)
        """
        if not url.startswith("https://"):
            if url.startswith("http://"):
                return False, "Site uses HTTP instead of HTTPS"
            url = f"https://{url}"
        
        try:
            # Create SSL context that validates certificates
            ssl_context = ssl.create_default_context()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    ssl=ssl_context, 
                    timeout=aiohttp.ClientTimeout(total=SSL_TIMEOUT_SECONDS),
                    allow_redirects=True
                ) as response:
                    # If we get here, SSL is valid
                    final_url = str(response.url)
                    uses_https = final_url.startswith("https://")
                    return uses_https, None
                    
        except aiohttp.ClientSSLError as e:
            return False, f"SSL Error: {str(e)[:100]}"
        except aiohttp.ClientError as e:
            return False, f"Connection Error: {str(e)[:100]}"
        except asyncio.TimeoutError:
            return False, "SSL check timeout"
        except Exception as e:
            return False, f"Unexpected error: {str(e)[:100]}"

    # -------------------------------------------------------------------------
    # EMAIL EXTRACTION
    # -------------------------------------------------------------------------
    
    def _clean_emails(self, raw_emails: List[str]) -> List[str]:
        """Limpia y filtra emails, removiendo duplicados y falsos positivos."""
        seen = set()
        cleaned = []
        
        for email in raw_emails:
            email = email.lower().strip()
            
            # Skip duplicates
            if email in seen:
                continue
            
            # Skip excluded patterns
            if any(re.match(pattern, email) for pattern in EXCLUDED_EMAIL_PATTERNS):
                continue
            
            # Basic validation
            if len(email) < 5 or len(email) > 254:
                continue
            
            seen.add(email)
            cleaned.append(email)
        
        return cleaned[:10]  # Limit to 10 emails max

    async def _extract_emails_from_page(self, page: Page) -> List[str]:
        """Extrae emails de la página actual."""
        emails = []
        
        try:
            # Method 1: Extract from page content
            content = await page.content()
            emails.extend(EMAIL_REGEX.findall(content))
            
            # Method 2: Extract from mailto: links
            mailto_emails = await page.eval_on_selector_all(
                "a[href^='mailto:']",
                "els => els.map(el => el.href.replace('mailto:', '').split('?')[0])"
            )
            emails.extend(mailto_emails)
            
        except Exception as e:
            logger.debug(f"Error extracting emails: {e}")
        
        return emails

    async def _find_contact_page(self, page: Page, base_url: str) -> Optional[str]:
        """Encuentra el link a la página de contacto."""
        try:
            links = await page.eval_on_selector_all(
                "a[href]",
                """els => els.map(el => ({
                    href: el.href,
                    text: (el.textContent || '').toLowerCase()
                }))"""
            )
            
            for link in links:
                href = link.get("href", "")
                text = link.get("text", "")
                
                # Check if link matches contact patterns
                if CONTACT_PAGE_PATTERNS.search(href) or CONTACT_PAGE_PATTERNS.search(text):
                    # Ensure it's from the same domain
                    if urlparse(href).netloc == urlparse(base_url).netloc or not urlparse(href).netloc:
                        return href
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding contact page: {e}")
            return None

    async def extract_emails_deep(self, page: Page, base_url: str) -> List[str]:
        """
        Extrae emails con estrategia de deep crawl.
        
        1. Extrae de la página actual
        2. Si no hay emails, busca página de contacto
        3. Visita la página de contacto y extrae
        """
        # Step 1: Extract from current page
        emails = await self._extract_emails_from_page(page)
        
        if emails:
            return self._clean_emails(emails)
        
        # Step 2: Find and visit contact page
        contact_url = await self._find_contact_page(page, base_url)
        
        if contact_url:
            try:
                logger.debug(f"🔍 Deep crawling contact page: {contact_url}")
                await page.goto(contact_url, timeout=PAGE_TIMEOUT_MS // 2, wait_until="domcontentloaded")
                emails = await self._extract_emails_from_page(page)
            except Exception as e:
                logger.debug(f"Error visiting contact page: {e}")
        
        return self._clean_emails(emails)

    # -------------------------------------------------------------------------
    # TECHNOLOGY DETECTION
    # -------------------------------------------------------------------------
    
    async def detect_technologies(self, page: Page) -> TechStack:
        """Detecta las tecnologías usadas en el sitio."""
        detected = TechStack()
        
        try:
            # Get page source and scripts
            content = await page.content()
            
            # Get script sources
            scripts = await page.eval_on_selector_all(
                "script[src]",
                "els => els.map(el => el.src)"
            )
            script_sources = " ".join(scripts)
            
            # Get meta generators
            generators = await page.eval_on_selector_all(
                "meta[name='generator']",
                "els => els.map(el => el.content || '')"
            )
            
            # Combine all sources for detection
            all_content = f"{content} {script_sources} {' '.join(generators)}".lower()
            
            # Detect CMS
            for tech, patterns in TECH_SIGNATURES["cms"].items():
                if any(p.lower() in all_content for p in patterns):
                    detected.cms = tech
                    break
            
            # Detect Framework
            for tech, patterns in TECH_SIGNATURES["framework"].items():
                if any(p.lower() in all_content for p in patterns):
                    detected.framework = tech
                    break
            
            # Detect E-commerce
            for tech, patterns in TECH_SIGNATURES["ecommerce"].items():
                if any(p.lower() in all_content for p in patterns):
                    detected.ecommerce = tech
                    break
            
            # Detect Analytics
            analytics = []
            for tech, patterns in TECH_SIGNATURES["analytics"].items():
                if any(p.lower() in all_content for p in patterns):
                    analytics.append(tech)
            detected.analytics = analytics
            
        except Exception as e:
            logger.debug(f"Error detecting technologies: {e}")
        
        return detected

    # -------------------------------------------------------------------------
    # SOCIAL LINKS EXTRACTION
    # -------------------------------------------------------------------------
    
    async def extract_social_links(self, page: Page) -> SocialLinks:
        """Extrae enlaces a redes sociales."""
        social = SocialLinks()
        
        try:
            # Get all links
            links = await page.eval_on_selector_all(
                "a[href]",
                "els => els.map(el => el.href)"
            )
            
            for link in links:
                link_lower = link.lower()
                
                for domain, platform in SOCIAL_DOMAINS.items():
                    if domain in link_lower:
                        # Set the appropriate platform field
                        if platform == "facebook" and not social.facebook:
                            social.facebook = link
                        elif platform == "instagram" and not social.instagram:
                            social.instagram = link
                        elif platform == "linkedin" and not social.linkedin:
                            social.linkedin = link
                        elif platform == "twitter" and not social.twitter:
                            social.twitter = link
                        elif platform == "tiktok" and not social.tiktok:
                            social.tiktok = link
                        elif platform == "youtube" and not social.youtube:
                            social.youtube = link
                        elif platform == "whatsapp" and not social.whatsapp:
                            social.whatsapp = link
                        break
            
        except Exception as e:
            logger.debug(f"Error extracting social links: {e}")
        
        return social

    # -------------------------------------------------------------------------
    # META TAGS EXTRACTION
    # -------------------------------------------------------------------------
    
    async def extract_meta_info(self, page: Page) -> Tuple[bool, bool, Optional[str]]:
        """Extrae información de meta tags."""
        has_description = False
        has_viewport = False
        title = None
        
        try:
            # Check meta description
            description = await page.query_selector("meta[name='description']")
            has_description = description is not None
            
            # Check viewport
            viewport = await page.query_selector("meta[name='viewport']")
            has_viewport = viewport is not None
            
            # Get title
            title_el = await page.query_selector("title")
            if title_el:
                title = await title_el.inner_text()
                title = title[:200] if title else None
                
        except Exception as e:
            logger.debug(f"Error extracting meta info: {e}")
        
        return has_description, has_viewport, title

    # -------------------------------------------------------------------------
    # MAIN AUDIT METHOD
    # -------------------------------------------------------------------------
    
    async def audit_website(self, url: str) -> AuditResult:
        """
        Ejecuta una auditoría profunda completa de un sitio web.
        
        Incluye: SSL, emails (deep crawl), tech detection, social links, meta info.
        """
        logger.debug(f"Iniciando Deep Audit: {url}")
        start_time = datetime.utcnow()
        
        # Normalize URL
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        context = None
        
        try:
            async with CONTEXT_SEMAPHORE:
                # Check SSL first (outside of browser)
                logger.debug(f"  [1/6] Validando SSL...")
                ssl_valid, ssl_error = await self.check_ssl(url)
                uses_https = url.startswith("https://") or ssl_valid
                if ssl_valid:
                    logger.debug(f"    OK: SSL valido")
                else:
                    logger.debug(f"    WARN: {ssl_error}")
                
                # Create context and page (stealth already applied to context)
                logger.debug(f"  [2/6] Creando contexto Playwright...")
                context = await self._get_context()
                page = await context.new_page()
                
                # Navigate to page
                logger.debug(f"  [3/6] Navegando a sitio...")
                response = await page.goto(
                    url, 
                    timeout=PAGE_TIMEOUT_MS, 
                    wait_until="domcontentloaded"
                )
                logger.debug(f"    OK: HTTP {response.status if response else '?'}")
                
                # Check for WAF/blocking
                if response and response.status in (403, 406, 429):
                    return AuditResult(
                        site_accessible=False,
                        block_reason=f"Blocked: HTTP {response.status}",
                        ssl_valid=ssl_valid,
                        ssl_error=ssl_error,
                        uses_https=uses_https,
                    )
                
                # Calculate response time
                response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                final_url = page.url
                logger.debug(f"    OK: Respuesta en {response_time}ms")
                
                # Extract all data in parallel
                logger.debug(f"  [4/6] Extrayendo emails...")
                emails_task = self.extract_emails_deep(page, url)
                logger.debug(f"  [5/6] Detectando tecnologias...")
                tech_task = self.detect_technologies(page)
                logger.debug(f"  [6/6] Extrayendo redes sociales y meta...")
                social_task = self.extract_social_links(page)
                meta_task = self.extract_meta_info(page)
                
                emails, tech_stack, social_links, meta_info = await asyncio.gather(
                    emails_task, tech_task, social_task, meta_task
                )
                
                logger.debug(f"    OK: Emails={len(emails)}, Tech={tech_stack.cms or 'N/A'}, Sociales={social_links.count}")
                
                has_description, has_viewport, title = meta_info
                
                # Determine if site is obsolete
                logger.debug(f"  Evaluando obsolescencia del sitio...")
                is_obsolete, obsolete_reasons = self._evaluate_obsolescence(
                    tech_stack, has_description, has_viewport
                )
                if is_obsolete:
                    logger.debug(f"    WARN: Sitio obsoleto - {obsolete_reasons}")
                else:
                    logger.debug(f"    OK: Sitio moderno")
                
                # Check for domain email
                has_domain_email = False
                if emails:
                    domain = urlparse(url).netloc.replace("www.", "")
                    has_domain_email = any(domain in email for email in emails)
                    if has_domain_email:
                        logger.debug(f"    OK: Encontrado email corporativo")
                
                result = AuditResult(
                    site_accessible=True,
                    response_time_ms=response_time,
                    final_url=final_url,
                    ssl_valid=ssl_valid,
                    ssl_error=ssl_error,
                    uses_https=uses_https,
                    emails=emails,
                    has_domain_email=has_domain_email,
                    tech_stack=tech_stack,
                    social_links=social_links,
                    has_meta_description=has_description,
                    has_viewport=has_viewport,
                    title=title,
                    is_obsolete=is_obsolete,
                    obsolete_reasons=obsolete_reasons,
                )
                
                # Log result summary
                ssl_badge = "OK" if ssl_valid else "WARN"
                email_badge = f"emails={len(emails)}" if emails else "NO_EMAILS"
                social_badge = f"sociales={social_links.count}" if social_links.count > 0 else "SIN_SOCIALES"
                tech_badge = tech_stack.cms or "custom"
                logger.info(f"AUDIT_COMPLETE: [{ssl_badge}] [{email_badge}] [{social_badge}] [tech={tech_badge}]")
                
                return result
                
        except PlaywrightTimeout:
            logger.warning(f"⏱️ Timeout: {url}")
            return AuditResult(
                site_accessible=False,
                block_reason="Timeout - site did not respond",
            )
            
        except Exception as e:
            logger.error(f"❌ Error auditing {url}: {e}")
            return AuditResult(
                site_accessible=False,
                block_reason=f"Error: {str(e)[:100]}",
            )
            
        finally:
            if context:
                await context.close()

    def _evaluate_obsolescence(
        self, 
        tech: TechStack, 
        has_description: bool, 
        has_viewport: bool
    ) -> Tuple[bool, List[str]]:
        """Evalúa si el sitio es tecnológicamente obsoleto."""
        reasons = []
        
        # Check for obsolete tech
        if tech.is_obsolete:
            reasons.append("Uses obsolete technology (Flash/Framesets)")
        
        # Check for missing SEO basics
        if not has_description:
            reasons.append("Missing meta description")
        
        if not has_viewport:
            reasons.append("Missing viewport (not mobile-friendly)")
        
        return len(reasons) > 0, reasons

    # -------------------------------------------------------------------------
    # BATCH PROCESSING
    # -------------------------------------------------------------------------
    
    async def audit_leads_batch(
        self, 
        leads: List[Dict[str, Any]],
        on_progress: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Audita un batch de leads con sus sitios web.
        
        Args:
            leads: Lista de leads a auditar
            on_progress: Callback opcional para reportar progreso
            
        Returns:
            Lista de leads con campos de audit actualizados
        """
        leads_with_web = [lead for lead in leads if lead.get("website")]
        
        if not leads_with_web:
            logger.info("📋 No leads with websites to audit")
            return leads
        
        logger.info(f"🌐 Starting deep audit for {len(leads_with_web)} leads...")
        
        total = len(leads_with_web)
        completed = 0
        
        async def audit_single_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal completed
            
            website = lead.get("website")
            audit_result = await self.audit_website(website)
            
            # Convert to LeadSchema for score calculation
            lead_schema = LeadSchema(**lead)
            
            # Calculate AI score
            ai_score = calculate_ai_score(lead_schema, audit_result)
            
            # Update lead with audit data
            lead["audit_status"] = AuditStatus.COMPLETED.value
            lead["ai_score"] = ai_score
            lead["audit_data"] = audit_result.to_db_json()
            lead["ssl_valid"] = audit_result.ssl_valid
            lead["emails"] = audit_result.emails
            lead["tech_stack"] = self._tech_to_list(audit_result.tech_stack)
            lead["social_links"] = audit_result.social_links.to_dict()
            lead["audit_completed_at"] = datetime.utcnow().isoformat()
            
            # Update legacy fields for backward compatibility
            lead["web_obsoleta"] = audit_result.is_obsolete
            lead["web_analisis_motivo"] = " | ".join(audit_result.obsolete_reasons) if audit_result.obsolete_reasons else None
            
            # Promote to "caliente" if high score
            if ai_score >= 70 and lead.get("status") != "caliente":
                lead["status"] = "caliente"
            
            completed += 1
            if on_progress:
                await on_progress(completed, total)
            
            return lead
        
        # Process all leads (semaphore handles concurrency internally)
        tasks = [audit_single_lead(lead) for lead in leads_with_web]
        audited_leads = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        for i, result in enumerate(audited_leads):
            if isinstance(result, Exception):
                logger.error(f"Failed to audit lead: {result}")
                leads_with_web[i]["audit_status"] = AuditStatus.FAILED.value
        
        # Create map of audited leads
        audited_map = {lead.get("website"): lead for lead in leads_with_web}
        
        # Update original list
        for i, lead in enumerate(leads):
            if lead.get("website") in audited_map:
                leads[i] = audited_map[lead["website"]]
            else:
                # Leads without website get minimum score
                leads[i]["audit_status"] = AuditStatus.COMPLETED.value
                leads[i]["ai_score"] = 10  # Minimum for Maps-only presence
        
        high_score = sum(1 for lead in leads if (lead.get("ai_score") or 0) >= 70)
        logger.info(f"✅ Audit complete: {high_score}/{len(leads)} high-priority leads")
        
        return leads

    def _tech_to_list(self, tech: TechStack) -> List[str]:
        """Convierte TechStack a lista de strings para BD."""
        result = []
        if tech.cms:
            result.append(tech.cms)
        if tech.framework:
            result.append(tech.framework)
        if tech.ecommerce:
            result.append(tech.ecommerce)
        result.extend(tech.analytics)
        return result

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    
    async def cleanup(self) -> None:
        """Cierra el browser y libera recursos."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._is_initialized = False
        logger.info("✅ Deep Audit Engine shutdown complete")


# =============================================================================
# SINGLETON MANAGEMENT
# =============================================================================

_audit_service: Optional[DeepAuditService] = None


def get_audit_service() -> DeepAuditService:
    """Factory para obtener el servicio de auditoría."""
    global _audit_service
    if _audit_service is None:
        _audit_service = DeepAuditService()
    return _audit_service


async def cleanup_audit_service() -> None:
    """Limpia recursos del servicio de auditoría."""
    global _audit_service
    if _audit_service:
        await _audit_service.cleanup()
        _audit_service = None


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================
# Keep old names for backward compatibility with existing code

WebAnalyzerService = DeepAuditService
get_analyzer_service = get_audit_service
cleanup_analyzer = cleanup_audit_service

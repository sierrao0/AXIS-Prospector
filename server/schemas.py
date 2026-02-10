"""
Esquemas Pydantic V2 para validación de entrada/salida.

Optimizaciones:
- Validaciones más estrictas
- Campos adicionales para mejor tracking
- Documentación mejorada
- Modelos de auditoría profunda (Deep Audit)
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, computed_field
from enum import Enum
import re


# =============================================================================
# ENUMS
# =============================================================================


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LeadStatus(str, Enum):
    CALIENTE = "caliente"
    TIBIO = "tibio"
    FRIO = "frío"
    CONTACTADO = "contactado"
    CERRADO = "cerrado"


class AuditStatus(str, Enum):
    """Estado del proceso de auditoría de un lead."""
    PENDING = "pending"
    AUDITING = "auditing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# AUDIT MODELS (Deep Audit Pipeline)
# =============================================================================


class TechStack(BaseModel):
    """Tecnologías detectadas en un sitio web."""
    cms: Optional[str] = Field(None, description="CMS detectado (WordPress, Wix, Shopify, etc.)")
    framework: Optional[str] = Field(None, description="Framework frontend (React, Vue, Angular, etc.)")
    ecommerce: Optional[str] = Field(None, description="Plataforma e-commerce (WooCommerce, Magento, etc.)")
    analytics: List[str] = Field(default_factory=list, description="Herramientas de analytics detectadas")
    server: Optional[str] = Field(None, description="Servidor web detectado (nginx, Apache, etc.)")
    
    @computed_field
    @property
    def is_modern(self) -> bool:
        """Determina si el stack tecnológico es moderno."""
        modern_frameworks = {"react", "vue", "angular", "nextjs", "nuxt", "svelte", "astro"}
        modern_cms = {"webflow", "framer", "ghost"}
        
        framework_lower = (self.framework or "").lower()
        cms_lower = (self.cms or "").lower()
        
        return framework_lower in modern_frameworks or cms_lower in modern_cms
    
    @computed_field
    @property
    def is_obsolete(self) -> bool:
        """Detecta tecnologías obsoletas."""
        obsolete_tech = {"flash", "framesets", "frontpage", "dreamweaver"}
        all_tech = f"{self.cms} {self.framework} {self.ecommerce}".lower()
        return any(tech in all_tech for tech in obsolete_tech)


class SocialLinks(BaseModel):
    """Enlaces a redes sociales encontrados en el sitio."""
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None
    whatsapp: Optional[str] = None
    
    @computed_field
    @property
    def count(self) -> int:
        """Número de redes sociales activas."""
        links = [self.facebook, self.instagram, self.linkedin, 
                 self.twitter, self.tiktok, self.youtube, self.whatsapp]
        return sum(1 for link in links if link)
    
    def to_dict(self) -> Dict[str, str]:
        """Convierte a diccionario sin valores nulos."""
        return {k: v for k, v in self.model_dump().items() if v and k != "count"}


class AuditResult(BaseModel):
    """
    Resultado completo de la auditoría profunda de un sitio web.
    
    Incluye: SSL, emails, tech stack, social links, y métricas de calidad.
    """
    # Accesibilidad
    site_accessible: bool = Field(..., description="Si el sitio fue accesible durante el audit")
    block_reason: Optional[str] = Field(None, description="Razón si el sitio bloqueó el audit (WAF, timeout, etc.)")
    response_time_ms: Optional[int] = Field(None, description="Tiempo de respuesta en ms")
    final_url: Optional[str] = Field(None, description="URL final después de redirects")
    
    # SSL/Security
    ssl_valid: bool = Field(False, description="Si el certificado SSL es válido")
    ssl_error: Optional[str] = Field(None, description="Error de SSL si aplica")
    uses_https: bool = Field(False, description="Si la URL final usa HTTPS")
    
    # Emails
    emails: List[str] = Field(default_factory=list, description="Emails encontrados en el sitio")
    has_domain_email: bool = Field(False, description="Si tiene email con dominio propio (no gmail/hotmail)")
    
    # Tecnologías
    tech_stack: TechStack = Field(default_factory=TechStack)
    
    # Social
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    
    # SEO/Meta
    has_meta_description: bool = Field(False)
    has_viewport: bool = Field(False)
    title: Optional[str] = None
    
    # Obsolescencia (migrado del análisis anterior)
    is_obsolete: bool = Field(False, description="Si el sitio se considera obsoleto")
    obsolete_reasons: List[str] = Field(default_factory=list)
    
    # Timestamps
    audited_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_db_json(self) -> Dict[str, Any]:
        """Serializa para guardar en JSONB de Supabase."""
        return self.model_dump(mode="json", exclude_none=True)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ProspectRequest(BaseModel):
    """Esquema de entrada para el endpoint de prospección."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Búsqueda a realizar (ej: 'Restaurantes en Bogotá')",
        examples=["Restaurantes en Chapinero Bogota"]
    )
    max_results: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Número máximo de resultados a obtener"
    )

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Valida y limpia el query de búsqueda."""
        # Remover espacios extras
        v = ' '.join(v.split())
        # Verificar que no sea solo números o caracteres especiales
        if not re.search(r'[a-záéíóúñA-ZÁÉÍÓÚÑ]', v):
            raise ValueError('El query debe contener texto válido')
        return v


class ProspectResponse(BaseModel):
    """Respuesta inmediata del endpoint de prospección."""
    task_id: str = Field(..., description="ID único de la tarea")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    message: str = Field(..., description="Mensaje de confirmación")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LeadSchema(BaseModel):
    """Esquema de un lead individual."""
    id: Optional[Union[int, str]] = None
    name: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    reviews_count: Optional[int] = Field(None, ge=0)
    location: Optional[str] = None
    category: Optional[str] = None
    status: LeadStatus = LeadStatus.CALIENTE
    
    # Campos legacy de análisis básico
    web_obsoleta: Optional[bool] = Field(None, description="True si el sitio web es obsoleto")
    web_analisis_motivo: Optional[str] = Field(None, description="Razón del diagnóstico web")
    
    # Campos de Deep Audit (Phase 1)
    audit_status: AuditStatus = Field(default=AuditStatus.PENDING, description="Estado del audit")
    ai_score: Optional[int] = Field(None, ge=0, le=100, description="Score de priorización 0-100")
    audit_data: Optional[AuditResult] = Field(None, description="Resultado completo del audit")
    ssl_valid: Optional[bool] = Field(None, description="Certificado SSL válido")
    emails: Optional[List[str]] = Field(default_factory=list, description="Emails encontrados")
    tech_stack: Optional[List[str]] = Field(default_factory=list, description="Tecnologías detectadas")
    social_links: Optional[Dict[str, str]] = Field(default_factory=dict, description="Redes sociales")
    audit_completed_at: Optional[datetime] = Field(None, description="Timestamp de auditoría")
    
    created_at: Optional[datetime] = None

    @field_validator('phone')
    @classmethod
    def clean_phone(cls, v: Optional[str]) -> Optional[str]:
        """Limpia el número de teléfono."""
        if v:
            # Remover caracteres no numéricos excepto +
            return re.sub(r'[^\d+]', '', v)
        return v


class TaskStatusResponse(BaseModel):
    """Respuesta del estado de una tarea."""
    task_id: str
    status: TaskStatus
    leads_count: Optional[int] = None
    error: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progreso en porcentaje")
    message: Optional[str] = Field(None, description="Mensaje de estado detallado")


class LeadsListResponse(BaseModel):
    """Respuesta paginada de lista de leads."""
    count: int = Field(..., description="Número de leads en esta página")
    total: int = Field(..., description="Total de leads en la base de datos")
    limit: int
    offset: int
    has_more: bool = Field(..., description="Si hay más páginas disponibles")
    data: List[LeadSchema]


class HealthResponse(BaseModel):
    """Respuesta del health check."""
    status: str = "ok"
    service: str = "Prospector By Sierra API"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Respuesta de error estandarizada."""
    request_id: str
    error: str
    detail: str
    type: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# AI SCORE CALCULATION - "THE HUNTER LOGIC"
# =============================================================================
"""
🧠 The Hunter Logic - Motor de Decisión para Sierra

Este algoritmo evalúa la "Propensión a la Conversión Técnica" de un lead.
Busca negocios que NECESITAN servicios de desarrollo web y automatización.

MODELO DE PUNTUACIÓN PONDERADA (0-100 puntos)

Tres capas de evaluación:
1. FUNDACIÓN: Base de 50 puntos
2. MULTIPLICADORES DE VALOR: Bonificaciones por activos existentes
3. PENALIZACIONES CRÍTICAS: Detractores que identifican oportunidades

IMPORTANTE: Un score BAJO no significa "ignorar", significa "MÁXIMA OPORTUNIDAD".
Los leads con problemas técnicos son nuestro target principal.

Clasificación:
- 80-100 🔥 Hot: Infraestructura sólida, listo para optimización/automatización
- 60-79  🌡️ Warm: Tiene base, necesita mejoras técnicas
- 40-59  ❄️ Cold: Problemas técnicos evidentes, candidato para desarrollo
- 0-39   🎯 OPPORTUNITY: Sin presencia digital = The Architect target
"""

# Emails genéricos que no aportan valor (comunicación no profesional)
GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", 
    "yahoo.es", "live.com", "msn.com", "icloud.com", "protonmail.com",
    "mail.com", "aol.com", "zoho.com", "yandex.com"
}

# Tecnologías modernas que indican inversión en tech
MODERN_TECH_INDICATORS = {
    "react", "vue", "nextjs", "nuxt", "svelte", "angular",
    "tailwind", "typescript", "graphql", "prisma"
}

# Tecnologías obsoletas que indican necesidad de modernización
OBSOLETE_TECH_INDICATORS = {
    "flash", "framesets", "frontpage", "dreamweaver",
    "jquery-1", "jquery-2", "bootstrap-2", "bootstrap-3"
}


def is_generic_email(email: str) -> bool:
    """Determina si un email es genérico (gmail, hotmail, etc.)."""
    if not email or "@" not in email:
        return True
    domain = email.split("@")[-1].lower()
    return domain in GENERIC_EMAIL_DOMAINS


def is_social_only_website(url: str) -> bool:
    """Determina si la URL es solo un perfil de red social."""
    if not url:
        return False
    social_domains = [
        "facebook.com", "instagram.com", "linkedin.com", 
        "twitter.com", "tiktok.com", "youtube.com"
    ]
    return any(domain in url.lower() for domain in social_domains)


def calculate_ai_score(lead: "LeadSchema", audit: Optional[AuditResult]) -> int:
    """
    🎯 THE HUNTER LOGIC - Calcula el AI Score de un lead.
    
    Este algoritmo identifica leads que NECESITAN servicios de Sierra.
    
    FUNDACIÓN:
    - Base: 50 puntos (punto medio para evaluar hacia arriba o abajo)
    
    MULTIPLICADORES DE VALOR (Bonificaciones):
    - Presencia Web Propia: +20 (URL que no sea solo redes sociales)
    - Seguridad Técnica (SSL): +15 (HTTPS con certificado válido)
    - Accesibilidad de Contacto: +10 (email encontrado en el sitio)
    - Modernidad del Stack: +10 (React, Next.js, Vue, etc.)
    - Huella Social: +5 por red (max +15)
    - Prueba Social: +5 (>50 reviews con >4.0 rating)
    
    PENALIZACIONES CRÍTICAS (Identifican oportunidades):
    - Inexistencia Digital: -30 (solo Google Maps, sin web)
    - Vulnerabilidad de Datos: -20 (HTTP o SSL vencido)
    - Tecnología Obsoleta: -15 (Flash, jQuery antiguo, tablas)
    - Comunicación Genérica: -5 (solo email gmail/hotmail)
    
    CLASIFICACIÓN:
    - 80-100: 🔥 Hot Lead → Contacto inmediato, auditoría técnica
    - 60-79:  🌡️ Warm Lead → Propuesta de optimización
    - 40-59:  ❄️ Cold Lead → Nutrición de contenido
    - 0-39:   🎯 OPPORTUNITY → Candidato para The Architect (nueva web)
    
    Args:
        lead: Datos del lead desde Google Maps
        audit: Resultado de la auditoría Playwright (puede ser None)
        
    Returns:
        Score entre 0 y 100
    """
    score = 50  # FUNDACIÓN: Base
    
    # =========================================================================
    # CASO ESPECIAL: Sin sitio web o sitio inaccesible
    # =========================================================================
    
    has_real_website = lead.website and not is_social_only_website(lead.website)
    
    if not has_real_website:
        # INEXISTENCIA DIGITAL: -30 puntos
        # Este es un candidato PERFECTO para The Architect
        score -= 30
        
        # Pero aún valoramos su potencial de negocio
        if lead.reviews_count and lead.rating:
            if lead.reviews_count > 100 and lead.rating >= 4.5:
                score += 15  # Negocio exitoso sin web = OPORTUNIDAD ORO
            elif lead.reviews_count > 50 and lead.rating >= 4.0:
                score += 10  # Negocio establecido sin web = OPORTUNIDAD
            elif lead.reviews_count > 20 and lead.rating >= 3.5:
                score += 5   # Negocio en crecimiento = Potencial
        
        # Si tiene teléfono, es contactable
        if lead.phone:
            score += 5
        
        return max(0, min(100, score))
    
    # =========================================================================
    # SITIO WEB EXISTE PERO NO FUE AUDITABLE
    # =========================================================================
    
    if audit is None or not audit.site_accessible:
        # Tiene web pero no pudimos auditarla (bloqueado, timeout, etc.)
        score -= 10  # Penalización menor por inaccesibilidad
        
        # Si es perfil de redes sociales, valorarlo
        if lead.website:
            if "instagram.com" in lead.website.lower():
                score += 5  # Instagram activo es señal de marketing
            if "facebook.com" in lead.website.lower():
                score += 3
        
        # Valorar reputación del negocio
        if lead.reviews_count and lead.rating:
            if lead.reviews_count > 50 and lead.rating >= 4.0:
                score += 5
        
        return max(0, min(100, score))
    
    # =========================================================================
    # SITIO WEB AUDITABLE - SCORING COMPLETO
    # =========================================================================
    
    # PRESENCIA WEB PROPIA: +20 puntos
    score += 20
    
    # SEGURIDAD TÉCNICA (SSL)
    if audit.ssl_valid and audit.uses_https:
        score += 15  # SSL válido = inversión en seguridad
    else:
        score -= 20  # VULNERABILIDAD DE DATOS: HTTP o SSL inválido
    
    # ACCESIBILIDAD DE CONTACTO
    if audit.emails:
        score += 10  # Tiene email visible
        
        # Bonus por email corporativo vs genérico
        has_corporate_email = any(not is_generic_email(e) for e in audit.emails)
        if has_corporate_email or audit.has_domain_email:
            score += 5  # Email profesional
        else:
            score -= 5  # COMUNICACIÓN GENÉRICA: Solo gmail/hotmail
    
    # MODERNIDAD DEL STACK
    if audit.tech_stack:
        if audit.tech_stack.is_modern:
            score += 10  # Tech moderna = cliente que valora tecnología
        
        if audit.tech_stack.is_obsolete:
            score -= 15  # TECNOLOGÍA OBSOLETA = Oportunidad de modernización
    
    # HUELLA SOCIAL: +5 por red (max +15)
    if audit.social_links:
        social_count = audit.social_links.count
        social_bonus = min(15, social_count * 5)
        score += social_bonus
    
    # PRUEBA SOCIAL (Reviews de Google Maps)
    if lead.reviews_count and lead.rating:
        if lead.reviews_count > 100 and lead.rating >= 4.5:
            score += 10  # Excelente reputación
        elif lead.reviews_count > 50 and lead.rating >= 4.0:
            score += 5   # Buena reputación
    
    # SEO BÁSICO (indicador de profesionalismo web)
    if audit.has_meta_description and audit.has_viewport:
        score += 5
    elif not audit.has_viewport:
        score -= 5  # No mobile-friendly = oportunidad
    
    # Clamp entre 0 y 100
    return max(0, min(100, score))


def calculate_opportunity_score(lead: "LeadSchema", audit: Optional[AuditResult]) -> int:
    """
    🎯 OPPORTUNITY SCORE - Qué tanto NECESITA el lead nuestros servicios.
    
    Este score es INVERSO al ai_score en ciertos aspectos:
    - Score ALTO = Lead con PROBLEMAS TÉCNICOS evidentes = MAYOR OPORTUNIDAD
    - Score BAJO = Lead con infraestructura sólida = Menor urgencia
    
    Usado para priorizar outreach en Phase 2 (The Sniper).
    
    Returns:
        Score entre 0 y 100 (100 = máxima oportunidad de venta)
    """
    opportunity = 50  # Base
    
    has_real_website = lead.website and not is_social_only_website(lead.website)
    
    # =========================================================================
    # OPORTUNIDADES PRINCIPALES
    # =========================================================================
    
    # Sin web = MÁXIMA oportunidad para The Architect
    if not has_real_website:
        opportunity += 40
        
        # Negocio exitoso sin web = ORO PURO
        if lead.reviews_count and lead.rating:
            if lead.reviews_count > 100 and lead.rating >= 4.5:
                opportunity += 10
            elif lead.reviews_count > 50 and lead.rating >= 4.0:
                opportunity += 5
        
        return min(100, opportunity)
    
    # Sitio inaccesible = Problema técnico evidente
    if audit is None or not audit.site_accessible:
        opportunity += 25
        return min(100, opportunity)
    
    # =========================================================================
    # INDICADORES DE OPORTUNIDAD EN SITIOS EXISTENTES
    # =========================================================================
    
    # Sin SSL = Urgencia de seguridad
    if not audit.ssl_valid or not audit.uses_https:
        opportunity += 25
    
    # Tech obsoleta = Modernización necesaria
    if audit.tech_stack and audit.tech_stack.is_obsolete:
        opportunity += 20
    
    # Sin emails visibles = Problema de conversión
    if not audit.emails:
        opportunity += 10
    
    # Solo email genérico = Falta de profesionalismo
    elif all(is_generic_email(e) for e in audit.emails):
        opportunity += 5
    
    # Sin meta/viewport = No mobile-friendly
    if not audit.has_viewport:
        opportunity += 15
    
    # Sin redes sociales = Oportunidad de marketing digital
    if not audit.social_links or audit.social_links.count == 0:
        opportunity += 10
    
    # =========================================================================
    # REDUCTORES (Menos oportunidad si ya tienen todo)
    # =========================================================================
    
    # Tech moderna = Ya invirtieron
    if audit.tech_stack and audit.tech_stack.is_modern:
        opportunity -= 20
    
    # Buen SEO = Profesionales trabajando
    if audit.has_meta_description and audit.has_viewport:
        opportunity -= 10
    
    return max(0, min(100, opportunity))


def get_lead_category(ai_score: int, opportunity_score: int) -> str:
    """
    Determina la categoría del lead combinando ambos scores.
    
    Returns:
        Categoría: 'hot', 'warm', 'cold', 'opportunity', 'ice'
    """
    # Alta oportunidad + bajo ai_score = OPPORTUNITY (The Architect target)
    if opportunity_score >= 70 and ai_score < 40:
        return "opportunity"  # 🎯 Candidato para nueva web
    
    # Alto ai_score = Lead calificado
    if ai_score >= 80:
        return "hot"      # 🔥 Hot lead
    elif ai_score >= 60:
        return "warm"     # 🌡️ Warm lead
    elif ai_score >= 40:
        return "cold"     # ❄️ Cold lead
    else:
        # Bajo ai_score pero baja oportunidad = skip
        if opportunity_score < 40:
            return "ice"  # 🧊 Ignorar
        else:
            return "opportunity"  # 🎯 Aún tiene potencial


def get_score_category(score: int) -> str:
    """Retorna la categoría del score para UI (legacy compatibility)."""
    if score >= 80:
        return "hot"      # 🔥 Hot lead
    elif score >= 60:
        return "warm"     # 🌡️ Warm lead
    elif score >= 40:
        return "cold"     # ❄️ Cold lead
    else:
        return "opportunity"  # 🎯 Opportunity (antes era "ice")


"""
Esquemas Pydantic V2 para validación de entrada/salida.

Optimizaciones:
- Validaciones más estrictas
- Campos adicionales para mejor tracking
- Documentación mejorada
- Modelos de auditoría profunda (Deep Audit)
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
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
    id: Optional[int] = None
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
    service: str = "AXIS Prospector API"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# AI SCORE CALCULATION
# =============================================================================

# Emails genéricos que no aportan valor
GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", 
    "yahoo.es", "live.com", "msn.com", "icloud.com", "protonmail.com",
    "mail.com", "aol.com", "zoho.com", "yandex.com"
}


def is_generic_email(email: str) -> bool:
    """Determina si un email es genérico (gmail, hotmail, etc.)."""
    if not email or "@" not in email:
        return True
    domain = email.split("@")[-1].lower()
    return domain in GENERIC_EMAIL_DOMAINS


def calculate_ai_score(lead: "LeadSchema", audit: Optional[AuditResult]) -> int:
    """
    Calcula el AI Score de un lead basado en los resultados de auditoría.
    
    Matriz de puntuación:
    - Base: 50 puntos
    - SSL válido: +15
    - Tiene emails: +10 (+5 bonus si es email de dominio)
    - Tech moderna: +10
    - Redes sociales: +5 cada una (max +15)
    - Reviews altos: +5 (>50 reviews con >4.0 rating)
    
    Penalizaciones:
    - Sin website: -30
    - Sin SSL: -20
    - Tech obsoleta: -15
    - Email genérico: -5
    
    Returns:
        Score entre 0 y 100
    """
    # Caso especial: sitio no accesible
    if audit is None or not audit.site_accessible:
        base = 10  # Mínimo: tiene presencia en Google Maps
        
        # Aún podemos dar puntos si sabemos que tiene redes sociales desde Maps
        if lead.website:
            social_domains = ["facebook.com", "instagram.com", "linkedin.com"]
            for domain in social_domains:
                if domain in lead.website.lower():
                    base += 5
        
        return min(20, base)  # Cap en 20 para sitios no accesibles
    
    # Scoring normal para sitios accesibles
    score = 50  # Base
    
    # SSL (+15 si válido, -20 si inválido)
    if audit.ssl_valid:
        score += 15
    else:
        score -= 20
    
    # Emails (+10 base, +5 bonus por email de dominio)
    if audit.emails:
        score += 10
        if audit.has_domain_email or any(not is_generic_email(e) for e in audit.emails):
            score += 5
        else:
            score -= 5  # Penalización por solo emails genéricos
    
    # Tech Stack
    if audit.tech_stack.is_modern:
        score += 10
    if audit.tech_stack.is_obsolete:
        score -= 15
    
    # Social Links (+5 por cada una, max +15)
    social_bonus = min(15, audit.social_links.count * 5)
    score += social_bonus
    
    # Reviews (bonus por buena reputación)
    if lead.reviews_count and lead.rating:
        if lead.reviews_count > 50 and lead.rating >= 4.0:
            score += 5
        elif lead.reviews_count > 100 and lead.rating >= 4.5:
            score += 10
    
    # SEO básico
    if audit.has_meta_description and audit.has_viewport:
        score += 5
    
    # Penalización por sitio sin web real (solo Maps)
    if not lead.website:
        score -= 30
    
    # Clamp entre 0 y 100
    return max(0, min(100, score))


def get_score_category(score: int) -> str:
    """Retorna la categoría del score para UI."""
    if score >= 80:
        return "hot"      # 🔥 Hot lead
    elif score >= 60:
        return "warm"     # 🌡️ Warm lead
    elif score >= 40:
        return "cold"     # ❄️ Cold lead
    else:
        return "ice"      # 🧊 Ice / skip

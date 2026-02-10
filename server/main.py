"""
Prospector By Sierra API - Punto de entrada principal.

API asíncrona para extracción y gestión de leads usando FastAPI.

Optimizaciones:
- Rate limiting para protección de endpoints
- Background tasks verdaderamente async
- Mejor manejo de errores con excepciones tipadas
- Cleanup de recursos en shutdown
"""
from __future__ import annotations

import uuid
import asyncio
import logging
import hmac
from typing import Dict, Optional, Tuple
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from datetime import datetime
from config import setup_logging, validate_environment, get_settings
from schemas import (
    ProspectRequest,
    ProspectResponse,
    TaskStatusResponse,
    HealthResponse,
    TaskStatus,
    LeadSchema,
    AuditStatus,
    calculate_ai_score,
    calculate_opportunity_score,
    get_lead_category,
    ErrorResponse,
)
from services.scraper import get_scraper_service, cleanup_scraper
from services.database import get_database_service, cleanup_database
from services.analyzer import get_analyzer_service, cleanup_analyzer
from services.exceptions import (
    SierraProspectorError,
    ScraperError,
    DatabaseError,
    LeadNotFoundError,
)

# Configurar logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Almacén en memoria para el estado de tareas (en producción usar Redis)
task_store: Dict[str, Dict] = {}
recent_queries: Dict[Tuple[str, str], datetime] = {}

# Context variable para task_id en logs
_task_id_context: ContextVar[Optional[str]] = ContextVar('task_id', default=None)


class TaskLoggerAdapter(logging.LoggerAdapter):
    """Adapter para incluir task_id en los logs."""
    
    def process(self, msg, kwargs):
        task_id = _task_id_context.get()
        if task_id:
            return f"[{task_id}] {msg}", kwargs
        return msg, kwargs


def get_task_logger() -> TaskLoggerAdapter:
    """Obtiene un logger con soporte para task_id."""
    return TaskLoggerAdapter(logger, {})


def separator(char: str = "=", width: int = 100) -> str:
    """Genera una linea separadora."""
    return char * width


def log_score_analysis(task_logger: TaskLoggerAdapter, lead_name: str, 
                       ai_score: int, opportunity_score: int, category: str,
                       audit_result=None) -> None:
    """
    Loguea el desglose de los scores de un lead.
    """
    # Emoji por score
    ai_badge = "HOT" if ai_score >= 80 else "WARM" if ai_score >= 60 else "COLD" if ai_score >= 40 else "OPP"
    
    if audit_result and audit_result.site_accessible:
        # Mostrar detalles del audit
        ssl_status = "SSL_OK" if audit_result.ssl_valid else "NO_SSL"
        emails_count = len(audit_result.emails) if audit_result.emails else 0
        socials = audit_result.social_links.count if audit_result.social_links else 0
        task_logger.info(
            f"    SCORING: ai={ai_score}/100 | opp={opportunity_score}/100 | "
            f"cat={category} | {ssl_status} | emails={emails_count} | sociales={socials}"
        )
    else:
        # Lead sin web o sitio inaccesible
        task_logger.info(
            f"    SCORING: ai={ai_score}/100 | opp={opportunity_score}/100 | "
            f"cat={category}"
        )


def _get_client_ip(request: Request) -> str:
    """Obtiene IP del cliente (fallback a 'unknown')."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _cleanup_recent_queries(cutoff_minutes: int = 10) -> None:
    """Limpia queries viejas para evitar crecimiento en memoria."""
    if not recent_queries:
        return
    cutoff = datetime.utcnow().timestamp() - (cutoff_minutes * 60)
    for key, ts in list(recent_queries.items()):
        if ts.timestamp() < cutoff:
            recent_queries.pop(key, None)


def _enforce_query_cooldown(request: Request, query: str) -> None:
    """Previene spam: mismo IP + query en un intervalo corto."""
    settings = get_settings()
    _cleanup_recent_queries()
    ip = _get_client_ip(request)
    key = (ip, query.lower())
    now = datetime.utcnow()
    last = recent_queries.get(key)
    if last and (now - last).total_seconds() < settings.request_cooldown_secs:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Solicitud duplicada. Espera {settings.request_cooldown_secs}s antes de reintentar."
        )
    recent_queries[key] = now


def _verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
) -> None:
    """Valida API Key si está configurada en entorno."""
    settings = get_settings()
    if not settings.api_key:
        return
    provided = x_api_key or ""
    if not hmac.compare_digest(provided, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o ausente"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación."""
    # Startup
    logger.info("🚀 Iniciando Prospector By Sierra API...")
    try:
        validate_environment()
        logger.info("✅ Variables de entorno validadas")
        
        # Pre-inicializar servicios para detectar errores temprano
        get_scraper_service()
        get_database_service()
        analyzer = get_analyzer_service()
        await analyzer.initialize()
        logger.info("✅ Servicios inicializados")
    except ValueError as e:
        logger.error(str(e))
        raise

    yield

    # Shutdown - Limpiar recursos
    logger.info("👋 Cerrando Prospector By Sierra API...")
    await cleanup_scraper()
    await cleanup_database()
    await cleanup_analyzer()
    logger.info("✅ Recursos liberados")


# Crear aplicación FastAPI
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API de prospección automatizada para Prospector By Sierra",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Agrega un request_id para trazabilidad."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(SierraProspectorError)
async def sierra_error_handler(request: Request, exc: SierraProspectorError):
    """Manejador global para errores de la aplicación."""
    logger.error(f"Error de aplicación: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            request_id=getattr(request.state, "request_id", "unknown"),
            error="application_error",
            detail=exc.message,
            type=type(exc).__name__,
        ).model_dump(mode="json")
    )


@app.exception_handler(LeadNotFoundError)
async def lead_not_found_handler(request: Request, exc: LeadNotFoundError):
    """Manejador para leads no encontrados."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            request_id=getattr(request.state, "request_id", "unknown"),
            error="not_found",
            detail=exc.message,
            type=type(exc).__name__,
        ).model_dump(mode="json")
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador para HTTPException con respuesta estandarizada."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            request_id=getattr(request.state, "request_id", "unknown"),
            error="http_error",
            detail=str(exc.detail),
            type="HTTPException",
        ).model_dump(mode="json")
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejador para errores de validación de request."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            request_id=getattr(request.state, "request_id", "unknown"),
            error="validation_error",
            detail="Error de validación en el request",
            type="RequestValidationError",
            errors=exc.errors(),
        ).model_dump(mode="json")
    )


# ============================================================================
# Background Tasks (Async)
# ============================================================================

async def ejecutar_prospeccion_async(task_id: str, query: str, max_results: int):
    """
    Tarea en segundo plano para ejecutar la prospección de forma async.
    
    Args:
        task_id: ID único de la tarea
        query: Término de búsqueda
        max_results: Número máximo de resultados
    """
    # Establecer task_id en el contexto
    _task_id_context.set(task_id)
    task_logger = get_task_logger()
    
    # Separadores visuales
    task_logger.info(separator("="))
    task_logger.info(f"Iniciando prospección: '{query}' (max: {max_results} resultados)")
    task_logger.info(separator("-"))
    
    task_store[task_id]["status"] = TaskStatus.RUNNING

    try:
        # 1. Extraer leads de Apify (async)
        task_logger.info("\n[FASE 1] Extracción de Leads (Apify)")
        task_logger.info(separator("-"))
        scraper = get_scraper_service()
        leads = await scraper.extraer_leads(query, max_results)

        # 2. Guardar en Supabase (async)
        task_logger.info("\n[FASE 2] Guardando Leads en Supabase")
        task_logger.info(separator("-"))
        db = get_database_service()
        saved_leads = await db.guardar_leads(leads) # Ahora retorna la lista de leads guardados
        count = len(saved_leads)
        task_logger.info(f"[OK] {count} leads guardados")

        # 3. Deep Audit (Async Pipeline)
        if saved_leads:
            task_logger.info("\n[FASE 3] Deep Audit de Sitios Web")
            task_logger.info(separator("-"))
            analyzer = get_analyzer_service()
            task_logger.info(f"Iniciando auditoría de {count} leads...")
            
            # Inicializar tracking de progreso
            task_store[task_id]["progress"] = 0.0
            task_store[task_id]["message"] = f"Iniciando auditoría de {count} leads..."
            processed_count = 0

            def _format_lead_tag(lead_data: Dict) -> str:
                """Construye etiqueta corta para logs por lead."""
                lead_id = lead_data.get("id", "unknown")
                name = (lead_data.get("name") or "sin nombre").strip()
                website = (lead_data.get("website") or "sin web").strip()
                return f"Lead {lead_id} | {name} | {website}"

            async def audit_with_retry(website: str, lead_tag: str):
                """Ejecuta auditoría con retry simple y backoff."""
                attempts = settings.audit_retry_attempts
                for attempt in range(1, attempts + 1):
                    task_logger.info(f"    [INTENTO {attempt}/{attempts}] Auditando...")
                    audit = await analyzer.audit_website(website)
                    if audit.site_accessible:
                        return audit
                    if attempt < attempts:
                        wait_seconds = settings.audit_retry_backoff_secs * attempt
                        task_logger.warning(
                            f"    [REINTENTO] Audiencia fallida, esperando {wait_seconds:.1f}s "
                            f"({attempt}/{attempts})"
                        )
                        await asyncio.sleep(wait_seconds)
                return audit
            
            async def process_audit(lead_data: Dict):
                nonlocal processed_count
                try:
                    lead_id = lead_data["id"]
                    website = lead_data.get("website")
                    lead_name = lead_data.get("name", "sin nombre")
                    lead_tag = _format_lead_tag(lead_data)
                    task_logger.info(f"  [LEAD] {lead_tag}")
                    
                    # Convertir a esquema para scoring
                    lead_obj = LeadSchema(**lead_data)
                    
                    if not website:
                        # Si no hay web (ej. solo Maps), score básico
                        # THE HUNTER LOGIC: Sin web = MÁXIMA OPORTUNIDAD
                        score = calculate_ai_score(lead_obj, None)
                        opportunity = calculate_opportunity_score(lead_obj, None)
                        category = get_lead_category(score, opportunity)
                        
                        await db.actualizar_audit_lead(lead_id, {
                            "audit_status": AuditStatus.COMPLETED.value,
                            "ai_score": score,
                            "opportunity_score": opportunity,
                            "lead_category": category,
                            "audit_completed_at": datetime.utcnow().isoformat()
                        })
                        task_logger.info(f"    [NO_WEB] Solo presencia en Google Maps")
                        log_score_analysis(task_logger, lead_name, score, opportunity, category, None)
                    else:
                        # Update status to auditing
                        await db.actualizar_audit_lead(lead_id, {"audit_status": AuditStatus.AUDITING.value})
                        task_logger.info(f"    [AUDIT] Iniciando auditoria de sitio web...")

                        # Execute audit
                        audit_result = await audit_with_retry(website, lead_tag)
                        if not audit_result.site_accessible:
                            task_logger.warning(f"    [WARN] Sitio no accesible durante audit")
                        
                        # Calculate Scores - THE HUNTER LOGIC
                        score = calculate_ai_score(lead_obj, audit_result)
                        opportunity = calculate_opportunity_score(lead_obj, audit_result)
                        category = get_lead_category(score, opportunity)
                        
                        # Prepare update data for flat columns and JSONB
                        tech_list = []
                        if audit_result.tech_stack:
                            if audit_result.tech_stack.cms: tech_list.append(audit_result.tech_stack.cms)
                            if audit_result.tech_stack.framework: tech_list.append(audit_result.tech_stack.framework)
                            if audit_result.tech_stack.ecommerce: tech_list.append(audit_result.tech_stack.ecommerce)

                        update_data = {
                            "audit_status": (AuditStatus.FAILED.value if not audit_result.site_accessible else AuditStatus.COMPLETED.value),
                            "audit_data": audit_result.to_db_json(),
                            "ai_score": score,
                            "opportunity_score": opportunity,
                            "lead_category": category,
                            "ssl_valid": audit_result.ssl_valid,
                            "web_obsoleta": audit_result.is_obsolete,
                            "tech_stack": tech_list,
                            "emails": audit_result.emails,
                            "social_links": audit_result.social_links.to_dict(),
                            "audit_completed_at": datetime.utcnow().isoformat()
                        }
                        
                        # Update DB
                        await db.actualizar_audit_lead(lead_id, update_data)
                        
                        # Log audit summary  
                        ssl_status = f"SSL={audit_result.ssl_valid}"
                        email_status = f"emails={len(audit_result.emails) if audit_result.emails else 0}"
                        tech_status = f"tech={audit_result.tech_stack.cms or 'custom'}" if audit_result.tech_stack else "tech=unknown"
                        task_logger.info(f"    [AUDIT_OK] {ssl_status} | {email_status} | {tech_status}")
                        log_score_analysis(task_logger, lead_name, score, opportunity, category, audit_result)
                    
                    # Update progress
                    processed_count += 1
                    progress_pct = (processed_count / count) * 100
                    task_store[task_id]["progress"] = round(progress_pct, 1)
                    task_store[task_id]["message"] = f"Auditando: {processed_count}/{count} leads ({int(progress_pct)}%)"
                    
                except Exception as e:
                    task_logger.error(f"    [ERROR] {str(e)[:80]}")
                    try:
                        await db.actualizar_audit_lead(
                            lead_data["id"], 
                            {"audit_status": AuditStatus.FAILED.value}
                        )
                    except:
                        pass
                    # Aún si falla, contamos el progreso
                    processed_count += 1
                    task_store[task_id]["progress"] = round((processed_count / count) * 100, 1)

            # Ejecutar auditorías concurrentemente
            # La concurrencia está limitada internamente por CONTEXT_SEMAPHORE en analyzer.py
            await asyncio.gather(*[process_audit(l) for l in saved_leads])
            
            task_logger.info(separator("-"))
            task_logger.info(f"[OK] Deep Audit completado para {count} leads")
            task_store[task_id]["progress"] = 100.0
            task_store[task_id]["message"] = "Prospección completada"

        # 4. Actualizar estado de la tarea
        task_store[task_id]["status"] = TaskStatus.COMPLETED
        task_store[task_id]["leads_count"] = count
        
        task_logger.info(separator("="))
        task_logger.info(f"[SUCCESS] Prospección completada exitosamente | {count} leads procesados")
        task_logger.info(separator("="))

    except ScraperError as e:
        error_msg = f"Error en scraping: {e.message}"
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["error"] = error_msg
        task_logger.error(separator("="))
        task_logger.error(f"[FAILED] ERROR: {error_msg}")
        task_logger.error(separator("="))

    except DatabaseError as e:
        error_msg = f"Error en base de datos: {e.message}"
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["error"] = error_msg
        task_logger.error(separator("="))
        task_logger.error(f"[FAILED] ERROR: {error_msg}")
        task_logger.error(separator("="))

    except Exception as e:
        error_msg = str(e)
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["error"] = error_msg
        task_logger.error(separator("="))
        task_logger.error(f"[FAILED] ERROR INESPERADO: {error_msg}")
        task_logger.error(separator("="))


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """Health check de la API."""
    return HealthResponse()


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Endpoint de salud para monitoreo."""
    return HealthResponse()


@app.post(
    "/api/v1/prospect",
    response_model=ProspectResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Prospecting"],
    summary="Start lead prospecting",
    description="Initiates a background task to search for leads on Google Maps."
)
@limiter.limit("10/minute")
async def prospect(
    request: Request,
    data: ProspectRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(_verify_api_key)
):
    """
    Inicia una prospección de leads.
    
    - **query**: Término de búsqueda (ej: "Restaurantes en Bogotá")
    - **max_results**: Número máximo de resultados (1-100)
    
    La búsqueda se ejecuta en segundo plano y los resultados se guardan en Supabase.
    Rate limit: 10 requests por minuto.
    """
    _enforce_query_cooldown(request, data.query)
    # Generar ID único para la tarea
    task_id = str(uuid.uuid4())

    # Inicializar estado de la tarea
    task_store[task_id] = {
        "status": TaskStatus.PENDING,
        "query": data.query,
        "max_results": data.max_results,
        "leads_count": None,
        "error": None
    }

    # Agregar tarea en segundo plano (async)
    background_tasks.add_task(
        ejecutar_prospeccion_async,
        task_id,
        data.query,
        data.max_results
    )

    logger.info(f"📌 Nueva tarea creada: {task_id} | Query: '{data.query}'")

    return ProspectResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message=f"Prospección iniciada. Buscando '{data.query}' (max: {data.max_results})"
    )


@app.get(
    "/api/v1/tasks/{task_id}",
    response_model=TaskStatusResponse,
    tags=["Prospecting"],
    summary="Get task status",
    description="Gets the current status of a prospecting task."
)
@limiter.limit("60/minute")
async def get_task_status(
    request: Request,
    task_id: str,
    _: None = Depends(_verify_api_key)
):
    """
    Consulta el estado de una tarea de prospección.
    
    - **task_id**: ID de la tarea retornado por /prospectar
    """
    if task_id not in task_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea '{task_id}' no encontrada"
        )

    tarea = task_store[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=tarea["status"],
        leads_count=tarea.get("leads_count"),
        error=tarea.get("error"),
        progress=tarea.get("progress"),
        message=tarea.get("message")
    )


@app.get(
    "/api/v1/leads",
    tags=["Leads"],
    summary="List leads",
    description="Gets the list of saved leads from the database."
)
@limiter.limit("30/minute")
async def list_leads(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    _: None = Depends(_verify_api_key)
):
    """
    Lists saved leads.
    
    - **limit**: Maximum number of results (default: 50)
    - **offset**: Pagination offset (default: 0)
    - **status**: Filter by status (optional)
    """
    db = get_database_service()
    leads = await db.obtener_leads(limit=limit, offset=offset, status=status)
    total = await db.contar_leads(status=status)
    
    return {
        "count": len(leads),
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(leads) < total,
        "data": leads
    }


@app.patch(
    "/api/v1/leads/{lead_id}/status",
    tags=["Leads"],
    summary="Update lead status",
    description="Updates the status of a specific lead."
)
@limiter.limit("30/minute")
async def update_lead(
    request: Request,
    lead_id: str,
    new_status: str,
    _: None = Depends(_verify_api_key)
):
    """
    Updates the status of a lead.
    
    - **lead_id**: Lead ID
    - **new_status**: New status (hot, warm, cold, contacted, closed)
    """
    valid_statuses = {"hot", "warm", "cold", "contacted", "closed"}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed values: {valid_statuses}"
        )
    
    db = get_database_service()
    await db.actualizar_estado_lead(lead_id, new_status)
    
    return {"message": f"Lead {lead_id} updated to '{new_status}'"}


# ============================================================================
# Ejecución
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
"""
AXIS Prospector API - Punto de entrada principal.

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
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import setup_logging, validate_environment, get_settings
from schemas import (
    ProspectRequest,
    ProspectResponse,
    TaskStatusResponse,
    HealthResponse,
    TaskStatus,
)
from services.scraper import get_scraper_service, cleanup_scraper
from services.database import get_database_service, cleanup_database
from services.analyzer import get_analyzer_service, cleanup_analyzer
from services.exceptions import (
    AXISProspectorError,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación."""
    # Startup
    logger.info("🚀 Iniciando AXIS Prospector API...")
    try:
        validate_environment()
        logger.info("✅ Variables de entorno validadas")
        
        # Pre-inicializar servicios para detectar errores temprano
        get_scraper_service()
        get_database_service()
        logger.info("✅ Servicios inicializados")
    except ValueError as e:
        logger.error(str(e))
        raise

    yield

    # Shutdown - Limpiar recursos
    logger.info("👋 Cerrando AXIS Prospector API...")
    await cleanup_scraper()
    await cleanup_database()
    await cleanup_analyzer()
    logger.info("✅ Recursos liberados")


# Crear aplicación FastAPI
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API de prospección automatizada para AXIS Agency",
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


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(AXISProspectorError)
async def axis_error_handler(request: Request, exc: AXISProspectorError):
    """Manejador global para errores de la aplicación."""
    logger.error(f"Error de aplicación: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.message, "type": type(exc).__name__}
    )


@app.exception_handler(LeadNotFoundError)
async def lead_not_found_handler(request: Request, exc: LeadNotFoundError):
    """Manejador para leads no encontrados."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message}
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
    logger.info(f"📋 Tarea {task_id}: Iniciando prospección...")
    task_store[task_id]["status"] = TaskStatus.RUNNING

    try:
        # 1. Extraer leads de Apify (async)
        scraper = get_scraper_service()
        leads = await scraper.extraer_leads(query, max_results)

        # 2. Guardar en Supabase (async)
        db = get_database_service()
        count = await db.guardar_leads(leads)

        # 3. Actualizar estado de la tarea
        task_store[task_id]["status"] = TaskStatus.COMPLETED
        task_store[task_id]["leads_count"] = count
        logger.info(f"✅ Tarea {task_id}: Completada. {count} leads guardados.")

    except ScraperError as e:
        error_msg = f"Error en scraping: {e.message}"
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["error"] = error_msg
        logger.error(f"❌ Tarea {task_id}: {error_msg}")

    except DatabaseError as e:
        error_msg = f"Error en base de datos: {e.message}"
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["error"] = error_msg
        logger.error(f"❌ Tarea {task_id}: {error_msg}")

    except Exception as e:
        error_msg = str(e)
        task_store[task_id]["status"] = TaskStatus.FAILED
        task_store[task_id]["error"] = error_msg
        logger.error(f"❌ Tarea {task_id}: Error inesperado - {error_msg}")


def ejecutar_prospeccion(task_id: str, query: str, max_results: int):
    """Wrapper para ejecutar la tarea async en background."""
    asyncio.create_task(ejecutar_prospeccion_async(task_id, query, max_results))


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
    "/api/v1/prospectar",
    response_model=ProspectResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Prospección"],
    summary="Iniciar prospección de leads",
    description="Inicia una tarea en segundo plano para buscar leads en Google Maps."
)
@limiter.limit("10/minute")
async def prospectar(
    request: Request,
    data: ProspectRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia una prospección de leads.
    
    - **query**: Término de búsqueda (ej: "Restaurantes en Bogotá")
    - **max_results**: Número máximo de resultados (1-100)
    
    La búsqueda se ejecuta en segundo plano y los resultados se guardan en Supabase.
    Rate limit: 10 requests por minuto.
    """
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
        ejecutar_prospeccion,
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
    "/api/v1/tareas/{task_id}",
    response_model=TaskStatusResponse,
    tags=["Prospección"],
    summary="Consultar estado de tarea",
    description="Obtiene el estado actual de una tarea de prospección."
)
@limiter.limit("60/minute")
async def obtener_estado_tarea(request: Request, task_id: str):
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
        error=tarea.get("error")
    )


@app.get(
    "/api/v1/leads",
    tags=["Leads"],
    summary="Listar leads",
    description="Obtiene la lista de leads guardados en la base de datos."
)
@limiter.limit("30/minute")
async def listar_leads(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    estado: Optional[str] = None
):
    """
    Lista los leads guardados.
    
    - **limit**: Número máximo de resultados (default: 50)
    - **offset**: Desplazamiento para paginación (default: 0)
    - **estado**: Filtrar por estado (opcional)
    """
    db = get_database_service()
    leads = await db.obtener_leads(limit=limit, offset=offset, status=estado)
    total = await db.contar_leads(status=estado)
    
    return {
        "count": len(leads),
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(leads) < total,
        "data": leads
    }


@app.patch(
    "/api/v1/leads/{lead_id}/estado",
    tags=["Leads"],
    summary="Actualizar estado de lead",
    description="Actualiza el estado de un lead específico."
)
@limiter.limit("30/minute")
async def actualizar_lead(
    request: Request,
    lead_id: int,
    nuevo_estado: str
):
    """
    Actualiza el estado de un lead.
    
    - **lead_id**: ID del lead
    - **nuevo_estado**: Nuevo estado (caliente, tibio, frío, contactado, cerrado)
    """
    estados_validos = {"caliente", "tibio", "frío", "contactado", "cerrado"}
    if nuevo_estado not in estados_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Valores permitidos: {estados_validos}"
        )
    
    db = get_database_service()
    await db.actualizar_estado_lead(lead_id, nuevo_estado)
    
    return {"message": f"Lead {lead_id} actualizado a '{nuevo_estado}'"}


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
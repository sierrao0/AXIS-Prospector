"""
Servicio de base de datos con Supabase.

Optimizaciones:
- Operaciones async
- Retry con backoff exponencial
- Batch inserts optimizados
- Mejor manejo de errores
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import List, Dict, Any, Optional

from supabase import create_client, Client
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from config import get_settings
from services.exceptions import (
    DatabaseError,
    SupabaseConnectionError,
    LeadNotFoundError,
)

logger = logging.getLogger(__name__)

# ThreadPool para operaciones sync de Supabase
_db_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="supabase_worker")

# Tamaño máximo de batch para inserts
BATCH_SIZE = 50


class DatabaseService:
    """Servicio CRUD para Supabase con operaciones async."""

    def __init__(self):
        settings = get_settings()
        
        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_KEY son requeridos")

        self.client: Client = create_client(settings.supabase_url, settings.supabase_key)
        self._is_initialized = True
        logger.info("✅ Conexión a Supabase establecida")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _insert_batch_sync(self, leads: List[Dict[str, Any]]) -> int:
        """Inserta un batch de leads de forma síncrona."""
        try:
            response = self.client.table("leads").insert(leads).execute()
            return len(response.data) if response.data else 0
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "network" in error_msg:
                raise SupabaseConnectionError(f"Error de conexión: {e}")
            raise DatabaseError(f"Error insertando leads: {e}")

    async def guardar_leads(self, leads: List[Dict[str, Any]]) -> int:
        """
        Guarda leads en la tabla 'leads' de forma async con batching.
        
        Args:
            leads: Lista de diccionarios con datos de leads
            
        Returns:
            Número de leads guardados
        """
        if not leads:
            logger.warning("⚠️ No hay leads para guardar")
            return 0

        loop = asyncio.get_event_loop()
        total_guardados = 0
        
        # Procesar en batches para evitar timeouts
        for i in range(0, len(leads), BATCH_SIZE):
            batch = leads[i:i + BATCH_SIZE]
            try:
                count = await loop.run_in_executor(
                    _db_executor,
                    partial(self._insert_batch_sync, batch)
                )
                total_guardados += count
                logger.debug(f"Batch {i//BATCH_SIZE + 1}: {count} leads guardados")
            except (SupabaseConnectionError, DatabaseError):
                raise
            except Exception as e:
                logger.error(f"❌ Error en batch {i//BATCH_SIZE + 1}: {e}")
                raise DatabaseError(f"Error guardando batch: {e}")

        logger.info(f"✅ {total_guardados} leads guardados en Supabase")
        return total_guardados

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _select_leads_sync(
        self,
        limit: int,
        offset: int,
        status: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Obtiene leads de forma síncrona."""
        try:
            query = self.client.table("leads").select("*")

            if status:
                query = query.eq("status", status)

            response = query.range(offset, offset + limit - 1).execute()
            return response.data or []
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg:
                raise SupabaseConnectionError(f"Error de conexión: {e}")
            raise DatabaseError(f"Error obteniendo leads: {e}")

    async def obtener_leads(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene leads de la base de datos de forma async.
        
        Args:
            limit: Número máximo de resultados
            offset: Desplazamiento para paginación
            status: Filtrar por estado (opcional)
            
        Returns:
            Lista de leads
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _db_executor,
                partial(self._select_leads_sync, limit, offset, status)
            )
        except (SupabaseConnectionError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"❌ Error obteniendo leads: {e}")
            raise DatabaseError(f"Error inesperado: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def _update_lead_sync(self, lead_id: int, nuevo_status: str) -> bool:
        """Actualiza un lead de forma síncrona."""
        try:
            response = self.client.table("leads").update(
                {"status": nuevo_status}
            ).eq("id", lead_id).execute()
            
            if not response.data:
                raise LeadNotFoundError(f"Lead {lead_id} no encontrado")
            return True
        except LeadNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Error actualizando lead: {e}")

    async def actualizar_estado_lead(self, lead_id: int, nuevo_status: str) -> bool:
        """
        Actualiza el estado de un lead de forma async.
        
        Args:
            lead_id: ID del lead
            nuevo_status: Nuevo estado
            
        Returns:
            True si se actualizó correctamente
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                _db_executor,
                partial(self._update_lead_sync, lead_id, nuevo_status)
            )
            logger.info(f"✅ Lead {lead_id} actualizado a '{nuevo_status}'")
            return result
        except (LeadNotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"❌ Error actualizando lead {lead_id}: {e}")
            raise DatabaseError(f"Error inesperado: {e}")

    async def contar_leads(self, status: Optional[str] = None) -> int:
        """Cuenta el total de leads (opcionalmente filtrado por status)."""
        loop = asyncio.get_event_loop()
        
        def _count_sync() -> int:
            query = self.client.table("leads").select("id", count="exact")
            if status:
                query = query.eq("status", status)
            response = query.execute()
            return response.count or 0
        
        return await loop.run_in_executor(_db_executor, _count_sync)


# Instancia singleton del servicio (lazy initialization)
_db_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Factory para obtener el servicio de base de datos."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service


async def cleanup_database() -> None:
    """Limpia recursos de la base de datos (llamar en shutdown)."""
    _db_executor.shutdown(wait=False)

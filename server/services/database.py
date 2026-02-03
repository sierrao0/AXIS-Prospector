"""
Servicio de base de datos con Supabase.

Optimizaciones:
- Operaciones async
- Retry con backoff exponencial
- Batch inserts optimizados
- Mejor manejo de errores
- Soporte para campos de Deep Audit (Phase 1)
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import List, Dict, Any, Optional, Union, Set
from datetime import datetime

from supabase import create_client, Client, ClientOptions
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from config import get_settings
from schemas import AuditStatus
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

        self.client: Client = create_client(
            settings.supabase_url, 
            settings.supabase_key,
            options=ClientOptions(
                persist_session=False,
                auto_refresh_token=False
            )
        )
        self._is_initialized = True
        logger.info("✅ Conexión a Supabase establecida")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _insert_batch_sync(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Inserta un batch de leads de forma síncrona con filtro de duplicados."""
        try:
            # 1. Filtrar duplicados antes de insertar (Best Practice)
            leads_to_insert = self._filter_duplicates(leads)
            
            if not leads_to_insert:
                logger.info("ℹ️ Todos los leads del batch ya existen o están duplicados.")
                return []
            
            # 2. Insertar solo los nuevos
            # Usamos upsert con ignore_duplicates=True como fallback si existe constraint en DB
            response = self.client.table("leads").upsert(
                leads_to_insert, 
                on_conflict="website",  # Asumiendo que website es unique key principal
                ignore_duplicates=True
            ).execute()
            
            logger.info(f"✅ Insertados {len(response.data) if response.data else 0} leads nuevos")
            return response.data or []
            
        except OSError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "network" in error_msg:
                raise SupabaseConnectionError(f"Error de conexión: {e}")
            raise DatabaseError(f"Error insertando leads: {e}")

    def _filter_duplicates(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra leads que ya existen en la base de datos verificando websites.
        Implementa estrategia de 'Check-Then-Act' para minimizar errores de constraint.
        """
        if not leads:
            return []

        # Extraer websites válidos para verificación
        websites_to_check = {l.get("website") for l in leads if l.get("website")}
        
        if not websites_to_check:
            # Si no hay websites, pasamos todos (o podríamos filtrar por teléfono si implementado)
            return leads

        existing_websites: Set[str] = set()
        
        try:
            # Consultar leads existentes con esos websites
            # Supabase permite filtrar por lista usando 'in_'
            response = self.client.table("leads") \
                .select("website") \
                .in_("website", list(websites_to_check)) \
                .execute()
                
            for row in response.data:
                if row.get("website"):
                    existing_websites.add(row["website"])
                    
        except Exception as e:
            logger.warning(f"⚠️ Error consultando duplicados (continuando con insert): {e}")
            # En caso de error de lectura, intentamos insertar todos confiando en la DB

        # Filtrar lista original
        unique_leads = []
        for lead in leads:
            website = lead.get("website")
            if website and website in existing_websites:
                logger.debug(f"🔁 Lead ignorado (ya existe): {website}")
                continue
            unique_leads.append(lead)
            
        return unique_leads

    async def guardar_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Guarda leads en la tabla 'leads' de forma async con batching.
        
        Args:
            leads: Lista de diccionarios con datos de leads
            
        Returns:
            Lista de leads guardados con sus IDs
        """
        if not leads:
            logger.warning("⚠️ No hay leads para guardar")
            return []

        loop = asyncio.get_event_loop()
        leads_guardados = []
        
        # Procesar en batches para evitar timeouts
        for i in range(0, len(leads), BATCH_SIZE):
            batch = leads[i:i + BATCH_SIZE]
            try:
                saved_batch = await loop.run_in_executor(
                    _db_executor,
                    partial(self._insert_batch_sync, batch)
                )
                leads_guardados.extend(saved_batch)
                logger.debug(f"Batch {i//BATCH_SIZE + 1}: {len(saved_batch)} leads guardados")
            except (SupabaseConnectionError, DatabaseError):
                raise
            except Exception as e:
                logger.error(f"❌ Error en batch {i//BATCH_SIZE + 1}: {e}")
                raise DatabaseError(f"Error guardando batch: {e}")

        logger.info(f"✅ {len(leads_guardados)} leads guardados en Supabase")
        return leads_guardados

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
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )

    def _update_lead_sync(self, lead_id: Union[int, str], nuevo_status: str) -> bool:
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
        except OSError:
            raise
        except Exception as e:
            raise DatabaseError(f"Error actualizando lead: {e}")

    async def actualizar_estado_lead(self, lead_id: Union[int, str], nuevo_status: str) -> bool:

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

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    def _update_audit_sync(self, lead_id: Union[int, str], audit_data: Dict[str, Any]) -> bool:
        """Actualiza los datos de auditoría de un lead."""
        try:
            response = self.client.table("leads").update(audit_data).eq("id", lead_id).execute()
            if not response.data:
                raise LeadNotFoundError(f"Lead {lead_id} no encontrado para audit update")
            return True
        except LeadNotFoundError:
            raise
        except OSError:
            # Re-raise OSError para que @retry lo capture (incluye Errno 35)
            raise
        except Exception as e:
            raise DatabaseError(f"Error actualizando audit lead: {e}")

    async def actualizar_audit_lead(self, lead_id: Union[int, str], audit_data: Dict[str, Any]) -> bool:
        """
        Actualiza los resultados del audit en la base de datos.
        
        Args:
            lead_id: ID del lead
            audit_data: Diccionario con campos de audit (score, emails, stats, etc)
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _db_executor,
                partial(self._update_audit_sync, lead_id, audit_data)
            )
        except Exception as e:
            logger.error(f"❌ Error guardando audit para lead {lead_id}: {e}")
            raise DatabaseError(f"Error guardando audit: {e}")

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

    # -------------------------------------------------------------------------
    # DEEP AUDIT METHODS (Phase 1)
    # -------------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def _update_audit_status_sync(self, lead_id: Union[int, str], audit_status: str) -> bool:
        """Actualiza el estado de auditoría de un lead."""
        try:
            response = self.client.table("leads").update(
                {"audit_status": audit_status}
            ).eq("id", lead_id).execute()
            
            if not response.data:
                raise LeadNotFoundError(f"Lead {lead_id} no encontrado")
            return True
        except LeadNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Error actualizando audit_status: {e}")

    async def actualizar_audit_status(self, lead_id: Union[int, str], audit_status: AuditStatus) -> bool:
        """
        Actualiza el estado de auditoría de un lead.
        
        Args:
            lead_id: ID del lead
            audit_status: Nuevo estado de auditoría (pending, auditing, completed, failed)
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _db_executor,
                partial(self._update_audit_status_sync, lead_id, audit_status.value)
            )
        except (LeadNotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"❌ Error actualizando audit_status para lead {lead_id}: {e}")
            raise DatabaseError(f"Error inesperado: {e}")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    def _update_lead_audit_sync(self, lead_id: Union[int, str], audit_data: Dict[str, Any]) -> bool:
        """Actualiza un lead con los datos de auditoría completos."""
        try:
            update_payload = {
                "audit_status": audit_data.get("audit_status", AuditStatus.COMPLETED.value),
                "ai_score": audit_data.get("ai_score", 0),
                "audit_data": audit_data.get("audit_data"),
                "ssl_valid": audit_data.get("ssl_valid"),
                "emails": audit_data.get("emails", []),
                "tech_stack": audit_data.get("tech_stack", []),
                "social_links": audit_data.get("social_links", {}),
                "audit_completed_at": audit_data.get("audit_completed_at", datetime.utcnow().isoformat()),
                # Legacy fields
                "web_obsoleta": audit_data.get("web_obsoleta"),
                "web_analisis_motivo": audit_data.get("web_analisis_motivo"),
            }
            
            # Also update status if lead is promoted to "caliente"
            if audit_data.get("status"):
                update_payload["status"] = audit_data["status"]
            
            response = self.client.table("leads").update(
                update_payload
            ).eq("id", lead_id).execute()
            
            if not response.data:
                raise LeadNotFoundError(f"Lead {lead_id} no encontrado")
            return True
        except LeadNotFoundError:
            raise
        except OSError:
            raise
        except Exception as e:
            raise DatabaseError(f"Error actualizando audit para lead: {e}")

    async def guardar_audit_result(self, lead_id: Union[int, str], audit_data: Dict[str, Any]) -> bool:
        """
        Guarda el resultado de la auditoría profunda para un lead.
        
        Args:
            lead_id: ID del lead
            audit_data: Diccionario con todos los campos de auditoría
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                _db_executor,
                partial(self._update_lead_audit_sync, lead_id, audit_data)
            )
            logger.debug(f"✅ Audit guardado para lead {lead_id} (score: {audit_data.get('ai_score')})")
            return result
        except (LeadNotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"❌ Error guardando audit para lead {lead_id}: {e}")
            raise DatabaseError(f"Error inesperado: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    def _batch_update_audits_sync(self, updates: List[Dict[str, Any]]) -> int:
        """Actualiza múltiples leads con datos de auditoría en batch."""
        updated = 0
        for update in updates:
            try:
                lead_id = update.pop("id")
                response = self.client.table("leads").update(update).eq("id", lead_id).execute()
                if response.data:
                    updated += 1
            except Exception as e:
                logger.warning(f"Error updating lead {update.get('id')}: {e}")
        return updated

    async def guardar_audits_batch(self, audits: List[Dict[str, Any]]) -> int:
        """
        Guarda resultados de auditoría para múltiples leads.
        
        Args:
            audits: Lista de diccionarios con id y campos de audit
            
        Returns:
            Número de leads actualizados
        """
        if not audits:
            return 0
        
        loop = asyncio.get_event_loop()
        try:
            count = await loop.run_in_executor(
                _db_executor,
                partial(self._batch_update_audits_sync, audits)
            )
            logger.info(f"✅ {count}/{len(audits)} audits guardados en batch")
            return count
        except Exception as e:
            logger.error(f"❌ Error en batch update de audits: {e}")
            raise DatabaseError(f"Error guardando audits en batch: {e}")

    async def obtener_leads_pending_audit(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene leads que aún no han sido auditados.
        
        Args:
            limit: Número máximo de leads a obtener
        """
        loop = asyncio.get_event_loop()
        
        def _fetch_sync() -> List[Dict[str, Any]]:
            response = self.client.table("leads").select("*").eq(
                "audit_status", AuditStatus.PENDING.value
            ).limit(limit).execute()
            return response.data or []
        
        return await loop.run_in_executor(_db_executor, _fetch_sync)


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

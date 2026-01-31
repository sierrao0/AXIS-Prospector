"""
Esquemas Pydantic V2 para validación de entrada/salida.

Optimizaciones:
- Validaciones más estrictas
- Campos adicionales para mejor tracking
- Documentación mejorada
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import re


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
    web_obsoleta: Optional[bool] = Field(None, description="True si el sitio web es obsoleto")
    web_analisis_motivo: Optional[str] = Field(None, description="Razón del diagnóstico web")
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

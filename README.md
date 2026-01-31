# 🕵️‍♂️ BusinesScraper: The Hunter Module

<div align="center">

![AXIS](https://img.shields.io/badge/AXIS-Prospector-blueviolet?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python)
![Next.js](https://img.shields.io/badge/Next.js-16-black?style=for-the-badge&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?style=for-the-badge&logo=fastapi)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ecf8e?style=for-the-badge&logo=supabase)

**Prospección B2B automatizada con IA**

[Inicio Rápido](#-inicio-rápido) • [Arquitectura](#-arquitectura) • [Stack](#-stack-tecnológico) • [API](#-api-endpoints) • [Roadmap](#-roadmap)

</div>

---

## 🎯 Misión

**BusinesScraper** es el núcleo de prospección inteligente de **AXIS Agency**. No es un simple scraper; es un **motor de inferencia asíncrono** diseñado para descubrir, calificar y auditar prospectos B2B en tiempo real.

> *"Encontrar el 20% de clientes que generan el 80% del valor."*

Este módulo automatiza el ciclo de vida inicial del lead:
1. **Extracción geográfica** desde Google Maps
2. **Auditoría técnica** de presencia web
3. **Clasificación inteligente** de leads por potencial

---

## 🧠 Funcionalidades Principales

| Feature | Descripción |
|---------|-------------|
| 🗺️ **Deep Extraction** | Ingesta masiva de datos desde Google Maps via Apify con filtrado inteligente |
| 🔍 **Web Audit** | Análisis de sitios web con Playwright para detectar webs obsoletas o ausencia digital |
| 📊 **Lead Scoring** | Clasificación automática en caliente/tibio/frío según potencial comercial |
| ⚡ **Async Pipeline** | Arquitectura no bloqueante con FastAPI + BackgroundTasks |
| 🔴 **Real-time Sync** | Streaming de datos hacia Supabase con actualización inmediata en el frontend |
| 🛡️ **Rate Limiting** | Protección de endpoints con SlowAPI |

---

## 🏗️ Arquitectura

```
BusinesScraper/
├── client/                 # Frontend Next.js 16
│   ├── src/
│   │   ├── app/           # App Router (pages)
│   │   │   ├── dashboard/ # Panel de control principal
│   │   │   └── page.tsx   # Landing page
│   │   ├── components/    # Componentes React
│   │   │   ├── LeadsTable.tsx       # Tabla de leads con badges
│   │   │   ├── ProspectorForm.tsx   # Formulario de prospección
│   │   │   └── ui/                  # shadcn/ui components
│   │   ├── hooks/         # Custom hooks (useLeads, useProspector)
│   │   └── lib/           # Utilidades (Supabase client, API)
│   └── package.json
│
├── server/                 # Backend Python FastAPI
│   ├── main.py            # Punto de entrada API
│   ├── config.py          # Configuración y variables de entorno
│   ├── schemas.py         # Modelos Pydantic
│   └── services/
│       ├── scraper.py     # Extracción de leads (Apify)
│       ├── analyzer.py    # Auditoría web (Playwright)
│       ├── database.py    # Persistencia (Supabase)
│       └── exceptions.py  # Jerarquía de errores personalizada
│
├── docker/                 # Dockerfiles para server y client
├── shared/                 # Tipos y contratos compartidos
└── docker-compose.yml      # Orquestación de servicios
```

---

## 🛠️ Stack Tecnológico

### Backend (Python)

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Python** | 3.12+ | Lenguaje principal |
| **FastAPI** | 0.109+ | Framework web asíncrono |
| **Pydantic** | 2.5+ | Validación de datos |
| **Playwright** | 1.40+ | Automatización web headless |
| **Apify Client** | 1.6+ | Extracción de Google Maps |
| **Supabase** | 2.3+ | Cliente PostgreSQL + Realtime |
| **Tenacity** | 8.2+ | Retry con backoff exponencial |
| **SlowAPI** | 0.1.9+ | Rate limiting |
| **Uvicorn** | 0.27+ | ASGI server |

### Frontend (TypeScript)

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Next.js** | 16.1 | Framework React fullstack |
| **React** | 19.2 | UI Library |
| **TypeScript** | 5+ | Type safety |
| **TailwindCSS** | 4+ | Styling utility-first |
| **TanStack Query** | 5.90+ | Server state management |
| **Supabase JS** | 2.93+ | Cliente Supabase + Realtime |
| **shadcn/ui** | Latest | Componentes UI (Radix) |
| **Framer Motion** | 12+ | Animaciones |
| **Sonner** | 2+ | Toast notifications |
| **Lucide React** | 0.563+ | Iconografía |

### Infraestructura

| Tecnología | Propósito |
|------------|-----------|
| **Docker** | Containerización |
| **Docker Compose** | Orquestación local |
| **Supabase** | Base de datos PostgreSQL + Auth + Realtime |
| **pnpm** | Package manager (frontend) |

---

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.12+
- Node.js 20+
- pnpm
- Docker (opcional)
- Cuenta en Supabase
- Token de Apify

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/BusinesScraper.git
cd BusinesScraper
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:

```env
# Apify
APIFY_TOKEN=tu_token_apify

# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu_anon_key
SUPABASE_PASSWORD=tu_password

# App Config
DEBUG=false
LOG_LEVEL=INFO

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://tu-proyecto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=tu_anon_key
```

### 3. Opción A: Docker Compose (Recomendado)

```bash
docker-compose up -d
```

Servicios disponibles:
- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### 3. Opción B: Desarrollo Local

**Backend:**
```bash
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd client
pnpm install
pnpm dev
```

---

## 📡 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Health check del servidor |
| `POST` | `/api/v1/prospectar` | Inicia una nueva tarea de prospección |
| `GET` | `/api/v1/tasks/{task_id}` | Estado de una tarea en ejecución |
| `GET` | `/api/v1/leads` | Lista de todos los leads |
| `GET` | `/api/v1/leads/{id}` | Detalle de un lead específico |

### Ejemplo: Iniciar Prospección

```bash
curl -X POST http://localhost:8000/api/v1/prospectar \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Restaurantes en Medellín",
    "max_results": 20
  }'
```

**Respuesta:**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "message": "Prospección iniciada"
}
```

---

## 📊 Modelo de Datos

### Lead

```typescript
interface Lead {
  id: string;
  nombre: string;
  direccion: string | null;
  telefono: string | null;
  website: string | null;
  rating: number | null;
  reviews_count: number | null;
  categoria: string | null;
  status: 'caliente' | 'tibio' | 'frío' | 'contactado' | 'cerrado';
  web_obsoleta: boolean;
  created_at: string;
  updated_at: string;
}
```

---

## 🗺️ Roadmap

- [x] **Phase 1:** Extracción básica de Google Maps
- [x] **Phase 2:** Auditoría web con Playwright
- [x] **Phase 3:** Dashboard realtime con Supabase
- [ ] **Phase 4:** AI Scoring con Gemini/GPT
- [ ] **Phase 5:** Integración CRM (HubSpot/Pipedrive)
- [ ] **Phase 6:** Campañas de outreach automatizadas

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea tu feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add: AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📄 Licencia

Este proyecto es privado y pertenece a **AXIS Agency**.

---

<div align="center">

**AXIS Prospector** — *Transforming raw data into actionable business intelligence.*

Built with ❤️ by the AXIS Team

</div>

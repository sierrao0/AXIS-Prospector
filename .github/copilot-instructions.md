# BusinesScraper - Copilot Instructions

## Architecture Overview

BusinesScraper is an async B2B lead prospecting system for AXIS Agency. Two-tier architecture:
- **Frontend** (`client/`): Next.js 16 + React 19 dashboard with Supabase Realtime
- **Backend** (`server/`): FastAPI async API with background task processing

**Data Flow:**
```
User submits query → POST /api/v1/prospectar → BackgroundTask spawns →
Apify extracts from Google Maps → Playwright audits websites →
AI score calculated → Upserted to Supabase → Frontend receives via Realtime
```

## Critical Patterns

### Async Wrapping for Sync Libraries
Apify and Supabase clients are synchronous. Wrap using `ThreadPoolExecutor`:
```python
# server/services/scraper.py pattern
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(_executor, partial(self._sync_method, args))
```

### Singleton Services
Services use lazy-initialized global singletons with cleanup on shutdown:
```python
_service: Optional[ServiceClass] = None
def get_service() -> ServiceClass:
    global _service
    if _service is None:
        _service = ServiceClass()
    return _service
```

### Playwright Browser Pool
Single browser instance + context pool (see [analyzer.py](server/services/analyzer.py)):
- `CONTEXT_SEMAPHORE = asyncio.Semaphore(8)` controls concurrency
- Each audit gets a new context (~50MB) not a new browser (~300MB)
- Uses `playwright-stealth` for bot evasion

### Type Mirroring
TypeScript types in `client/src/lib/supabase.ts` mirror Pydantic models in `server/schemas.py`. Keep synchronized when modifying `Lead`, `AuditResult`, etc.

## Development Commands

```bash
# Backend (from /server)
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
python -m playwright install chromium
python main.py                    # or: uvicorn main:app --reload --port 8000

# Frontend (from /client)
pnpm install
pnpm dev                          # Requires backend on :8000

# Full stack (from root)
docker-compose up -d
```

## Environment Variables

Root `.env` file (copy from `.env.example`):
- `APIFY_TOKEN` - Apify API token for Google Maps extraction
- `SUPABASE_URL`, `SUPABASE_KEY` - Supabase connection
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Frontend Supabase
- `NEXT_PUBLIC_API_URL` - Backend URL (default: `http://localhost:8000/api/v1`)

## Code Conventions

### Language
- **Spanish** for comments, logs, variable names: `prospectar`, `guardar_leads`, `caliente`/`tibio`/`frío`
- **Emoji prefixes** in logs: 🔍 search, ✅ success, ❌ error, 📋 task, 📡 realtime

### Backend (Python)
- Pydantic V2: Use `field_validator`, `computed_field`, `model_config` dict
- Custom exceptions inherit from `AXISProspectorError` ([exceptions.py](server/services/exceptions.py))
- Retry with tenacity: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))`
- Rate limiting via `@limiter.limit()` decorator on endpoints

### Frontend (TypeScript)
- shadcn/ui components in `components/ui/` — add via CLI, don't edit directly
- Use `cn()` helper for Tailwind class merging
- TanStack Query for data fetching; `refetchInterval` for polling async tasks
- Supabase Realtime for live lead updates (see [useLeads.ts](client/src/hooks/useLeads.ts))

## Key Files

| File | Purpose |
|------|---------|
| [server/main.py](server/main.py) | FastAPI app, endpoints, lifespan, exception handlers |
| [server/services/scraper.py](server/services/scraper.py) | Apify integration, lead filtering (80/20 rule) |
| [server/services/analyzer.py](server/services/analyzer.py) | Playwright deep audit, tech detection, AI scoring |
| [server/schemas.py](server/schemas.py) | Pydantic models, enums, `calculate_ai_score()` |
| [client/src/hooks/useLeads.ts](client/src/hooks/useLeads.ts) | Realtime subscription pattern |
| [client/src/lib/api.ts](client/src/lib/api.ts) | Axios instance, base URL config |

## Database Schema

Supabase `leads` table:
- Core: `id`, `name`, `website`, `phone`, `location`, `category`
- Scoring: `rating`, `reviews_count`, `ai_score`, `status`
- Audit: `audit_data` (JSONB), `audit_status`, `web_obsoleta`
- Lead statuses: `caliente` (hot), `tibio` (warm), `frío` (cold), `contactado`, `cerrado`

## Current Gaps (Phase 1)

See [PHASE1_IMPLEMENTATION_PLAN.md](PHASE1_IMPLEMENTATION_PLAN.md) for full status. Key remaining:
- Deep Audit integration into background pipeline
- `ai_score` column and calculation in DB
- Lead Detail Sheet component
- RLS policies for production security

# Prospector By Sierra API - Copilot Instructions

## Architecture Overview

This is an async FastAPI application for lead prospecting from Google Maps, storing results in Supabase.

**Data Flow:** `POST /api/v1/prospectar` → Background Task → Apify (Google Maps scraper) → Filter leads → Supabase

**Key Components:**
- `main.py` (root) - FastAPI app with endpoints, rate limiting (slowapi), and background tasks
- `Backend/services/scraper.py` - Apify integration via ThreadPoolExecutor for async wrapping
- `Backend/services/database.py` - Supabase CRUD with batch operations
- `Backend/services/exceptions.py` - Custom exception hierarchy rooted at `SierraProspectorError`

## Critical Patterns

### Async Wrapping for Sync Libraries
Both Apify and Supabase clients are synchronous. This project wraps them using `ThreadPoolExecutor`:
```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(_executor, partial(self._sync_method, args))
```
Follow this pattern when adding new external service integrations.

### Singleton Services with Lazy Init
Services use factory functions with global singletons:
```python
_service: Optional[ServiceClass] = None
def get_service() -> ServiceClass:
    global _service
    if _service is None:
        _service = ServiceClass()
    return _service
```

### Lead Filtering (80/20 Rule)
Leads are filtered to prioritize businesses without websites or using only social media. See `SOCIAL_MEDIA_DOMAINS` in [Backend/services/scraper.py](Backend/services/scraper.py) and `_filtrar_lead()` method.

### Web Analysis (Playwright)
Leads with websites are analyzed to detect obsolete sites via [Backend/services/analyzer.py](Backend/services/analyzer.py):
- Extracts header `innerText` - if < 20 chars, marked obsolete
- Checks for SEO meta tags (`description`, `viewport`) - missing = obsolete
- Obsolete web leads are promoted to `caliente` status
- Uses async browser with semaphore for controlled concurrency

### Exception Hierarchy
All custom exceptions inherit from `SierraProspectorError`. Use specific exceptions:
- `ScraperError`, `ApifyConnectionError`, `ApifyTimeoutError` - scraping issues
- `DatabaseError`, `SupabaseConnectionError`, `LeadNotFoundError` - database issues

### Retry Logic
Use `tenacity` decorators for resilient external calls:
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
```

## Developer Workflow

```bash
# Create virtual environment and install dependencies (using uv)
uv venv && source .venv/bin/activate
uv pip install -r Backend/requirements.txt

# Install Playwright browsers (required for web analysis)
python -m playwright install chromium

# Run development server (from root)
python main.py
# Or: uvicorn main:app --reload --port 8000

# API docs available at http://localhost:8000/docs
```

### Required Environment Variables
Create `.env` in root with:
- `APIFY_TOKEN` - Apify API token
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon/service key

## Code Conventions

- **Language:** Comments, logs, and variable names in Spanish (e.g., `prospectar`, `guardar_leads`)
- **Logging:** Use emoji prefixes: 🔍 search, ✅ success, ❌ error, 📋 task, 📌 new item
- **Pydantic V2:** Use `field_validator` (not `validator`), `model_config` dict (not `Config` class)
- **Rate Limits:** Defined per endpoint with `@limiter.limit()` decorator

## Database Schema

Supabase table `leads` with columns: `id`, `name`, `website`, `phone`, `rating`, `reviews_count`, `location`, `category`, `status`, `created_at`

Lead statuses: `caliente` (hot), `tibio` (warm), `frío` (cold), `contactado`, `cerrado`

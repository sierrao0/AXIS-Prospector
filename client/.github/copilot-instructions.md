# Copilot Instructions for BusinesScraper Frontend

## Project Overview
Dashboard para agencia de IA/Automatización que captura y gestiona leads de negocios. Estética tipo Vercel/Linear/OpenAI: limpia, dark mode por defecto, bordes finos.

**Stack Core:**
- Next.js 16 (App Router) + React 19 + TypeScript (no negociable — mirrors Pydantic del backend)
- FastAPI backend con BackgroundTasks para scraping asíncrono
- Supabase para auth + Realtime (leads aparecen en vivo sin refresh)
- TanStack Query para caché, loading states y polling de tareas async

## Tech Stack & Key Dependencies
- **Framework**: Next.js 16 with App Router (`src/app/`)
- **UI Components**: shadcn/ui (new-york style) — estética premium con mínimo esfuerzo
- **Styling**: Tailwind CSS v4 con CSS variables (dark mode by default)
- **State**: TanStack Query (`@tanstack/react-query`) — polling para BackgroundTasks
- **Realtime**: Supabase Realtime Subscriptions — leads en vivo
- **Auth**: Supabase (`@supabase/supabase-js`)
- **HTTP**: Axios para FastAPI (base URL: `NEXT_PUBLIC_API_URL`)
- **Animations**: Framer Motion
- **Icons**: Lucide React

## Project Structure
```
src/
├── app/              # Rutas (Dashboard, Login, etc.)
├── components/
│   ├── ui/           # Componentes shadcn/ui (NO modificar directamente)
│   └── shared/       # Componentes propios (Navbar, Sidebar, etc.)
├── hooks/            # Custom hooks (ej: useLeads, useAuth)
├── lib/              # Config (Supabase client, api.ts, utils.ts)
├── services/         # Llamadas a la API FastAPI (leads.service.ts, etc.)
└── types/            # Interfaces TypeScript (mirrors de Pydantic)
```

## Development Commands
```bash
pnpm dev    # Start dev server (localhost:3000) — requires FastAPI on :8000
pnpm build  # Production build
pnpm lint   # Run ESLint
```

## Conventions & Patterns

### Styling
- Use the `cn()` helper from `@/lib/utils` to merge Tailwind classes: `cn("base-class", conditional && "conditional-class", className)`
- Theme colors use CSS variables defined in `globals.css` (e.g., `bg-primary`, `text-muted-foreground`)
- Dark mode: use `.dark` variant with `@custom-variant dark (&:is(.dark *))`
- Border radius uses `--radius` variable: `rounded-lg`, `rounded-md`, `rounded-sm`

### Components
- shadcn/ui components live in `components/ui/` — add via CLI, don't edit directly
- Custom reusable components go in `components/shared/`
- Use `cva` (class-variance-authority) for component variants (see [button.tsx](src/components/ui/button.tsx))
- Prefer function component syntax: `function ComponentName({ ...props }: Props) {}`

### Services & API
- Axios instance configured in `lib/api.ts` with base URL from `NEXT_PUBLIC_API_URL`
- Create service files in `services/` for each domain (e.g., `leads.service.ts`)
- Types mirror Pydantic models from FastAPI — keep in `types/` (e.g., `types/lead.ts`)

```typescript
// Example: services/leads.service.ts
import { api } from '@/lib/api';
import type { Lead } from '@/types/lead';

export const getLeads = () => api.get<Lead[]>('/leads');
```

### Hooks
- Custom hooks in `hooks/` wrap React Query + services
- Naming: `use[Resource]` (e.g., `useLeads`, `useAuth`)
- Para tareas async del backend, usa `refetchInterval` para polling:

```typescript
// Example: hooks/useLeads.ts
import { useQuery } from '@tanstack/react-query';
import { getLeads } from '@/services/leads.service';

export const useLeads = () => useQuery({ queryKey: ['leads'], queryFn: getLeads });

// Para polling mientras scraping está en progreso:
export const useScrapeJob = (jobId: string) => useQuery({
  queryKey: ['scrape-job', jobId],
  queryFn: () => getScrapeJob(jobId),
  refetchInterval: (query) => query.state.data?.status === 'completed' ? false : 3000,
});
```

### Realtime (Supabase)
- Usa Supabase Realtime para que leads aparezcan sin refresh
- Combina con React Query para invalidar caché al recibir eventos

```typescript
// Example: hooks/useRealtimeLeads.ts
useEffect(() => {
  const channel = supabase.channel('leads').on('postgres_changes', 
    { event: 'INSERT', schema: 'public', table: 'leads' },
    () => queryClient.invalidateQueries({ queryKey: ['leads'] })
  ).subscribe();
  return () => { supabase.removeChannel(channel); };
}, []);
```

### Path Aliases
- `@/*` maps to `./src/*` — always use `@/components/ui`, `@/lib/utils`, etc.

### Adding UI Components
Use the shadcn CLI to add new components:
```bash
pnpm dlx shadcn@latest add [component-name]
```

## Integration Points
- **FastAPI Backend**: `http://localhost:8000/api/v1` (configure via `NEXT_PUBLIC_API_URL`)
- **Supabase**: Auth client in `lib/supabase.ts`
- **React Query**: Wrap app with `QueryClientProvider`; use `useQuery`/`useMutation` hooks
- **Toast notifications**: Use `sonner` via the Toaster component

## File Naming
- React components: PascalCase (`Button.tsx`, `LeadCard.tsx`)
- Services: kebab-case with `.service.ts` suffix (`leads.service.ts`)
- Hooks: camelCase with `use` prefix (`useLeads.ts`)
- Types: kebab-case (`lead.ts`, `scrape-job.ts`)
- Pages: lowercase with Next.js conventions (`page.tsx`, `layout.tsx`)

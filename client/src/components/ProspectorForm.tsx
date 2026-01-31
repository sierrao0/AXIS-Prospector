'use client';

import { useState, FormEvent } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { useProspector } from '@/hooks/useProspector';
import { toast } from 'sonner';

interface ProspectorFormProps {
  onTaskStarted?: (taskId: string) => void;
}

/**
 * Formulario de prospección para buscar leads.
 * 
 * Dispara el POST /prospectar del backend FastAPI.
 */
export function ProspectorForm({ onTaskStarted }: ProspectorFormProps) {
  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(20);
  const { prospect, isLoading } = useProspector();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      toast.error('Ingresa un término de búsqueda');
      return;
    }

    try {
      const response = await prospect(query, maxResults);
      toast.success(`🚀 Prospección iniciada: ${response.task_id}`);
      onTaskStarted?.(response.task_id);
      setQuery('');
    } catch {
      toast.error('Error al iniciar la prospección');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="size-5" />
          Nueva Prospección
        </CardTitle>
        <CardDescription>
          Busca negocios en Google Maps para generar leads calificados
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="query" className="text-sm font-medium">
              Búsqueda
            </label>
            <Input
              id="query"
              placeholder="Ej: Restaurantes en Medellín"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="maxResults" className="text-sm font-medium">
              Máximo de resultados
            </label>
            <Input
              id="maxResults"
              type="number"
              min={1}
              max={100}
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              disabled={isLoading}
            />
          </div>

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Buscando...
              </>
            ) : (
              <>
                <Search className="size-4" />
                Iniciar Prospección
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

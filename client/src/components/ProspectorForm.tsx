'use client';

import { useState, FormEvent, useEffect } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
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
  const { prospect, isLoading, activeTaskId, getTaskStatus } = useProspector();
  const [progress, setProgress] = useState(0);

  // Polling interno para la barra de progreso
  useEffect(() => {
    if (!activeTaskId) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const status = await getTaskStatus(activeTaskId);
        if (status.status === 'running') {
          setProgress(status.progress || 0);
        } else if (status.status === 'completed') {
          setProgress(100);
          clearInterval(interval);
        }
      } catch {
        // Ignorar errores de sondeo en UI
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [activeTaskId, getTaskStatus]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      toast.error('Ingresa un término de búsqueda');
      return;
    }

    try {
      const response = await prospect(query, maxResults);
      toast.success(`🚀 Prospección iniciada`);
      onTaskStarted?.(response.task_id);
      setQuery('');
      setProgress(0); 
    } catch {
      toast.error('Error al iniciar la prospección');
    }
  };

  return (
    <Card className="border-border bg-card shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-foreground">
          <Search className="size-5 text-muted-foreground" />
          Nueva Prospección
        </CardTitle>
        <CardDescription>
          Busca negocios en Google Maps para generar leads calificados
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="query" className="text-sm font-medium text-foreground">
              Búsqueda
            </label>
            <Input
              id="query"
              placeholder="Ej: Restaurantes en Medellín"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isLoading}
              className="bg-background"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="maxResults" className="text-sm font-medium text-foreground">
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
              className="bg-background"
            />
          </div>

          <Button 
            type="submit" 
            disabled={isLoading} 
            className="w-full font-medium"
          >
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

          {/* Barra de Progreso Liquid Glass */}
          {(isLoading || (activeTaskId && progress < 100)) && (
            <div className="mt-2 space-y-1 animate-fade-in">
              <div className="flex justify-between text-xs font-medium text-muted-foreground">
                <span>Estado: {progress < 100 ? 'Auditando...' : 'Completado'}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Wifi, WifiOff, Users } from 'lucide-react';
import { Toaster } from 'sonner';
import { ProspectorForm } from '@/components/ProspectorForm';
import { LeadsTable } from '@/components/LeadsTable';
import { useLeads } from '@/hooks/useLeads';
import { useProspector } from '@/hooks/useProspector';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function DashboardPage() {
  const { leads, isLoading, error, refetch, isRealtimeConnected } = useLeads();
  const { activeTaskId, getTaskStatus } = useProspector();
  const [taskProgress, setTaskProgress] = useState<string | null>(null);

  // Polling del estado de la tarea activa
  useEffect(() => {
    if (!activeTaskId) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await getTaskStatus(activeTaskId);
        
        if (status.status === 'running') {
          setTaskProgress(`Procesando... ${status.progress?.toFixed(0) || 0}%`);
        } else if (status.status === 'completed') {
          setTaskProgress(`✅ Completado: ${status.leads_count} leads`);
          clearInterval(pollInterval);
        } else if (status.status === 'failed') {
          setTaskProgress(`❌ Error: ${status.error}`);
          clearInterval(pollInterval);
        }
      } catch {
        console.error('Error polling task status');
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [activeTaskId, getTaskStatus]);



  const handleTaskStarted = (taskId: string) => {
    setTaskProgress(`Tarea ${taskId.slice(0, 8)}... iniciada`);
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <Toaster position="top-right" richColors />
      
      {/* Header */}
      <header className="border-b bg-white dark:bg-zinc-900">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold">🎯 AXIS Prospector</h1>
            <Badge variant={isRealtimeConnected ? 'default' : 'destructive'} className="gap-1">
              {isRealtimeConnected ? (
                <>
                  <Wifi className="size-3" />
                  Realtime
                </>
              ) : (
                <>
                  <WifiOff className="size-3" />
                  Conectando...
                </>
              )}
            </Badge>
          </div>

          <div className="flex items-center gap-4">
            {taskProgress && (
              <span className="text-sm text-muted-foreground">{taskProgress}</span>
            )}
            <Button variant="outline" size="sm" onClick={refetch}>
              <RefreshCw className="size-4" />
              Actualizar
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Sidebar - Formulario */}
          <div className="lg:col-span-1">
            <ProspectorForm onTaskStarted={handleTaskStarted} />
          </div>

          {/* Main - Tabla de Leads */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Users className="size-5" />
                      Leads
                    </CardTitle>
                    <CardDescription>
                      {leads.length} leads encontrados • Actualización en tiempo real
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {error ? (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
                    <p className="font-medium">Error cargando leads</p>
                    <p className="text-sm">{error}</p>
                  </div>
                ) : (
                  <LeadsTable leads={leads} isLoading={isLoading} />
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Wifi, WifiOff, Users } from 'lucide-react';
import { Toaster } from 'sonner';
import { ProspectorForm } from '@/components/ProspectorForm';
import { LeadsTable } from '@/components/LeadsTable';
import { StatsCard } from '@/components/StatsCard';
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
    <div className="min-h-screen bg-background">
      <Toaster position="top-right" richColors />
      
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground tracking-tight">
              Prospector By Sierra
            </h1>
            <Badge 
              variant={isRealtimeConnected ? 'default' : 'destructive'} 
              className={`gap-1.5 font-medium ${isRealtimeConnected ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400' : ''}`}
            >
              {isRealtimeConnected ? (
                <>
                  <Wifi className="size-3 animate-pulse" />
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
              <span className="text-sm text-muted-foreground font-medium">{taskProgress}</span>
            )}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={refetch}
              className="gap-2"
            >
              <RefreshCw className="size-4" />
              Actualizar
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Stats Overview */}
        <div className="mb-8 animate-fade-in">
          <StatsCard leads={leads} />
        </div>

        {/* Content Grid */}
        <div className="grid gap-8 lg:grid-cols-4 animate-fade-in" style={{ animationDelay: '0.1s' }}>
          {/* Sidebar - Formulario */}
          <div className="lg:col-span-1">
            <div className="sticky top-24">
              <ProspectorForm onTaskStarted={handleTaskStarted} />
            </div>
          </div>

          {/* Main - Tabla de Leads */}
          <div className="lg:col-span-3">
            <Card className="border-border bg-card shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-foreground">
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
                  <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-destructive">
                    <p className="font-medium">Error cargando leads</p>
                    <p className="text-sm opacity-80">{error}</p>
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

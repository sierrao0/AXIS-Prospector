'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase, Lead } from '@/lib/supabase';
import { RealtimePostgresChangesPayload } from '@supabase/supabase-js';

interface UseLeadsOptions {
  /** Límite de leads a cargar inicialmente */
  limit?: number;
  /** Orden de los leads */
  orderBy?: keyof Lead;
  /** Dirección del orden */
  ascending?: boolean;
}

interface UseLeadsReturn {
  leads: Lead[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  isRealtimeConnected: boolean;
}

/**
 * Hook para manejar leads con actualización en tiempo real.
 * 
 * Características:
 * - Carga inicial de leads
 * - Suscripción a cambios en tiempo real (INSERT, UPDATE, DELETE)
 * - Manejo de errores
 * - Refetch manual
 */
export function useLeads(options: UseLeadsOptions = {}): UseLeadsReturn {
  const { limit = 100, orderBy = 'created_at', ascending = false } = options;
  
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRealtimeConnected, setIsRealtimeConnected] = useState(false);

  // Cargar leads inicial
  const fetchLeads = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const { data, error: fetchError } = await supabase
        .from('leads')
        .select('*')
        .order(orderBy, { ascending })
        .limit(limit);

      if (fetchError) throw fetchError;
      setLeads(data || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error cargando leads';
      setError(message);
      console.error('Error fetching leads:', err);
    } finally {
      setIsLoading(false);
    }
  }, [limit, orderBy, ascending]);

  // Manejar cambios en tiempo real
  const handleRealtimeChange = useCallback(
    (payload: RealtimePostgresChangesPayload<Lead>) => {
      console.log('📡 Realtime event:', payload.eventType, payload);

      switch (payload.eventType) {
        case 'INSERT':
          // Agregar nuevo lead al inicio
          setLeads((prev) => [payload.new as Lead, ...prev]);
          break;

        case 'UPDATE':
          // Actualizar lead existente
          setLeads((prev) =>
            prev.map((lead) =>
              lead.id === (payload.new as Lead).id ? (payload.new as Lead) : lead
            )
          );
          break;

        case 'DELETE':
          // Remover lead eliminado
          setLeads((prev) =>
            prev.filter((lead) => lead.id !== (payload.old as Lead).id)
          );
          break;
      }
    },
    []
  );

  useEffect(() => {
    // Carga inicial
    fetchLeads();

    // Suscripción a cambios en tiempo real
    const channel = supabase
      .channel('leads-realtime')
      .on<Lead>(
        'postgres_changes',
        {
          event: '*', // INSERT, UPDATE, DELETE
          schema: 'public',
          table: 'leads',
        },
        handleRealtimeChange
      )
      .subscribe((status) => {
        console.log('📡 Realtime subscription status:', status);
        setIsRealtimeConnected(status === 'SUBSCRIBED');
      });

    // Cleanup
    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchLeads, handleRealtimeChange]);

  return {
    leads,
    isLoading,
    error,
    refetch: fetchLeads,
    isRealtimeConnected,
  };
}

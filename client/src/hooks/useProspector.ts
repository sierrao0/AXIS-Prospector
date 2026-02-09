'use client';

import { useState, useCallback } from 'react';
import { api } from '@/lib/api';

interface ProspectRequest {
  query: string;
  max_results?: number;
}

interface ProspectResponse {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message: string;
  created_at: string;
}

interface TaskStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  leads_count: number | null;
  error: string | null;
  progress: number | null;
}

interface UseProspectorReturn {
  /** Inicia una nueva prospección */
  prospect: (query: string, maxResults?: number) => Promise<ProspectResponse>;
  /** Consulta el estado de una tarea */
  getTaskStatus: (taskId: string) => Promise<TaskStatus>;
  /** ID de la tarea activa */
  activeTaskId: string | null;
  /** Estado de carga */
  isLoading: boolean;
  /** Error si existe */
  error: string | null;
}

/**
 * Hook para manejar las operaciones de prospección.
 * 
 * Uso:
 * ```tsx
 * const { prospect, isLoading } = useProspector();
 * await prospect('Restaurantes en Medellín');
 * ```
 */
export function useProspector(): UseProspectorReturn {
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const prospect = useCallback(
    async (query: string, maxResults: number = 20): Promise<ProspectResponse> => {
      setIsLoading(true);
      setError(null);

      try {
        const payload: ProspectRequest = {
          query,
          max_results: maxResults,
        };

        const { data } = await api.post<ProspectResponse>('/prospect', payload);
        setActiveTaskId(data.task_id);
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Error iniciando prospección';
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const getTaskStatus = useCallback(async (taskId: string): Promise<TaskStatus> => {
    try {
      const { data } = await api.get<TaskStatus>(`/tasks/${taskId}`);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error consultando estado';
      throw new Error(message);
    }
  }, []);

  return {
    prospect,
    getTaskStatus,
    activeTaskId,
    isLoading,
    error,
  };
}

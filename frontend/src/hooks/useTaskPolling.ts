import { useState, useEffect, useRef } from 'react';
import { api } from '../lib/apiClient';
import type { TaskStatus } from '../lib/types';

/** Polls GET /api/tasks/{id} (the generic Celery task-status endpoint every
 * async backend feature returns a task_id from) until it leaves
 * PENDING/PROGRESS. Used for both submission evaluation and standalone
 * analysis triggers. */
export function useTaskPolling<T = any>(taskId: string | null, intervalMs = 2500) {
  const [status, setStatus] = useState<TaskStatus<T> | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    setStatus(null);
    if (!taskId) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const result = await api.get<TaskStatus<T>>(`/api/tasks/${taskId}`);
        if (cancelled) return;
        setStatus(result);
        if (result.status === 'PENDING' || result.status === 'PROGRESS') {
          timerRef.current = window.setTimeout(poll, intervalMs);
        }
      } catch {
        if (!cancelled) timerRef.current = window.setTimeout(poll, intervalMs);
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [taskId, intervalMs]);

  return status;
}

import { useState, useCallback } from 'react';
import { ApiError, formatApiError } from '../lib/apiClient';

/** Replaces the alert()-only button handlers with real loading/error state
 * around an async API call, without each dashboard re-implementing the same
 * try/catch/finally boilerplate. */
export function useAsyncAction<Args extends unknown[]>(action: (...args: Args) => Promise<void>) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const run = useCallback(
    async (...args: Args) => {
      setIsLoading(true);
      setError(null);
      setSuccessMessage(null);
      try {
        await action(...args);
      } catch (e) {
        setError(e instanceof ApiError ? formatApiError(e.detail) : 'Something went wrong. Please try again.');
      } finally {
        setIsLoading(false);
      }
    },
    [action]
  );

  return { run, isLoading, error, successMessage, setSuccessMessage, clearError: () => setError(null) };
}

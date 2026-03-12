import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * usePolling Hook
 * 
 * Polls for status updates at exponential backoff intervals
 * Used for waiting for try-on generation results
 */
interface PollingOptions {
  maxAttempts?: number;
  initialDelay?: number;
  maxDelay?: number;
  onSuccess?: (data: unknown) => void;
  onError?: (error: string) => void;
}

export function usePolling(
  asyncFunction: () => Promise<{ status: string; error?: string; [key: string]: unknown }>,
  {
    maxAttempts = 150,
    initialDelay = 2000,
    maxDelay = 10000,
    onSuccess,
    onError
  }: PollingOptions = {}
) {
  const [status, setStatus] = useState('idle'); // idle | polling | success | error
  const [result, setResult] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(async () => {
    if (attempt >= maxAttempts) {
      setStatus('error');
      setError('Maximum polling attempts reached');
      onError?.(( 'timeout'));
      return;
    }

    try {
      const data = await asyncFunction();

      // Check if polling is complete
      if (data.status === 'completed' || data.status === 'succeeded') {
        setStatus('success');
        setResult(data);
        onSuccess?.(data);
        return;
      } else if (data.status === 'failed' || data.status === 'error') {
        setStatus('error');
        const errorMsg = data.error || 'Operation failed';
        setError(errorMsg);
        onError?.(errorMsg);
        return;
      }

      // Schedule next poll with exponential backoff
      const nextAttempt = attempt + 1;
      setAttempt(nextAttempt);

      const delay = Math.min(initialDelay * nextAttempt, maxDelay);
      timeoutRef.current = setTimeout(() => {
        poll();
      }, delay);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setStatus('error');
      setError(message);
      onError?.(message);
    }
  }, [attempt, maxAttempts, asyncFunction, initialDelay, maxDelay, onSuccess, onError]);

  const start = useCallback(() => {
    setStatus('polling');
    setAttempt(0);
    setError(null);
    setResult(null);
    poll();
  }, [poll]);

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setStatus('idle');
    setAttempt(0);
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    status,
    result,
    error,
    attempt,
    start,
    cancel,
    isPolling: status === 'polling'
  };
}

export default usePolling;

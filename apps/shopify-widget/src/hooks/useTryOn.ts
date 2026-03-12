import { useState, useCallback } from 'react';

/**
 * useTryOn Hook
 * 
 * Manages try-on generation and tracking
 * Calls /api/v1/try-on/generate and /api/v1/try-on/{id}
 */
interface TryOnState {
  id: string;
  status: string;
  userImageUrl: string;
  garmentImageUrl: string;
  createdAt: Date;
  [key: string]: unknown;
}

export function useTryOn() {
  const [tryons, setTryons] = useState<TryOnState[]>([]);
  const [current, setCurrent] = useState<TryOnState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(
    async (userImageUrl: string, garmentImageUrl: string, productId: string, category = 'upper_body') => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch('/api/v1/try-on/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_image_url: userImageUrl,
            garment_image_url: garmentImageUrl,
            product_id: productId,
            category
          })
        });

        if (!response.ok) {
          throw new Error('Failed to generate try-on');
        }

        const data = await response.json();
        const newState: TryOnState = {
          id: data.prediction_id as string,
          status: 'processing',
          userImageUrl,
          garmentImageUrl,
          createdAt: new Date()
        };
        setCurrent(newState);

        return data.prediction_id;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const getStatus = useCallback(async (tryonId: string) => {
    try {
      const response = await fetch(`/api/v1/try-on/${tryonId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch status');
      }

      const data = await response.json();

      // Update current if it matches
      if (current?.id === tryonId) {
        setCurrent(prev => (prev ? {
          ...prev,
          ...data,
          status: data.status
        } : null));
      }

      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      throw err;
    }
  }, [current]);

  const getHistory = useCallback(async (limit = 10, offset = 0) => {
    try {
      const response = await fetch(
        `/api/v1/try-on/history?limit=${limit}&offset=${offset}`
      );
      if (!response.ok) {
        throw new Error('Failed to fetch history');
      }

      const data = await response.json();
      setTryons(data.tryons as TryOnState[]);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      throw err;
    }
  }, []);

  return {
    tryons,
    current,
    loading,
    error,
    generate,
    getStatus,
    getHistory,
    clear: () => {
      setCurrent(null);
      setError(null);
    }
  };
}

export default useTryOn;

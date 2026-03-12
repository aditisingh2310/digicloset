import { useState, useEffect } from 'react';

/**
 * useAuth Hook
 * 
 * Manages authentication state and merchant context
 * Fetches from /api/v1/merchant/profile
 */
export function useAuth() {
  const [merchant, setMerchant] = useState(null);
  const [credits, setCredits] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAuth = async () => {
      try {
        // Get merchant profile
        const merchantRes = await fetch('/api/v1/merchant/profile');
        if (!merchantRes.ok) throw new Error('Failed to fetch merchant');
        const merchantData = await merchantRes.json();
        setMerchant(merchantData);

        // Get credit status
        const creditRes = await fetch('/api/v1/billing/credits/check');
        if (!creditRes.ok) throw new Error('Failed to fetch credits');
        const creditData = await creditRes.json();
        setCredits(creditData);

        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        console.error('Auth error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAuth();
  }, []);

  const isAuthenticated = !!merchant;

  return {
    merchant,
    credits,
    isAuthenticated,
    loading,
    error,
    refresh: async () => {
      setLoading(true);
      try {
        const res = await fetch('/api/v1/merchant/profile');
        const data = await res.json();
        setMerchant(data);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
      } finally {
        setLoading(false);
      }
    }
  };
}

export default useAuth;

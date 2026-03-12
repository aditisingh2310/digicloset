import { useState } from 'react';
import './TryOnWidget.css';
import ImageUpload from './ImageUpload';
import ResultDisplay from './ResultDisplay';
import ProcessingSpinner from './ProcessingSpinner';

interface TryOnResult {
  id: string;
  status: string;
  image_url: string;
  error?: string;
  [key: string]: unknown;
}

/**
 * Main Try-On Widget Component
 * 
 * Embeds on Shopify product pages and manages:
 * - Image upload
 * - Try-on generation
 * - Result display
 * - Error handling
 */
export default function TryOnWidget() {
  const [state, setState] = useState('upload'); // upload | processing | result | error
  const [result, setResult] = useState<TryOnResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (userImage: string, garmentImage: string): Promise<void> => {
    setState('processing');
    setError(null);

    try {
      // Call backend API
      const productId = (window as any).productId || 'unknown';
      const response = await fetch('/api/v1/try-on/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_image_url: userImage,
          garment_image_url: garmentImage,
          product_id: productId,
          category: 'upper_body'
        })
      });

      if (!response.ok) {
        throw new Error('Generation failed');
      }

      const data = await response.json();
      
      // Poll for result
      await pollResult(data.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      setState('error');
    }
  };

  const pollResult = async (tryonId: string): Promise<void> => {
    const maxAttempts = 150;
    let attempt = 0;

    while (attempt < maxAttempts) {
      try {
        const response = await fetch(`/api/v1/try-on/${tryonId}`);
        const data = await response.json();

        if (data.status === 'completed') {
          setResult(data as TryOnResult);
          setState('result');
          return;
        } else if (data.status === 'failed') {
          throw new Error(data.error || 'Generation failed');
        }

        // Exponential backoff: 2s, 4s, 6s, max 10s
        const delay = Math.min(2000 * (attempt + 1), 10000);
        await new Promise(resolve => setTimeout(resolve, delay));
        attempt++;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        setState('error');
        return;
      }
    }

    setError('Generation timeout');
    setState('error');
  };

  return (
    <div className="tryon-widget">
      {state === 'upload' && (
        <ImageUpload onUpload={handleUpload} />
      )}
      {state === 'processing' && (
        <ProcessingSpinner />
      )}
      {state === 'result' && result && (
        <ResultDisplay result={result} onRetry={() => setState('upload')} />
      )}
      {state === 'error' && (
        <div className="error-message">
          {error}
          <button onClick={() => setState('upload')}>Try Again</button>
        </div>
      )}
    </div>
  );
}

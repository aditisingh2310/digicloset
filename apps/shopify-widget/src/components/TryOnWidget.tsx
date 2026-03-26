import { useState } from 'react';
import './TryOnWidget.css';
import ImageUpload from './ImageUpload';
import ResultDisplay from './ResultDisplay';
import ProcessingSpinner from './ProcessingSpinner';

interface TryOnResult {
  id: string;
  status: string;
  image_url?: string;
  generated_image_url?: string;
  job_id?: string;
  prediction_id?: string;
  error?: string;
  processing_time?: number;
  generation_time?: number;
  [key: string]: unknown;
}

type WidgetView = 'upload' | 'processing' | 'result' | 'error';

const STATUS_COPY = [
  'Preparing secure upload',
  'Matching pose and garment silhouette',
  'Refining fabric detail and lighting',
  'Finalizing your preview',
];

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
  const [state, setState] = useState<WidgetView>('upload');
  const [result, setResult] = useState<TryOnResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pollAttempt, setPollAttempt] = useState(0);
  const [statusText, setStatusText] = useState(STATUS_COPY[0]);

  const resetWidget = (): void => {
    setState('upload');
    setResult(null);
    setError(null);
    setPollAttempt(0);
    setStatusText(STATUS_COPY[0]);
  };

  const resolveTryOnId = (data: Record<string, unknown>): string => {
    const candidate = data.id ?? data.job_id ?? data.prediction_id;
    return typeof candidate === 'string' ? candidate : '';
  };

  const resolveImageUrl = (value: unknown): string | undefined => {
    if (typeof value !== 'string' || !value) {
      return undefined;
    }

    if (value.startsWith('/')) {
      return new URL(value, window.location.origin).toString();
    }

    return value;
  };

  const normalizeResult = (
    data: Record<string, unknown>,
    fallbackId: string
  ): TryOnResult => {
    const generationTime =
      typeof data.generation_time === 'number'
        ? Math.round(data.generation_time / 1000)
        : undefined;

    return {
      ...data,
      id: resolveTryOnId(data) || fallbackId,
      status: typeof data.status === 'string' ? data.status : 'completed',
      image_url: resolveImageUrl(data.image_url) || resolveImageUrl(data.generated_image_url),
      processing_time:
        typeof data.processing_time === 'number'
          ? data.processing_time
          : generationTime,
    };
  };

  const handleUpload = async (
    userImage: string,
    garmentImage: string
  ): Promise<void> => {
    setState('processing');
    setError(null);
    setPollAttempt(0);
    setStatusText(STATUS_COPY[0]);

    try {
      const productId = (window as any).productId || 'demo-product';
      const response = await fetch('/api/v1/try-on/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_image_url: userImage,
          garment_image_url: garmentImage,
          product_id: productId,
          category: 'upper_body',
        }),
      });

      if (!response.ok) {
        throw new Error(`Generation failed with status ${response.status}`);
      }

      const data = (await response.json()) as Record<string, unknown>;
      const tryOnId = resolveTryOnId(data);

      if (!tryOnId) {
        throw new Error('Generation started but no try-on ID was returned');
      }

      await pollResult(tryOnId);
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
        setPollAttempt(attempt + 1);
        setStatusText(STATUS_COPY[Math.min(attempt, STATUS_COPY.length - 1)]);

        const response = await fetch(`/api/v1/try-on/${tryonId}`);

        if (!response.ok) {
          throw new Error(`Unable to check status (${response.status})`);
        }

        const data = (await response.json()) as Record<string, unknown>;

        if (data.status === 'completed' || data.status === 'succeeded') {
          const normalized = normalizeResult(data, tryonId);
          setResult(normalized);
          window.dispatchEvent(
            new CustomEvent('tryon:generated', {
              detail: { id: normalized.id, image_url: normalized.image_url },
            })
          );
          setState('result');
          return;
        }

        if (data.status === 'failed' || data.status === 'error') {
          throw new Error(
            typeof data.error === 'string' ? data.error : 'Generation failed'
          );
        }

        const delay = Math.min(2000 + attempt * 1000, 7000);
        await new Promise((resolve) => setTimeout(resolve, delay));
        attempt++;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        window.dispatchEvent(
          new CustomEvent('tryon:error', {
            detail: { id: tryonId, error: message },
          })
        );
        setState('error');
        return;
      }
    }

    setError('Generation timeout');
    setState('error');
  };

  return (
    <div className="tryon-widget">
      <div className="tryon-widget__shell">
        <header className="tryon-widget__header">
          <div className="tryon-widget__header-copy">
            <p className="tryon-widget__eyebrow">DigiCloset try-on</p>
            <h2>Let shoppers preview the look before checkout.</h2>
            <p className="tryon-widget__summary">
              Upload one customer photo and one product image to create a clean,
              product-page friendly try-on preview.
            </p>
          </div>

          <ul className="tryon-widget__meta" aria-label="Widget highlights">
            <li>Two image inputs</li>
            <li>Usually under a minute</li>
            <li>Built for PDP placement</li>
          </ul>
        </header>

        <section className="tryon-widget__panel" aria-live="polite">
          {state === 'upload' && <ImageUpload onUpload={handleUpload} />}
          {state === 'processing' && (
            <ProcessingSpinner
              attempt={pollAttempt}
              statusText={statusText}
              onCancel={resetWidget}
            />
          )}
          {state === 'result' && result && (
            <ResultDisplay result={result} onRetry={resetWidget} />
          )}
          {state === 'error' && (
            <div className="tryon-widget__error-card">
              <p className="tryon-widget__error-eyebrow">Try-on interrupted</p>
              <h2>We could not finish your preview.</h2>
              <p className="error-message">
                {error || 'Something went wrong while generating the try-on.'}
              </p>
              <div className="tryon-widget__error-actions">
                <button className="btn btn-primary" onClick={resetWidget}>
                  Try again
                </button>
                <a className="btn btn-secondary" href="mailto:support@digicloset.ai">
                  Contact support
                </a>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

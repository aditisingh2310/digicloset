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
      image_url:
        typeof data.image_url === 'string'
          ? data.image_url
          : typeof data.generated_image_url === 'string'
            ? data.generated_image_url
            : undefined,
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
          setResult(normalizeResult(data, tryonId));
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
        <aside className="tryon-widget__hero">
          <p className="tryon-widget__eyebrow">DigiCloset virtual fitting room</p>
          <h1>Help shoppers see the product on a real person before they buy.</h1>
          <p className="tryon-widget__summary">
            Upload a selfie and the garment image. We turn that into a clean
            try-on preview designed to reduce hesitation and keep the PDP
            experience feeling premium.
          </p>

          <div className="tryon-widget__trust">
            <div className="tryon-widget__trust-item">
              <strong>Fast</strong>
              <span>Most previews finish in under a minute.</span>
            </div>
            <div className="tryon-widget__trust-item">
              <strong>Private</strong>
              <span>Session images are handled for rendering only.</span>
            </div>
            <div className="tryon-widget__trust-item">
              <strong>Flexible</strong>
              <span>Works with customer selfies and product shots.</span>
            </div>
          </div>
        </aside>

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

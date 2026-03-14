"""
Frontend Integration Guide for Async Try-On System

Shows React/TypeScript examples for consuming the async try-on API.
"""

# ============================================================
# 1. API CLIENT SETUP
# ============================================================

## TypeScript Types

```typescript
// api/types/tryon.ts

export interface TryOnRequest {
  user_image_url: string;
  garment_image_url: string;
  product_id: string;
  category: string;
  shop_id: number;
}

export interface TryOnJobResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface TryOnStatusResponse {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  image_url?: string;
  generation_time?: number;
  error?: string;
  created_at: string;
}

export interface TryOnHistory {
  jobs: TryOnHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface TryOnHistoryItem {
  job_id: string;
  status: string;
  product_id: string;
  image_url?: string;
  created_at: string;
  updated_at: string;
}
```

## API Client

```typescript
// api/client/tryonClient.ts

import axios, { AxiosInstance } from 'axios';
import { TryOnRequest, TryOnJobResponse, TryOnStatusResponse, TryOnHistory } from '../types/tryon';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class TryOnClient {
  private axiosInstance: AxiosInstance;

  constructor(baseURL: string = API_BASE) {
    this.axiosInstance = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Submit a try-on generation request
   * Returns immediately with job_id
   */
  async submitRequest(request: TryOnRequest): Promise<TryOnJobResponse> {
    const response = await this.axiosInstance.post<TryOnJobResponse>(
      '/try-on/request',
      request
    );
    return response.data;
  }

  /**
   * Poll job status
   * Use in conjunction with setTimeout/setInterval for polling
   */
  async getStatus(jobId: string): Promise<TryOnStatusResponse> {
    const response = await this.axiosInstance.get<TryOnStatusResponse>(
      `/try-on/status/${jobId}`
    );
    return response.data;
  }

  /**
   * Get try-on history for a shop
   */
  async getHistory(shopId: number, limit: number = 20, offset: number = 0): Promise<TryOnHistory> {
    const response = await this.axiosInstance.get<TryOnHistory>(
      '/try-on/history',
      {
        params: { shop_id: shopId, limit, offset },
      }
    );
    return response.data;
  }
}

export const tryOnClient = new TryOnClient();
```

# ============================================================
# 2. REACT HOOKS FOR TRY-ON
# ============================================================

## useJobPolling Hook

```typescript
// hooks/useJobPolling.ts

import { useState, useEffect, useCallback } from 'react';
import { TryOnStatusResponse } from '../api/types/tryon';
import { tryOnClient } from '../api/client/tryonClient';

const POLLING_INTERVAL = 2000; // 2 seconds
const MAX_POLLING_TIME = 10 * 60 * 1000; // 10 minutes

interface UseJobPollingOptions {
  onSuccess?: (result: TryOnStatusResponse) => void;
  onError?: (error: string) => void;
  onUpdate?: (status: TryOnStatusResponse) => void;
}

export function useJobPolling(
  jobId: string | null,
  options: UseJobPollingOptions = {}
) {
  const [status, setStatus] = useState<TryOnStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const { onSuccess, onError, onUpdate } = options;

  const poll = useCallback(async () => {
    if (!jobId) return;

    try {
      const result = await tryOnClient.getStatus(jobId);
      setStatus(result);
      setError(null);
      
      onUpdate?.(result);

      // Job completed successfully
      if (result.status === 'completed' && result.image_url) {
        onSuccess?.(result);
        return; // Stop polling
      }

      // Job failed
      if (result.status === 'failed') {
        setError(result.error || 'Generation failed');
        onError?.(result.error || 'Unknown error');
        return; // Stop polling
      }

      // Continue polling
      setTimeout(poll, POLLING_INTERVAL);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      onError?.(errorMessage);
    }
  }, [jobId, onSuccess, onError, onUpdate]);

  useEffect(() => {
    if (!jobId) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    const startTime = Date.now();

    const timeout = setTimeout(() => {
      if (Date.now() - startTime > MAX_POLLING_TIME) {
        setError('Job timed out after 10 minutes');
        onError?.('Job timed out after 10 minutes');
        setIsLoading(false);
      } else {
        poll();
      }
    }, 0);

    return () => clearTimeout(timeout);
  }, [jobId, poll, onError]);

  return { status, error, isLoading };
}
```

## useTryOn Hook

```typescript
// hooks/useTryOn.ts

import { useState, useCallback } from 'react';
import { TryOnRequest, TryOnJobResponse } from '../api/types/tryon';
import { tryOnClient } from '../api/client/tryonClient';
import { useJobPolling } from './useJobPolling';

interface UseTryOnOptions {
  onSuccess?: (imageUrl: string, generationTime?: number) => void;
  onError?: (error: string) => void;
  onStatusUpdate?: (status: string) => void;
}

export function useTryOn(options: UseTryOnOptions = {}) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [remainingGenerations, setRemainingGenerations] = useState<number | null>(null);

  const handleStatusUpdate = useCallback((statusResponse) => {
    options.onStatusUpdate?.(statusResponse.status);
    
    // Attempt to parse remaining count from message
    if (statusResponse.status === 'pending') {
      const match = statusResponse.message?.match(/(\d+) generations remaining/);
      if (match) {
        setRemainingGenerations(parseInt(match[1], 10));
      }
    }
  }, [options]);

  const { status, error, isLoading } = useJobPolling(jobId, {
    onSuccess: (result) => {
      if (result.image_url) {
        options.onSuccess?.(result.image_url, result.generation_time);
      }
    },
    onError: options.onError,
    onUpdate: handleStatusUpdate,
  });

  const generate = useCallback(
    async (request: TryOnRequest) => {
      setIsSubmitting(true);
      setSubmitError(null);
      setJobId(null);

      try {
        const response: TryOnJobResponse = await tryOnClient.submitRequest(request);
        setJobId(response.job_id);

        // Parse remaining from response message
        const match = response.message.match(/(\d+) generations remaining/);
        if (match) {
          setRemainingGenerations(parseInt(match[1], 10));
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to submit request';
        setSubmitError(errorMessage);
        options.onError?.(errorMessage);
      } finally {
        setIsSubmitting(false);
      }
    },
    [options]
  );

  return {
    generate,
    jobId,
    status: status?.status || null,
    imageUrl: status?.image_url || null,
    generationTime: status?.generation_time || null,
    error: submitError || error,
    isSubmitting,
    isLoading: isLoading && jobId !== null,
    remainingGenerations,
  };
}
```

# ============================================================
# 3. REACT COMPONENTS
# ============================================================

## TryOn Component

```typescript
// components/TryOn.tsx

import React, { useState } from 'react';
import { useTryOn } from '../hooks/useTryOn';
import { TryOnRequest } from '../api/types/tryon';
import './TryOn.css';

interface TryOnProps {
  productId: string;
  shopId: number;
}

export const TryOn: React.FC<TryOnProps> = ({ productId, shopId }) => {
  const [userImage, setUserImage] = useState<File | null>(null);
  const [garmentImage, setGarmentImage] = useState<File | null>(null);

  const {
    generate,
    status,
    imageUrl,
    generationTime,
    isSubmitting,
    isLoading,
    remainingGenerations,
    error,
  } = useTryOn({
    onSuccess: (url, time) => {
      console.log(`✓ Generated in ${time}ms:`, url);
    },
    onError: (err) => {
      console.error('✗ Error:', err);
    },
    onStatusUpdate: (newStatus) => {
      console.log('Status:', newStatus);
    },
  });

  const handleUserImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setUserImage(file);
  };

  const handleGarmentImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setGarmentImage(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!userImage || !garmentImage) {
      alert('Please select both images');
      return;
    }

    // Upload to temporary storage (or use pre-signed URLs)
    const userImageUrl = URL.createObjectURL(userImage);
    const garmentImageUrl = URL.createObjectURL(garmentImage);

    const request: TryOnRequest = {
      user_image_url: userImageUrl,
      garment_image_url: garmentImageUrl,
      product_id: productId,
      category: 'upper_body',
      shop_id: shopId,
    };

    await generate(request);
  };

  return (
    <div className="tryon-container">
      <h2>Virtual Try-On</h2>

      {error && (
        <div className="tryon-error">
          <p>⚠️ {error}</p>
        </div>
      )}

      {remainingGenerations !== null && (
        <div className="tryon-quota">
          <p>Remaining generations: <strong>{remainingGenerations}</strong></p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="tryon-form">
        <div className="form-group">
          <label>Your Photo</label>
          <input
            type="file"
            accept="image/*"
            onChange={handleUserImageChange}
            disabled={isSubmitting || isLoading}
          />
          {userImage && <img src={URL.createObjectURL(userImage)} alt="User" />}
        </div>

        <div className="form-group">
          <label>Garment</label>
          <input
            type="file"
            accept="image/*"
            onChange={handleGarmentImageChange}
            disabled={isSubmitting || isLoading}
          />
          {garmentImage && <img src={URL.createObjectURL(garmentImage)} alt="Garment" />}
        </div>

        <button
          type="submit"
          disabled={isSubmitting || isLoading || !userImage || !garmentImage}
          className={isLoading ? 'loading' : ''}
        >
          {isSubmitting && 'Submitting...'}
          {isLoading && `Generating... (${status})`}
          {!isSubmitting && !isLoading && 'Generate Try-On'}
        </button>
      </form>

      {isLoading && (
        <div className="tryon-progress">
          <div className="spinner"></div>
          <p>Status: {status}</p>
          <p className="note">This usually takes 10-30 seconds...</p>
        </div>
      )}

      {imageUrl && (
        <div className="tryon-result">
          <h3>Result</h3>
          <img src={imageUrl} alt="Try-on result" />
          {generationTime && (
            <p className="generation-time">Generated in {generationTime}ms</p>
          )}
          <button onClick={() => {
            // Download or share result
            const a = document.createElement('a');
            a.href = imageUrl;
            a.download = `tryon-${Date.now()}.png`;
            a.click();
          }}>
            Download
          </button>
        </div>
      )}
    </div>
  );
};
```

## CSS Styling

```css
/* components/TryOn.css */

.tryon-container {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
  border-radius: 8px;
  background: #f9f9f9;
}

.tryon-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  color: #333;
}

.form-group input[type="file"] {
  padding: 0.5rem;
  border: 2px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.form-group img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 4px;
  margin-top: 0.5rem;
}

button {
  padding: 1rem;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s;
}

button:hover {
  background: #0056b3;
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

button.loading::after {
  content: " ⌛";
}

.tryon-progress {
  margin-top: 2rem;
  text-align: center;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.tryon-result {
  margin-top: 2rem;
  text-align: center;
}

.tryon-result img {
  max-width: 100%;
  border-radius: 8px;
  margin: 1rem 0;
}

.generation-time {
  color: #666;
  font-size: 0.9rem;
}

.tryon-error {
  padding: 1rem;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.tryon-quota {
  padding: 1rem;
  background: #d1ecf1;
  color: #0c5460;
  border-radius: 4px;
  margin-bottom: 1rem;
}
```

# ============================================================
# 4. IMPLEMENTATION EXAMPLE
# ============================================================

## Page Component

```typescript
// pages/ProductPage.tsx

import React from 'react';
import { useParams } from 'react-router-dom';
import { TryOn } from '../components/TryOn';

export const ProductPage: React.FC = () => {
  const { shopId, productId } = useParams<{ shopId: string; productId: string }>();

  return (
    <div className="product-page">
      <h1>Product Details</h1>
      
      {/* Product info... */}

      {/* Try-on section */}
      <TryOn
        productId={productId!}
        shopId={parseInt(shopId!, 10)}
      />
    </div>
  );
};
```

# ============================================================
# 5. ERROR HANDLING & BEST PRACTICES
# ============================================================

## Graceful Degradation

```typescript
// Fallback if async queue is unavailable
async function tryOnWithFallback(request: TryOnRequest) {
  try {
    // Try async endpoint
    return await tryOnClient.submitRequest(request);
  } catch (error) {
    // Fallback to synchronous endpoint (if available)
    console.warn('Async endpoint failed, using sync fallback...');
    return await legacyTryOnClient.generateSync(request);
  }
}
```

## Timeout Handling

```typescript
// Auto-cancel polling after max time
const MAX_WAIT_TIME = 10 * 60 * 1000; // 10 minutes

function useJobPollingWithTimeout(jobId: string) {
  useEffect(() => {
    const timeout = setTimeout(() => {
      // Show message to user
      alert('Try-on generation is taking longer than expected. Please check back later.');
    }, MAX_WAIT_TIME);

    return () => clearTimeout(timeout);
  }, [jobId]);
}
```

## Optimistic Updates

```typescript
// Show preview while waiting
const [previewUrl, setPreviewUrl] = useState<string | null>(null);

const handleSubmit = async (request: TryOnRequest) => {
  // Show preview immediately
  setPreviewUrl(URL.createObjectURL(garmentImage));

  // Submit async job
  const { job_id } = await generate(request);

  // Replace preview with real result once ready
};
```


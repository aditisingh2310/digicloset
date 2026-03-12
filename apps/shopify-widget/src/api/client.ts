/**
 * API Client for Shopify Widget
 * 
 * Provides typed methods for calling backend-api service
 * Base URL: /api/v1
 */

const BASE_URL = '/api/v1';

// ==================== TRY-ON ENDPOINTS ====================

export async function generateTryOn(
  userImageUrl: string,
  garmentImageUrl: string,
  productId: string,
  category: string = 'upper_body'
) {
  const response = await fetch(`${BASE_URL}/try-on/generate`, {
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
    throw new Error(`Try-on generation failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getTryOnStatus(tryonId: string) {
  const response = await fetch(`${BASE_URL}/try-on/${tryonId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch try-on status: ${response.statusText}`);
  }

  return response.json();
}

export async function getTryOnHistory(limit: number = 10, offset: number = 0) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const response = await fetch(`${BASE_URL}/try-on/history?${query}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch try-on history: ${response.statusText}`);
  }

  return response.json();
}

// ==================== BILLING ENDPOINTS ====================

export async function checkCredits() {
  const response = await fetch(`${BASE_URL}/billing/credits/check`);

  if (!response.ok) {
    throw new Error(`Failed to check credits: ${response.statusText}`);
  }

  return response.json();
}

export async function getBillingHistory(limit: number = 20, offset: number = 0) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const response = await fetch(`${BASE_URL}/billing/history?${query}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch billing history: ${response.statusText}`);
  }

  return response.json();
}

// ==================== MERCHANT ENDPOINTS ====================

export async function getMerchantProfile() {
  const response = await fetch(`${BASE_URL}/merchant/profile`);

  if (!response.ok) {
    throw new Error(`Failed to fetch merchant profile: ${response.statusText}`);
  }

  return response.json();
}

export async function updateMerchantSettings(settings: Record<string, any>) {
  const response = await fetch(`${BASE_URL}/merchant/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings)
  });

  if (!response.ok) {
    throw new Error(`Failed to update settings: ${response.statusText}`);
  }

  return response.json();
}

export async function handleOAuthCallback(code: string, state: string) {
  const response = await fetch(`${BASE_URL}/merchant/oauth/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, state })
  });

  if (!response.ok) {
    throw new Error(`OAuth callback failed: ${response.statusText}`);
  }

  return response.json();
}

// ==================== ERROR HANDLING ====================

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public endpoint: string,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ==================== RETRY LOGIC ====================

export async function fetchWithRetry(
  fn: () => Promise<Response>,
  maxRetries = 3,
  delayMs = 1000
) {
  let lastError;

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fn();
      if (response.ok) {
        return response;
      }
      lastError = new Error(`HTTP ${response.status}`);
    } catch (err) {
      lastError = err;
    }

    if (i < maxRetries - 1) {
      await new Promise(resolve => setTimeout(resolve, delayMs * (i + 1)));
    }
  }

  throw lastError;
}

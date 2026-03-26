export async function requestJson(path, options = {}) {
  const headers = new Headers(options.headers || {});

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  const text = await response.text();
  let payload = null;

  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const detail =
      payload?.detail ||
      payload?.message ||
      (typeof payload === "string" ? payload : response.statusText);
    throw new Error(detail || "Request failed");
  }

  return payload;
}

export function formatCredits(value) {
  if (value === null || value === undefined) {
    return "0";
  }

  if (value === Infinity || value === "unlimited") {
    return "Unlimited";
  }

  return new Intl.NumberFormat().format(value);
}

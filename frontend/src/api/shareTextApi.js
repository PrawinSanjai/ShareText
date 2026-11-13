const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const message = body?.detail || body?.message || "Request failed";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return body;
}

export function createText(text, { ttlHours = 24, maxViews = null, password = "" } = {}) {
  return request("/text/store", {
    method: "POST",
    body: JSON.stringify({ text, ttl_hours: ttlHours, max_views: maxViews, password: password || null }),
  });
}

export function readText(textId, password = "") {
  return request(`/text/${encodeURIComponent(textId)}/read`, {
    method: "POST",
    body: JSON.stringify({ password: password || null }),
  });
}

export function readTextBySecret(secretKey) {
  return request("/text/manage", {
    method: "POST",
    body: JSON.stringify({ secret_key: secretKey }),
  });
}

export function updateText({ text, secretKey }) {
  return request("/text/edit", {
    method: "PUT",
    body: JSON.stringify({ text, secret_key: secretKey }),
  });
}

export function deleteText(secretKey) {
  return request("/text/delete", {
    method: "DELETE",
    body: JSON.stringify({ secret_key: secretKey }),
  });
}

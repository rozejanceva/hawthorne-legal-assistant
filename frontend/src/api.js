const API = "/api";

export function apiDate(value) {
  if (!value) return value;
  return value.length === 16 ? `${value}:00` : value;
}

export async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : "Request failed.");
  }
  return data;
}

/**
 * Python backend connectivity configuration.
 *
 * Set NEXT_PUBLIC_PYTHON_BACKEND_URL to the FastAPI server address
 * (e.g. http://localhost:8000). When unset, the UI falls back to
 * demo/mock data — no real Python backend is required.
 */

const ENV_KEY = "NEXT_PUBLIC_PYTHON_BACKEND_URL";

export function getPythonBackendUrl(): string | null {
  if (typeof process !== "undefined" && process.env?.[ENV_KEY]) {
    return process.env[ENV_KEY]!;
  }
  return null;
}

export function isPythonBackendConfigured(): boolean {
  return getPythonBackendUrl() !== null;
}

/**
 * Call the Python backend at the given path, forwarding JSON body if present.
 * Returns null if the backend is not configured or unreachable.
 */
export async function callPythonBackend<T>(
  path: string,
  options?: { method?: string; body?: unknown }
): Promise<T | null> {
  const baseUrl = getPythonBackendUrl();
  if (!baseUrl) return null;
  const url = `${baseUrl}${path}`;
  try {
    const res = await fetch(url, {
      method: options?.method ?? "GET",
      headers: { "Content-Type": "application/json" },
      body: options?.body ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(120_000),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

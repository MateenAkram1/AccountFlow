export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CSRF_HEADER = "X-Requested-With";
const CSRF_VALUE = "XMLHttpRequest";

export type ApiFetchOptions = RequestInit & {
  /** When false, 401 does not navigate to /login (used by session probes). Default true. */
  authRedirect?: boolean;
};

function mergeHeaders(init?: HeadersInit, method?: string, body?: BodyInit | null): Headers {
  const headers = new Headers(init || {});
  const m = (method || "GET").toUpperCase();
  if (m !== "GET" && m !== "HEAD" && m !== "OPTIONS") {
    headers.set(CSRF_HEADER, CSRF_VALUE);
  }
  // Let the browser set multipart boundary for FormData
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    headers.delete("Content-Type");
  }
  return headers;
}

function redirectToLogin(nextPath: string) {
  if (typeof window === "undefined") return;
  const path = window.location.pathname;
  const onAuthPage = path.startsWith("/login") || path.startsWith("/register");
  if (!onAuthPage) {
    window.location.href = `/login?next=${encodeURIComponent(nextPath)}`;
  }
}

export async function apiFetch<T>(path: string, options?: ApiFetchOptions): Promise<T> {
  const { authRedirect = true, ...init } = options || {};
  const method = init.method || "GET";
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: mergeHeaders(init.headers, method, init.body),
  });
  if (res.status === 401 && authRedirect) {
    redirectToLogin(typeof window !== "undefined" ? window.location.pathname : "/");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(detail)
          : "API error"
    );
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export async function createRun(formData: FormData) {
  const res = await fetch(`${API_URL}/runs`, {
    method: "POST",
    body: formData,
    credentials: "include",
    headers: { [CSRF_HEADER]: CSRF_VALUE },
  });
  if (!res.ok) {
    if (res.status === 401) {
      redirectToLogin("/runs/new");
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create run");
  }
  return res.json();
}

export type Me = { id: string; email: string; name: string | null };

export async function fetchMe(): Promise<Me | null> {
  try {
    return await apiFetch<Me>("/auth/me", { authRedirect: false });
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST", authRedirect: false });
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CSRF_HEADER = "X-Requested-With";
const CSRF_VALUE = "XMLHttpRequest";

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

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method || "GET";
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: mergeHeaders(options?.headers, method, options?.body),
  });
  if (res.status === 401 && typeof window !== "undefined") {
    const onAuthPage =
      window.location.pathname.startsWith("/login") ||
      window.location.pathname.startsWith("/register");
    if (!onAuthPage) {
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    }
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
    if (res.status === 401 && typeof window !== "undefined") {
      window.location.href = `/login?next=${encodeURIComponent("/runs/new")}`;
    }
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create run");
  }
  return res.json();
}

export type Me = { id: string; email: string; name: string | null };

export async function fetchMe(): Promise<Me | null> {
  try {
    return await apiFetch<Me>("/auth/me");
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
}

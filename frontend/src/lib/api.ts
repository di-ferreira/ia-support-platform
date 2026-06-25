const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Options = RequestInit & {
  params?: Record<string, string | number | undefined | null>;
};

async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { params, ...init } = options;
  let url = `${API_URL}${path}`;

  if (params) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) search.set(k, String(v));
    });
    const qs = search.toString();
    if (qs) url += `?${qs}`;
  }

  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Erro na requisição");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string, params?: Options["params"]) =>
    request<T>(path, { params }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

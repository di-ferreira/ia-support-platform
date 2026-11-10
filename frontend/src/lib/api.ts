const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

type Options = RequestInit & {
  params?: Record<string, string | number | undefined | null>;
};

// Spec 07/03 (gaps 07-2 e 03-10): tenta renovar o access token expirado
// usando o refresh_token persistido. Retorna true se a renovação ocorreu.
async function renovarSessao(): Promise<boolean> {
  const refresh_token = localStorage.getItem("refresh_token");
  if (!refresh_token) return false;
  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) return false;
    const data = (await res.json()) as {
      access_token: string;
      refresh_token?: string;
    };
    if (!data?.access_token) return false;
    localStorage.setItem("token", data.access_token);
    if (data.refresh_token) {
      localStorage.setItem("refresh_token", data.refresh_token);
    }
    return true;
  } catch {
    return false;
  }
}

async function request<T>(
  path: string,
  options: Options = {},
  retried = false,
): Promise<T> {
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

  if (
    res.status === 401 &&
    !retried &&
    !path.startsWith("/auth/") &&
    typeof window !== "undefined"
  ) {
    // Access token expirado: tenta um refresh (uma única vez) e refaz a
    // requisição original. Sem refresh_token ou com falha, encerra a sessão.
    const renovado = await renovarSessao();
    if (renovado) {
      return request<T>(path, options, true);
    }
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
    throw new Error("Sessão expirada");
  }

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

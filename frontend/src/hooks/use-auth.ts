"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth-store";
import { api } from "@/lib/api";

export function useAuth() {
  const { token, user, setAuth, logout, loading } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!token) return;
    api.get<{ id: number; nome: string; email: string; perfil: string; ativo: boolean }>("/auth/me")
      .then((u) => setAuth(token, u))
      .catch(() => logout());
  }, []);

  const login = async (email: string, senha: string) => {
    const res = await api.post<{ access_token: string }>("/auth/login", { email, senha });
    const me = await api.get<{ id: number; nome: string; email: string; perfil: string; ativo: boolean }>("/auth/me");
    setAuth(res.access_token, me);
    router.push("/dashboard");
  };

  return { token, user, loading, login, logout };
}

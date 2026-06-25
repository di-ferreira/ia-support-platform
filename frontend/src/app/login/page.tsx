"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth-store";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth, token } = useAuthStore();
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    if (token) router.replace("/dashboard");
  }, [token]);

  return (
    <div className="flex min-h-screen">
      <div className="flex w-full max-w-md flex-col justify-center px-8 mx-auto">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 h-12 w-12 rounded-lg bg-accent-500" />
          <h1 className="text-2xl font-bold text-gray-900">EMSoft Support</h1>
          <p className="mt-1 text-sm text-gray-500">Plataforma de Atendimento Inteligente</p>
        </div>
        <form
          className="space-y-4"
          onSubmit={async (e) => {
            e.preventDefault();
            setErro("");
            setCarregando(true);
            try {
              const form = new FormData(e.currentTarget);
              const email = String(form.get("email"));
              const senha = String(form.get("senha"));
              const res = await api.post<{ access_token: string }>("/auth/login", { email, senha });
              localStorage.setItem("token", res.access_token);
              const me = await api.get<{ id: number; nome: string; email: string; perfil: string; ativo: boolean }>("/auth/me");
              setAuth(res.access_token, me);
              router.push("/dashboard");
            } catch (err) {
              setErro(err instanceof Error ? err.message : "Erro ao fazer login");
              setCarregando(false);
            }
          }}
        >
          {erro && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{erro}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              name="email"
              type="email"
              required
              className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="seu@email.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
            <input
              name="senha"
              type="password"
              required
              className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="••••••"
            />
          </div>
          <button
            type="submit"
            disabled={carregando}
            className="w-full h-10 rounded-md bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors disabled:opacity-50"
          >
            {carregando ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
      <div className="hidden lg:flex flex-1 bg-gradient-to-br from-primary-900 to-primary-700 items-center justify-center">
        <div className="text-center text-white">
          <h2 className="text-3xl font-bold">Suporte Inteligente</h2>
          <p className="mt-2 text-primary-200">Reduza em 70% a carga operacional do suporte</p>
        </div>
      </div>
    </div>
  );
}

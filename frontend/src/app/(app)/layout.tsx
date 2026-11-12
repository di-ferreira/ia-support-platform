"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { useAuthStore } from "@/lib/stores/auth-store";
import { api } from "@/lib/api";
import { podeAcessarRota } from "@/lib/permissoes";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, user, loading, setAuth, loadFromStorage } = useAuthStore();
  const [acessoNegado, setAcessoNegado] = useState<string | null>(null);

  useEffect(() => {
    loadFromStorage();
  }, []);

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    api.get<{ id: string; nome: string; email: string; perfil: string; ativo: boolean }>("/auth/me")
      .then((u) => {
        const t = localStorage.getItem("token")!;
        const r = localStorage.getItem("refresh_token");
        setAuth(t, u, r ?? undefined);
      })
      .catch(() => {
        localStorage.removeItem("token");
        localStorage.removeItem("refresh_token");
        router.replace("/login");
      });
  }, []);

  // Gaps 07-11/04-3: guarda de rota por perfil (conveniência de UI — o
  // backend continua autorizando). Só decide com o perfil carregado, para
  // não redirecionar durante o `/auth/me` inicial. `/atendimento` é
  // liberado para todo perfil, então o fallback nunca cria loop.
  useEffect(() => {
    if (loading || !token || !user) return;
    if (podeAcessarRota(user.perfil, pathname)) return;
    if (pathname === "/atendimento") return;
    setAcessoNegado(pathname);
    router.replace("/atendimento");
  }, [loading, token, user, pathname, router]);

  if (!token) return null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto bg-neutral-50 p-6">
          {acessoNegado ? (
            <div
              role="alert"
              className="mb-4 flex items-center justify-between gap-4 rounded-lg border border-status-danger-soft bg-status-danger-soft px-4 py-3 text-sm text-status-danger"
            >
              <p>
                Você não tem acesso à página <strong>{acessoNegado}</strong> com o
                seu perfil.
              </p>
              <button
                type="button"
                onClick={() => setAcessoNegado(null)}
                className="shrink-0 rounded-md px-2 py-1 font-medium hover:bg-status-danger-soft"
              >
                Fechar
              </button>
            </div>
          ) : null}
          {children}
        </main>
      </div>
    </div>
  );
}

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { useAuthStore } from "@/lib/stores/auth-store";
import { api } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token, setAuth, loadFromStorage } = useAuthStore();

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

  if (!token) return null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto bg-gray-50 p-6">{children}</main>
      </div>
    </div>
  );
}

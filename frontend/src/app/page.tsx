"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function Home() {
  const router = useRouter();
  const { loadFromStorage, token } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, []);

  useEffect(() => {
    if (token) router.replace("/dashboard");
    else router.replace("/login");
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-primary-900">
      <p className="text-primary-200">Carregando...</p>
    </div>
  );
}

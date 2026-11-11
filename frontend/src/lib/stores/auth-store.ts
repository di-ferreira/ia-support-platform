import { create } from "zustand";

import { api } from "@/lib/api";

interface Atendente {
  id: string;
  nome: string;
  email: string;
  perfil: string;
  ativo: boolean;
  departamento_id?: string | null;
}

interface AuthState {
  token: string | null;
  refresh_token: string | null;
  user: Atendente | null;
  loading: boolean;
  setAuth: (token: string, user: Atendente, refreshToken?: string) => void;
  logout: () => void;
  loadFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  refresh_token: null,
  user: null,
  loading: true,
  setAuth: (token, user, refreshToken) => {
    // Spec 07/03 (gaps 07-2 e 03-10): o refresh_token é persistido para
    // permitir renovação automática do access token expirado (api.ts).
    localStorage.setItem("token", token);
    if (refreshToken) {
      localStorage.setItem("refresh_token", refreshToken);
    }
    set({ token, refresh_token: refreshToken ?? null, user, loading: false });
  },
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    set({ token: null, refresh_token: null, user: null, loading: false });
  },
  loadFromStorage: async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      set({ token: null, refresh_token: null, user: null, loading: false });
      return;
    }
    set({ token, loading: true });
    try {
      const user = await api.get<Atendente>("/auth/me");
      set({
        token,
        refresh_token: localStorage.getItem("refresh_token"),
        user,
        loading: false,
      });
    } catch {
      localStorage.removeItem("token");
      localStorage.removeItem("refresh_token");
      set({ token: null, refresh_token: null, user: null, loading: false });
    }
  },
}));

import { create } from "zustand";

interface Atendente {
  id: number;
  nome: string;
  email: string;
  perfil: string;
  ativo: boolean;
}

interface AuthState {
  token: string | null;
  user: Atendente | null;
  loading: boolean;
  setAuth: (token: string, user: Atendente) => void;
  logout: () => void;
  loadFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  loading: true,
  setAuth: (token, user) => {
    localStorage.setItem("token", token);
    set({ token, user, loading: false });
  },
  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, user: null, loading: false });
  },
  loadFromStorage: () => {
    const token = localStorage.getItem("token");
    set({ token, loading: false });
  },
}));

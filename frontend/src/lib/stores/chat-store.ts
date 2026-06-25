import { create } from "zustand";

interface ChatSummary {
  id: number;
  cliente_nome: string | null;
  status: string;
  prioridade: string;
  resumo_problema: string | null;
  ultima_mensagem_em: string | null;
}

interface ChatState {
  chats: ChatSummary[];
  chatAtivo: number | null;
  setChats: (chats: ChatSummary[]) => void;
  setChatAtivo: (id: number | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  chats: [],
  chatAtivo: null,
  setChats: (chats) => set({ chats }),
  setChatAtivo: (id) => set({ chatAtivo: id }),
}));

import { create } from "zustand";

/** Chat ativo no store: id + os campos exibidos na página (gap 07-5). */
export interface ChatAtivo {
  id: string;
  cliente_nome?: string | null;
  status?: string;
  prioridade?: string;
  departamento_id?: string | null;
  atendente_id?: string | null;
}

/** Payload do evento `chat_atualizado` do backend (app/api/realtime.py). */
export interface ChatAtualizadoEvent {
  chat_id: string;
  status?: string;
  prioridade?: string;
  departamento_id?: string | null;
  atendente_id?: string | null;
}

interface ChatState {
  /** Fonte única do chat ativo (gap 07-5). */
  chatAtivo: ChatAtivo | null;
  /** Seleciona/troca o chat ativo; null limpa. */
  setChatAtivo: (chat: ChatAtivo | null) => void;
  /** Aplica o evento `chat_atualizado` apenas quando ele mira o chat ativo. */
  aplicarChatAtualizado: (dados: ChatAtualizadoEvent) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  chatAtivo: null,
  setChatAtivo: (chat) => set({ chatAtivo: chat }),
  aplicarChatAtualizado: (dados) =>
    set((state) =>
      state.chatAtivo && state.chatAtivo.id === dados.chat_id
        ? {
            chatAtivo: {
              ...state.chatAtivo,
              ...(dados.status !== undefined ? { status: dados.status } : {}),
              ...(dados.prioridade !== undefined
                ? { prioridade: dados.prioridade }
                : {}),
              ...(dados.departamento_id !== undefined
                ? { departamento_id: dados.departamento_id }
                : {}),
              ...(dados.atendente_id !== undefined
                ? { atendente_id: dados.atendente_id }
                : {}),
            },
          }
        : {},
    ),
}));

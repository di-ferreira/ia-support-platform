import { beforeEach, describe, expect, it } from "vitest";

import { useChatStore } from "@/lib/stores/chat-store";

const chatA = {
  id: "chat-1",
  cliente_nome: "Ana",
  status: "NOVO",
  prioridade: "media",
  departamento_id: "depto-1",
  atendente_id: null,
};

describe("chat store — fonte única do chat ativo (gap 07-5)", () => {
  beforeEach(() => {
    useChatStore.setState({ chatAtivo: null });
  });

  it("seleciona o chat ativo com id + objeto", () => {
    useChatStore.getState().setChatAtivo(chatA);
    expect(useChatStore.getState().chatAtivo).toEqual(chatA);
  });

  it("troca o chat ativo mantendo apenas o mais recente", () => {
    useChatStore.getState().setChatAtivo(chatA);
    useChatStore.getState().setChatAtivo({
      ...chatA,
      id: "chat-2",
      cliente_nome: "Bruno",
    });
    expect(useChatStore.getState().chatAtivo?.id).toBe("chat-2");
    expect(useChatStore.getState().chatAtivo?.cliente_nome).toBe("Bruno");
  });

  it("limpa o chat ativo com null", () => {
    useChatStore.getState().setChatAtivo(chatA);
    useChatStore.getState().setChatAtivo(null);
    expect(useChatStore.getState().chatAtivo).toBeNull();
  });

  it("atualiza o chat ativo no evento chat_atualizado quando o id casa", () => {
    useChatStore.getState().setChatAtivo(chatA);
    useChatStore.getState().aplicarChatAtualizado({
      chat_id: "chat-1",
      status: "EM_ATENDIMENTO",
      prioridade: "urgente",
      departamento_id: "depto-2",
      atendente_id: "atendente-9",
    });
    expect(useChatStore.getState().chatAtivo).toEqual({
      id: "chat-1",
      cliente_nome: "Ana",
      status: "EM_ATENDIMENTO",
      prioridade: "urgente",
      departamento_id: "depto-2",
      atendente_id: "atendente-9",
    });
  });

  it("ignora o evento chat_atualizado de outro chat", () => {
    useChatStore.getState().setChatAtivo(chatA);
    useChatStore.getState().aplicarChatAtualizado({
      chat_id: "chat-2",
      status: "RESOLVIDO",
    });
    expect(useChatStore.getState().chatAtivo).toEqual(chatA);
  });

  it("ignora o evento chat_atualizado quando nao ha chat ativo", () => {
    useChatStore.getState().aplicarChatAtualizado({ chat_id: "chat-1" });
    expect(useChatStore.getState().chatAtivo).toBeNull();
  });
});

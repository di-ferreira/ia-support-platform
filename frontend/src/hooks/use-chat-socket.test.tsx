import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useChatSocket } from "@/hooks/use-chat-socket";

class FakeWebSocket {
  static instancias: FakeWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((evento: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  enviados: string[] = [];

  constructor(public url: string) {
    FakeWebSocket.instancias.push(this);
  }

  send(dados: string) {
    this.enviados.push(dados);
  }

  close() {
    this.onclose?.();
  }

  abrir() {
    this.onopen?.();
  }

  derrubar() {
    this.onclose?.();
  }
}

function montar(chatId: string) {
  const client = new QueryClient();
  return {
    client,
    ...renderHook(() => useChatSocket(chatId), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      ),
    }),
  };
}

describe("useChatSocket", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(Math, "random").mockReturnValue(1); // atraso = teto (determinístico)
    localStorage.setItem("token", "abc");
    FakeWebSocket.instancias = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("envia o token como primeira mensagem", () => {
    const { unmount } = montar("c1");
    const socket = FakeWebSocket.instancias[0];

    act(() => socket.abrir());

    expect(JSON.parse(socket.enviados[0])).toEqual({ token: "abc" });
    unmount();
  });

  it("reconecta com backoff de 1s apos queda", () => {
    const { unmount } = montar("c1");
    const primeiro = FakeWebSocket.instancias[0];

    act(() => primeiro.abrir());
    act(() => primeiro.derrubar());

    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(FakeWebSocket.instancias).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(FakeWebSocket.instancias).toHaveLength(2);
    unmount();
  });

  it("nao reconecta depois de desmontar", () => {
    const { unmount } = montar("c1");
    const socket = FakeWebSocket.instancias[0];

    act(() => socket.abrir());
    unmount();

    act(() => {
      vi.advanceTimersByTime(60000);
    });
    expect(FakeWebSocket.instancias).toHaveLength(1);
  });

  it("zera o backoff apos reconectar", () => {
    const { unmount } = montar("c1");
    const primeiro = FakeWebSocket.instancias[0];

    act(() => primeiro.abrir());
    act(() => primeiro.derrubar());
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const segundo = FakeWebSocket.instancias[1];

    act(() => segundo.abrir());
    act(() => segundo.derrubar());

    // 2a queda apos reconexao: espera volta a 1s (sem o reset seria 2s)
    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(FakeWebSocket.instancias).toHaveLength(2);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(FakeWebSocket.instancias).toHaveLength(3);
    unmount();
  });

  it("expoe o status da conexao", () => {
    const { result, unmount } = montar("c1");
    const socket = FakeWebSocket.instancias[0];

    expect(result.current.status).toBe("reconectando");

    act(() => socket.abrir());
    expect(result.current.status).toBe("conectado");

    act(() => socket.derrubar());
    expect(result.current.status).toBe("reconectando");
    unmount();
  });

  it("invalida o roteamento ao receber diagnostico", () => {
    const { client, unmount } = montar("c1");
    const invalidar = vi.spyOn(client, "invalidateQueries");
    const socket = FakeWebSocket.instancias[0];

    act(() => socket.abrir());
    act(() =>
      socket.onmessage?.({
        data: JSON.stringify({ event: "diagnostico", data: { chat_id: "c1" } }),
      })
    );

    expect(invalidar).toHaveBeenCalledWith({
      queryKey: ["roteamento", "c1"],
    });
    unmount();
  });
});

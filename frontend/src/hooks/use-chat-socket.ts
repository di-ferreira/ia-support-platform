"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { proximoBackoff } from "@/lib/reconnect";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001";

/** Status da conexão exposto para a UI (gap 07-3). */
export type StatusSocket = "conectado" | "reconectando";

/**
 * Invalidações centralizadas por evento (spec 07 §Cache e tempo real):
 * o cliente nunca atualiza estado local — invalida a query e relê.
 */
const INVALIDACOES: Record<string, (chatId: string) => string[][]> = {
  nova_mensagem: (id) => [
    ["mensagens", id],
    ["chats"],
    ["chat", id],
  ],
  status_update: (id) => [
    ["chat", id],
    ["chats"],
    ["kanban"],
  ],
  chat_atualizado: (id) => [
    ["chat", id],
    ["chats"],
    ["kanban"],
  ],
  diagnostico: (id) => [
    ["roteamento", id],
    ["chat", id],
    ["chats"],
  ],
};

export function useChatSocket(chatId: string | number | null) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<StatusSocket>("reconectando");

  useEffect(() => {
    if (!chatId) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    let encerrado = false;
    let tentativas = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const conectar = () => {
      if (encerrado) return;

      const ws = new WebSocket(`${WS_BASE}/ws/chat/${chatId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (wsRef.current !== ws) return;
        tentativas = 0;
        setStatus("conectado");
        // Envia o token como primeira mensagem (evita expor em query string/logs)
        ws.send(JSON.stringify({ token }));
      };

      ws.onmessage = (event) => {
        let msg: { event?: string; data?: { chat_id?: string | number } };
        try {
          msg = JSON.parse(String(event.data));
        } catch {
          return; // ignora mensagens malformadas
        }
        const invalidar = INVALIDACOES[msg.event ?? ""];
        if (!invalidar) return;
        const id = String(msg.data?.chat_id ?? chatId);
        for (const chave of invalidar(id)) {
          queryClient.invalidateQueries({ queryKey: chave });
        }
      };

      ws.onclose = () => {
        if (encerrado || wsRef.current !== ws) return;
        setStatus("reconectando");
        const espera = proximoBackoff(tentativas);
        tentativas += 1;
        timer = setTimeout(conectar, espera);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    conectar();

    return () => {
      encerrado = true;
      if (timer) clearTimeout(timer);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [chatId, queryClient]);

  return { status };
}

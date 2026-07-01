"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001";

export function useChatSocket(chatId: number | null) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!chatId) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const url = `${WS_BASE}/ws/chat/${chatId}?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`[WS] Connected to chat ${chatId}`);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const eventName = msg.event || "unknown";

        if (eventName === "nova_mensagem" && msg.data?.chat_id) {
          queryClient.invalidateQueries({ queryKey: ["mensagens", msg.data.chat_id] });
          queryClient.invalidateQueries({ queryKey: ["chats"] });
          queryClient.invalidateQueries({ queryKey: ["chat", msg.data.chat_id] });
        }

        if (eventName === "status_update" && msg.data?.chat_id) {
          queryClient.invalidateQueries({ queryKey: ["chat", msg.data.chat_id] });
          queryClient.invalidateQueries({ queryKey: ["chats"] });
        }

        if (eventName === "diagnostico" && msg.data?.chat_id) {
          queryClient.invalidateQueries({ queryKey: ["chat", msg.data.chat_id] });
          queryClient.invalidateQueries({ queryKey: ["chats"] });
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      console.log(`[WS] Disconnected from chat ${chatId}`);
    };

    ws.onerror = () => {
      ws.close();
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [chatId, queryClient]);
}

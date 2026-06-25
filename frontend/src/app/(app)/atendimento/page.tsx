"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { useState } from "react";

export default function AtendimentoPage() {
  const queryClient = useQueryClient();
  const [chatAtivo, setChatAtivo] = useState<number | null>(null);
  const [novaMsg, setNovaMsg] = useState("");

  const { data: chats } = useQuery({
    queryKey: ["chats"],
    queryFn: () => api.get<any[]>("/chats"),
    refetchInterval: 10000,
  });

  const { data: mensagens } = useQuery({
    queryKey: ["mensagens", chatAtivo],
    queryFn: () => api.get<any[]>(`/chats/${chatAtivo}/mensagens`),
    enabled: !!chatAtivo,
    refetchInterval: 5000,
  });

  const { data: chatDetail } = useQuery({
    queryKey: ["chat", chatAtivo],
    queryFn: () => api.get<any>(`/chats/${chatAtivo}`),
    enabled: !!chatAtivo,
  });

  const sendMsg = useMutation({
    mutationFn: (conteudo: string) =>
      api.post(`/chats/${chatAtivo}/mensagens`, {
        remetente: "atendente",
        tipo: "texto",
        conteudo,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mensagens", chatAtivo] });
      setNovaMsg("");
    },
  });

  const statusLabels: Record<string, string> = {
    NOVO: "Novo",
    IA_ANALISANDO: "IA Analisando",
    AGUARDANDO_HUMANO_COM_SOLUCAO: "Com Solução",
    AGUARDANDO_HUMANO_SEM_SOLUCAO: "Sem Solução",
    EM_ATENDIMENTO: "Em Atendimento",
    AGUARDANDO_CLIENTE: "Aguardando Cliente",
    RESOLVIDO: "Resolvido",
    ENCERRADO: "Encerrado",
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Inbox */}
      <div className="w-80 flex flex-col rounded-lg border bg-white">
        <div className="border-b p-4">
          <h2 className="font-semibold text-gray-900">Conversas</h2>
        </div>
        <div className="flex-1 overflow-auto">
          {chats?.map((chat: any) => (
            <button
              key={chat.id}
              onClick={() => setChatAtivo(chat.id)}
              className={`w-full border-b p-4 text-left transition-colors hover:bg-gray-50 ${
                chatAtivo === chat.id ? "bg-primary-50 border-l-4 border-l-primary-500" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-900">{chat.cliente_nome || `Cliente #${chat.cliente_id}`}</p>
                <Badge
                  variant={
                    chat.prioridade === "urgente" || chat.prioridade === "alta"
                      ? "danger"
                      : "neutral"
                  }
                  className="text-[10px]"
                >
                  {chat.prioridade}
                </Badge>
              </div>
              <div className="mt-1 flex items-center gap-2">
                <span className="text-xs text-gray-500">{statusLabels[chat.status] || chat.status}</span>
                {chat.solucao_sugerida_ia && <Bot className="h-3 w-3 text-green-500" />}
              </div>
            </button>
          ))}
          {(!chats || chats.length === 0) && (
            <p className="p-4 text-sm text-gray-400 text-center">Nenhuma conversa</p>
          )}
        </div>
      </div>

      {/* Chat */}
      <div className="flex flex-1 flex-col rounded-lg border bg-white">
        {chatAtivo ? (
          <>
            <div className="border-b p-4">
              <h3 className="font-semibold text-gray-900">
                {chatDetail?.cliente_nome || `Cliente #${chatDetail?.cliente_id}`}
              </h3>
              <Badge>{statusLabels[chatDetail?.status] || chatDetail?.status}</Badge>
            </div>
            <div className="flex-1 overflow-auto space-y-3 p-4">
              {mensagens?.map((msg: any) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.remetente === "atendente" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg px-4 py-2 text-sm ${
                      msg.remetente === "atendente"
                        ? "bg-primary-500 text-white"
                        : msg.remetente === "ia"
                        ? "bg-green-100 text-green-900"
                        : "bg-gray-100 text-gray-900"
                    }`}
                  >
                    <div className="flex items-center gap-1 mb-1">
                      {msg.remetente === "ia" ? (
                        <Bot className="h-3 w-3" />
                      ) : msg.remetente === "atendente" ? (
                        <User className="h-3 w-3" />
                      ) : null}
                      <span className="text-[10px] opacity-70 capitalize">{msg.remetente}</span>
                    </div>
                    <p>{msg.conteudo}</p>
                  </div>
                </div>
              ))}
              {(!mensagens || mensagens.length === 0) && (
                <p className="text-sm text-gray-400 text-center py-8">Nenhuma mensagem ainda</p>
              )}
            </div>
            <div className="border-t p-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (novaMsg.trim()) sendMsg.mutate(novaMsg);
                }}
                className="flex gap-2"
              >
                <input
                  className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Digite sua mensagem..."
                  value={novaMsg}
                  onChange={(e) => setNovaMsg(e.target.value)}
                />
                <Button type="submit" size="sm" disabled={!novaMsg.trim()}>
                  {sendMsg.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-gray-400">Selecione uma conversa</p>
          </div>
        )}
      </div>

      {/* IA Summary Panel */}
      {chatDetail && (
        <div className="w-72 flex flex-col rounded-lg border bg-white">
          <div className="border-b p-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Bot className="h-4 w-4 text-green-500" /> IA Diagnóstico
            </h3>
          </div>
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {chatDetail.resumo_problema ? (
              <>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">Resumo</p>
                  <p className="mt-1 text-sm text-gray-900">{chatDetail.resumo_problema}</p>
                </div>
                {chatDetail.causa_provavel && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Causa Provável</p>
                    <p className="mt-1 text-sm text-gray-900">{chatDetail.causa_provavel}</p>
                  </div>
                )}
                {chatDetail.solucao_sugerida_ia && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Solução Sugerida</p>
                    <p className="mt-1 text-sm text-green-700">{chatDetail.solucao_sugerida_ia}</p>
                  </div>
                )}
                {chatDetail.nivel_confianca_ia !== null && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Confiança</p>
                    <div className="mt-1 h-2 rounded-full bg-gray-100">
                      <div
                        className="h-2 rounded-full bg-green-500"
                        style={{ width: `${Math.round((chatDetail.nivel_confianca_ia || 0) * 100)}%` }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      {Math.round((chatDetail.nivel_confianca_ia || 0) * 100)}%
                    </p>
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">IA ainda não analisou este chamado</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

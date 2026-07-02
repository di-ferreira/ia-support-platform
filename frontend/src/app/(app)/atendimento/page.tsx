"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/auth-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Send, Bot, User, Loader2, UserPlus, X } from "lucide-react";
import { useState } from "react";
import { useChatSocket } from "@/hooks/use-chat-socket";

export default function AtendimentoPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [chatAtivo, setChatAtivo] = useState<number | null>(null);
  const [novaMsg, setNovaMsg] = useState("");

  useChatSocket(chatAtivo);

  const { data: iaSettings } = useQuery({
    queryKey: ["settings", "ia-name"],
    queryFn: () => api.get<{ name: string }>("/settings/ia-name"),
    staleTime: 600000,
  });
  const iaName = iaSettings?.name || "EMSoft IA";

  const { data: chats } = useQuery({
    queryKey: ["chats"],
    queryFn: () => api.get<any[]>("/chats"),
    refetchInterval: 30000,
  });

  const { data: mensagens } = useQuery({
    queryKey: ["mensagens", chatAtivo],
    queryFn: () => api.get<any[]>(`/chats/${chatAtivo}/mensagens`),
    enabled: !!chatAtivo,
    refetchInterval: 30000,
  });

  const { data: chatDetail } = useQuery({
    queryKey: ["chat", chatAtivo],
    queryFn: () => api.get<any>(`/chats/${chatAtivo}`),
    enabled: !!chatAtivo,
  });

  const [erroMsg, setErroMsg] = useState("");

  const prioridadeLabels: Record<string, string> = {
    baixa: "Baixa",
    media: "Média",
    alta: "Alta",
    urgente: "Urgente",
  };

  const updatePrioridade = useMutation({
    mutationFn: (prioridade: string) =>
      api.patch(`/chats/${chatAtivo}/prioridade`, { prioridade }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat", chatAtivo] });
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      setErroMsg("");
    },
    onError: (err: any) => {
      setErroMsg(err?.message || "Erro ao alterar prioridade");
    },
  });

  const updateStatus = useMutation({
    mutationFn: (status: string) =>
      api.patch(`/chats/${chatAtivo}/status`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat", chatAtivo] });
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      setErroMsg("");
    },
    onError: (err: any) => {
      setErroMsg(err?.message || "Erro ao alterar status");
    },
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
      setErroMsg("");
    },
    onError: (err: any) => {
      setErroMsg(err?.message || "Erro ao enviar mensagem");
    },
  });

  const [transferModalOpen, setTransferModalOpen] = useState(false);
  const [transferTab, setTransferTab] = useState<"atendente" | "grupo">("atendente");
  const [transferAtendenteId, setTransferAtendenteId] = useState<number | null>(null);
  const [transferSetor, setTransferSetor] = useState("");

  const { data: atendentes } = useQuery({
    queryKey: ["atendentes"],
    queryFn: () => api.get<any[]>("/atendentes/ativos"),
    enabled: transferModalOpen,
  });

  const pegarChat = useMutation({
    mutationFn: () => api.patch(`/chats/${chatAtivo}/pegar`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      queryClient.invalidateQueries({ queryKey: ["chat", chatAtivo] });
      setErroMsg("");
    },
    onError: (err: any) => setErroMsg(err?.message || "Erro ao pegar chamado"),
  });

  const transferirChat = useMutation({
    mutationFn: (atendente_id: number) =>
      api.patch(`/chats/${chatAtivo}/transferir`, { atendente_id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      queryClient.invalidateQueries({ queryKey: ["chat", chatAtivo] });
      setTransferModalOpen(false);
      setErroMsg("");
    },
    onError: (err: any) => setErroMsg(err?.message || "Erro ao transferir"),
  });

  const transferirGrupo = useMutation({
    mutationFn: (setor: string) =>
      api.patch(`/chats/${chatAtivo}/transferir-grupo`, { setor }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chats"] });
      queryClient.invalidateQueries({ queryKey: ["chat", chatAtivo] });
      setTransferModalOpen(false);
      setErroMsg("");
    },
    onError: (err: any) => setErroMsg(err?.message || "Erro ao transferir para grupo"),
  });

  const setoresDisponiveis = ["atendimento", "supervisao", "programadores"];

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
              {chat.ultima_mensagem && (
                <p className="mt-1 truncate text-xs text-gray-400">{chat.ultima_mensagem}</p>
              )}
              {!chat.atendente_id && (
                <div className="mt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 text-xs gap-1"
                    onClick={(e) => {
                      e.stopPropagation();
                      setChatAtivo(chat.id);
                      pegarChat.mutate();
                    }}
                    disabled={pegarChat.isPending}
                  >
                    <UserPlus className="h-3 w-3" /> Pegar
                  </Button>
                </div>
              )}
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
            <div className="border-b p-4 space-y-2">
              <h3 className="font-semibold text-gray-900">
                {chatDetail?.cliente_nome || `Cliente #${chatDetail?.cliente_id}`}
              </h3>
              <div className="flex items-center gap-2">
                <select
                  value={chatDetail?.status || ""}
                  onChange={(e) => updateStatus.mutate(e.target.value)}
                  className="text-xs rounded border border-gray-300 bg-white px-2 py-1 text-gray-700"
                >
                  {Object.entries(statusLabels).map(([key, label]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </select>
                <select
                  value={chatDetail?.prioridade || "media"}
                  onChange={(e) => updatePrioridade.mutate(e.target.value)}
                  className={`text-xs rounded border bg-white px-2 py-1 ${
                    chatDetail?.prioridade === "urgente" || chatDetail?.prioridade === "alta"
                      ? "border-red-300 text-red-700"
                      : "border-gray-300 text-gray-700"
                  }`}
                >
                  {Object.entries(prioridadeLabels).map(([key, label]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </select>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 text-xs"
                  onClick={() => setTransferModalOpen(true)}
                >
                  Transferir
                </Button>
                {chatDetail?.setor_alvo && (
                  <Badge variant="warning" className="text-[10px]">
                    📋 {chatDetail.setor_alvo}
                  </Badge>
                )}
              </div>
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
                      {msg.remetente === "ia" ? <Bot className="h-3 w-3" /> : null}
                      {msg.remetente === "atendente" ? <User className="h-3 w-3" /> : null}
                      <span className="text-[10px] opacity-70">
                        {msg.remetente === "atendente"
                          ? user?.nome || "Atendente"
                          : msg.remetente === "ia"
                          ? iaName
                          : chatDetail?.cliente_nome || "Cliente"}
                      </span>
                    </div>
                    <p>{msg.conteudo}</p>
                    <span className="text-[10px] opacity-50 block mt-1">
                      {new Date(msg.created_at).toLocaleTimeString("pt-BR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
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

      {/* Error feedback */}
      {erroMsg && (
        <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 rounded-lg bg-red-500 text-white px-4 py-2 text-sm shadow-lg">
          {erroMsg}
        </div>
      )}

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

      {/* Transfer Modal */}
      {transferModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-96 rounded-lg bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Transferir Chamado</h3>
              <button onClick={() => setTransferModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setTransferTab("atendente")}
                className={`px-3 py-1 text-sm rounded ${
                  transferTab === "atendente" ? "bg-primary-100 text-primary-700" : "text-gray-500"
                }`}
              >
                Para Atendente
              </button>
              <button
                onClick={() => setTransferTab("grupo")}
                className={`px-3 py-1 text-sm rounded ${
                  transferTab === "grupo" ? "bg-primary-100 text-primary-700" : "text-gray-500"
                }`}
              >
                Para Grupo
              </button>
            </div>

            {transferTab === "atendente" ? (
              <div className="space-y-2 max-h-60 overflow-auto">
                {atendentes
                  ?.filter((a: any) => a.id !== user?.id)
                  .map((a: any) => (
                    <button
                      key={a.id}
                      onClick={() => {
                        setTransferAtendenteId(a.id);
                        transferirChat.mutate(a.id);
                      }}
                      disabled={transferirChat.isPending}
                      className="w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors"
                    >
                      <p className="text-sm font-medium text-gray-900">{a.nome}</p>
                      <p className="text-xs text-gray-500">{a.perfil}{a.setor ? ` · ${a.setor}` : ""}</p>
                    </button>
                  ))}
                {(!atendentes || atendentes.length === 0) && (
                  <p className="text-sm text-gray-400 text-center py-4">Nenhum atendente disponível</p>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {setoresDisponiveis.map((setor) => (
                  <button
                    key={setor}
                    onClick={() => transferirGrupo.mutate(setor)}
                    disabled={transferirGrupo.isPending}
                    className="w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors"
                  >
                    <p className="text-sm font-medium text-gray-900 capitalize">{setor}</p>
                    <p className="text-xs text-gray-500">Transferir para grupo {setor}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

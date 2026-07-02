"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/auth-store";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2, UserPlus, X } from "lucide-react";
import { useState } from "react";

const statusLabels: Record<string, string> = {
  NOVO: "Novos",
  IA_ANALISANDO: "IA Analisando",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "Com Solução",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "Sem Solução",
  EM_ATENDIMENTO: "Em Atendimento",
  AGUARDANDO_CLIENTE: "Aguardando Cliente",
  RESOLVIDO: "Resolvidos",
};

const setoresDisponiveis = ["atendimento", "supervisao", "programadores"];

export default function KanbanPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [transferModal, setTransferModal] = useState<{
    chatId: number;
    tab: "atendente" | "grupo";
  } | null>(null);
  const [pegarLoading, setPegarLoading] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["kanban"],
    queryFn: () => api.get<{ colunas: any[] }>("/kanban"),
    refetchInterval: 10000,
  });

  const { data: atendentes } = useQuery({
    queryKey: ["atendentes"],
    queryFn: () => api.get<any[]>("/atendentes/ativos"),
    enabled: !!transferModal,
  });

  const moveMutation = useMutation({
    mutationFn: ({ chatId, status }: { chatId: number; status: string }) =>
      api.patch(`/chats/${chatId}/status`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["kanban"] }),
  });

  const pegarMutation = useMutation({
    mutationFn: (chatId: number) => api.patch(`/chats/${chatId}/pegar`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      setPegarLoading(null);
    },
    onError: () => setPegarLoading(null),
  });

  const transferirMutation = useMutation({
    mutationFn: ({ chatId, atendente_id }: { chatId: number; atendente_id: number }) =>
      api.patch(`/chats/${chatId}/transferir`, { atendente_id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      setTransferModal(null);
    },
  });

  const transferirGrupoMutation = useMutation({
    mutationFn: ({ chatId, setor }: { chatId: number; setor: string }) =>
      api.patch(`/chats/${chatId}/transferir-grupo`, { setor }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kanban"] });
      setTransferModal(null);
    },
  });

  const handleDragStart = (e: React.DragEvent, chatId: number, currentStatus: string) => {
    e.dataTransfer.setData("text/plain", JSON.stringify({ chatId, currentStatus }));
  };

  const handleDrop = (e: React.DragEvent, targetStatus: string) => {
    e.preventDefault();
    const { chatId, currentStatus } = JSON.parse(e.dataTransfer.getData("text/plain"));
    if (currentStatus !== targetStatus) {
      moveMutation.mutate({ chatId, status: targetStatus });
    }
  };

  const colunas = data?.colunas || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kanban</h1>
          <p className="mt-1 text-sm text-gray-500">Gerencie o fluxo de atendimento</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 gap-4 overflow-x-auto">
        {colunas.map((col: any) => (
          <div
            key={col.status}
            className="flex flex-col rounded-lg bg-gray-100 min-h-[400px]"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => handleDrop(e, col.status)}
          >
            <div className="flex items-center justify-between p-3 border-b bg-white rounded-t-lg">
              <h3 className="text-sm font-semibold text-gray-700">{statusLabels[col.status] || col.status}</h3>
              <Badge variant="neutral">{col.cards.length}</Badge>
            </div>
            <div className="flex-1 space-y-2 p-2 overflow-auto">
              {col.cards.map((card: any) => (
                <Card
                  key={card.id}
                  className="cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow"
                  draggable
                  onDragStart={(e) => handleDragStart(e, card.id, col.status)}
                >
                  <CardContent className="p-3 space-y-2">
                    <div className="flex items-start justify-between">
                      <p className="text-sm font-medium text-gray-900">{card.cliente_nome}</p>
                      {!card.atendente_id && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-xs text-primary-600"
                          onClick={(e) => {
                            e.stopPropagation();
                            setPegarLoading(card.id);
                            pegarMutation.mutate(card.id);
                          }}
                          disabled={pegarLoading === card.id}
                        >
                          {pegarLoading === card.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <UserPlus className="h-3 w-3" />
                          )}
                        </Button>
                      )}
                    </div>
                    {card.resumo_problema && (
                      <p className="text-xs text-gray-500 line-clamp-2">{card.resumo_problema}</p>
                    )}
                    <div className="flex items-center justify-between">
                      <Badge
                        variant={
                          card.prioridade === "urgente" || card.prioridade === "alta"
                            ? "danger"
                            : card.prioridade === "media"
                            ? "warning"
                            : "neutral"
                        }
                      >
                        {card.prioridade}
                      </Badge>
                      {card.nivel_confianca_ia !== null && card.nivel_confianca_ia !== undefined && (
                        <span className="text-xs text-gray-400">
                          IA: {Math.round(card.nivel_confianca_ia * 100)}%
                        </span>
                      )}
                    </div>
                    {card.setor_alvo && (
                      <Badge variant="warning" className="text-[10px]">
                        📋 {card.setor_alvo}
                      </Badge>
                    )}
                    <div className="flex items-center justify-between">
                      {card.atendente_nome ? (
                        <span className="text-xs text-primary-600">👤 {card.atendente_nome}</span>
                      ) : (
                        <span className="text-xs text-gray-400">Sem atendente</span>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          setTransferModal({ chatId: card.id, tab: "atendente" });
                        }}
                      >
                        Transferir
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Transfer Modal */}
      {transferModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-96 rounded-lg bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Transferir Chamado</h3>
              <button onClick={() => setTransferModal(null)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setTransferModal({ ...transferModal, tab: "atendente" })}
                className={`px-3 py-1 text-sm rounded ${
                  transferModal.tab === "atendente" ? "bg-primary-100 text-primary-700" : "text-gray-500"
                }`}
              >
                Para Atendente
              </button>
              <button
                onClick={() => setTransferModal({ ...transferModal, tab: "grupo" })}
                className={`px-3 py-1 text-sm rounded ${
                  transferModal.tab === "grupo" ? "bg-primary-100 text-primary-700" : "text-gray-500"
                }`}
              >
                Para Grupo
              </button>
            </div>

            {transferModal.tab === "atendente" ? (
              <div className="space-y-2 max-h-60 overflow-auto">
                {atendentes
                  ?.filter((a: any) => a.id !== user?.id)
                  .map((a: any) => (
                    <button
                      key={a.id}
                      onClick={() =>
                        transferirMutation.mutate({ chatId: transferModal.chatId, atendente_id: a.id })
                      }
                      disabled={transferirMutation.isPending}
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
                    onClick={() =>
                      transferirGrupoMutation.mutate({ chatId: transferModal.chatId, setor })
                    }
                    disabled={transferirGrupoMutation.isPending}
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

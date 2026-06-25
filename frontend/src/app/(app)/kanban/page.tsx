"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

const statusLabels: Record<string, string> = {
  NOVO: "Novos",
  IA_ANALISANDO: "IA Analisando",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "Com Solução",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "Sem Solução",
  EM_ATENDIMENTO: "Em Atendimento",
  AGUARDANDO_CLIENTE: "Aguardando Cliente",
  RESOLVIDO: "Resolvidos",
};

export default function KanbanPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["kanban"],
    queryFn: () => api.get<{ colunas: any[] }>("/kanban"),
    refetchInterval: 10000,
  });

  const moveMutation = useMutation({
    mutationFn: ({ chatId, status }: { chatId: number; status: string }) =>
      api.patch(`/chats/${chatId}/status`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["kanban"] }),
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
                    <p className="text-sm font-medium text-gray-900">{card.cliente_nome}</p>
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
                    {card.atendente_nome && (
                      <p className="text-xs text-primary-600">👤 {card.atendente_nome}</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

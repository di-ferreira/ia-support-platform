"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MessageSquare, Bot, Clock, TrendingUp, AlertTriangle, Users } from "lucide-react";

const kpis = [
  { label: "Total de Chamados", key: "total", icon: MessageSquare, color: "text-blue-600" },
  { label: "Resolvidos por IA", key: "ia_resolvidos", icon: Bot, color: "text-green-600" },
  { label: "Transbordo Humano", key: "transbordo", icon: Users, color: "text-orange-600" },
  { label: "Tempo Médio", key: "tempo_medio", icon: Clock, color: "text-purple-600" },
  { label: "Taxa de Resolução IA", key: "taxa_ia", icon: TrendingUp, color: "text-primary-600" },
  { label: "Críticos", key: "criticos", icon: AlertTriangle, color: "text-red-600" },
];

export default function DashboardPage() {
  const { data: chats } = useQuery({
    queryKey: ["chats"],
    queryFn: () => api.get<any[]>("/chats"),
  });

  const { data: kanban } = useQuery({
    queryKey: ["kanban"],
    queryFn: () => api.get<{ colunas: any[] }>("/kanban"),
  });

  const total = chats?.length || 0;
  const criticos = chats?.filter((c: any) => c.status === "AGUARDANDO_HUMANO_SEM_SOLUCAO").length || 0;
  const ia_resolvidos = chats?.filter((c: any) => c.status === "RESOLVIDO").length || 0;
  const taxa_ia = total > 0 ? Math.round((ia_resolvidos / total) * 100) : 0;

  const stats = { total, ia_resolvidos, transbordo: total - ia_resolvidos, tempo_medio: "—", taxa_ia: `${taxa_ia}%`, criticos };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Visão geral do atendimento</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpis.map((kpi) => (
          <Card key={kpi.key}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{kpi.label}</p>
                  <p className="mt-1 text-3xl font-bold text-gray-900">
                    {stats[kpi.key as keyof typeof stats]}
                  </p>
                </div>
                <kpi.icon className={`h-10 w-10 ${kpi.color} opacity-20`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>Chamados por Status</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3">
              {kanban?.colunas?.map((col: any) => (
                <div key={col.status} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{col.label}</span>
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-32 rounded-full bg-gray-100">
                      <div
                        className="h-2 rounded-full bg-primary-500"
                        style={{ width: `${total > 0 ? (col.cards.length / total) * 100 : 0}%` }}
                      />
                    </div>
                    <Badge variant={col.cards.length > 0 ? "primary" : "neutral"}>
                      {col.cards.length}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Chamados Recentes</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3">
              {chats?.slice(0, 5).map((chat: any) => (
                <div key={chat.id} className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{chat.cliente_nome || `Cliente #${chat.cliente_id}`}</p>
                    <p className="text-xs text-gray-500">{chat.status?.replace(/_/g, " ")}</p>
                  </div>
                  <Badge variant={chat.prioridade === "alta" || chat.prioridade === "urgente" ? "danger" : "neutral"}>
                    {chat.prioridade}
                  </Badge>
                </div>
              ))}
              {(!chats || chats.length === 0) && (
                <p className="text-sm text-gray-400 text-center py-4">Nenhum chamado recente</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

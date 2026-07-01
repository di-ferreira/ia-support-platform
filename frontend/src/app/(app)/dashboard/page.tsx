"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import {
  MessageSquare, Bot, Users, Clock, TrendingUp, AlertTriangle, Brain,
} from "lucide-react";

const KPI_COLORS = [
  "text-blue-600", "text-green-600", "text-orange-600", "text-purple-600",
  "text-primary-600", "text-red-600", "text-indigo-600", "text-teal-600",
];

const PIE_COLORS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#3b82f6", "#a855f7", "#14b8a6", "#6b7280",
];

const STATUS_LABELS: Record<string, string> = {
  NOVO: "Novo",
  IA_ANALISANDO: "IA Analisando",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "Com Solução",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "Sem Solução",
  EM_ATENDIMENTO: "Em Atendimento",
  AGUARDANDO_CLIENTE: "Aguardando Cliente",
  RESOLVIDO: "Resolvido",
  ENCERRADO: "Encerrado",
};

export default function DashboardPage() {
  const { data: dash } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<any>("/dashboard"),
    refetchInterval: 30000,
  });

  const kpis = dash?.kpis;

  const kpiCards = kpis
    ? [
        { label: "Total de Chamados", value: kpis.total, icon: MessageSquare },
        { label: "Resolvidos por IA", value: kpis.ia_resolvidos, icon: Bot },
        { label: "Transbordo Humano", value: kpis.transbordo_humano, icon: Users },
        {
          label: "Tempo Médio Resposta",
          value: kpis.tempo_medio_resposta != null
            ? `${Math.round(kpis.tempo_medio_resposta / 60)} min`
            : "—",
          icon: Clock,
        },
        {
          label: "Taxa Resolução IA",
          value: `${Math.round(kpis.taxa_resolucao_ia * 100)}%`,
          icon: TrendingUp,
        },
        { label: "Críticos", value: kpis.criticos, icon: AlertTriangle },
        {
          label: "Confiança Média IA",
          value: kpis.confianca_media != null
            ? `${Math.round(kpis.confianca_media * 100)}%`
            : "—",
          icon: Brain,
        },
        { label: "Sugestões Feitas", value: kpis.sugestoes_feitas, icon: Brain },
      ]
    : [];

  const barData = (dash?.por_status || []).map((s: any) => ({
    name: STATUS_LABELS[s.status] || s.status,
    quantidade: s.quantidade,
  }));

  const pieData = barData.filter((d: any) => d.quantidade > 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Visão geral do atendimento</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((kpi, i) => (
          <Card key={kpi.label}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{kpi.label}</p>
                  <p className="mt-1 text-3xl font-bold text-gray-900">{kpi.value}</p>
                </div>
                <kpi.icon className={`h-10 w-10 ${KPI_COLORS[i]} opacity-20`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>Chamados por Status</CardTitle></CardHeader>
          <CardContent>
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="quantidade" fill="#063778" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">Nenhum chamado</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Distribuição</CardTitle></CardHeader>
          <CardContent>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="quantidade"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                  >
                    {pieData.map((_: any, i: number) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">Nenhum chamado</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Chamados Recentes</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-3">
            {dash?.recentes?.map((chat: any) => (
              <div key={chat.id} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {chat.cliente_nome || `Cliente #${chat.cliente_id}`}
                  </p>
                  <p className="text-xs text-gray-500">
                    {STATUS_LABELS[chat.status] || chat.status}
                  </p>
                </div>
                <Badge
                  variant={
                    chat.prioridade === "urgente" || chat.prioridade === "alta"
                      ? "danger"
                      : "neutral"
                  }
                >
                  {chat.prioridade}
                </Badge>
              </div>
            ))}
            {(!dash?.recentes || dash.recentes.length === 0) && (
              <p className="text-sm text-gray-400 text-center py-4">Nenhum chamado recente</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

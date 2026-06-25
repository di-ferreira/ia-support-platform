"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Bot, Brain, CheckCircle2, XCircle, TrendingUp } from "lucide-react";

export default function IaDashboardPage() {
  const { data: diagnosticos } = useQuery({
    queryKey: ["diagnosticos"],
    queryFn: () => api.get<any[]>("/chats"),
  });

  const { data: kanban } = useQuery({
    queryKey: ["kanban"],
    queryFn: () => api.get<{ colunas: any[] }>("/kanban"),
  });

  const totalChats = diagnosticos?.length || 0;
  const comSolucao = diagnosticos?.filter((c) => c.solucao_sugerida_ia).length || 0;
  const resolvidosIA = kanban?.colunas?.find((c) => c.status === "RESOLVIDO")?.cards?.length || 0;
  const taxaResolucao = totalChats > 0 ? Math.round((resolvidosIA / totalChats) * 100) : 0;
  const confiancaMedia = diagnosticos?.reduce((acc: number, c: any) => acc + (c.nivel_confianca_ia || 0), 0) / (totalChats || 1);

  const kpis = [
    { label: "Taxa de Resolução IA", value: `${taxaResolucao}%`, icon: Brain, color: "text-green-600" },
    { label: "Sugestões Feitas", value: comSolucao, icon: Bot, color: "text-blue-600" },
    { label: "Resolvidos pela IA", value: resolvidosIA, icon: CheckCircle2, color: "text-green-600" },
    { label: "Confiança Média", value: `${Math.round(confiancaMedia * 100)}%`, icon: TrendingUp, color: "text-purple-600" },
    { label: "Sem Solução (Críticos)", value: diagnosticos?.filter((c) => c.status === "AGUARDANDO_HUMANO_SEM_SOLUCAO").length || 0, icon: XCircle, color: "text-red-600" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">IA Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Métricas de performance da inteligência artificial</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {kpis.map((kpi) => (
          <Card key={kpi.label}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{kpi.label}</p>
                  <p className="mt-1 text-2xl font-bold text-gray-900">{kpi.value}</p>
                </div>
                <kpi.icon className={`h-8 w-8 ${kpi.color} opacity-20`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle>Distribuição por Status</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-3">
            {kanban?.colunas?.map((col: any) => (
              <div key={col.status} className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{col.label}</span>
                <Badge variant={col.cards.length > 0 ? "primary" : "neutral"}>{col.cards.length}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

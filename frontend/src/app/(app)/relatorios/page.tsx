"use client";

import { Card, CardContent } from "@/components/ui/card";
import { BarChart3, FileText, Users, Bot, Clock, TrendingUp, PieChart, Download } from "lucide-react";

const reports = [
  { label: "Volume de Chamados", desc: "Chamados por período", icon: BarChart3 },
  { label: "SLA", desc: "Tempo de resposta e resolução", icon: Clock },
  { label: "CSAT / NPS", desc: "Satisfação do cliente", icon: TrendingUp },
  { label: "Performance da Equipe", desc: "Produtividade dos atendentes", icon: Users },
  { label: "Performance da IA", desc: "Taxa de resolução e precisão", icon: Bot },
  { label: "Por Categoria", desc: "Chamados por módulo do ERP", icon: PieChart },
  { label: "Tendências", desc: "Evolução diária/semanal", icon: TrendingUp },
  { label: "Relatório Completo", desc: "Exportar dados completos", icon: Download },
];

export default function RelatoriosPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Relatórios</h1>
        <p className="mt-1 text-sm text-gray-500">Análises e exportação de dados</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {reports.map((report) => (
          <Card key={report.label} className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6 space-y-3">
              <report.icon className="h-8 w-8 text-primary-500" />
              <div>
                <h3 className="font-semibold text-gray-900">{report.label}</h3>
                <p className="text-sm text-gray-500">{report.desc}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

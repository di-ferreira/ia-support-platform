"use client";

import { Card, CardContent } from "@/components/ui/card";
import { MessageSquare, Clock, Users, Bell, Tags, Bot, Puzzle, Settings as SettingsIcon } from "lucide-react";

const sections = [
  { label: "WhatsApp", desc: "Conexão Evolution API", icon: MessageSquare },
  { label: "SLA", desc: "Tempos por prioridade", icon: Clock },
  { label: "Equipe", desc: "Gerenciar atendentes", icon: Users },
  { label: "Notificações", desc: "Alertas e notificações", icon: Bell },
  { label: "Categorias", desc: "Tags e categorias de chamados", icon: Tags },
  { label: "IA", desc: "Modelo e prompt da IA", icon: Bot },
  { label: "Integrações", desc: "n8n, webhooks", icon: Puzzle },
  { label: "Gerais", desc: "Configurações gerais do sistema", icon: SettingsIcon },
];

export default function ConfiguracoesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configurações</h1>
        <p className="mt-1 text-sm text-gray-500">Gerencie as configurações do sistema</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {sections.map((section) => (
          <Card key={section.label} className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6 space-y-3">
              <section.icon className="h-8 w-8 text-primary-500" />
              <div>
                <h3 className="font-semibold text-gray-900">{section.label}</h3>
                <p className="text-sm text-gray-500">{section.desc}</p>
              </div>
              <div className="flex items-center gap-2 pt-2">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <span className="text-xs text-gray-400">Configurado</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

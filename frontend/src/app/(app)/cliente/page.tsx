"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Plus, Store } from "lucide-react";
import Link from "next/link";

export default function ClientePage() {
  const [search, setSearch] = useState("");
  const [clienteId, setClienteId] = useState<number | null>(null);

  const { data: clientes } = useQuery({
    queryKey: ["clientes", search],
    queryFn: () => api.get<any[]>("/clientes", { nome: search || undefined }),
  });

  const { data: cliente } = useQuery({
    queryKey: ["cliente", clienteId],
    queryFn: () => api.get<any>(`/clientes/${clienteId}`),
    enabled: !!clienteId,
  });

  const { data: lojas } = useQuery({
    queryKey: ["lojas", clienteId],
    queryFn: () => api.get<any[]>(`/clientes/${clienteId}/lojas`),
    enabled: !!clienteId,
  });

  const { data: chats } = useQuery({
    queryKey: ["chats", "cliente", clienteId],
    queryFn: () => api.get<any[]>("/chats", { cliente_id: clienteId }),
    enabled: !!clienteId,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Clientes</h1>
        <p className="mt-1 text-sm text-gray-500">CRM e gestão de clientes</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lista */}
        <Card className="lg:col-span-1">
          <CardContent className="p-4 space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <Input
                className="pl-9"
                placeholder="Buscar cliente..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="space-y-1 max-h-[600px] overflow-auto">
              {clientes?.map((c: any) => (
                <button
                  key={c.id}
                  onClick={() => setClienteId(c.id)}
                  className={`w-full rounded-lg p-3 text-left transition-colors hover:bg-gray-50 ${
                    clienteId === c.id ? "bg-primary-50 border border-primary-200" : "border border-transparent"
                  }`}
                >
                  <p className="text-sm font-medium text-gray-900">{c.nome}</p>
                  <p className="text-xs text-gray-500">{c.documento}</p>
                </button>
              ))}
              {(!clientes || clientes.length === 0) && (
                <p className="text-sm text-gray-400 text-center py-4">Nenhum cliente encontrado</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Detalhe */}
        <Card className="lg:col-span-2">
          <CardContent className="p-6">
            {cliente ? (
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{cliente.nome}</h2>
                  <p className="text-sm text-gray-500">Documento: {cliente.documento}</p>
                  {cliente.versao_erp && (
                    <Badge variant="info">ERP v{cliente.versao_erp}</Badge>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Email</p>
                    <p className="text-sm text-gray-900">{cliente.email || "—"}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Telefone</p>
                    <p className="text-sm text-gray-900">{cliente.telefone || "—"}</p>
                  </div>
                </div>

                {lojas && lojas.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase mb-2 flex items-center gap-1">
                      <Store className="h-3 w-3" /> Lojas / Filiais
                    </p>
                    <div className="space-y-2">
                      {lojas.map((loja: any) => (
                        <div key={loja.id} className="rounded-lg border p-3">
                          <p className="text-sm font-medium">{loja.nome}</p>
                          {loja.documento && <p className="text-xs text-gray-500">{loja.documento}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {chats && chats.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase mb-2">Chamados Recentes</p>
                    <div className="space-y-2">
                      {chats.map((chat: any) => (
                        <div key={chat.id} className="rounded-lg border p-3 flex items-center justify-between">
                          <div>
                            <p className="text-sm text-gray-900">{chat.resumo_problema || "Sem resumo"}</p>
                            <p className="text-xs text-gray-500">{chat.status?.replace(/_/g, " ")}</p>
                          </div>
                          <Badge variant={chat.prioridade === "alta" || chat.prioridade === "urgente" ? "danger" : "neutral"}>
                            {chat.prioridade}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-64">
                <p className="text-gray-400">Selecione um cliente para ver os detalhes</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

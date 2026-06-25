"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen, FileText, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useState } from "react";

const categoryLabels: Record<string, string> = {
  fiscal: "Fiscal",
  estoque: "Estoque",
  compras: "Compras",
  vendas: "Vendas",
  financeiro: "Financeiro",
};

const categoryColors: Record<string, "primary" | "success" | "warning" | "info" | "neutral" | "danger"> = {
  fiscal: "danger",
  estoque: "success",
  compras: "warning",
  vendas: "info",
  financeiro: "primary",
};

export default function ConhecimentoPage() {
  const [categoria, setCategoria] = useState<string | undefined>();
  const [search, setSearch] = useState("");

  const { data: artigos } = useQuery({
    queryKey: ["knowledge-base", categoria],
    queryFn: () => api.get<any[]>("/knowledge-base", { categoria: categoria || undefined }),
  });

  const filtered = artigos?.filter((a) =>
    a.titulo.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Base de Conhecimento</h1>
        <p className="mt-1 text-sm text-gray-500">Artigos e documentação do ERP</p>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <Input className="pl-9" placeholder="Buscar artigos..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setCategoria(undefined)}
          className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
            !categoria ? "bg-primary-500 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Todas
        </button>
        {Object.entries(categoryLabels).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setCategoria(key)}
            className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
              categoria === key ? "bg-primary-500 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered?.map((artigo: any) => (
          <Card key={artigo.id} className="hover:shadow-md transition-shadow">
            <CardContent className="p-5 space-y-3">
              <div className="flex items-start justify-between">
                <FileText className="h-8 w-8 text-primary-500" />
                <Badge variant={categoryColors[artigo.categoria] || "neutral"}>
                  {categoryLabels[artigo.categoria] || artigo.categoria}
                </Badge>
              </div>
              <h3 className="font-semibold text-gray-900">{artigo.titulo}</h3>
              {artigo.conteudo && (
                <p className="text-sm text-gray-500 line-clamp-3">{artigo.conteudo}</p>
              )}
              {artigo.tipo_arquivo && (
                <p className="text-xs text-gray-400">Tipo: {artigo.tipo_arquivo}</p>
              )}
            </CardContent>
          </Card>
        ))}
        {(!filtered || filtered.length === 0) && (
          <div className="col-span-full text-center py-12">
            <BookOpen className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-2 text-sm text-gray-400">Nenhum artigo encontrado</p>
          </div>
        )}
      </div>
    </div>
  );
}

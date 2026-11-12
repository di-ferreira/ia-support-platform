"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  GitBranch,
  Inbox,
  Loader2,
  Pencil,
  Plus,
  Power,
  PowerOff,
  Users,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/auth-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectItem } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";

type Departamento = {
  id: string;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
  ordem: number | null;
  recebe_transferencias: boolean;
  permite_atribuicao_automatica: boolean;
  created_at: string;
  updated_at: string;
};

type Atendente = {
  id: string;
  nome: string;
  email: string;
  perfil: string;
  setor?: string | null;
};

type Regra = {
  id: string;
  intencao: string;
  subintencao: string | null;
  categoria_erp: string | null;
  departamento_id: string;
  prioridade_regra: number;
  ativo: boolean;
};

type ChatFila = {
  id: string;
  cliente_id: string;
  cliente_nome: string | null;
  status: string;
  prioridade: string;
  atendente_id: string | null;
  departamento_id: string | null;
  resumo_problema: string | null;
  ultima_mensagem_em: string | null;
  created_at: string;
};

// Spec 10 §Processo de assunção: a fila lista chats sem atendente nos
// estados humanos (o backend já aplica o escopo RBAC em `GET /chats`).
const STATUS_HUMANOS = new Set([
  "AGUARDANDO_HUMANO_COM_SOLUCAO",
  "AGUARDANDO_HUMANO_SEM_SOLUCAO",
]);

const statusLabels: Record<string, string> = {
  AGUARDANDO_HUMANO_COM_SOLUCAO: "Com solução da IA",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "Sem solução da IA",
  NOVO: "Novo",
  IA_ANALISANDO: "IA analisando",
  EM_ATENDIMENTO: "Em atendimento",
  AGUARDANDO_CLIENTE: "Aguardando cliente",
  RESOLVIDO: "Resolvido",
  ENCERRADO: "Encerrado",
};

function mensagemErro(err: unknown): string {
  const e = err as { message?: string; detail?: string } | null;
  return e?.message || e?.detail || "Erro inesperado";
}

export default function DepartamentosPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAdmin = user?.perfil === "admin";
  const podeVerInativos = isAdmin || user?.perfil === "supervisor";
  const podeVerAtendentes = isAdmin || user?.perfil === "supervisor";

  const [incluirInativos, setIncluirInativos] = useState(false);
  const [selecionadoId, setSelecionadoId] = useState<string | null>(null);
  const [aba, setAba] = useState<"atendentes" | "regras" | "fila">("fila");
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Departamento | null>(null);
  const [aviso, setAviso] = useState<{ tipo: "erro" | "sucesso"; texto: string } | null>(
    null,
  );

  const departamentosQuery = useQuery({
    queryKey: ["departamentos", incluirInativos],
    queryFn: () =>
      api.get<Departamento[]>("/departamentos", {
        incluir_inativos: incluirInativos ? "true" : undefined,
      }),
  });

  const departamentos = useMemo(
    () => departamentosQuery.data ?? [],
    [departamentosQuery.data],
  );
  const selecionado = useMemo(
    () => departamentos.find((d) => d.id === selecionadoId) ?? null,
    [departamentos, selecionadoId],
  );

  const atendentesQuery = useQuery({
    queryKey: ["departamento-atendentes", selecionadoId],
    queryFn: () => api.get<Atendente[]>(`/departamentos/${selecionadoId}/atendentes`),
    enabled: !!selecionadoId && podeVerAtendentes,
  });

  const regrasQuery = useQuery({
    queryKey: ["departamento-regras", selecionadoId],
    queryFn: () => api.get<Regra[]>(`/departamentos/${selecionadoId}/regras`),
    enabled: !!selecionadoId,
  });

  const filaQuery = useQuery({
    queryKey: ["departamento-fila", selecionadoId],
    queryFn: () =>
      api.get<ChatFila[]>("/chats", {
        departamento_id: selecionadoId ?? undefined,
        limit: 200,
      }),
    enabled: !!selecionadoId,
    refetchInterval: 30000,
  });

  const fila = useMemo(
    () =>
      (filaQuery.data ?? []).filter(
        (c) => !c.atendente_id && STATUS_HUMANOS.has(c.status),
      ),
    [filaQuery.data],
  );

  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: ["departamentos"] });
    queryClient.invalidateQueries({ queryKey: ["departamento-atendentes"] });
    queryClient.invalidateQueries({ queryKey: ["departamento-regras"] });
    queryClient.invalidateQueries({ queryKey: ["departamento-fila"] });
    queryClient.invalidateQueries({ queryKey: ["chats"] });
  };

  const desativar = useMutation({
    mutationFn: (id: string) => api.delete(`/departamentos/${id}`),
    onSuccess: () => {
      setAviso({
        tipo: "sucesso",
        texto: "Departamento desativado. As referências existentes foram preservadas.",
      });
      invalidar();
    },
    onError: (err) => setAviso({ tipo: "erro", texto: mensagemErro(err) }),
  });

  const reativar = useMutation({
    mutationFn: (id: string) => api.patch(`/departamentos/${id}`, { ativo: true }),
    onSuccess: () => {
      setAviso({ tipo: "sucesso", texto: "Departamento reativado." });
      invalidar();
    },
    onError: (err) => setAviso({ tipo: "erro", texto: mensagemErro(err) }),
  });

  const assumir = useMutation({
    mutationFn: (chatId: string) => api.patch(`/chats/${chatId}/pegar`),
    onSuccess: () => {
      setAviso({ tipo: "sucesso", texto: "Chamado assumido." });
      invalidar();
      queryClient.invalidateQueries({ queryKey: ["chat"] });
    },
    onError: (err) => {
      setAviso({ tipo: "erro", texto: mensagemErro(err) });
      // Concorrência (spec 10): outro atendente venceu; recarrega a fila.
      queryClient.invalidateQueries({ queryKey: ["departamento-fila"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Departamentos</h1>
          <p className="mt-1 text-sm text-gray-500">
            Cadastro, associação de atendentes, regras de roteamento e fila por
            departamento.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {podeVerInativos && (
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500"
                checked={incluirInativos}
                onChange={(e) => setIncluirInativos(e.target.checked)}
              />
              Mostrar inativos
            </label>
          )}
          {isAdmin && (
            <Button
              onClick={() => {
                setEditando(null);
                setModalOpen(true);
              }}
            >
              <Plus className="h-4 w-4" /> Novo departamento
            </Button>
          )}
        </div>
      </div>

      {aviso && (
        <div
          role="status"
          className={`flex items-start justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${
            aviso.tipo === "erro"
              ? "border-danger/30 bg-danger/5 text-danger"
              : "border-success/30 bg-success/5 text-success"
          }`}
        >
          <span>{aviso.texto}</span>
          <button
            onClick={() => setAviso(null)}
            className="text-xs underline-offset-2 hover:underline"
          >
            fechar
          </button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
        <Card className="self-start">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 className="h-4 w-4 text-primary-500" /> Cadastro
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {departamentosQuery.isLoading && (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            )}

            {departamentosQuery.isError && (
              <ErrorState
                title="Não foi possível carregar os departamentos"
                description={mensagemErro(departamentosQuery.error)}
                onRetry={() => departamentosQuery.refetch()}
              />
            )}

            {!departamentosQuery.isLoading &&
              !departamentosQuery.isError &&
              departamentos.length === 0 && (
                <EmptyState
                  icon={Building2}
                  title="Nenhum departamento cadastrado"
                  description="Cadastre o primeiro departamento para iniciar o roteamento e a fila de atendimento."
                  action={
                    isAdmin ? (
                      <Button
                        size="sm"
                        onClick={() => {
                          setEditando(null);
                          setModalOpen(true);
                        }}
                      >
                        <Plus className="h-4 w-4" /> Criar departamento
                      </Button>
                    ) : undefined
                  }
                />
              )}

            {departamentos.map((depto) => (
              <button
                key={depto.id}
                onClick={() => setSelecionadoId(depto.id)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  selecionadoId === depto.id
                    ? "border-primary-400 bg-primary-50"
                    : "hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-gray-900">
                    {depto.nome}
                  </span>
                  <Badge variant={depto.ativo ? "success" : "neutral"}>
                    {depto.ativo ? "Ativo" : "Inativo"}
                  </Badge>
                </div>
                <p className="mt-1 font-mono text-xs text-gray-500">{depto.codigo}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {depto.recebe_transferencias && (
                    <Badge variant="info">Recebe transferências</Badge>
                  )}
                  {depto.permite_atribuicao_automatica && (
                    <Badge variant="primary">Atribuição automática</Badge>
                  )}
                  {depto.ordem !== null && (
                    <Badge variant="neutral">Ordem {depto.ordem}</Badge>
                  )}
                </div>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          {!selecionado ? (
            <CardContent className="py-16">
              <EmptyState
                icon={Building2}
                title="Selecione um departamento"
                description="Escolha um departamento na lista para ver atendentes, regras de roteamento e a fila de chamados."
              />
            </CardContent>
          ) : (
            <>
              <CardHeader className="flex flex-row items-start justify-between gap-3">
                <div>
                  <CardTitle>{selecionado.nome}</CardTitle>
                  <p className="mt-1 font-mono text-xs text-gray-500">
                    {selecionado.codigo}
                  </p>
                  {selecionado.descricao && (
                    <p className="mt-2 max-w-xl text-sm text-gray-600">
                      {selecionado.descricao}
                    </p>
                  )}
                </div>
                {isAdmin && (
                  <div className="flex shrink-0 items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditando(selecionado);
                        setModalOpen(true);
                      }}
                    >
                      <Pencil className="h-4 w-4" /> Editar
                    </Button>
                    {selecionado.ativo ? (
                      <Button
                        variant="danger"
                        size="sm"
                        disabled={desativar.isPending}
                        onClick={() => desativar.mutate(selecionado.id)}
                      >
                        {desativar.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <PowerOff className="h-4 w-4" />
                        )}
                        Desativar
                      </Button>
                    ) : (
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={reativar.isPending}
                        onClick={() => reativar.mutate(selecionado.id)}
                      >
                        {reativar.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Power className="h-4 w-4" />
                        )}
                        Reativar
                      </Button>
                    )}
                  </div>
                )}
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="flex gap-2 border-b pb-2">
                  {(
                    [
                      ["fila", "Fila", Inbox],
                      ["atendentes", "Atendentes", Users],
                      ["regras", "Regras", GitBranch],
                    ] as const
                  ).map(([valor, label, Icon]) => (
                    <button
                      key={valor}
                      onClick={() => setAba(valor)}
                      className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${
                        aba === valor
                          ? "bg-primary-100 text-primary-700"
                          : "text-gray-500 hover:bg-gray-50"
                      }`}
                    >
                      <Icon className="h-4 w-4" /> {label}
                    </button>
                  ))}
                </div>

                {aba === "fila" && (
                  <div className="space-y-3">
                    <p className="text-xs text-gray-500">
                      Chamados sem atendente em estados humanos. A assunção
                      valida atividade, departamento e concorrência no backend.
                    </p>

                    {filaQuery.isLoading && (
                      <div className="space-y-2">
                        {[0, 1, 2].map((i) => (
                          <Skeleton key={i} className="h-14 w-full" />
                        ))}
                      </div>
                    )}

                    {filaQuery.isError && (
                      <ErrorState
                        title="Não foi possível carregar a fila"
                        description={mensagemErro(filaQuery.error)}
                        onRetry={() => filaQuery.refetch()}
                      />
                    )}

                    {!filaQuery.isLoading && !filaQuery.isError && fila.length === 0 && (
                      <EmptyState
                        icon={Inbox}
                        title="Fila vazia"
                        description="Nenhum chamado aguardando assunção neste departamento."
                      />
                    )}

                    {fila.map((chat) => (
                      <div
                        key={chat.id}
                        className="flex items-start justify-between gap-3 rounded-lg border p-3"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-gray-900">
                            {chat.cliente_nome || `Cliente #${chat.cliente_id}`}
                          </p>
                          <p className="mt-0.5 text-xs text-gray-500">
                            {statusLabels[chat.status] || chat.status} ·{" "}
                            {chat.prioridade}
                          </p>
                          {chat.resumo_problema && (
                            <p className="mt-1 truncate text-xs text-gray-400">
                              {chat.resumo_problema}
                            </p>
                          )}
                        </div>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={assumir.isPending}
                          onClick={() => assumir.mutate(chat.id)}
                        >
                          Assumir
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {aba === "atendentes" && (
                  <div className="space-y-3">
                    {!podeVerAtendentes ? (
                      <p className="rounded-lg border border-dashed p-4 text-sm text-gray-500">
                        A lista de atendentes associados é visível para admin e
                        supervisor (spec 10). Seu departamento aparece no seu
                        perfil.
                      </p>
                    ) : atendentesQuery.isLoading ? (
                      <div className="space-y-2">
                        {[0, 1].map((i) => (
                          <Skeleton key={i} className="h-12 w-full" />
                        ))}
                      </div>
                    ) : atendentesQuery.isError ? (
                      <ErrorState
                        title="Não foi possível carregar os atendentes"
                        description={mensagemErro(atendentesQuery.error)}
                        onRetry={() => atendentesQuery.refetch()}
                      />
                    ) : (atendentesQuery.data ?? []).length === 0 ? (
                      <EmptyState
                        icon={Users}
                        title="Nenhum atendente associado"
                        description="Associe atendentes a este departamento no formulário de usuário."
                      />
                    ) : (
                      (atendentesQuery.data ?? []).map((a) => (
                        <div
                          key={a.id}
                          className="flex items-center justify-between rounded-lg border p-3"
                        >
                          <div>
                            <p className="text-sm font-medium text-gray-900">{a.nome}</p>
                            <p className="text-xs text-gray-500">{a.email}</p>
                          </div>
                          <Badge variant="neutral" className="capitalize">
                            {a.perfil}
                          </Badge>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {aba === "regras" && (
                  <div className="space-y-3">
                    <p className="text-xs text-gray-500">
                      Regras determinísticas de intenção → departamento. A
                      categoria ERP refina a regra, mas não define o
                      departamento (spec 10).
                    </p>
                    {regrasQuery.isLoading && (
                      <div className="space-y-2">
                        {[0, 1].map((i) => (
                          <Skeleton key={i} className="h-12 w-full" />
                        ))}
                      </div>
                    )}
                    {regrasQuery.isError && (
                      <ErrorState
                        title="Não foi possível carregar as regras"
                        description={mensagemErro(regrasQuery.error)}
                        onRetry={() => regrasQuery.refetch()}
                      />
                    )}
                    {!regrasQuery.isLoading &&
                      !regrasQuery.isError &&
                      (regrasQuery.data ?? []).length === 0 && (
                        <EmptyState
                          icon={GitBranch}
                          title="Nenhuma regra de roteamento"
                          description="Sem regras específicas, o roteamento usa fallback/atendimento geral."
                        />
                      )}
                    {(regrasQuery.data ?? []).map((regra) => (
                      <div key={regra.id} className="rounded-lg border p-3 text-sm">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="primary">{regra.intencao}</Badge>
                          {regra.subintencao && (
                            <Badge variant="info">{regra.subintencao}</Badge>
                          )}
                          {regra.categoria_erp && (
                            <Badge variant="neutral">
                              ERP: {regra.categoria_erp}
                            </Badge>
                          )}
                          <Badge variant={regra.ativo ? "success" : "neutral"}>
                            {regra.ativo ? "Ativa" : "Inativa"}
                          </Badge>
                        </div>
                        <p className="mt-2 text-xs text-gray-500">
                          Prioridade {regra.prioridade_regra}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </>
          )}
        </Card>
      </div>

      {modalOpen && (
        <DepartamentoFormModal
          departamento={editando}
          onClose={() => setModalOpen(false)}
          onSaved={(depto) => {
            setModalOpen(false);
            setSelecionadoId(depto.id);
            setAviso({
              tipo: "sucesso",
              texto: editando ? "Departamento atualizado." : "Departamento criado.",
            });
            invalidar();
          }}
        />
      )}
    </div>
  );
}

function DepartamentoFormModal({
  departamento,
  onClose,
  onSaved,
}: {
  departamento: Departamento | null;
  onClose: () => void;
  onSaved: (depto: Departamento) => void;
}) {
  const editando = !!departamento;
  const [codigo, setCodigo] = useState(departamento?.codigo || "");
  const [nome, setNome] = useState(departamento?.nome || "");
  const [descricao, setDescricao] = useState(departamento?.descricao || "");
  const [ordem, setOrdem] = useState(
    departamento?.ordem !== null && departamento?.ordem !== undefined
      ? String(departamento.ordem)
      : "",
  );
  const [recebeTransferencias, setRecebeTransferencias] = useState(
    departamento?.recebe_transferencias ?? true,
  );
  const [atribuicaoAutomatica, setAtribuicaoAutomatica] = useState(
    departamento?.permite_atribuicao_automatica ?? false,
  );
  const [ativo, setAtivo] = useState(departamento?.ativo ?? true);
  const [error, setError] = useState("");

  const salvar = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      editando
        ? api.patch<Departamento>(`/departamentos/${departamento.id}`, payload)
        : api.post<Departamento>("/departamentos", payload),
    onSuccess: onSaved,
    onError: (err) => setError(mensagemErro(err)),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!editando && !/^[a-z][a-z0-9_]*$/.test(codigo)) {
      setError(
        "Código inválido: use letras minúsculas, números e _ (começando por letra).",
      );
      return;
    }
    const payload: Record<string, unknown> = {
      nome,
      descricao: descricao || null,
      ordem: ordem === "" ? null : Number(ordem),
      recebe_transferencias: recebeTransferencias,
      permite_atribuicao_automatica: atribuicaoAutomatica,
    };
    if (editando) {
      payload.ativo = ativo;
    } else {
      payload.codigo = codigo.trim().toLowerCase();
    }
    salvar.mutate(payload);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="departamento-form-title"
      >
        <h2
          id="departamento-form-title"
          className="mb-4 text-lg font-semibold text-gray-900"
        >
          {editando ? "Editar departamento" : "Novo departamento"}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="depto-codigo"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Código
            </label>
            <Input
              id="depto-codigo"
              name="codigo"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              placeholder="suporte_tecnico"
              disabled={editando}
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Slug estável (letras minúsculas, números e _). Não pode ser
              alterado depois de referenciado por regras.
            </p>
          </div>
          <div>
            <label
              htmlFor="depto-nome"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Nome
            </label>
            <Input
              id="depto-nome"
              name="nome"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              required
            />
          </div>
          <div>
            <label
              htmlFor="depto-descricao"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Descrição
            </label>
            <textarea
              id="depto-descricao"
              name="descricao"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              rows={3}
              maxLength={1000}
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="depto-ordem"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Ordem
              </label>
              <Input
                id="depto-ordem"
                name="ordem"
                type="number"
                value={ordem}
                onChange={(e) => setOrdem(e.target.value)}
                placeholder="Opcional"
              />
            </div>
            {editando && (
              <div>
                <label
                  htmlFor="depto-ativo"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
                  Situação
                </label>
                <Select
                  id="depto-ativo"
                  valor={ativo ? "true" : "false"}
                  onValorChange={(valor) => setAtivo(valor === "true")}
                >
                  <SelectItem value="true">Ativo</SelectItem>
                  <SelectItem value="false">Inativo</SelectItem>
                </Select>
              </div>
            )}
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500"
              checked={recebeTransferencias}
              onChange={(e) => setRecebeTransferencias(e.target.checked)}
            />
            Recebe transferências de outros departamentos
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500"
              checked={atribuicaoAutomatica}
              onChange={(e) => setAtribuicaoAutomatica(e.target.checked)}
            />
            Permite atribuição automática de atendente
          </label>

          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={salvar.isPending}>
              {salvar.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {editando ? "Salvar" : "Criar"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

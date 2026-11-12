"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRightLeft,
  Bot,
  CheckCircle2,
  ClipboardCopy,
  ExternalLink,
  Inbox,
  LifeBuoy,
  Loader2,
  RefreshCw,
  Send,
  ShieldAlert,
  User,
  UserPlus,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useChatStore } from "@/lib/stores/chat-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectItem } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useChatSocket } from "@/hooks/use-chat-socket";

type Chat = {
  id: string;
  cliente_id: string;
  cliente_nome: string | null;
  status: string;
  prioridade: string;
  resumo_problema: string | null;
  solucao_sugerida_ia: string | null;
  nivel_confianca_ia: number | null;
  necessita_humano: boolean | null;
  atendente_id: string | null;
  departamento_id: string | null;
  setor_alvo: string | null;
  ultima_mensagem_em: string | null;
  ultima_mensagem: string | null;
  created_at: string;
};

type ChatDetail = Chat & {
  causa_provavel: string | null;
  whatsapp_number: string | null;
  updated_at: string;
};

type Departamento = {
  id: string;
  codigo: string;
  nome: string;
  ativo: boolean;
  recebe_transferencias: boolean;
};

type Atendente = {
  id: string;
  nome: string;
  perfil: string;
  setor: string | null;
  departamento_id: string | null;
};

type Roteamento = {
  chat_id: string;
  departamento_id: string | null;
  departamento_codigo: string | null;
  intencao: string | null;
  subintencao: string | null;
  categoria_erp: string | null;
  departamento_sugerido_codigo: string | null;
  motivo: string | null;
  confianca: number | null;
  artigos_consultados:
    | { id?: string; titulo?: string; score?: number; categoria?: string }[]
    | null;
  tem_diagnostico: boolean;
};

type IntegracaoChamado = {
  external_ticket_id?: string | null;
  external_url?: string | null;
  status?: string | null;
  assignee_kind?: string | null;
  external_assignee_id?: string | null;
  department_code?: string | null;
  external_status?: string | null;
  external_status_intent?: string | null;
  tentativas?: number | null;
  ultimo_erro?: string | null;
  ultima_tentativa_em?: string | null;
};

type EventoSync = {
  id: string;
  event_key: string;
  event_type: string;
  event_version?: number | null;
  status: string;
  tentativas: number;
  ultima_tentativa_em: string | null;
  ultimo_erro: string | null;
  next_attempt_at: string | null;
  ator: string | null;
  motivo: string | null;
  created_at: string;
};

type Sincronizacao = {
  chat_id: string;
  status_integracao?: string | null;
  pendencias: number;
  integracao?: IntegracaoChamado | null;
  eventos?: EventoSync[];
};

type Modal =
  | "transferir-departamento"
  | "atribuir"
  | "nao-resolveu"
  | "reprocessar"
  | null;

const statusLabels: Record<string, string> = {
  NOVO: "Novo",
  IA_ANALISANDO: "IA analisando",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "Aguardando humano (com solução)",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "Aguardando humano (sem solução)",
  EM_ATENDIMENTO: "Em atendimento",
  AGUARDANDO_CLIENTE: "Aguardando cliente",
  RESOLVIDO: "Resolvido",
  ENCERRADO: "Encerrado",
};

const statusVariants: Record<string, "primary" | "success" | "warning" | "danger" | "info" | "neutral"> = {
  NOVO: "info",
  IA_ANALISANDO: "primary",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "warning",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "warning",
  EM_ATENDIMENTO: "primary",
  AGUARDANDO_CLIENTE: "info",
  RESOLVIDO: "success",
  ENCERRADO: "neutral",
};

const prioridadeLabels: Record<string, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
  urgente: "Urgente",
};

const syncStatusVariants: Record<string, "primary" | "success" | "warning" | "danger" | "info" | "neutral"> = {
  PENDENTE: "warning",
  SINCRONIZADO: "success",
  ERRO: "danger",
  RECONCILIACAO: "info",
};

function mensagemErro(err: unknown): string {
  const e = err as { message?: string; detail?: string } | null;
  return e?.message || e?.detail || "Erro inesperado";
}

function humanizar(valor: string | null | undefined): string {
  if (!valor) return "—";
  return valor.replace(/_/g, " ");
}

export default function AtendimentoPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const { chatAtivo, setChatAtivo } = useChatStore();
  const chatAtivoId = chatAtivo?.id ?? null;
  const [novaMsg, setNovaMsg] = useState("");
  const [filtroDepartamento, setFiltroDepartamento] = useState("");
  const [modal, setModal] = useState<Modal>(null);
  const [erroModal, setErroModal] = useState("");
  const [aviso, setAviso] = useState<{ tipo: "erro" | "sucesso"; texto: string } | null>(
    null,
  );

  // Estados dos modais de ação
  const [deptoDestinoId, setDeptoDestinoId] = useState("");
  const [motivoTransferencia, setMotivoTransferencia] = useState("");
  const [preservarAtendente, setPreservarAtendente] = useState(false);
  const [atendenteDestinoId, setAtendenteDestinoId] = useState("");
  const [motivoAtribuicao, setMotivoAtribuicao] = useState("");
  const [motivoNaoResolveu, setMotivoNaoResolveu] = useState("");
  const [motivoReprocesso, setMotivoReprocesso] = useState("");

  const possuiGestao =
    user?.perfil === "admin" || user?.perfil === "supervisor";

  useChatSocket(chatAtivoId);

  const { data: iaSettings } = useQuery({
    queryKey: ["settings", "ia-name"],
    queryFn: () => api.get<{ name: string }>("/settings/ia-name"),
    staleTime: 600000,
  });
  const iaName = iaSettings?.name || "EMSoft IA";

  const departamentosQuery = useQuery({
    queryKey: ["departamentos", false],
    queryFn: () => api.get<Departamento[]>("/departamentos"),
    staleTime: 60000,
  });
  const departamentos = useMemo(
    () => departamentosQuery.data ?? [],
    [departamentosQuery.data],
  );

  const chatsQuery = useQuery({
    queryKey: ["chats", filtroDepartamento],
    queryFn: () =>
      api.get<Chat[]>("/chats", {
        departamento_id: filtroDepartamento || undefined,
      }),
    refetchInterval: 30000,
  });
  const chats = useMemo(() => chatsQuery.data ?? [], [chatsQuery.data]);

  const mensagensQuery = useQuery({
    queryKey: ["mensagens", chatAtivoId],
    queryFn: () => api.get<any[]>(`/chats/${chatAtivoId}/mensagens`),
    enabled: !!chatAtivoId,
    refetchInterval: 30000,
  });
  const mensagens = mensagensQuery.data ?? [];

  const chatDetailQuery = useQuery({
    queryKey: ["chat", chatAtivoId],
    queryFn: () => api.get<ChatDetail>(`/chats/${chatAtivoId}`),
    enabled: !!chatAtivoId,
  });
  const chatDetail = chatDetailQuery.data;

  const roteamentoQuery = useQuery({
    queryKey: ["roteamento", chatAtivoId],
    queryFn: () => api.get<Roteamento>(`/chats/${chatAtivoId}/roteamento`),
    enabled: !!chatAtivoId,
    retry: false,
  });
  const roteamento = roteamentoQuery.data;

  // Spec 03 L76: atendente só vê detalhes de sincronização do próprio chat.
  const podeVerSync =
    !!chatDetail && (possuiGestao || chatDetail.atendente_id === user?.id);

  const syncQuery = useQuery({
    queryKey: ["integracao", chatAtivoId],
    queryFn: () =>
      api.get<Sincronizacao>(`/integracoes/chamados/${chatAtivoId}`),
    enabled: !!chatAtivoId && podeVerSync,
    retry: false,
  });
  const sync = syncQuery.data;

  const integracaoStatusQuery = useQuery({
    queryKey: ["integracao-status"],
    queryFn: () =>
      api.get<{ ativa: boolean; motivo: string | null }>(
        "/integracoes/chamados/status",
      ),
    enabled: possuiGestao,
    staleTime: 60000,
  });

  const atendentesQuery = useQuery({
    queryKey: ["atendentes"],
    queryFn: () => api.get<Atendente[]>("/atendentes/ativos"),
    enabled: !!modal && modal === "atribuir",
  });
  const atendentes = atendentesQuery.data ?? [];

  const chatSelecionado = chatAtivo;

  const nomeDepartamento = (id: string | null | undefined) =>
    departamentos.find((d) => d.id === id)?.nome ?? null;

  const invalidarChat = (chatId: string | null) => {
    queryClient.invalidateQueries({ queryKey: ["chats"] });
    if (!chatId) return;
    queryClient.invalidateQueries({ queryKey: ["chat", chatId] });
    queryClient.invalidateQueries({ queryKey: ["roteamento", chatId] });
    queryClient.invalidateQueries({ queryKey: ["integracao", chatId] });
  };

  const abrirModal = (tipo: Modal) => {
    setErroModal("");
    setAviso(null);
    setModal(tipo);
  };

  const fecharModal = () => {
    setModal(null);
    setErroModal("");
  };

  const updatePrioridade = useMutation({
    mutationFn: (prioridade: string) =>
      api.patch(`/chats/${chatAtivoId}/prioridade`, { prioridade }),
    onSuccess: () => {
      invalidarChat(chatAtivoId);
      setAviso({ tipo: "sucesso", texto: "Prioridade atualizada." });
    },
    onError: (err) => setAviso({ tipo: "erro", texto: mensagemErro(err) }),
  });

  const updateStatus = useMutation({
    mutationFn: (status: string) =>
      api.patch(`/chats/${chatAtivoId}/status`, { status }),
    onSuccess: () => {
      invalidarChat(chatAtivoId);
      setAviso({ tipo: "sucesso", texto: "Status atualizado." });
    },
    onError: (err) => setAviso({ tipo: "erro", texto: mensagemErro(err) }),
  });

  const sendMsg = useMutation({
    mutationFn: (conteudo: string) =>
      api.post(`/chats/${chatAtivoId}/mensagens`, {
        remetente: "atendente",
        tipo: "texto",
        conteudo,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mensagens", chatAtivoId] });
      setNovaMsg("");
    },
    onError: (err) => setAviso({ tipo: "erro", texto: mensagemErro(err) }),
  });

  const pegarChat = useMutation({
    mutationFn: (chatId: string) => api.patch(`/chats/${chatId}/pegar`),
    onSuccess: (_data, chatId) => {
      invalidarChat(chatId);
      setAviso({ tipo: "sucesso", texto: "Chamado assumido por você." });
    },
    onError: (err) => {
      setAviso({ tipo: "erro", texto: mensagemErro(err) });
      // Concorrência: outro atendente venceu a assunção (spec 10).
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });

  const transferirDepartamento = useMutation({
    mutationFn: () =>
      api.patch(`/chats/${chatAtivoId}/transferir-departamento`, {
        departamento_id: deptoDestinoId,
        preservar_atendente_se_compativel: preservarAtendente,
        ...(motivoTransferencia.trim()
          ? { motivo: motivoTransferencia.trim() }
          : {}),
      }),
    onSuccess: () => {
      invalidarChat(chatAtivoId);
      fecharModal();
      setDeptoDestinoId("");
      setMotivoTransferencia("");
      setPreservarAtendente(false);
      setAviso({ tipo: "sucesso", texto: "Chamado transferido de departamento." });
    },
    onError: (err) => setErroModal(mensagemErro(err)),
  });

  const atribuirAtendente = useMutation({
    mutationFn: () =>
      api.patch(`/chats/${chatAtivoId}/atribuir-atendente`, {
        atendente_id: atendenteDestinoId,
        ...(motivoAtribuicao.trim() ? { motivo: motivoAtribuicao.trim() } : {}),
      }),
    onSuccess: () => {
      invalidarChat(chatAtivoId);
      fecharModal();
      setAtendenteDestinoId("");
      setMotivoAtribuicao("");
      setAviso({ tipo: "sucesso", texto: "Atendente atribuído." });
    },
    onError: (err) => setErroModal(mensagemErro(err)),
  });

  const confirmarResolucao = useMutation({
    mutationFn: () => api.patch(`/chats/${chatAtivoId}/confirmar-resolucao`),
    onSuccess: () => {
      invalidarChat(chatAtivoId);
      setAviso({ tipo: "sucesso", texto: "Resolução confirmada." });
    },
    onError: (err) => setAviso({ tipo: "erro", texto: mensagemErro(err) }),
  });

  const reabrir = useMutation({
    mutationFn: () =>
      api.patch(`/chats/${chatAtivoId}/reabrir`, {
        ...(motivoNaoResolveu.trim()
          ? { motivo: motivoNaoResolveu.trim() }
          : {}),
      }),
    onSuccess: () => {
      invalidarChat(chatAtivoId);
      fecharModal();
      setMotivoNaoResolveu("");
      setAviso({
        tipo: "sucesso",
        texto: "Cliente informado que não resolveu: chamado reaberto para a IA.",
      });
    },
    onError: (err) => setErroModal(mensagemErro(err)),
  });

  const solicitarHumano = useMutation({
    mutationFn: () =>
      api.patch(`/chats/${chatAtivoId}/status`, {
        status: chatDetail?.solucao_sugerida_ia
          ? "AGUARDANDO_HUMANO_COM_SOLUCAO"
          : "AGUARDANDO_HUMANO_SEM_SOLUCAO",
      }),
    onSuccess: () => {
      invalidarChat(chatAtivoId);
      setAviso({
        tipo: "sucesso",
        texto: "Intervenção humana solicitada: chamado encaminhado à fila.",
      });
    },
    onError: (err) => setAviso({ tipo: "erro", texto: mensagemErro(err) }),
  });

  const reprocessar = useMutation({
    mutationFn: () =>
      api.post(`/integracoes/chamados/${chatAtivoId}/reprocessar`, {
        motivo: motivoReprocesso.trim(),
      }),
    onSuccess: () => {
      invalidarChat(chatAtivoId);
      fecharModal();
      setMotivoReprocesso("");
      setAviso({
        tipo: "sucesso",
        texto: "Reprocessamento da sincronização solicitado.",
      });
    },
    onError: (err) => setErroModal(mensagemErro(err)),
  });

  const podeAgirNoChat =
    !chatDetail?.atendente_id ||
    chatDetail?.atendente_id === user?.id ||
    possuiGestao;

  const podeTransferirDepto =
    possuiGestao || chatDetail?.atendente_id === user?.id;

  const departamentosDestino = departamentos.filter(
    (d) => d.ativo && d.recebe_transferencias,
  );

  const naoResolveuVisivel =
    podeAgirNoChat &&
    (chatDetail?.status === "AGUARDANDO_CLIENTE" ||
      chatDetail?.status === "RESOLVIDO");

  const integracaoAtiva = integracaoStatusQuery.data?.ativa;

  const copiar = (texto: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(texto).catch(() => undefined);
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Inbox */}
      <div className="flex w-80 flex-col rounded-lg border bg-white">
        <div className="space-y-2 border-b p-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Conversas</h2>
            <Badge variant="neutral">{chats.length}</Badge>
          </div>
          <Select
            aria-label="Filtrar por departamento"
            valor={filtroDepartamento}
            onValorChange={(valor) => setFiltroDepartamento(valor)}
            placeholder="Todos os departamentos"
            className="h-8 text-xs"
          >
            {departamentos.map((d) => (
              <SelectItem key={d.id} value={d.id}>
                {d.nome}
              </SelectItem>
            ))}
          </Select>
        </div>
        <div className="flex-1 overflow-auto">
          {chatsQuery.isLoading && (
            <div className="space-y-2 p-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          )}

          {chatsQuery.isError && (
            <div className="p-4">
              <ErrorState
                title="Não foi possível carregar a fila"
                description={mensagemErro(chatsQuery.error)}
                onRetry={() => chatsQuery.refetch()}
              />
            </div>
          )}

          {!chatsQuery.isLoading && !chatsQuery.isError && chats.length === 0 && (
            <div className="p-4">
              <EmptyState
                icon={Inbox}
                title="Nenhuma conversa"
                description={
                  filtroDepartamento
                    ? "Nenhuma conversa no departamento selecionado."
                    : "Nenhuma conversa disponível no seu escopo."
                }
              />
            </div>
          )}

          {chats.map((chat) => (
            <button
              key={chat.id}
              onClick={() => setChatAtivo(chat)}
              className={`w-full border-b p-4 text-left transition-colors hover:bg-gray-50 ${
                chatAtivo?.id === chat.id
                  ? "border-l-4 border-l-primary-500 bg-primary-50"
                  : ""
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium text-gray-900">
                  {chat.cliente_nome || `Cliente #${chat.cliente_id}`}
                </p>
                <Badge
                  variant={
                    chat.prioridade === "urgente" || chat.prioridade === "alta"
                      ? "danger"
                      : "neutral"
                  }
                  className="text-[10px]"
                >
                  {prioridadeLabels[chat.prioridade] || chat.prioridade}
                </Badge>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <Badge
                  variant={statusVariants[chat.status] || "neutral"}
                  className="text-[10px]"
                >
                  {statusLabels[chat.status] || chat.status}
                </Badge>
                {chat.solucao_sugerida_ia && (
                  <Bot className="h-3 w-3 text-primary-500" aria-label="IA sugere solução" />
                )}
                {chat.necessita_humano && (
                  <LifeBuoy className="h-3 w-3 text-warning" aria-label="Necessita humano" />
                )}
              </div>
              {chat.departamento_id && nomeDepartamento(chat.departamento_id) && (
                <p className="mt-1 truncate text-[11px] text-gray-500">
                  {nomeDepartamento(chat.departamento_id)}
                </p>
              )}
              {chat.ultima_mensagem && (
                <p className="mt-1 truncate text-xs text-gray-400">
                  {chat.ultima_mensagem}
                </p>
              )}
              {!chat.atendente_id && (
                <div className="mt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 gap-1 text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      setChatAtivo(chat);
                      pegarChat.mutate(chat.id);
                    }}
                    disabled={pegarChat.isPending}
                  >
                    <UserPlus className="h-3 w-3" /> Assumir
                  </Button>
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Chat */}
      <div className="flex flex-1 flex-col rounded-lg border bg-white">
        {chatAtivoId ? (
          <>
            <div className="space-y-3 border-b p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <h3 className="truncate font-semibold text-gray-900">
                    {chatSelecionado?.cliente_nome ||
                      `Cliente #${chatDetail?.cliente_id ?? ""}`}
                  </h3>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <Badge variant={statusVariants[chatDetail?.status || ""] || "neutral"}>
                      {statusLabels[chatDetail?.status || ""] || chatDetail?.status}
                    </Badge>
                    {chatDetail?.departamento_id && (
                      <Badge variant="primary">
                        {nomeDepartamento(chatDetail.departamento_id) ||
                          "Departamento"}
                      </Badge>
                    )}
                    {chatDetail?.necessita_humano && (
                      <Badge variant="warning">Necessita humano</Badge>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Select
                    aria-label="Status do chamado"
                    valor={chatDetail?.status ?? ""}
                    onValorChange={(valor) => updateStatus.mutate(valor)}
                    className="h-8 w-auto text-xs"
                  >
                    {Object.entries(statusLabels).map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                      </SelectItem>
                    ))}
                  </Select>
                  <Select
                    aria-label="Prioridade do chamado"
                    valor={chatDetail?.prioridade ?? "media"}
                    onValorChange={(valor) => updatePrioridade.mutate(valor)}
                    className="h-8 w-auto text-xs"
                  >
                    {Object.entries(prioridadeLabels).map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                      </SelectItem>
                    ))}
                  </Select>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {!chatDetail?.atendente_id && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => pegarChat.mutate(chatAtivoId)}
                    disabled={pegarChat.isPending}
                  >
                    <UserPlus className="h-4 w-4" /> Assumir
                  </Button>
                )}
                {podeTransferirDepto && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => abrirModal("transferir-departamento")}
                  >
                    <ArrowRightLeft className="h-4 w-4" /> Transferir depto
                  </Button>
                )}
                {possuiGestao && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => abrirModal("atribuir")}
                  >
                    <User className="h-4 w-4" /> Atribuir atendente
                  </Button>
                )}
                {podeAgirNoChat && chatDetail?.status === "AGUARDANDO_CLIENTE" && (
                  <Button
                    size="sm"
                    onClick={() => confirmarResolucao.mutate()}
                    disabled={confirmarResolucao.isPending}
                  >
                    <CheckCircle2 className="h-4 w-4" /> Confirmar resolução
                  </Button>
                )}
                {naoResolveuVisivel && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => abrirModal("nao-resolveu")}
                  >
                    <ShieldAlert className="h-4 w-4" /> Não resolveu
                  </Button>
                )}
                {podeAgirNoChat && chatDetail?.status === "IA_ANALISANDO" && (
                  <Button
                    size="sm"
                    variant="accent"
                    onClick={() => solicitarHumano.mutate()}
                    disabled={solicitarHumano.isPending}
                  >
                    <LifeBuoy className="h-4 w-4" /> Solicitar humano
                  </Button>
                )}
              </div>
            </div>

            <div className="flex-1 space-y-3 overflow-auto p-4">
              {mensagensQuery.isLoading && (
                <div className="space-y-2">
                  {[0, 1, 2].map((i) => (
                    <Skeleton key={i} className="h-14 w-2/3" />
                  ))}
                </div>
              )}
              {mensagensQuery.isError && (
                <ErrorState
                  title="Não foi possível carregar as mensagens"
                  description={mensagemErro(mensagensQuery.error)}
                  onRetry={() => mensagensQuery.refetch()}
                />
              )}
              {!mensagensQuery.isLoading &&
                !mensagensQuery.isError &&
                mensagens.length === 0 && (
                  <p className="py-8 text-center text-sm text-gray-400">
                    Nenhuma mensagem ainda
                  </p>
                )}
              {mensagens.map((msg: any) => (
                <div
                  key={msg.id}
                  className={`flex ${
                    msg.remetente === "atendente" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg px-4 py-2 text-sm ${
                      msg.remetente === "atendente"
                        ? "bg-primary-500 text-white"
                        : msg.remetente === "ia"
                          ? "bg-primary-50 text-primary-900"
                          : "bg-gray-100 text-gray-900"
                    }`}
                  >
                    <div className="mb-1 flex items-center gap-1">
                      {msg.remetente === "ia" ? <Bot className="h-3 w-3" /> : null}
                      {msg.remetente === "atendente" ? (
                        <User className="h-3 w-3" />
                      ) : null}
                      <span className="text-[10px] opacity-70">
                        {msg.remetente === "atendente"
                          ? user?.nome || "Atendente"
                          : msg.remetente === "ia"
                            ? iaName
                            : chatSelecionado?.cliente_nome ||
                              chatDetail?.cliente_nome ||
                              "Cliente"}
                      </span>
                    </div>
                    <p>{msg.conteudo}</p>
                    <span className="mt-1 block text-[10px] opacity-50">
                      {new Date(msg.created_at).toLocaleTimeString("pt-BR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="border-t p-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (novaMsg.trim()) sendMsg.mutate(novaMsg);
                }}
                className="flex gap-2"
              >
                <Input
                  placeholder="Digite sua mensagem..."
                  value={novaMsg}
                  onChange={(e) => setNovaMsg(e.target.value)}
                  aria-label="Mensagem"
                />
                <Button type="submit" size="sm" disabled={!novaMsg.trim()}>
                  {sendMsg.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center p-6">
            <EmptyState
              icon={Inbox}
              title="Selecione uma conversa"
              description="Escolha um chamado na fila para responder e acompanhar o diagnóstico da IA."
            />
          </div>
        )}
      </div>

      {/* Painel de diagnóstico e sincronização */}
      {chatAtivoId && (
        <div className="flex w-80 flex-col gap-4 overflow-auto">
          <section className="rounded-lg border bg-white">
            <div className="border-b p-4">
              <h3 className="flex items-center gap-2 font-semibold text-gray-900">
                <Bot className="h-4 w-4 text-primary-500" /> Diagnóstico
              </h3>
              <p className="mt-1 text-[11px] text-gray-500">
                Sugestão automática da IA — confirme antes de usar.
              </p>
            </div>
            <div className="space-y-3 p-4 text-sm">
              {roteamentoQuery.isLoading && (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              )}
              {roteamentoQuery.isError && (
                <div className="space-y-2">
                  <p className="text-xs text-gray-500">
                    {mensagemErro(roteamentoQuery.error)}
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => roteamentoQuery.refetch()}
                  >
                    Tentar novamente
                  </Button>
                </div>
              )}
              {roteamento && !roteamento.tem_diagnostico && (
                <p className="py-4 text-center text-xs text-gray-400">
                  IA ainda não analisou este chamado.
                </p>
              )}

              {roteamento?.tem_diagnostico && (
                <>
                  <Campo
                    label="Intenção"
                    valor={humanizar(roteamento.intencao)}
                  />
                  <Campo
                    label="Subintenção"
                    valor={humanizar(roteamento.subintencao)}
                  />
                  <Campo
                    label="Categoria ERP"
                    valor={roteamento.categoria_erp || "—"}
                    hint="Refina a regra; não define o departamento."
                  />
                  <Campo
                    label="Departamento sugerido"
                    valor={roteamento.departamento_sugerido_codigo || "—"}
                  />
                  <Campo
                    label="Departamento atual"
                    valor={
                      roteamento.departamento_codigo ||
                      nomeDepartamento(roteamento.departamento_id) ||
                      "—"
                    }
                  />
                  <Campo label="Justificativa" valor={roteamento.motivo || "—"} />
                  {roteamento.confianca !== null &&
                    roteamento.confianca !== undefined && (
                      <div>
                        <p className="text-xs font-medium uppercase text-gray-500">
                          Confiança (auxiliar)
                        </p>
                        <div className="mt-1 h-2 rounded-full bg-gray-100">
                          <div
                            className="h-2 rounded-full bg-primary-500"
                            style={{
                              width: `${Math.round(
                                Math.min(
                                  Math.max(roteamento.confianca, 0),
                                  1,
                                ) * 100,
                              )}%`,
                            }}
                          />
                        </div>
                        <p className="mt-1 text-xs text-gray-500">
                          {Math.round(roteamento.confianca * 100)}% — não é
                          prova de correção
                        </p>
                      </div>
                    )}
                  {roteamento.artigos_consultados &&
                    roteamento.artigos_consultados.length > 0 && (
                      <div>
                        <p className="text-xs font-medium uppercase text-gray-500">
                          Artigos consultados
                        </p>
                        <ul className="mt-1 space-y-1">
                          {roteamento.artigos_consultados.map((artigo, i) => (
                            <li
                              key={artigo.id || i}
                              className="rounded border px-2 py-1 text-xs text-gray-700"
                            >
                              {artigo.titulo || artigo.id || "Artigo"}
                              {typeof artigo.score === "number" && (
                                <span className="ml-1 text-gray-400">
                                  ({Math.round(artigo.score * 100)}%)
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                </>
              )}

              {chatDetail?.resumo_problema && (
                <Campo label="Resumo" valor={chatDetail.resumo_problema} />
              )}
              {chatDetail?.causa_provavel && (
                <Campo label="Causa provável" valor={chatDetail.causa_provavel} />
              )}
              {chatDetail?.solucao_sugerida_ia && (
                <div>
                  <p className="text-xs font-medium uppercase text-gray-500">
                    Solução sugerida
                  </p>
                  <p className="mt-1 whitespace-pre-line text-sm text-gray-900">
                    {chatDetail.solucao_sugerida_ia}
                  </p>
                </div>
              )}
            </div>
          </section>

          <section className="rounded-lg border bg-white">
            <div className="border-b p-4">
              <h3 className="flex items-center gap-2 font-semibold text-gray-900">
                <RefreshCw className="h-4 w-4 text-primary-500" /> Sincronização
              </h3>
              {possuiGestao && integracaoStatusQuery.data && (
                <p className="mt-1 text-[11px] text-gray-500">
                  Integração Emsoft:{" "}
                  {integracaoAtiva ? "habilitada" : "desabilitada"}
                </p>
              )}
            </div>
            <div className="space-y-3 p-4 text-sm">
              {!podeVerSync && (
                <p className="text-xs text-gray-500">
                  Detalhes de sincronização visíveis apenas para o atendente
                  responsável, supervisor ou admin.
                </p>
              )}

              {podeVerSync && syncQuery.isLoading && (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              )}

              {podeVerSync && syncQuery.isError && (
                <p className="text-xs text-gray-500">
                  Não foi possível consultar o status de sincronização agora.
                </p>
              )}

              {sync && (
                <>
                  {sync.integracao !== undefined ? (
                    <>
                      {sync.integracao ? (
                        <>
                          <Campo
                            label="Status"
                            valor={
                              <Badge
                                variant={
                                  syncStatusVariants[
                                    sync.integracao.status || ""
                                  ] || "neutral"
                                }
                              >
                                {sync.integracao.status || "PENDENTE"}
                              </Badge>
                            }
                          />
                          {sync.integracao.external_ticket_id && (
                            <div>
                              <p className="text-xs font-medium uppercase text-gray-500">
                                Chamado Emsoft
                              </p>
                              <div className="mt-1 flex items-center gap-2">
                                <code className="rounded bg-gray-100 px-2 py-1 font-mono text-xs text-gray-800">
                                  {sync.integracao.external_ticket_id}
                                </code>
                                <button
                                  type="button"
                                  onClick={() =>
                                    copiar(sync.integracao?.external_ticket_id || "")
                                  }
                                  className="text-gray-400 hover:text-gray-600"
                                  aria-label="Copiar ID do chamado"
                                >
                                  <ClipboardCopy className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>
                          )}
                          {sync.integracao.external_url && (
                            <a
                              href={sync.integracao.external_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-primary-600 hover:underline"
                            >
                              Abrir chamado <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                          {sync.integracao.external_status && (
                            <Campo
                              label="Status externo"
                              valor={sync.integracao.external_status}
                            />
                          )}
                          {sync.integracao.department_code && (
                            <Campo
                              label="Departamento no Emsoft"
                              valor={sync.integracao.department_code}
                            />
                          )}
                          {typeof sync.integracao.tentativas === "number" && (
                            <Campo
                              label="Tentativas"
                              valor={String(sync.integracao.tentativas)}
                            />
                          )}
                          {sync.integracao.ultima_tentativa_em && (
                            <Campo
                              label="Última tentativa"
                              valor={new Date(
                                sync.integracao.ultima_tentativa_em,
                              ).toLocaleString("pt-BR")}
                            />
                          )}
                          {sync.integracao.ultimo_erro && (
                            <div className="rounded border border-danger/20 bg-danger/5 p-2">
                              <p className="text-xs font-medium uppercase text-danger">
                                Último erro (sanitizado)
                              </p>
                              <p className="mt-1 break-words text-xs text-danger">
                                {sync.integracao.ultimo_erro}
                              </p>
                            </div>
                          )}
                        </>
                      ) : (
                        <p className="text-xs text-gray-500">
                          Chamado externo ainda não criado/sincronizado.
                        </p>
                      )}
                      <Campo
                        label="Pendências na fila"
                        valor={String(sync.pendencias)}
                      />
                      {sync.eventos && sync.eventos.length > 0 && (
                        <details className="rounded border p-2">
                          <summary className="cursor-pointer text-xs font-medium text-gray-700">
                            Eventos recentes ({sync.eventos.length})
                          </summary>
                          <ul className="mt-2 space-y-1">
                            {sync.eventos.slice(0, 8).map((evento) => (
                              <li
                                key={evento.id}
                                className="rounded bg-gray-50 px-2 py-1 text-[11px] text-gray-600"
                              >
                                <span className="font-medium">
                                  {evento.event_type}
                                </span>{" "}
                                · {evento.status}
                                {evento.tentativas > 0 &&
                                  ` · ${evento.tentativas} tentativa(s)`}
                                {evento.ator && ` · ${evento.ator}`}
                                {evento.ultimo_erro && (
                                  <span className="block text-danger">
                                    {evento.ultimo_erro}
                                  </span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </>
                  ) : (
                    <>
                      <Campo
                        label="Status da integração"
                        valor={
                          <Badge
                            variant={
                              syncStatusVariants[sync.status_integracao || ""] ||
                              "neutral"
                            }
                          >
                            {sync.status_integracao || "Não sincronizado"}
                          </Badge>
                        }
                      />
                      <Campo
                        label="Pendências na fila"
                        valor={String(sync.pendencias)}
                      />
                      <p className="text-[11px] text-gray-500">
                        Detalhes do chamado e erros são restritos a supervisor e
                        admin.
                      </p>
                    </>
                  )}
                </>
              )}

              {possuiGestao && chatAtivoId && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => abrirModal("reprocessar")}
                >
                  <RefreshCw className="h-4 w-4" /> Reprocessar sincronização
                </Button>
              )}

              <p className="text-[11px] text-gray-400">
                Integração pendente não bloqueia o atendimento.
              </p>
            </div>
          </section>
        </div>
      )}

      {/* Feedback global */}
      {aviso && (
        <div
          role="status"
          className={`fixed bottom-6 left-1/2 z-50 flex max-w-lg -translate-x-1/2 items-start gap-3 rounded-lg px-4 py-2 text-sm shadow-lg ${
            aviso.tipo === "erro"
              ? "bg-danger text-white"
              : "bg-success text-white"
          }`}
        >
          <span>{aviso.texto}</span>
          <button
            onClick={() => setAviso(null)}
            aria-label="Fechar aviso"
            className="opacity-80 hover:opacity-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Modal: transferir departamento */}
      {modal === "transferir-departamento" && (
        <ModalBase
          titulo="Transferir de departamento"
          onClose={fecharModal}
          footer={
            <>
              <Button variant="ghost" onClick={fecharModal}>
                Cancelar
              </Button>
              <Button
                onClick={() => transferirDepartamento.mutate()}
                disabled={
                  !deptoDestinoId || transferirDepartamento.isPending
                }
              >
                {transferirDepartamento.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Transferir
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <div>
              <label
                htmlFor="depto-destino"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Departamento de destino
              </label>
              <Select
                id="depto-destino"
                valor={deptoDestinoId}
                onValorChange={(valor) => setDeptoDestinoId(valor)}
                placeholder="Selecione…"
              >
                {departamentosDestino.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.nome}
                    {d.id === chatDetail?.departamento_id ? " (atual)" : ""}
                  </SelectItem>
                ))}
              </Select>
              {departamentosDestino.length === 0 && (
                <p className="mt-1 text-xs text-warning">
                  Nenhum departamento ativo recebe transferências.
                </p>
              )}
            </div>
            <div>
              <label
                htmlFor="motivo-transferencia"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Motivo (opcional)
              </label>
              <textarea
                id="motivo-transferencia"
                value={motivoTransferencia}
                onChange={(e) => setMotivoTransferencia(e.target.value)}
                maxLength={500}
                rows={2}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500"
                checked={preservarAtendente}
                onChange={(e) => setPreservarAtendente(e.target.checked)}
              />
              Preservar atendente atual se ele pertence ao destino
            </label>
            <p className="text-xs text-gray-500">
              A transferência remove o responsável atual e devolve o chamado à
              fila do departamento de destino.
            </p>
            {erroModal && (
              <p role="alert" className="text-sm text-danger">
                {erroModal}
              </p>
            )}
          </div>
        </ModalBase>
      )}

      {/* Modal: atribuir atendente */}
      {modal === "atribuir" && (
        <ModalBase
          titulo="Atribuir atendente"
          onClose={fecharModal}
          footer={
            <>
              <Button variant="ghost" onClick={fecharModal}>
                Cancelar
              </Button>
              <Button
                onClick={() => atribuirAtendente.mutate()}
                disabled={!atendenteDestinoId || atribuirAtendente.isPending}
              >
                {atribuirAtendente.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Atribuir
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <div>
              <label
                htmlFor="atendente-destino"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Atendente
              </label>
              <Select
                id="atendente-destino"
                valor={atendenteDestinoId}
                onValorChange={(valor) => setAtendenteDestinoId(valor)}
                placeholder="Selecione…"
              >
                {atendentes.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.nome} —{" "}
                    {nomeDepartamento(a.departamento_id) || "sem departamento"}
                  </SelectItem>
                ))}
              </Select>
            </div>
            <div>
              <label
                htmlFor="motivo-atribuicao"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Motivo
              </label>
              <textarea
                id="motivo-atribuicao"
                value={motivoAtribuicao}
                onChange={(e) => setMotivoAtribuicao(e.target.value)}
                maxLength={500}
                rows={2}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Obrigatório quando o atendente é de outro departamento
                (override auditável).
              </p>
            </div>
            {erroModal && (
              <p role="alert" className="text-sm text-danger">
                {erroModal}
              </p>
            )}
          </div>
        </ModalBase>
      )}

      {/* Modal: não resolveu */}
      {modal === "nao-resolveu" && (
        <ModalBase
          titulo="Cliente informou que não resolveu"
          onClose={fecharModal}
          footer={
            <>
              <Button variant="ghost" onClick={fecharModal}>
                Cancelar
              </Button>
              <Button
                onClick={() => reabrir.mutate()}
                disabled={reabrir.isPending}
              >
                {reabrir.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Reabrir para a IA
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              O chamado volta para a análise da IA. O mesmo chamado externo é
              atualizado — não é criado um segundo ticket (spec 11).
            </p>
            <div>
              <label
                htmlFor="motivo-nao-resolveu"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Motivo (opcional)
              </label>
              <textarea
                id="motivo-nao-resolveu"
                value={motivoNaoResolveu}
                onChange={(e) => setMotivoNaoResolveu(e.target.value)}
                maxLength={500}
                rows={2}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            {erroModal && (
              <p role="alert" className="text-sm text-danger">
                {erroModal}
              </p>
            )}
          </div>
        </ModalBase>
      )}

      {/* Modal: reprocessar sincronização */}
      {modal === "reprocessar" && (
        <ModalBase
          titulo="Reprocessar sincronização"
          onClose={fecharModal}
          footer={
            <>
              <Button variant="ghost" onClick={fecharModal}>
                Cancelar
              </Button>
              <Button
                onClick={() => reprocessar.mutate()}
                disabled={
                  motivoReprocesso.trim().length < 3 || reprocessar.isPending
                }
              >
                {reprocessar.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Reprocessar
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Reaproveita o evento incompleto mais recente ou enfileira um novo
              pedido de sincronização. O motivo fica registrado na auditoria.
            </p>
            <div>
              <label
                htmlFor="motivo-reprocesso"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Motivo (3 a 500 caracteres)
              </label>
              <textarea
                id="motivo-reprocesso"
                value={motivoReprocesso}
                onChange={(e) => setMotivoReprocesso(e.target.value)}
                maxLength={500}
                rows={2}
                required
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            {erroModal && (
              <p role="alert" className="text-sm text-danger">
                {erroModal}
              </p>
            )}
          </div>
        </ModalBase>
      )}
    </div>
  );
}

function Campo({
  label,
  valor,
  hint,
}: {
  label: string;
  valor: React.ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase text-gray-500">{label}</p>
      <div className="mt-1 break-words text-sm text-gray-900">{valor}</div>
      {hint && <p className="mt-0.5 text-[11px] text-gray-400">{hint}</p>}
    </div>
  );
}

function ModalBase({
  titulo,
  onClose,
  children,
  footer,
}: {
  titulo: string;
  onClose: () => void;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">{titulo}</h3>
          <button
            onClick={onClose}
            aria-label="Fechar"
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
        <div className="mt-4 flex justify-end gap-2">{footer}</div>
      </div>
    </div>
  );
}

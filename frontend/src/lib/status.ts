export type VarianteBadge =
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "neutral";

export const STATUS_CHAT = [
  "NOVO",
  "IA_ANALISANDO",
  "AGUARDANDO_CLIENTE",
  "AGUARDANDO_HUMANO_COM_SOLUCAO",
  "AGUARDANDO_HUMANO_SEM_SOLUCAO",
  "EM_ATENDIMENTO",
  "RESOLVIDO",
  "ENCERRADO",
] as const;

const ROTULOS_STATUS: Record<string, string> = {
  NOVO: "Novo",
  IA_ANALISANDO: "IA analisando",
  AGUARDANDO_CLIENTE: "Aguardando cliente",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "Aguardando humano (com solução)",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "Aguardando humano (sem solução)",
  EM_ATENDIMENTO: "Em atendimento",
  RESOLVIDO: "Resolvido",
  ENCERRADO: "Encerrado",
};

const VARIANTES_STATUS: Record<string, VarianteBadge> = {
  NOVO: "primary",
  IA_ANALISANDO: "primary",
  AGUARDANDO_CLIENTE: "warning",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "info",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "warning",
  EM_ATENDIMENTO: "info",
  RESOLVIDO: "success",
  ENCERRADO: "neutral",
};

export const PRIORIDADES = ["baixa", "media", "alta", "urgente"] as const;
export type PrioridadeChat = (typeof PRIORIDADES)[number];

const ROTULOS_PRIORIDADE: Record<string, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
  urgente: "Urgente",
};

export function rotuloStatus(status: string): string {
  return ROTULOS_STATUS[status] ?? status;
}

export function rotuloPrioridade(prioridade: string): string {
  return ROTULOS_PRIORIDADE[prioridade] ?? prioridade;
}

export function varianteStatus(status: string): VarianteBadge {
  return VARIANTES_STATUS[status] ?? "neutral";
}

export function variantePrioridade(prioridade: string): VarianteBadge {
  return prioridade === "alta" || prioridade === "urgente" ? "danger" : "neutral";
}

export function statusEncerrado(status: string): boolean {
  return status === "RESOLVIDO" || status === "ENCERRADO";
}

/**
 * Formata a média CSAT para exibição (gap 00-11).
 * Devolve "—" quando não há dados, senão "4.6 / 5" com uma casa decimal.
 */
export function formatarCsat(media: number | null | undefined): string {
  if (media == null) return "—";
  return `${media.toFixed(1)} / 5`;
}

/**
 * Formata o percentual de clientes satisfeitos (gap 00-11).
 * Devolve "—" quando não há dados, senão o valor arredondado, ex.: "83%".
 */
export function percentualSatisfeitos(pct: number | null | undefined): string {
  if (pct == null) return "—";
  return `${Math.round(pct)}%`;
}

const ROTULOS_NOTA: Record<number, string> = {
  1: "Muito insatisfeito",
  2: "Insatisfeito",
  3: "Neutro",
  4: "Satisfeito",
  5: "Muito satisfeito",
};

/**
 * Rótulo textual da nota de 1 a 5 (gap 00-11).
 * Devolve "—" para notas fora da faixa.
 */
export function rotuloNota(nota: number): string {
  return ROTULOS_NOTA[nota] ?? "—";
}

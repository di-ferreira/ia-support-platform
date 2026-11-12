/** Constantes do backoff de reconexão do WebSocket (gap 07-3). */
export const BACKOFF_INICIAL_MS = 1000;
export const BACKOFF_TETO_MS = 30000;

/**
 * Calcula o atraso da próxima tentativa de reconexão: backoff exponencial
 * (1s, 2s, 4s, ...) limitado a 30s, com jitter em [teto/2, teto] para
 * evitar tempestade de reconexão. Função pura: `aleatorio` é injetável
 * para testes determinísticos (Math.random retorna [0, 1)).
 */
export function proximoBackoff(
  tentativa: number,
  aleatorio: () => number = Math.random
): number {
  const teto = Math.min(
    BACKOFF_INICIAL_MS * 2 ** Math.max(0, tentativa),
    BACKOFF_TETO_MS
  );
  return teto / 2 + aleatorio() * (teto / 2);
}

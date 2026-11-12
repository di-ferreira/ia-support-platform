import { describe, expect, it } from "vitest";

import {
  BACKOFF_INICIAL_MS,
  BACKOFF_TETO_MS,
  proximoBackoff,
} from "@/lib/reconnect";

const SEM_JITTER = () => 0; // atraso = teto / 2
const JITTER_MAXIMO = () => 1; // atraso = teto

describe("backoff de reconexao", () => {
  it("dobra o teto a cada tentativa", () => {
    expect(proximoBackoff(0, SEM_JITTER)).toBe(BACKOFF_INICIAL_MS / 2);
    expect(proximoBackoff(1, SEM_JITTER)).toBe(2000 / 2);
    expect(proximoBackoff(2, SEM_JITTER)).toBe(4000 / 2);
    expect(proximoBackoff(3, SEM_JITTER)).toBe(8000 / 2);
    expect(proximoBackoff(4, SEM_JITTER)).toBe(16000 / 2);
  });

  it("limita o teto em 30s a partir da tentativa 5", () => {
    expect(proximoBackoff(5, JITTER_MAXIMO)).toBe(BACKOFF_TETO_MS);
    expect(proximoBackoff(10, JITTER_MAXIMO)).toBe(BACKOFF_TETO_MS);
    expect(proximoBackoff(100, JITTER_MAXIMO)).toBe(BACKOFF_TETO_MS);
  });

  it("mantem o atraso dentro de [teto/2, teto] para qualquer jitter", () => {
    for (const tentativa of [0, 1, 2, 3, 4, 5, 10]) {
      const teto = Math.min(
        BACKOFF_INICIAL_MS * 2 ** tentativa,
        BACKOFF_TETO_MS
      );
      const baixo = proximoBackoff(tentativa, SEM_JITTER);
      const alto = proximoBackoff(tentativa, JITTER_MAXIMO);
      expect(baixo).toBeGreaterThanOrEqual(teto / 2);
      expect(alto).toBeLessThanOrEqual(teto);
    }
  });

  it("clampa tentativas negativas para a primeira espera", () => {
    expect(proximoBackoff(-3, JITTER_MAXIMO)).toBe(BACKOFF_INICIAL_MS);
  });
});

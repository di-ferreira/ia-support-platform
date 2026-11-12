import { describe, expect, it } from "vitest";

import {
  PRIORIDADES,
  STATUS_CHAT,
  rotuloPrioridade,
  rotuloStatus,
  statusEncerrado,
  variantePrioridade,
  varianteStatus,
} from "@/lib/status";

describe("catalogo de status", () => {
  it("cobre os oito status do dominio", () => {
    expect(STATUS_CHAT).toHaveLength(8);
    expect(STATUS_CHAT).toContain("AGUARDANDO_HUMANO_SEM_SOLUCAO");
  });

  it("rotula cada status em portugues", () => {
    expect(rotuloStatus("NOVO")).toBe("Novo");
    expect(rotuloStatus("IA_ANALISANDO")).toBe("IA analisando");
    expect(rotuloStatus("AGUARDANDO_CLIENTE")).toBe("Aguardando cliente");
    expect(rotuloStatus("EM_ATENDIMENTO")).toBe("Em atendimento");
    expect(rotuloStatus("ENCERRADO")).toBe("Encerrado");
  });

  it("devolve o proprio codigo quando o status e desconhecido", () => {
    expect(rotuloStatus("STATUS_FUTURO")).toBe("STATUS_FUTURO");
  });

  it("marca resolvido e encerrado como concluidos", () => {
    expect(statusEncerrado("RESOLVIDO")).toBe(true);
    expect(statusEncerrado("ENCERRADO")).toBe(true);
    expect(statusEncerrado("NOVO")).toBe(false);
  });
});

describe("catalogo de prioridade", () => {
  it("ordena as quatro prioridades", () => {
    expect(PRIORIDADES).toEqual(["baixa", "media", "alta", "urgente"]);
  });

  it("destaca alta e urgente como perigo", () => {
    expect(variantePrioridade("urgente")).toBe("danger");
    expect(variantePrioridade("alta")).toBe("danger");
    expect(variantePrioridade("media")).toBe("neutral");
    expect(variantePrioridade("baixa")).toBe("neutral");
  });

  it("rotula prioridade desconhecida sem quebrar", () => {
    expect(rotuloPrioridade("critica")).toBe("critica");
  });
});

describe("variante de status", () => {
  it("usa info para fila humana e success para resolvido", () => {
    expect(varianteStatus("AGUARDANDO_HUMANO_COM_SOLUCAO")).toBe("info");
    expect(varianteStatus("AGUARDANDO_HUMANO_SEM_SOLUCAO")).toBe("warning");
    expect(varianteStatus("RESOLVIDO")).toBe("success");
    expect(varianteStatus("ENCERRADO")).toBe("neutral");
  });
});

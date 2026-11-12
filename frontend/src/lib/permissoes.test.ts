import { describe, expect, it } from "vitest";

import { linksVisiveis, podeAcessarRota } from "@/lib/permissoes";

describe("guarda de rota por perfil", () => {
  it("admin acessa todas as rotas mapeadas", () => {
    for (const rota of ["/dashboard", "/atendimento", "/usuarios", "/configuracoes", "/departamentos", "/conhecimento"]) {
      expect(podeAcessarRota("admin", rota)).toBe(true);
    }
  });

  it("atendente nao acessa usuarios, configuracoes, conhecimento nem departamentos", () => {
    expect(podeAcessarRota("atendente", "/usuarios")).toBe(false);
    expect(podeAcessarRota("atendente", "/configuracoes")).toBe(false);
    expect(podeAcessarRota("atendente", "/conhecimento")).toBe(false);
    expect(podeAcessarRota("atendente", "/departamentos")).toBe(false);
  });

  it("atendente acessa a operacao", () => {
    for (const rota of ["/dashboard", "/atendimento", "/kanban", "/cliente"]) {
      expect(podeAcessarRota("atendente", rota)).toBe(true);
    }
  });

  it("supervisor acessa gestao mas nao configuracoes", () => {
    expect(podeAcessarRota("supervisor", "/usuarios")).toBe(true);
    expect(podeAcessarRota("supervisor", "/departamentos")).toBe(true);
    expect(podeAcessarRota("supervisor", "/configuracoes")).toBe(false);
  });

  it("sem perfil nao acessa rota mapeada (fail-closed)", () => {
    expect(podeAcessarRota(null, "/usuarios")).toBe(false);
    expect(podeAcessarRota(undefined, "/dashboard")).toBe(false);
  });

  it("rota nao mapeada depende apenas de sessao", () => {
    expect(podeAcessarRota("atendente", "/rota-nova")).toBe(true);
  });

  it("filtra os links da sidebar por perfil", () => {
    const hrefs = linksVisiveis("atendente").map((rota) => rota.href);
    expect(hrefs).toContain("/atendimento");
    expect(hrefs).not.toContain("/usuarios");
    expect(hrefs).not.toContain("/configuracoes");
  });
});

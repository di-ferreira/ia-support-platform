import { describe, expect, it } from "vitest";

import { linksVisiveis, podeAcessarRota, podeTransferirChat } from "@/lib/permissoes";

describe("guarda de rota por perfil", () => {
  it("admin acessa todas as rotas mapeadas", () => {
    for (const rota of ["/dashboard", "/atendimento", "/usuarios", "/configuracoes", "/departamentos", "/conhecimento"]) {
      expect(podeAcessarRota("admin", rota)).toBe(true);
    }
  });

  it("atendente nao acessa usuarios, configuracoes nem conhecimento", () => {
    expect(podeAcessarRota("atendente", "/usuarios")).toBe(false);
    expect(podeAcessarRota("atendente", "/configuracoes")).toBe(false);
    expect(podeAcessarRota("atendente", "/conhecimento")).toBe(false);
  });

  it("atendente acessa a operacao e a fila de departamentos (spec 04)", () => {
    for (const rota of ["/dashboard", "/atendimento", "/kanban", "/cliente", "/departamentos"]) {
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

describe("podeTransferirChat (spec 04, gap 04-3)", () => {
  const dono = { id: "at-1", perfil: "atendente" };
  const deOutro = { id: "at-2", perfil: "atendente" };

  it("admin transfere qualquer chamado", () => {
    expect(podeTransferirChat({ id: "adm", perfil: "admin" }, { atendente_id: "at-2" })).toBe(true);
    expect(podeTransferirChat({ id: "adm", perfil: "admin" }, { atendente_id: null })).toBe(true);
  });

  it("supervisor transfere qualquer chamado", () => {
    expect(podeTransferirChat({ id: "sup", perfil: "supervisor" }, { atendente_id: "at-2" })).toBe(true);
    expect(podeTransferirChat({ id: "sup", perfil: "supervisor" }, { atendente_id: null })).toBe(true);
  });

  it("atendente dono do chamado transfere", () => {
    expect(podeTransferirChat(dono, { atendente_id: "at-1" })).toBe(true);
  });

  it("atendente nao transfere chamado de colega", () => {
    expect(podeTransferirChat(deOutro, { atendente_id: "at-1" })).toBe(false);
  });

  it("chat sem atendente: atendente comum nao transfere", () => {
    expect(podeTransferirChat(dono, { atendente_id: null })).toBe(false);
    expect(podeTransferirChat(dono, undefined)).toBe(false);
  });

  it("sem usuario, fail-closed", () => {
    expect(podeTransferirChat(null, { atendente_id: "at-1" })).toBe(false);
    expect(podeTransferirChat(undefined, undefined)).toBe(false);
  });
});

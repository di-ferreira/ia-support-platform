import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(process.cwd(), "src");
const PROIBIDO =
  /(?:text|bg|border|ring|divide|from|via|to)-(?:gray|green|red|blue|yellow|orange|amber|emerald|rose|indigo|slate|zinc)-\d{2,3}/g;

function arquivosTsx(diretorio: string): string[] {
  return readdirSync(diretorio).flatMap((entrada) => {
    const caminho = join(diretorio, entrada);
    if (statSync(caminho).isDirectory()) return arquivosTsx(caminho);
    if (!caminho.endsWith(".tsx")) return [];
    if (caminho.endsWith("tokens.test.ts")) return [];
    return [caminho];
  });
}

describe("tokens de cor", () => {
  it("nenhum componente usa cor raw do Tailwind", () => {
    const infratores = arquivosTsx(RAIZ).flatMap((arquivo) => {
      const conteudo = readFileSync(arquivo, "utf8");
      const achados = conteudo.match(PROIBIDO) ?? [];
      return achados.map((achado) => `${arquivo}: ${achado}`);
    });

    expect(infratores).toEqual([]);
  });

  it("os tokens de estado existem no tema", () => {
    const css = readFileSync(join(RAIZ, "app/globals.css"), "utf8");

    for (const token of [
      "--color-status-success",
      "--color-status-success-soft",
      "--color-status-danger",
      "--color-status-danger-soft",
      "--color-status-warning",
      "--color-status-warning-soft",
      "--color-status-info",
      "--color-status-info-soft",
    ]) {
      expect(css).toContain(token);
    }
  });
});

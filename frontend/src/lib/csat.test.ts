import { describe, expect, it } from "vitest";

import { formatarCsat, percentualSatisfeitos, rotuloNota } from "@/lib/csat";

describe("formatarCsat", () => {
  it("devolve '—' quando nao ha dados", () => {
    expect(formatarCsat(null)).toBe("—");
    expect(formatarCsat(undefined)).toBe("—");
  });

  it("formata a media com uma casa decimal e o sufixo '/ 5'", () => {
    expect(formatarCsat(4.6)).toBe("4.6 / 5");
    expect(formatarCsat(4)).toBe("4.0 / 5");
  });

  it("arredonda para uma casa decimal", () => {
    expect(formatarCsat(4.37)).toBe("4.4 / 5");
    expect(formatarCsat(4.62)).toBe("4.6 / 5");
  });
});

describe("percentualSatisfeitos", () => {
  it("devolve '—' quando nao ha dados", () => {
    expect(percentualSatisfeitos(null)).toBe("—");
    expect(percentualSatisfeitos(undefined)).toBe("—");
  });

  it("arredonda e formata como percentual", () => {
    expect(percentualSatisfeitos(83.2)).toBe("83%");
    expect(percentualSatisfeitos(83.7)).toBe("84%");
    expect(percentualSatisfeitos(100)).toBe("100%");
  });
});

describe("rotuloNota", () => {
  it("rotula as notas extremas e intermediarias", () => {
    expect(rotuloNota(1)).toBe("Muito insatisfeito");
    expect(rotuloNota(3)).toBe("Neutro");
    expect(rotuloNota(5)).toBe("Muito satisfeito");
  });

  it("rotula as demais notas da faixa 1-5", () => {
    expect(rotuloNota(2)).toBe("Insatisfeito");
    expect(rotuloNota(4)).toBe("Satisfeito");
  });

  it("devolve '—' para notas fora da faixa", () => {
    expect(rotuloNota(0)).toBe("—");
    expect(rotuloNota(6)).toBe("—");
  });
});

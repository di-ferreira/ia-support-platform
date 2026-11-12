import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Select, SelectItem } from "@/components/ui/select";

function montar(onValorChange = vi.fn()) {
  render(
    <Select valor="media" onValorChange={onValorChange} aria-label="Prioridade">
      <SelectItem value="baixa">Baixa</SelectItem>
      <SelectItem value="media">Média</SelectItem>
      <SelectItem value="urgente">Urgente</SelectItem>
    </Select>
  );
  return onValorChange;
}

describe("Select acessível", () => {
  it("expõe o valor atual e o rótulo acessível", () => {
    montar();

    expect(screen.getByRole("combobox", { name: "Prioridade" })).toHaveTextContent(
      "Média"
    );
  });

  it("troca o valor pela lista aberta", async () => {
    const onValorChange = montar();

    await userEvent.click(screen.getByRole("combobox", { name: "Prioridade" }));
    await userEvent.click(screen.getByRole("option", { name: "Urgente" }));

    expect(onValorChange).toHaveBeenCalledWith("urgente");
  });

  it("abre com o teclado", async () => {
    montar();
    const combo = screen.getByRole("combobox", { name: "Prioridade" });

    combo.focus();
    await userEvent.keyboard("{Enter}");

    expect(await screen.findByRole("listbox")).toBeInTheDocument();
  });
});

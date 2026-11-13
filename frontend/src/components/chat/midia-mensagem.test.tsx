import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";
import { MidiaMensagem } from "@/components/chat/midia-mensagem";

vi.mock("@/lib/api", () => ({
  api: {
    blob: vi.fn(),
  },
}));

const blobMock = vi.mocked(api.blob);

beforeEach(() => {
  // jsdom não implementa createObjectURL/revokeObjectURL
  URL.createObjectURL = vi.fn(() => "blob:http://localhost/teste");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  blobMock.mockReset();
});

describe("MidiaMensagem", () => {
  it("não renderiza nada quando a mensagem não tem url_arquivo", () => {
    const { container } = render(
      <MidiaMensagem
        chatId="chat_1"
        mensagem={{ id: "msg_1", tipo: "texto", conteudo: "Oi" }}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("exibe a imagem com o alt derivado do conteudo", async () => {
    blobMock.mockResolvedValue(new Blob(["x"], { type: "image/png" }));

    render(
      <MidiaMensagem
        chatId="chat_1"
        mensagem={{
          id: "msg_2",
          tipo: "imagem",
          conteudo: "Foto do produto",
          url_arquivo: "appwrite://midias/arquivo.png",
        }}
      />
    );

    const img = await screen.findByRole("img", {
      name: "Foto do produto",
    });
    expect(img).toHaveAttribute("src", "blob:http://localhost/teste");
  });

  it("avisa quando o download da mídia falha", async () => {
    blobMock.mockRejectedValue(new Error("falha"));

    render(
      <MidiaMensagem
        chatId="chat_1"
        mensagem={{
          id: "msg_3",
          tipo: "documento",
          url_arquivo: "appwrite://midias/doc.pdf",
        }}
      />
    );

    expect(await screen.findByText("(mídia indisponível)")).toBeInTheDocument();
  });
});

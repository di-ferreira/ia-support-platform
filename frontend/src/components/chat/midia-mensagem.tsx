"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

type MensagemMidia = {
  id: string;
  tipo: string;
  conteudo?: string | null;
  url_arquivo?: string | null;
};

export function MidiaMensagem({
  chatId,
  mensagem,
}: {
  chatId: string;
  mensagem: MensagemMidia;
}) {
  const ehMidiaAppwrite = mensagem.url_arquivo?.startsWith("appwrite://midias/");
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    if (!ehMidiaAppwrite) return;
    let url: string | null = null;
    let cancelado = false;
    api
      .blob(`/chats/${chatId}/mensagens/${mensagem.id}/arquivo`)
      .then((blob) => {
        if (cancelado) return;
        url = URL.createObjectURL(blob);
        setObjectUrl(url);
        setCarregando(false);
      })
      .catch(() => {
        if (!cancelado) {
          setErro(true);
          setCarregando(false);
        }
      });
    return () => {
      cancelado = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [ehMidiaAppwrite, chatId, mensagem.id]);

  if (!ehMidiaAppwrite) return null;

  if (erro) {
    return (
      <span className="block text-xs text-neutral-500">
        (mídia indisponível)
      </span>
    );
  }
  if (carregando || !objectUrl) return null;

  if (mensagem.tipo === "imagem" || mensagem.tipo === "sticker") {
    return (
      <img
        src={objectUrl}
        alt={mensagem.conteudo || "Imagem recebida"}
        className="max-h-64 rounded"
      />
    );
  }
  if (mensagem.tipo === "audio") {
    return <audio controls src={objectUrl} className="max-w-full" />;
  }
  return (
    <a href={objectUrl} download={mensagem.id} className="underline">
      Baixar arquivo
    </a>
  );
}

"""Armazenamento de mídias do WhatsApp no Appwrite Storage (gaps 00-12, 02-6).

Recebe o bloco de mídia repassado pelo n8n no webhook (`midia`) e devolve a
referência `appwrite://midias/<file_id>` a persistir em `mensagens.url_arquivo`.

`midia` tem duas formas:
- `dict {key, message}`: envelope bruto da Evolution — os bytes são baixados
  via `getBase64FromMediaMessage` da API da Evolution;
- `str`: base64 ou data URL — decodificado diretamente, sem chamar a Evolution.
  Uma `str` que começa com `{` é tratada como o envelope JSON serializado
  (o n8n/HTTP pode serializar o payload) e é normalizada de volta a `dict`
  antes do fluxo; se a conversão falhar, cai no caminho base64.

Best-effort: qualquer falha loga warning e devolve `None` — o webhook segue
201 sem `url_arquivo`.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import re
from uuid import uuid4

from app.appwrite.storage import StorageService
from app.core.config import settings
from app.services.evolution_service import EvolutionService

logger = logging.getLogger(__name__)

MIMES_PADRAO = {
    "imagem": "image/jpeg",
    "audio": "audio/ogg",
    "documento": "application/octet-stream",
}

_ROTULOS = {
    "imagem": "[imagem]",
    "audio": "[áudio]",
    "documento": "[documento]",
}

# Ordem importa: a primeira chave presente no bloco `message` define a mídia.
_BLOCOS_MIDIA = (
    "imageMessage",
    "audioMessage",
    "documentMessage",
    "videoMessage",
    "stickerMessage",
)

_DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,")


def _rotulo_para(tipo: str) -> str:
    return _ROTULOS.get(tipo, f"[{tipo}]")


def _mime_padrao(tipo: str | None) -> str:
    return MIMES_PADRAO.get(tipo or "", "application/octet-stream")


def _nome_gerado(tipo: str | None) -> str:
    return f"{tipo or 'midia'}-{uuid4().hex[:8]}"


def _limpar_base64(valor: str) -> str:
    """Remove o cabeçalho `data:<mime>;base64,` quando presente."""
    return valor.split(",", 1)[1] if "," in valor else valor


class MidiaService:
    """Baixa e armazena mídias de WhatsApp (best-effort, nunca derruba o webhook).

    O parâmetro `repos` é aceito por consistência com os demais serviços da
    camada (padrão de injeção do projeto); este serviço não o usa.
    """

    def __init__(
        self,
        repos: object | None = None,
        evolution: EvolutionService | None = None,
        storage: StorageService | None = None,
    ) -> None:
        self.repos = repos
        self.evolution = evolution if evolution is not None else EvolutionService()
        self.storage = storage if storage is not None else StorageService()

    @staticmethod
    def extrair(midia: dict | str, tipo: str | None = None) -> tuple[str, str]:
        """Devolve `(filename, mime)` do bloco de mídia.

        `dict`: nome/mime vêm do primeiro bloco de mídia presente em
        `midia["message"]` (`fileName`/`mimetype`), com fallback gerado.
        `str`: mime do cabeçalho do data URL (quando houver) ou default do
        tipo; nome sempre gerado.
        """
        if isinstance(midia, str):
            match = _DATA_URL_RE.match(midia)
            mime = match.group("mime") if match else _mime_padrao(tipo)
            return _nome_gerado(tipo), mime
        message = midia.get("message") or {}
        for chave in _BLOCOS_MIDIA:
            bloco = message.get(chave)
            if bloco:
                mime = bloco.get("mimetype") or _mime_padrao(tipo)
                return bloco.get("fileName") or _nome_gerado(tipo), mime
        return _nome_gerado(tipo), _mime_padrao(tipo)

    @staticmethod
    def _normalizar_midia(midia: dict | str) -> dict | str:
        """Normaliza um envelope serializado em string JSON para `dict`.

        O n8n/HTTP pode serializar o payload antes de chegar aqui; base64
        puro não começa com `{`, então `json.loads` que falha cai de volta
        no caminho base64.
        """
        if isinstance(midia, str) and midia.strip().startswith("{"):
            try:
                return json.loads(midia)
            except json.JSONDecodeError:
                logger.warning("Midia: payload string não é JSON válido; tentando base64")
        return midia

    @staticmethod
    def _decodificar_str(midia: str) -> bytes | None:
        try:
            return base64.b64decode(_limpar_base64(midia))
        except (binascii.Error, ValueError) as exc:
            logger.warning("Midia: base64 inválido na payload do webhook: %s", exc)
            return None

    async def _baixar_evolution(
        self, midia: dict, message_id: str | None
    ) -> bytes | None:
        """Baixa os bytes da mídia pela API da Evolution (best-effort)."""
        try:
            # A API v2 da Evolution exige a `key` DENTRO de `message`
            # (`message.key.id`); fora de `message` a chamada é rejeitada.
            resposta = await self.evolution._request(
                "POST",
                f"/chat/getBase64FromMediaMessage/{settings.evolution_instance_name}",
                json={
                    "message": {
                        **(midia.get("message") or {}),
                        "key": midia.get("key") or {"id": message_id},
                    },
                    "convertToMp4": False,
                },
            )
        except Exception as exc:
            logger.warning("Evolution: falha ao baixar mídia %s: %s", message_id, exc)
            return None
        bloco = resposta.get("media") if isinstance(resposta, dict) else None
        base64_str = bloco.get("base64") if isinstance(bloco, dict) else None
        if not base64_str and isinstance(resposta, dict):
            base64_str = resposta.get("base64") or resposta.get("data")
        if not base64_str:
            logger.warning("Evolution: resposta sem base64 da mídia %s", message_id)
            return None
        try:
            return base64.b64decode(_limpar_base64(str(base64_str)))
        except (binascii.Error, ValueError) as exc:
            logger.warning("Evolution: base64 inválido da mídia %s: %s", message_id, exc)
            return None

    async def armazenar(
        self,
        midia: dict | str,
        tipo: str,
        whatsapp_message_id: str | None = None,
        conteudo: str | None = None,
    ) -> tuple[str, str] | None:
        """Baixa e salva a mídia; devolve `(url, conteudo)` ou `None` em falha.

        A url é `appwrite://midias/<file_id>`; o conteudo volta como recebido
        quando já há texto (ex.: caption), ou como rótulo `[imagem]`/
        `[áudio]`/`[documento]` quando vazio.
        """
        try:
            midia = self._normalizar_midia(midia)
            if isinstance(midia, str):
                dados = self._decodificar_str(midia)
            else:
                dados = await self._baixar_evolution(midia, whatsapp_message_id)
            if dados is None:
                return None
            filename, mime = self.extrair(midia, tipo)
            url = await self.storage.salvar(uuid4().hex, dados, filename, mime)
            if not conteudo or not conteudo.strip():
                conteudo = _rotulo_para(tipo)
            return url, conteudo
        except Exception as exc:
            logger.warning(
                "Midia: falha ao armazenar %s (whatsapp_message_id=%s): %s",
                tipo,
                whatsapp_message_id,
                exc,
            )
            return None

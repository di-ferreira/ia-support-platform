from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.appwrite.repositories import Repositories
from app.models.chat import StatusChat
from app.models.mensagem import RemetenteMensagem


def _val(x):
    return x.value if hasattr(x, "value") else x


class WebhookService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    async def receber_mensagem(self, data: dict) -> dict:
        whatsapp = data.get("whatsapp_number")
        chat_id = data.get("chat_id")

        if whatsapp and "@" in whatsapp:
            whatsapp = whatsapp.split("@")[0]

        if chat_id:
            chat = await self.repos.chats.get(chat_id)
        else:
            chat = await self.repos.chats.get_by_whatsapp(whatsapp)

        if not chat:
            cliente = await self.repos.clientes.get_by_telefone(whatsapp)
            if not cliente:
                cliente = await self.repos.clientes.create(
                    {
                        "nome": f"Novo {whatsapp[-8:]}",
                        "documento": whatsapp,
                        "telefone": whatsapp,
                    }
                )
            chat = await self.repos.chats.create(
                {
                    "cliente_id": cliente["id"],
                    "whatsapp_number": whatsapp,
                    "status": StatusChat.novo.value,
                }
            )

        chat_id = chat["id"]
        remetente_str = data.get("remetente", "cliente")
        remetente = (
            RemetenteMensagem(remetente_str)
            if remetente_str in tuple(e.value for e in RemetenteMensagem)
            else RemetenteMensagem.cliente
        )

        mensagem = await self.repos.mensagens.create(
            {
                "chat_id": chat_id,
                "remetente": remetente.value,
                "tipo": _val(data.get("tipo", "texto")),
                "conteudo": data.get("conteudo"),
                "url_arquivo": data.get("url_arquivo"),
            }
        )
        await self.repos.chats.update(
            chat_id, {"ultima_mensagem_em": datetime.now(UTC).isoformat()}
        )
        return mensagem

    async def atualizar_status(self, chat_id: str, novo_status: StatusChat) -> dict:
        chat = await self.repos.chats.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )
        await self.repos.chats.update(chat_id, {"status": _val(status)})
        return await self.repos.chats.get(chat_id)

    async def atualizar_cliente(self, chat_id: str, data: dict) -> dict:
        chat = await self.repos.chats.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )
        cliente = await self.repos.clientes.get(chat["cliente_id"])
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado para este chat",
            )
        update = {
            field: data[field]
            for field in ("nome", "documento", "email", "telefone", "endereco", "versao_erp")
            if data.get(field) is not None
        }
        if update:
            await self.repos.clientes.update(cliente["id"], update)
        return await self.repos.clientes.get(cliente["id"])

    async def salvar_diagnostico(self, data: dict) -> dict:
        chat_id = data.get("chat_id")
        chat = await self.repos.chats.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )

        diagnostico = await self.repos.ia_diagnosticos.create(
            {
                "chat_id": chat_id,
                "status_ia": _val(data["status_ia"]),
                "resumo": data.get("resumo"),
                "solucao": data.get("solucao"),
                "causa_provavel": data.get("causa_provavel"),
                "confianca": data.get("confianca"),
                "modelo_usado": data.get("modelo_usado"),
                "tokens_usados": data.get("tokens_usados"),
            }
        )
        await self.repos.chats.update(
            chat_id,
            {
                "resumo_problema": data.get("resumo"),
                "solucao_sugerida_ia": data.get("solucao"),
                "causa_provavel": data.get("causa_provavel"),
                "nivel_confianca_ia": data.get("confianca"),
            },
        )
        return diagnostico

    async def obter_contexto(self, chat_id: str) -> dict | None:
        chat = await self.repos.chats.get(chat_id)
        if not chat:
            return None

        msgs = await self.repos.mensagens.list_by_chat(chat_id)
        ultima_msg = max(msgs, key=lambda m: m["created_at"]) if msgs else None
        cliente = await self.repos.clientes.get(chat["cliente_id"])

        return {
            "chat_id": chat["id"],
            "status": chat["status"],
            "cliente_id": chat["cliente_id"],
            "cliente_nome": cliente["nome"] if cliente else None,
            "whatsapp_number": chat["whatsapp_number"],
            "ultima_mensagem": ultima_msg["conteudo"] if ultima_msg else None,
        }

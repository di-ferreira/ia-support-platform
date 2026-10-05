from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.appwrite.repositories import Repositories
from app.models.chat import PrioridadeChat, StatusChat

STATUS_TRANSITIONS = {
    StatusChat.novo: [StatusChat.ia_analisando],
    StatusChat.ia_analisando: [
        StatusChat.aguardando_cliente,
        StatusChat.aguardando_humano_com_solucao,
        StatusChat.aguardando_humano_sem_solucao,
    ],
    StatusChat.aguardando_cliente: [
        StatusChat.ia_analisando,
        StatusChat.em_atendimento,
        StatusChat.resolvido,
        StatusChat.encerrado,
    ],
    StatusChat.aguardando_humano_com_solucao: [StatusChat.em_atendimento],
    StatusChat.aguardando_humano_sem_solucao: [StatusChat.em_atendimento],
    StatusChat.em_atendimento: [
        StatusChat.aguardando_cliente,
        StatusChat.resolvido,
        StatusChat.encerrado,
    ],
    StatusChat.resolvido: [StatusChat.ia_analisando, StatusChat.encerrado],
    StatusChat.encerrado: [],
}


class ChatService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    async def listar(
        self,
        skip: int = 0,
        limit: int = 50,
        status: StatusChat | None = None,
        cliente_id: str | None = None,
        prioridade: PrioridadeChat | None = None,
        user: dict | None = None,
    ) -> tuple[list[dict], int]:
        chats = await self.repos.chats.list_all()

        if user and user["perfil"] == "atendente":
            def pode_ver(c: dict) -> bool:
                if c["atendente_id"] == user["id"]:
                    return True
                return (
                    c["atendente_id"] is None
                    and (c["setor_alvo"] is None or c["setor_alvo"] == user["setor"])
                )

            chats = [c for c in chats if pode_ver(c)]
        if status:
            chats = [c for c in chats if c["status"] == status.value]
        if cliente_id:
            chats = [c for c in chats if c["cliente_id"] == cliente_id]
        if prioridade:
            chats = [c for c in chats if c["prioridade"] == prioridade.value]

        chats.sort(key=lambda c: c.get("ultima_mensagem_em") or "", reverse=True)
        total = len(chats)
        page = chats[skip : skip + limit]

        result = []
        for c in page:
            cliente = await self.repos.clientes.get(c["cliente_id"])
            msgs = await self.repos.mensagens.list_by_chat(c["id"])
            ultima = max(msgs, key=lambda m: m["created_at"]) if msgs else None
            result.append(
                {
                    "id": c["id"],
                    "cliente_id": c["cliente_id"],
                    "cliente_nome": cliente["nome"] if cliente else None,
                    "status": c["status"],
                    "prioridade": c["prioridade"],
                    "resumo_problema": c["resumo_problema"],
                    "solucao_sugerida_ia": c["solucao_sugerida_ia"],
                    "nivel_confianca_ia": c["nivel_confianca_ia"],
                    "necessita_humano": c["necessita_humano"],
                    "atendente_id": c["atendente_id"],
                    "setor_alvo": c["setor_alvo"],
                    "ultima_mensagem_em": c["ultima_mensagem_em"],
                    "ultima_mensagem": ultima["conteudo"] if ultima else None,
                    "created_at": c["created_at"],
                }
            )
        return result, total

    async def obter(self, chat_id: str) -> dict:
        chat = await self.repos.chats.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )
        return chat

    async def criar(self, data: dict) -> dict:
        if not await self.repos.clientes.get(data["cliente_id"]):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
            )
        return await self.repos.chats.create(
            {
                "cliente_id": data["cliente_id"],
                "loja_id": data.get("loja_id"),
                "whatsapp_number": data.get("whatsapp_number"),
                "status": StatusChat.novo.value,
                "prioridade": PrioridadeChat.media.value,
            }
        )

    async def atualizar_status(self, chat_id: str, novo_status: StatusChat) -> dict:
        chat = await self.obter(chat_id)
        if novo_status not in STATUS_TRANSITIONS.get(chat["status"], []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transição inválida: {chat['status']} → {novo_status.value}",
            )
        data = {"status": novo_status.value}
        if novo_status in (StatusChat.resolvido, StatusChat.encerrado):
            data["ultima_mensagem_em"] = datetime.now(UTC).isoformat()
        return await self.repos.chats.update(chat_id, data)

    async def assinar(self, chat_id: str, atendente_id: str) -> dict:
        chat = await self.obter(chat_id)
        data = {"atendente_id": atendente_id}
        if chat["status"] == StatusChat.novo:
            data["status"] = StatusChat.em_atendimento.value
        return await self.repos.chats.update(chat_id, data)

    async def definir_prioridade(
        self, chat_id: str, prioridade: PrioridadeChat
    ) -> dict:
        await self.obter(chat_id)
        return await self.repos.chats.update(chat_id, {"prioridade": prioridade.value})

    async def pegar(self, chat_id: str, atendente_id: str) -> dict:
        chat = await self.obter(chat_id)
        if chat["atendente_id"] is not None and chat["atendente_id"] != atendente_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este chamado já está com outro atendente",
            )
        data = {"atendente_id": atendente_id, "setor_alvo": None}
        if chat["status"] == StatusChat.novo:
            data["status"] = StatusChat.em_atendimento.value
        return await self.repos.chats.update(chat_id, data)

    async def transferir(self, chat_id: str, novo_atendente_id: str, user: dict) -> dict:
        chat = await self.obter(chat_id)
        if user["perfil"] == "atendente" and chat["atendente_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode transferir chamados seus",
            )
        if not await self.repos.atendentes.get(novo_atendente_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado"
            )
        data = {"atendente_id": novo_atendente_id, "setor_alvo": None}
        if chat["status"] in (
            "AGUARDANDO_HUMANO_COM_SOLUCAO",
            "AGUARDANDO_HUMANO_SEM_SOLUCAO",
            "NOVO",
        ):
            data["status"] = StatusChat.em_atendimento.value
        return await self.repos.chats.update(chat_id, data)

    async def transferir_grupo(self, chat_id: str, setor: str, user: dict) -> dict:
        chat = await self.obter(chat_id)
        if user["perfil"] == "atendente" and chat["atendente_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode transferir chamados seus",
            )
        data = {"atendente_id": None, "setor_alvo": setor}
        if chat["status"] == StatusChat.em_atendimento:
            data["status"] = StatusChat.novo.value
        return await self.repos.chats.update(chat_id, data)

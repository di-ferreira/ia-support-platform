import logging

from app.appwrite.repositories import Repositories
from app.core.config import settings
from app.models.chat import StatusChat
from app.models.mensagem import RemetenteMensagem
from app.services.evolution_service import EvolutionService
from app.services.mensagem_service import MensagemService

logger = logging.getLogger(__name__)


class WhatsappEnvioError(Exception):
    """Falha de transporte no envio via WhatsApp (vira 502 na rota)."""


class WhatsappService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    async def enviar_para_numero(self, numero: str, conteudo: str) -> tuple[str, str]:
        """Salva a mensagem e a envia via WhatsApp, devolvendo `(chat_id, mensagem_id)`.

        Resolve ou cria o cliente pelo telefone, reusa o chat ativo mais recente
        (fora de `ENCERRADO`/`RESOLVIDO`) ou cria um, registra a mensagem como
        atendente e dispara o envio pela Evolution.
        """
        cliente = await self.repos.clientes.get_by_telefone(numero)
        if not cliente:
            cliente = await self.repos.clientes.create({
                "nome": f"Novo {numero[-8:]}",
                "documento": numero,
                "telefone": numero,
            })

        ativas = [
            c
            for c in await self.repos.chats.list_by("cliente_id", cliente["id"])
            if c["status"] not in (StatusChat.encerrado.value, StatusChat.resolvido.value)
        ]
        ativas.sort(key=lambda c: c["created_at"] or "", reverse=True)
        chat = ativas[0] if ativas else None
        if chat is None:
            chat = await self.repos.chats.create({
                "cliente_id": cliente["id"],
                "whatsapp_number": numero,
            })

        mensagem = await MensagemService(self.repos).enviar({
            "chat_id": chat["id"],
            "remetente": RemetenteMensagem.atendente,
            "tipo": "texto",
            "conteudo": conteudo,
        })

        try:
            await EvolutionService().enviar_texto(
                instance_name=settings.evolution_instance_name,
                number=numero,
                text=conteudo,
            )
        except Exception as exc:
            logger.warning("Falha ao enviar mensagem via WhatsApp: %s", exc)
            raise WhatsappEnvioError from exc

        return chat["id"], mensagem["id"]

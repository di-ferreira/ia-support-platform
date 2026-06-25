import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StatusChat(str, enum.Enum):
    novo = "NOVO"
    ia_analisando = "IA_ANALISANDO"
    aguardando_cliente = "AGUARDANDO_CLIENTE"
    aguardando_humano_com_solucao = "AGUARDANDO_HUMANO_COM_SOLUCAO"
    aguardando_humano_sem_solucao = "AGUARDANDO_HUMANO_SEM_SOLUCAO"
    em_atendimento = "EM_ATENDIMENTO"
    resolvido = "RESOLVIDO"
    encerrado = "ENCERRADO"


class PrioridadeChat(str, enum.Enum):
    baixa = "baixa"
    media = "media"
    alta = "alta"
    urgente = "urgente"


class Chat(Base):
    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id"), index=True)
    loja_id: Mapped[int | None] = mapped_column(ForeignKey("loja.id"))
    atendente_id: Mapped[int | None] = mapped_column(ForeignKey("atendente.id"))

    status: Mapped[StatusChat] = mapped_column(
        Enum(StatusChat), default=StatusChat.novo, index=True
    )
    prioridade: Mapped[PrioridadeChat] = mapped_column(
        Enum(PrioridadeChat), default=PrioridadeChat.media
    )

    resumo_problema: Mapped[str | None] = mapped_column(Text)
    solucao_sugerida_ia: Mapped[str | None] = mapped_column(Text)
    causa_provavel: Mapped[str | None] = mapped_column(Text)
    nivel_confianca_ia: Mapped[float | None] = mapped_column(Float)
    necessita_humano: Mapped[bool | None] = mapped_column(Boolean)

    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    ultima_mensagem_em: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="chats")
    atendente: Mapped["Atendente"] = relationship()
    mensagens: Mapped[list["Mensagem"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    diagnosticos: Mapped[list["IADiagnostico"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="chat_tag", back_populates="chats"
    )

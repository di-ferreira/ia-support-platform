import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoMensagem(str, enum.Enum):
    texto = "texto"
    audio = "audio"
    documento = "documento"
    imagem = "imagem"


class RemetenteMensagem(str, enum.Enum):
    cliente = "cliente"
    ia = "ia"
    atendente = "atendente"
    sistema = "sistema"


class Mensagem(Base):
    __tablename__ = "mensagem"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id"), index=True)
    remetente: Mapped[RemetenteMensagem] = mapped_column(
        Enum(RemetenteMensagem)
    )
    tipo: Mapped[TipoMensagem] = mapped_column(
        Enum(TipoMensagem), default=TipoMensagem.texto
    )
    conteudo: Mapped[str | None] = mapped_column(Text)
    url_arquivo: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    chat: Mapped["Chat"] = relationship(back_populates="mensagens")

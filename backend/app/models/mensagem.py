from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RemetenteMensagem, TipoMensagem  # noqa: F401 (reexport histórico)

if TYPE_CHECKING:
    from app.models.chat import Chat

__all__ = ["Mensagem", "RemetenteMensagem", "TipoMensagem"]


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
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    chat: Mapped["Chat"] = relationship(back_populates="mensagens")

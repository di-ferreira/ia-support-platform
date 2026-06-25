from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Historico(Base):
    __tablename__ = "historico"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id"), index=True)
    campo_alterado: Mapped[str] = mapped_column(String(100))
    valor_anterior: Mapped[str | None] = mapped_column(Text)
    valor_novo: Mapped[str | None] = mapped_column(Text)
    alterado_por: Mapped[str] = mapped_column(String(255))
    alterado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chat: Mapped["Chat"] = relationship(back_populates="historico")

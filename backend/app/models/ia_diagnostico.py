from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import StatusIA  # noqa: F401 (reexport histórico)

if TYPE_CHECKING:
    from app.models.chat import Chat

__all__ = ["IADiagnostico", "StatusIA"]


class IADiagnostico(Base):
    __tablename__ = "ia_diagnostico"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id"), index=True)
    status_ia: Mapped[StatusIA] = mapped_column(Enum(StatusIA))
    resumo: Mapped[str | None] = mapped_column(Text)
    solucao: Mapped[str | None] = mapped_column(Text)
    causa_provavel: Mapped[str | None] = mapped_column(Text)
    confianca: Mapped[float | None] = mapped_column(Float)
    modelo_usado: Mapped[str | None] = mapped_column(String(100))
    tokens_usados: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chat: Mapped["Chat"] = relationship(back_populates="diagnosticos")

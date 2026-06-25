import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StatusIA(str, enum.Enum):
    resolvido_pela_ia = "RESOLVIDO_PELA_IA"
    transferir_com_solucao = "TRANSFERIR_COM_SOLUCAO"
    transferir_sem_solucao = "TRANSFERIR_SEM_SOLUCAO"


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
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chat: Mapped["Chat"] = relationship(back_populates="diagnosticos")

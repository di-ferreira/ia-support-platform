import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PerfilAtendente(str, enum.Enum):
    admin = "admin"
    supervisor = "supervisor"
    atendente = "atendente"


class Atendente(Base):
    __tablename__ = "atendente"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hash_senha: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[PerfilAtendente] = mapped_column(
        Enum(PerfilAtendente), default=PerfilAtendente.atendente
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

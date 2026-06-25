import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255))
    documento: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    endereco: Mapped[str | None] = mapped_column(Text)
    versao_erp: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    lojas: Mapped[list["Loja"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    chats: Mapped[list["Chat"]] = relationship(back_populates="cliente")


class Loja(Base):
    __tablename__ = "loja"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id"))
    nome: Mapped[str] = mapped_column(String(255))
    documento: Mapped[str | None] = mapped_column(String(20))
    endereco: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cliente: Mapped["Cliente"] = relationship(back_populates="lojas")

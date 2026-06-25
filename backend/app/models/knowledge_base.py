import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CategoriaConhecimento(str, enum.Enum):
    fiscal = "fiscal"
    estoque = "estoque"
    compras = "compras"
    vendas = "vendas"
    financeiro = "financeiro"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(255))
    conteudo: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[CategoriaConhecimento] = mapped_column(
        Enum(CategoriaConhecimento)
    )
    tipo_arquivo: Mapped[str | None] = mapped_column(String(50))
    url_arquivo: Mapped[str | None] = mapped_column(String(500))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

chat_tag = Table(
    "chat_tag",
    Base.metadata,
    Column("chat_id", ForeignKey("chat.id"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    cor: Mapped[str | None] = mapped_column(String(7))

    chats = relationship("Chat", secondary=chat_tag, back_populates="tags")

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from app.core.database import Base

chat_tag = Table(
    "chat_tag",
    Base.metadata,
    Column("chat_id", ForeignKey("chat.id"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tag"

    id: int = Column(Integer, primary_key=True)
    nome: str = Column(String(100), nullable=False)
    cor: str | None = Column(String(7))

    chats = relationship("Chat", secondary=chat_tag, back_populates="tags")

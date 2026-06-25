from datetime import datetime

from pydantic import BaseModel

from app.models.knowledge_base import CategoriaConhecimento


class KnowledgeBaseCreate(BaseModel):
    titulo: str
    conteudo: str | None = None
    categoria: CategoriaConhecimento
    tipo_arquivo: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    titulo: str | None = None
    conteudo: str | None = None
    categoria: CategoriaConhecimento | None = None
    ativo: bool | None = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    titulo: str
    conteudo: str | None = None
    categoria: CategoriaConhecimento
    tipo_arquivo: str | None = None
    url_arquivo: str | None = None
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

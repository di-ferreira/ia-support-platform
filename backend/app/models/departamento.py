"""Taxonomia de domínio de departamentos e roteamento.

Este módulo contém **apenas enums** (sem ORM): ele sobrevive à remoção da
camada SQLAlchemy legada planejada na Trilha R2. Os enums são a fonte
canônica; `app/appwrite/schema.py` deriva as listas de valores deles.
"""

from app.models.enums import CategoriaERP, Intencao  # noqa: F401 (reexport histórico)

__all__ = ["CategoriaERP", "Intencao"]

"""Travas de remoção do caminho morto ORM/Alembic/PostgreSQL (gaps 02-11, 08-7, 09-12).

Garante que os artefatos legados não retornem ao repositório, que as
dependências de ORM sumam da lista de pacotes, que `Settings` não tenha
mais `database_url*` e que a fonte canônica de enums continue sendo
`app.models.enums` (reexportada para as collections Appwrite).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"

_LEGACY_ARTEFATOS = [
    BACKEND / "alembic",
    BACKEND / "alembic.ini",
    BACKEND / "app" / "core" / "database.py",
    REPO_ROOT / "scripts" / "migrate.sh",
    REPO_ROOT / "scripts" / "seed_knowledge_base.py",
]

_LIBS_PROIBIDAS = ("sqlalchemy", "asyncpg", "alembic")


@pytest.mark.parametrize(
    "artefato",
    _LEGACY_ARTEFATOS,
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_artefato_legado_removido(artefato: Path) -> None:
    assert not artefato.exists(), (
        f"Artefato legado de ORM/Alembic retornou ao repositório: {artefato}"
    )


@pytest.mark.parametrize("arquivo", ["pyproject.toml", "requirements.txt"])
def test_lista_pacotes_sem_orm(arquivo: str) -> None:
    conteudo = (BACKEND / arquivo).read_text(encoding="utf-8")
    ofensas = [lib for lib in _LIBS_PROIBIDAS if lib in conteudo]
    assert not ofensas, f"Dependências de ORM retornaram a {arquivo}: {ofensas}"


def test_settings_sem_database_url() -> None:
    from app.core.config import Settings

    ofensas = [campo for campo in Settings.model_fields if campo.startswith("database_url")]
    assert not ofensas, f"Settings voltou a declarar campos de banco: {ofensas}"
    assert not hasattr(Settings, "active_database_url")


def test_compose_prod_sem_database_url() -> None:
    conteudo = (REPO_ROOT / "infra" / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "DATABASE_URL" not in conteudo, "compose de produção voltou a injetar DATABASE_URL"


def test_sem_imports_de_orm_em_codigo() -> None:
    alvos = [BACKEND / "app", BACKEND / "tests", REPO_ROOT / "scripts"]
    ofensas: list[str] = []
    for raiz in alvos:
        for arquivo in raiz.rglob("*"):
            if arquivo.suffix not in {".py", ".sh"} or "__pycache__" in arquivo.parts:
                continue
            conteudo = arquivo.read_text(encoding="utf-8")
            for lib in _LIBS_PROIBIDAS:
                if re.search(rf"^\s*(?:import|from)\s+{lib}\b", conteudo, re.MULTILINE):
                    ofensas.append(f"{arquivo.relative_to(REPO_ROOT)}: '{lib}'")
    assert not ofensas, "Imports de ORM/Alembic retornaram ao código: " + ", ".join(ofensas)


def test_schema_appwrite_usa_enums_canonicos() -> None:
    from app.appwrite import schema
    from app.models import enums

    # O schema Appwrite consome enums via reexport dos módulos de modelo;
    # todos devem ser exatamente os objetos definidos em app.models.enums.
    for nome in ("StatusIA", "CategoriaConhecimento", "AcaoAuditoria", "StatusOutbox"):
        assert getattr(schema, nome) is getattr(enums, nome), (
            f"{nome} em app/appwrite/schema.py não é o enum canônico de app.models.enums"
        )

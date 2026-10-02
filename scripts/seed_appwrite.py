#!/usr/bin/env python3
"""Seed idempotente do Appwrite: garante o schema e cria o primeiro atendente.

As credenciais vêm de variáveis de ambiente (com defaults):
  SEED_ATENDENTE_EMAIL   (default: admin@emsoft.app)
  SEED_ATENDENTE_SENHA   (default: admin123)
  SEED_ATENDENTE_NOME    (default: Admin)

Rode a partir de `backend/` (o `Settings()` lê `backend/.env`):
  uv run python ../scripts/seed_appwrite.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from appwrite.id import ID

from app.appwrite.bootstrap import ensure_appwrite_schema
from app.appwrite.schema import DB_ID
from app.core.appwrite import build_appwrite_client
from app.core.config import settings
from app.core.security import hash_password
from appwrite.services.databases import Databases

DEFAULT_EMAIL = "admin@emsoft.app"
DEFAULT_SENHA = "admin123"
DEFAULT_NOME = "Admin"


def _existing_email(databases: Databases, email: str) -> bool:
    docs = databases.list_documents(DB_ID, "atendentes").documents
    return any(doc.data.get("email") == email for doc in docs)


def main() -> None:
    if not settings.appwrite_project_id or not settings.appwrite_api_key:
        sys.exit(
            "APPWRITE_PROJECT_ID / APPWRITE_API_KEY ausentes em backend/.env — "
            "crie o project e a API key no console (http://localhost:8020) e preencha o .env."
        )

    email = os.environ.get("SEED_ATENDENTE_EMAIL", DEFAULT_EMAIL)
    senha = os.environ.get("SEED_ATENDENTE_SENHA", DEFAULT_SENHA)
    nome = os.environ.get("SEED_ATENDENTE_NOME", DEFAULT_NOME)

    client = build_appwrite_client()
    databases = Databases(client)

    print("Garantindo schema Appwrite (database + collections + attributes)...")
    ensure_appwrite_schema(databases)

    if _existing_email(databases, email):
        print(f"Atendente com e-mail {email} já existe — seed ignorado.")
        return

    databases.create_document(
        DB_ID,
        "atendentes",
        ID.unique(),
        {
            "nome": nome,
            "email": email,
            "hash_senha": hash_password(senha),
            "perfil": "admin",
            "setor": "Suporte",
            "ativo": True,
        },
    )
    print(f"Seed concluído: atendente admin criado ({email}).")


if __name__ == "__main__":
    main()

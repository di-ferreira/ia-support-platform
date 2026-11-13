"""Pacote de modelos de domínio.

Os enums de domínio vivem em `app.models.enums` (fonte canônica); os
módulos `app.models.<x>` reexportam cada enum por compatibilidade
histórica. A persistência é feita pelo Appwrite
(`app/appwrite/schema.py`); a camada ORM/Postgres foi removida
(gaps 02-11, 08-7 e 09-12).
"""

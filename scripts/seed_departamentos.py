#!/usr/bin/env python3
"""Popula os departamentos iniciais no Appwrite (idempotente)."""

import asyncio
import os
import sys

script_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(script_dir, "..", "backend"))

from app.appwrite.bootstrap import ensure_appwrite_schema  # noqa: E402
from app.appwrite.repositories import Repositories  # noqa: E402
from app.core.appwrite import build_appwrite_client, build_appwrite_databases  # noqa: E402
from app.services.departamento_seed import semear  # noqa: E402


async def main() -> None:
    databases = build_appwrite_databases(build_appwrite_client())
    await asyncio.to_thread(ensure_appwrite_schema, databases)
    relatorio = await semear(Repositories(databases))
    print(
        f"departamentos: {relatorio['criados']} criados, "
        f"{relatorio['atualizados']} atualizados, "
        f"{relatorio['ignorados']} sem alteração"
    )


if __name__ == "__main__":
    asyncio.run(main())

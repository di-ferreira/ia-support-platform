#!/usr/bin/env python3
"""Migra setor/setor_alvo legado para departamento_id.

Uso:
  python scripts/migrate_setor_departamento.py --dry-run
  python scripts/migrate_setor_departamento.py --apply
"""

import argparse
import asyncio
import json
import os
import sys

script_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(script_dir, "..", "backend"))

from app.appwrite.repositories import Repositories  # noqa: E402
from app.core.appwrite import build_appwrite_client, build_appwrite_databases  # noqa: E402
from app.services.migracao_setor_service import migrar  # noqa: E402


async def main(aplicar: bool) -> None:
    repositories = Repositories(build_appwrite_databases(build_appwrite_client()))
    relatorio = await migrar(repositories, aplicar=aplicar)
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    if relatorio["orfaos"]:
        print(
            f"\nATENCAO: {len(relatorio['orfaos'])} documento(s) sem correspondencia "
            "de departamento. Corrija manualmente antes do passo 7."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--dry-run", action="store_true")
    grupo.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(aplicar=args.apply))

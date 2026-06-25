#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

echo "Seeding database..."
python -c "
import asyncio
from app.core.database import async_session, engine, Base
from app.core.security import hash_password
from app.models import *

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        from sqlalchemy import text
        result = await session.execute(text('SELECT COUNT(*) FROM atendente'))
        count = result.scalar()
        if count == 0:
            from app.models.atendente import Atendente
            session.add(Atendente(
                nome='Admin',
                email='admin@emsoft.app',
                hash_senha=hash_password('admin123'),
                perfil='admin',
                ativo=True,
            ))
            session.add(Atendente(
                nome='Suporte',
                email='suporte@emsoft.app',
                hash_senha=hash_password('suporte123'),
                perfil='atendente',
                ativo=True,
            ))
            await session.commit()
            print('Seed completed: admin user created.')
        else:
            print('Seed skipped: data already exists.')

asyncio.run(seed())
"
echo "Done."

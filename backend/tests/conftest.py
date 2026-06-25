from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_session
from app.core.security import hash_password
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as s:
        yield s


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    from app.models.atendente import Atendente

    async with TestSession() as s:
        s.add(
            Atendente(
                nome="Admin",
                email="admin@test.com",
                hash_senha=hash_password("admin123"),
                perfil="admin",
                ativo=True,
            )
        )
        await s.commit()

    resp = await client.post(
        "/auth/login", json={"email": "admin@test.com", "senha": "admin123"}
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def supervisor_token(client: AsyncClient) -> str:
    from app.models.atendente import Atendente

    async with TestSession() as s:
        s.add(
            Atendente(
                nome="Supervisor",
                email="sup@test.com",
                hash_senha=hash_password("sup123"),
                perfil="supervisor",
                ativo=True,
            )
        )
        await s.commit()

    resp = await client.post(
        "/auth/login", json={"email": "sup@test.com", "senha": "sup123"}
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def atendente_token(client: AsyncClient) -> str:
    from app.models.atendente import Atendente

    async with TestSession() as s:
        s.add(
            Atendente(
                nome="Atendente",
                email="atendente@test.com",
                hash_senha=hash_password("ate123"),
                perfil="atendente",
                ativo=True,
            )
        )
        await s.commit()

    resp = await client.post(
        "/auth/login", json={"email": "atendente@test.com", "senha": "ate123"}
    )
    return resp.json()["access_token"]

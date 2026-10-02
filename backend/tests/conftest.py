from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_repositories
from app.appwrite import schema as appwrite_schema
from app.core.config import settings
from app.core.security import hash_password
from app.main import app


def _defaults_for(collection: str) -> dict:
    attrs = appwrite_schema.COLLECTIONS[collection]["attributes"]
    return {a["key"]: a.get("default") for a in attrs}


def _now() -> str:
    return datetime.now(UTC).isoformat()


class FakeStore:
    def __init__(self, collection: str) -> None:
        self.rows: dict[str, dict] = {}
        self._defaults = _defaults_for(collection)

    async def create(self, data: dict) -> dict:
        record = {**self._defaults, **data}
        record["id"] = str(uuid4())
        record["created_at"] = _now()
        record["updated_at"] = _now()
        self.rows[record["id"]] = record
        return dict(record)

    async def get(self, id: str) -> dict | None:
        row = self.rows.get(id)
        return dict(row) if row else None

    async def update(self, id: str, data: dict) -> dict:
        row = self.rows.get(id)
        if row is None:
            raise LookupError(id)
        row.update(data)
        row["updated_at"] = _now()
        self.rows[id] = row
        return dict(row)

    async def delete(self, id: str) -> None:
        self.rows.pop(id, None)

    async def list_all(self) -> list[dict]:
        return [dict(r) for r in self.rows.values()]

    async def get_by(self, key: str, value) -> dict | None:
        for r in self.rows.values():
            if r.get(key) == value:
                return dict(r)
        return None

    async def list_by(self, key: str, value) -> list[dict]:
        return [dict(r) for r in self.rows.values() if r.get(key) == value]


class FakeAtendentes(FakeStore):
    async def get_by_email(self, email: str) -> dict | None:
        return await self.get_by("email", email)


class FakeClientes(FakeStore):
    async def get_by_documento(self, documento: str) -> dict | None:
        return await self.get_by("documento", documento)

    async def get_by_telefone(self, telefone: str) -> dict | None:
        return await self.get_by("telefone", telefone)


class FakeLojas(FakeStore):
    async def list_by_cliente(self, cliente_id: str) -> list[dict]:
        return await self.list_by("cliente_id", cliente_id)


class FakeChats(FakeStore):
    async def get_by_whatsapp(self, whatsapp_number: str) -> dict | None:
        return await self.get_by("whatsapp_number", whatsapp_number)


class FakeMensagens(FakeStore):
    async def list_by_chat(self, chat_id: str) -> list[dict]:
        return await self.list_by("chat_id", chat_id)


class FakeIADiagnosticos(FakeStore):
    async def get_by_chat(self, chat_id: str) -> dict | None:
        return await self.get_by("chat_id", chat_id)


class FakeRepositories:
    def __init__(self) -> None:
        self.databases = None
        self.atendentes = FakeAtendentes("atendentes")
        self.clientes = FakeClientes("clientes")
        self.lojas = FakeLojas("lojas")
        self.chats = FakeChats("chats")
        self.mensagens = FakeMensagens("mensagens")
        self.ia_diagnosticos = FakeIADiagnosticos("ia_diagnosticos")
        self.knowledge_bases = FakeStore("knowledge_bases")


@pytest.fixture
def fake_repos() -> FakeRepositories:
    return FakeRepositories()


@pytest.fixture(autouse=True)
def webhook_secret():
    settings.webhook_secret = "test-webhook-secret"
    yield
    settings.webhook_secret = None


@pytest_asyncio.fixture
async def client(fake_repos: FakeRepositories) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_repositories] = lambda: fake_repos
    app.state.repositories = fake_repos
    app.state.appwrite = None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _login_token(client: AsyncClient, email: str, senha: str, perfil: str, nome: str) -> str:
    resp = await client.post(
        "/auth/login", json={"email": email, "senha": senha}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, fake_repos: FakeRepositories) -> str:
    await fake_repos.atendentes.create(
        {
            "nome": "Admin",
            "email": "admin@test.com",
            "hash_senha": hash_password("admin123"),
            "perfil": "admin",
        }
    )
    return await _login_token(client, "admin@test.com", "admin123", "admin", "Admin")


@pytest_asyncio.fixture
async def supervisor_token(client: AsyncClient, fake_repos: FakeRepositories) -> str:
    await fake_repos.atendentes.create(
        {
            "nome": "Supervisor",
            "email": "sup@test.com",
            "hash_senha": hash_password("sup123"),
            "perfil": "supervisor",
        }
    )
    return await _login_token(client, "sup@test.com", "sup123", "supervisor", "Supervisor")


@pytest_asyncio.fixture
async def atendente_token(client: AsyncClient, fake_repos: FakeRepositories) -> str:
    await fake_repos.atendentes.create(
        {
            "nome": "Atendente",
            "email": "atendente@test.com",
            "hash_senha": hash_password("ate123"),
            "perfil": "atendente",
        }
    )
    return await _login_token(client, "atendente@test.com", "ate123", "atendente", "Atendente")

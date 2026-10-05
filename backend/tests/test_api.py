import pytest

from app.core.security import hash_password


async def seed_client(client, token, nome="Auto Peças Ltda", documento="11222333000181") -> str:
    resp = await client.post(
        "/clientes",
        json={"nome": nome, "documento": documento},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def seed_chat(client, token, cliente_id: str) -> str:
    resp = await client.post(
        "/chats",
        json={"cliente_id": cliente_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def seed_client_direct(fake_repos, nome="Teste", documento="11222333000181") -> str:
    """Cria um cliente direto no repositório, sem passar pela rota (permissoes)."""
    rec = await fake_repos.clientes.create({"nome": nome, "documento": documento})
    return rec["id"]


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_login_success(client, fake_repos):
    await fake_repos.atendentes.create(
        {
            "nome": "Admin",
            "email": "admin@test.com",
            "hash_senha": hash_password("admin123"),
            "perfil": "admin",
        }
    )
    resp = await client.post(
        "/auth/login", json={"email": "admin@test.com", "senha": "admin123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid(client):
    resp = await client.post(
        "/auth/login", json={"email": "noone@test.com", "senha": "wrong"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client, admin_token):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_refresh_token_rejected_as_access(client, fake_repos):
    await fake_repos.atendentes.create(
        {
            "nome": "Admin",
            "email": "admin@test.com",
            "hash_senha": hash_password("admin123"),
            "perfil": "admin",
        }
    )
    login = await client.post(
        "/auth/login", json={"email": "admin@test.com", "senha": "admin123"}
    )
    refresh_token = login.json()["refresh_token"]
    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_access_token_rejected_at_refresh(client, fake_repos):
    await fake_repos.atendentes.create(
        {
            "nome": "Admin",
            "email": "admin@test.com",
            "hash_senha": hash_password("admin123"),
            "perfil": "admin",
        }
    )
    login = await client.post(
        "/auth/login", json={"email": "admin@test.com", "senha": "admin123"}
    )
    access_token = login.json()["access_token"]
    resp = await client.post(
        "/auth/refresh", json={"refresh_token": access_token}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_cliente(client, admin_token):
    resp = await client.post(
        "/clientes",
        json={"nome": "Auto Peças Ltda", "documento": "11222333000181"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["nome"] == "Auto Peças Ltda"


@pytest.mark.asyncio
async def test_list_clientes_empty(client, admin_token):
    resp = await client.get(
        "/clientes", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_chat(client, admin_token):
    cliente_id = await seed_client(client, admin_token)
    resp = await client.post(
        "/chats",
        json={"cliente_id": cliente_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "NOVO"


@pytest.mark.asyncio
async def test_create_message(client, admin_token):
    cliente_id = await seed_client(client, admin_token)
    chat_id = await seed_chat(client, admin_token, cliente_id)
    resp = await client.post(
        f"/chats/{chat_id}/mensagens",
        json={"remetente": "cliente", "tipo": "texto", "conteudo": "NF-e rejeitada"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["conteudo"] == "NF-e rejeitada"


@pytest.mark.asyncio
async def test_kanban(client, admin_token):
    cliente_id = await seed_client(client, admin_token)
    await seed_chat(client, admin_token, cliente_id)
    resp = await client.get(
        "/kanban", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["colunas"]) == 7
    novos = [c for c in data["colunas"] if c["status"] == "NOVO"]
    assert len(novos) == 1
    assert len(novos[0]["cards"]) >= 1


@pytest.mark.asyncio
async def test_webhook_message(client, fake_repos):
    from app.core.config import settings

    await fake_repos.clientes.create(
        {"nome": "Cliente Teste", "documento": "5511999999999", "telefone": "5511999999999"}
    )
    headers = {
        "content-type": "application/json",
        "X-Webhook-Secret": settings.webhook_secret,
    }
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "Teste webhook"},
        headers=headers,
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_atendente_cannot_create_cliente(client, atendente_token):
    resp = await client.post(
        "/clientes",
        json={"nome": "Teste", "documento": "11222333000181"},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_atendente_cannot_set_prioridade(client, atendente_token, fake_repos):
    cliente_id = await seed_client_direct(fake_repos)
    chat_id = await seed_chat(client, atendente_token, cliente_id)
    resp = await client.patch(
        f"/chats/{chat_id}/prioridade",
        json={"prioridade": "alta"},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_set_prioridade(client, admin_token):
    cliente_id = await seed_client(client, admin_token)
    chat_id = await seed_chat(client, admin_token, cliente_id)
    resp = await client.patch(
        f"/chats/{chat_id}/prioridade",
        json={"prioridade": "urgente"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["prioridade"] == "urgente"


@pytest.mark.asyncio
async def test_atendente_cannot_assinar_chat(client, atendente_token, fake_repos):
    cliente_id = await seed_client_direct(fake_repos)
    chat_id = await seed_chat(client, atendente_token, cliente_id)
    atendentes = await fake_repos.atendentes.list_all()
    atendente_id = atendentes[0]["id"] if atendentes else "sem-atendente"
    resp = await client.patch(
        f"/chats/{chat_id}/assinar",
        json={"atendente_id": atendente_id},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_supervisor_can_create_cliente(client, supervisor_token):
    resp = await client.post(
        "/clientes",
        json={"nome": "Sup Teste", "documento": "99888777000111"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_knowledge_base_crud(client, admin_token, monkeypatch):
    from app.services import knowledge_base_service, qdrant_service

    async def _ensure_collection():
        return None

    async def _upsert_article(**kwargs):
        return None

    async def _delete_article(artigo_id):
        return None

    class _FakeEmbedder:
        async def embed(self, texto):
            return [0.0] * 768

    monkeypatch.setattr(qdrant_service, "ensure_collection", _ensure_collection)
    monkeypatch.setattr(qdrant_service, "upsert_article", _upsert_article)
    monkeypatch.setattr(qdrant_service, "delete_article", _delete_article)
    monkeypatch.setattr(knowledge_base_service, "get_embedder", lambda: _FakeEmbedder())

    create = await client.post(
        "/knowledge-base",
        json={"titulo": "Erro NF-e", "categoria": "fiscal", "conteudo": "Solução para erro NF-e"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create.status_code == 201
    artigo_id = create.json()["id"]

    get = await client.get(
        f"/knowledge-base/{artigo_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get.status_code == 200

    list_resp = await client.get(
        "/knowledge-base", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    delete = await client.delete(
        f"/knowledge-base/{artigo_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert delete.status_code == 204

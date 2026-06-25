import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_login_success(client, session):
    from app.core.security import hash_password
    from app.models.atendente import Atendente

    session.add(Atendente(nome="Admin", email="admin@test.com", hash_senha=hash_password("admin123"), perfil="admin", ativo=True))
    await session.commit()

    resp = await client.post("/auth/login", json={"email": "admin@test.com", "senha": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid(client):
    resp = await client.post("/auth/login", json={"email": "noone@test.com", "senha": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client, admin_token):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


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
    resp = await client.get("/clientes", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_chat(client, admin_token):
    await test_create_cliente(client, admin_token)
    resp = await client.post(
        "/chats",
        json={"cliente_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "NOVO"


@pytest.mark.asyncio
async def test_create_message(client, admin_token):
    await test_create_cliente(client, admin_token)
    await client.post("/chats", json={"cliente_id": 1}, headers={"Authorization": f"Bearer {admin_token}"})
    resp = await client.post(
        "/chats/1/mensagens",
        json={"remetente": "cliente", "tipo": "texto", "conteudo": "NF-e rejeitada"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["conteudo"] == "NF-e rejeitada"


@pytest.mark.asyncio
async def test_kanban(client, admin_token):
    await test_create_cliente(client, admin_token)
    await client.post("/chats", json={"cliente_id": 1}, headers={"Authorization": f"Bearer {admin_token}"})
    resp = await client.get("/kanban", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["colunas"]) == 7
    novos = [c for c in data["colunas"] if c["status"] == "NOVO"]
    assert len(novos) == 1
    assert len(novos[0]["cards"]) >= 1


@pytest.mark.asyncio
async def test_webhook_message(client, session):
    from app.models.cliente import Cliente

    session.add(Cliente(nome="Cliente Teste", documento="5511999999999", telefone="5511999999999"))
    await session.commit()

    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "Teste webhook"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_atendente_cannot_create_cliente(client, atendente_token, session):
    resp = await client.post(
        "/clientes",
        json={"nome": "Teste", "documento": "11222333000181"},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_atendente_cannot_set_prioridade(client, atendente_token, session):
    from app.models.cliente import Cliente

    session.add(Cliente(nome="Teste", documento="11222333000181"))
    await session.commit()
    await client.post("/chats", json={"cliente_id": 1}, headers={"Authorization": f"Bearer {atendente_token}"})
    resp = await client.patch(
        "/chats/1/prioridade",
        json={"prioridade": "alta"},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_atendente_cannot_assinar_chat(client, atendente_token, session):
    from app.models.cliente import Cliente

    session.add(Cliente(nome="Teste", documento="11222333000181"))
    await session.commit()
    await client.post("/chats", json={"cliente_id": 1}, headers={"Authorization": f"Bearer {atendente_token}"})
    resp = await client.patch(
        "/chats/1/assinar",
        json={"atendente_id": 1},
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
async def test_knowledge_base_crud(client, admin_token):
    create = await client.post(
        "/knowledge-base",
        json={"titulo": "Erro NF-e", "categoria": "fiscal", "conteudo": "Solução para erro NF-e"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create.status_code == 201
    artigo_id = create.json()["id"]

    get = await client.get(f"/knowledge-base/{artigo_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get.status_code == 200

    list_resp = await client.get("/knowledge-base", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    delete = await client.delete(f"/knowledge-base/{artigo_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert delete.status_code == 204

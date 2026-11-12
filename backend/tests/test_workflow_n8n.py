"""Harness de validação do workflow n8n (fecha 14-7).

Carrega ``infra/n8n/workflow-support-ai.json`` (JSON é YAML válido, então
usamos ``yaml.safe_load``) e valida a integridade estrutural do workflow:

(a) nós essenciais presentes: webhook, HTTP para o backend, decisão/roteamento
    e resposta;
(b) sem URL de backend hardcoded — os nós HTTP usam ``$env.BACKEND_URL``;
(c) toda variável ``$env.*`` usada existe em ``infra/.env.example`` E é
    passada no bloco do serviço ``n8n`` no ``infra/docker-compose.dev.yml``;
(d) todo nó HTTP tem ``onError`` definido;
(e) path do webhook é o esperado (``emsoft-whatsapp``, POST);
(f) ``connections`` sem nó órfão (toda referência aponta para nó existente
    e todo nó, exceto o webhook, recebe ao menos uma aresta de entrada).

Estado atual (12/11/2026): todos os itens passam no workflow vigente; não há
pontos abertos a registrar. Se algum item vier a falhar, registre o item
aberto aqui (ex.: 06-18) e ajuste a asserção ao comportamento real — o teste
não pode nascer vermelho.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / "infra" / "n8n" / "workflow-support-ai.json"
ENV_EXAMPLE_PATH = REPO_ROOT / "infra" / ".env.example"
COMPOSE_DEV_PATH = REPO_ROOT / "infra" / "docker-compose.dev.yml"

HTTP_REQUEST_TYPE = "n8n-nodes-base.httpRequest"
WEBHOOK_TYPE = "n8n-nodes-base.webhook"
IF_TYPE = "n8n-nodes-base.if"
EVOLUTION_API_TYPE = "n8n-nodes-evolution-api.evolutionApi"


@pytest.fixture(scope="module")
def workflow() -> dict:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return yaml.safe_load(text)


@pytest.fixture(scope="module")
def env_example_keys() -> set[str]:
    return {
        line.split("=", 1)[0].strip()
        for line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
        if line and not line.lstrip().startswith("#") and "=" in line
    }


@pytest.fixture(scope="module")
def n8n_compose_env() -> set[str]:
    """Variáveis injetadas no serviço n8n do docker-compose.dev.yml."""
    compose = yaml.safe_load(COMPOSE_DEV_PATH.read_text(encoding="utf-8"))
    services = compose.get("services", {})
    assert "n8n" in services, "serviço n8n ausente no docker-compose.dev.yml"
    env = services["n8n"].get("environment", {})
    if isinstance(env, list):
        return {item.split("=", 1)[0].strip() for item in env}
    return set(env)


def _nodes(workflow: dict) -> dict[str, dict]:
    return {node["name"]: node for node in workflow["nodes"]}


def _env_vars_used(workflow: dict) -> set[str]:
    text = json.dumps(workflow, ensure_ascii=False)
    return set(re.findall(r"\$env\.([A-Za-z0-9_]+)", text))


def test_nodes_essenciais_presentes(workflow: dict) -> None:
    """(a) webhook, HTTP para o backend, decisão/roteamento e resposta."""
    nodes = _nodes(workflow)

    webhooks = [n for n in nodes.values() if n["type"] == WEBHOOK_TYPE]
    assert webhooks, "workflow sem nó de webhook"

    http_requisitos = [n for n in nodes.values() if n["type"] == HTTP_REQUEST_TYPE]
    assert http_requisitos, "workflow sem nó de HTTP para o backend"

    decisoes = [n for n in nodes.values() if n["type"] == IF_TYPE]
    assert decisoes, "workflow sem nó de decisão/roteamento"

    respostas = [
        n for n in nodes.values()
        if n["type"] == EVOLUTION_API_TYPE or n["name"] == "Enviar texto"
    ]
    assert respostas, "workflow sem nó de resposta ao WhatsApp"


def test_sem_url_backend_hardcoded(workflow: dict) -> None:
    """(b) nós HTTP usam $env.BACKEND_URL; nenhuma URL de backend hardcoded."""
    for node in workflow["nodes"]:
        if node["type"] != HTTP_REQUEST_TYPE:
            continue
        url = node.get("parameters", {}).get("url", "")
        assert isinstance(url, str) and "$env.BACKEND_URL" in url, (
            f"nó HTTP '{node['name']}' não usa $env.BACKEND_URL: {url!r}"
        )

    text = json.dumps(workflow, ensure_ascii=False)
    assert not re.search(r"https?://[^\"' ]+?8000", text), (
        "URL de backend (porta 8000) hardcoded no workflow"
    )


def test_env_vars_em_env_example_e_compose(
    workflow: dict,
    env_example_keys: set[str],
    n8n_compose_env: set[str],
) -> None:
    """(c) toda $env.* usada existe no .env.example e é passada no compose."""
    usadas = _env_vars_used(workflow)
    assert usadas, "nenhuma variável $env.* encontrada — checagem vazia"

    assert (
        ENV_EXAMPLE_PATH.exists()
    ), f"arquivo ausente: {ENV_EXAMPLE_PATH}"
    faltando_example = usadas - env_example_keys
    assert not faltando_example, (
        f"variáveis $env usadas no workflow ausentes de {ENV_EXAMPLE_PATH.name}: "
        f"{sorted(faltando_example)}"
    )

    faltando_compose = usadas - n8n_compose_env
    assert not faltando_compose, (
        f"variáveis $env usadas no workflow não injetadas no serviço n8n do "
        f"docker-compose.dev.yml: {sorted(faltando_compose)}"
    )


def test_todos_nos_http_tem_onerror(workflow: dict) -> None:
    """(d) todo nó HTTP tem onError definido."""
    http_sem_onerror = [
        node["name"]
        for node in workflow["nodes"]
        if node["type"] == HTTP_REQUEST_TYPE and "onError" not in node
    ]
    assert not http_sem_onerror, (
        f"nós HTTP sem onError: {http_sem_onerror}"
    )


def test_path_do_webhook(workflow: dict) -> None:
    """(e) o webhook escuta POST /webhook/emsoft-whatsapp."""
    webhooks = [n for n in workflow["nodes"] if n["type"] == WEBHOOK_TYPE]
    assert len(webhooks) == 1, f"esperado 1 webhook, encontrados {len(webhooks)}"

    params = webhooks[0]["parameters"]
    assert params.get("path") == "emsoft-whatsapp"
    assert params.get("httpMethod", "GET").upper() == "POST"


def test_sem_no_orfao(workflow: dict) -> None:
    """(f) connections sem nó órfão: alvos existentes e entradas cobrindo todos."""
    nodes = _nodes(workflow)
    connections = workflow.get("connections", {})

    # Nenhuma referência a nó que não existe.
    alvos: set[str] = set()
    for origem, saidas in connections.items():
        assert origem in nodes, f"connections referencia nó inexistente: {origem}"
        for saidas_por_tipo in saidas.values():
            for lista in saidas_por_tipo:
                for conexao in lista or []:
                    alvo = conexao["node"]
                    assert alvo in nodes, (
                        f"aresta {origem} -> {alvo} aponta para nó inexistente"
                    )
                    alvos.add(alvo)

    # Todo nó, exceto o webhook (entrada raiz), recebe pelo menos uma aresta.
    orfaos = set(nodes) - alvos - {n for n in nodes if nodes[n]["type"] == WEBHOOK_TYPE}
    assert not orfaos, f"nós órfãos (sem aresta de entrada): {sorted(orfaos)}"

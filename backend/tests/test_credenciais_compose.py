"""Compose de producao sem segredo literal e sem servico orfao (09-3, 09-8)."""

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = (RAIZ / "infra/docker-compose.prod.yml").read_text(encoding="utf-8")
EXEMPLO = (RAIZ / "infra/.env.example").read_text(encoding="utf-8")
BACKUP = (RAIZ / "scripts/backup.sh").read_text(encoding="utf-8")

SERVICOS_ESPERADOS = {
    "traefik",
    "backend",
    "frontend",
    "postgres",
    "redis",
    "qdrant",
    "ollama",
    "n8n",
    "evolution-api",
}


def test_senha_do_postgres_vem_do_env():
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}" in COMPOSE
    assert "POSTGRES_PASSWORD: emsoft" not in COMPOSE


def test_uri_da_evolution_usa_a_senha_do_env():
    assert "postgresql://emsoft:${POSTGRES_PASSWORD}@postgres:5432/emsoft" in COMPOSE
    assert "emsoft:emsoft@" not in COMPOSE


def test_minio_orfao_removido():
    assert "minio" not in COMPOSE.lower()
    assert "MINIO_" not in COMPOSE


def test_env_example_documenta_a_senha():
    assert "POSTGRES_PASSWORD=" in EXEMPLO


def test_backup_nao_depende_de_minio():
    assert "minio" not in BACKUP.lower()


def test_lista_de_servicios_travada():
    data = yaml.safe_load(COMPOSE)
    servicos = set(data["services"])
    if servicos != SERVICOS_ESPERADOS:
        extra = servicos - SERVICOS_ESPERADOS
        faltando = SERVICOS_ESPERADOS - servicos
        assert not extra and not faltando, (
            "A lista de serviços do compose prod mudou. Cada serviço exige um "
            "consumidor comprovado no código — revise intencionalmente antes de "
            f"atualizar SERVICOS_ESPERADOS. Ajustes: +{sorted(extra)} -{sorted(faltando)}"
        )


def test_backend_nao_depende_de_postgres():
    data = yaml.safe_load(COMPOSE)
    depends = set(data["services"]["backend"].get("depends_on", {}))
    assert "postgres" not in depends, (
        "O backend usa Appwrite (app/appwrite/repositories) e não abre conexão "
        "com o Postgres — a dependência só segurava o boot à toa."
    )


def test_volumes_declarados_sao_usados_por_um_servico():
    data = yaml.safe_load(COMPOSE)
    declarados = set(data.get("volumes") or {})
    usados: set[str] = set()
    for servico in data["services"].values():
        for volume in servico.get("volumes", []):
            # Entradas "monte:/alvo[:modo]" ou "nome:alvo"; nome é o 1º campo
            nome = volume.split(":")[0].strip()
            if not nome.startswith(("/", ".")):  # montagens bind não são volumes
                usados.add(nome)
    sem_usuario = declarados - usados
    assert not sem_usuario, (
        f"Volumes declarados sem serviço que os use: {sorted(sem_usuario)}. "
        "Remova-os do compose ou aponte um serviço para o volume."
    )

"""Métricas Prometheus: registro, middleware e GET /metrics (spec 08, gap 08-6)."""

from app.core.config import settings
from app.core.metricas import RegistroMetricas


def test_contador_soma_por_serie_de_labels():
    reg = RegistroMetricas()
    reg.definir_contador("pedidos_total", "Pedidos criados.")
    reg.contar("pedidos_total", regiao="sul")
    reg.contar("pedidos_total", valor=2, regiao="norte")

    texto = reg.render()

    assert "# HELP pedidos_total Pedidos criados." in texto
    assert "# TYPE pedidos_total counter" in texto
    assert 'pedidos_total{regiao="norte"} 2' in texto
    assert 'pedidos_total{regiao="sul"} 1' in texto


def test_labels_sempre_em_ordem_alfabetica():
    reg = RegistroMetricas()
    reg.contar("x", b="2", a="1")

    linha = next(linha for linha in reg.render().splitlines() if linha.startswith("x{"))

    assert linha == 'x{a="1",b="2"} 1'


def test_sanitiza_nome_de_metrica_e_de_labels():
    reg = RegistroMetricas()
    reg.contar("pedidos total!", **{"min-max": "3"})

    texto = reg.render()

    assert "pedidos_total_" in texto
    assert 'min_max="3"' in texto


def test_histograma_emite_buckets_sum_e_count():
    reg = RegistroMetricas()
    reg.definir_histograma("duracao_segundos", "Duração em segundos.")
    reg.observar("duracao_segundos", 0.1)
    reg.observar("duracao_segundos", 2.0)

    linhas = reg.render().splitlines()

    assert "# TYPE duracao_segundos histogram" in linhas
    assert 'duracao_segundos_bucket{le="0.05"} 0' in linhas
    assert 'duracao_segundos_bucket{le="0.1"} 1' in linhas
    assert 'duracao_segundos_bucket{le="2.5"} 2' in linhas
    assert 'duracao_segundos_bucket{le="+Inf"} 2' in linhas
    assert "duracao_segundos_sum 2.1" in linhas
    assert "duracao_segundos_count 2" in linhas


async def test_metrics_expose_middleware_depois_de_health(client):
    await client.get("/health")

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert 'http_requests_total{metodo="GET",rota="/health",status="200"}' in resp.text
    assert (
        'http_request_duracao_segundos_count{metodo="GET",rota="/health"}' in resp.text
    )


async def test_metrics_nao_contabiliza_a_si_mesma(client):
    await client.get("/metrics")

    resp = await client.get("/metrics")

    assert 'rota="/metrics"' not in resp.text


async def test_rota_inexistente_usa_label_nao_encontrada(client):
    resp = await client.get("/rota-que-nao-existe")
    assert resp.status_code == 404

    texto = (await client.get("/metrics")).text

    assert 'http_requests_total{metodo="GET",rota="<nao_encontrada>",status="404"}' in texto


async def test_metrics_exige_bearer_token_quando_configurado(client, monkeypatch):
    monkeypatch.setattr(settings, "metricas_token", "s3gr3d0")

    assert (await client.get("/metrics")).status_code == 401
    errado = await client.get("/metrics", headers={"Authorization": "Bearer errad0"})
    assert errado.status_code == 401

    certo = await client.get("/metrics", headers={"Authorization": "Bearer s3gr3d0"})
    assert certo.status_code == 200
    assert "http_requests_total" in certo.text

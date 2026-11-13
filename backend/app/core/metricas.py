"""Registro de métricas Prometheus em memória, sem dependência externa.

Spec 08, gap 08-6 (parte 1): expõe contadores e histogramas no formato de
exposição Prometheus (text/plain, version=0.0.4). Thread-safe via lock.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Sequence
from typing import TypedDict, cast

# Nomes de métricas e nomes de labels são sanitizados; valores de label não
# são (só escapados) para preservar, ex., rota="/health".
_SANITIZAR = re.compile(r"[^a-zA-Z0-9_]")

BUCKETS_PADRAO: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1,
    2.5,
    5,
    10,
)


def _nome(nome: str) -> str:
    return _SANITIZAR.sub("_", nome)


def _escapar(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _fmt_num(valor: float) -> str:
    if valor == int(valor):
        return str(int(valor))
    return repr(valor)


def _fmt_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    partes = [
        f'{_nome(chave)}="{_escapar(str(labels[chave]))}"' for chave in sorted(labels)
    ]
    return "{" + ",".join(partes) + "}"


class _DadosHistograma(TypedDict):
    b: list[int]
    sum: float
    count: int


class _Registro[Ag]:
    """Séries de uma métrica: o conjunto de labels é fixo por série.

    Se o mesmo nome de métrica surgir com um novo conjunto de labels, vira
    uma série separada — nunca se inventa valor para o que não foi observado.
    """

    def __init__(self, descricao: str) -> None:
        self.descricao = descricao
        # chaves de label (ordem alfabética) -> valores de label -> agregado
        self.series: dict[tuple[str, ...], dict[tuple[str, ...], Ag]] = {}


class _Histograma(_Registro[_DadosHistograma]):
    def __init__(self, descricao: str, buckets: list[float]) -> None:
        super().__init__(descricao)
        self.buckets = buckets


class RegistroMetricas:
    """Contadores e histogramas em memória, renderizados no formato Prometheus."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._contadores: dict[str, _Registro[float]] = {}
        self._istogramas: dict[str, _Histograma] = {}

    # -- definição ------------------------------------------------------------

    def definir_contador(self, nome: str, descricao: str) -> None:
        with self._lock:
            self._contadores[_nome(nome)] = _Registro[float](descricao)

    def definir_histograma(
        self, nome: str, descricao: str, buckets: Sequence[float] = BUCKETS_PADRAO
    ) -> None:
        with self._lock:
            self._istogramas[_nome(nome)] = _Histograma(descricao, list(buckets))

    # -- registro de valores --------------------------------------------------

    def contar(self, nome: str, valor: float = 1.0, **labels: str) -> None:
        nome = _nome(nome)
        chaves = tuple(sorted(labels))
        with self._lock:
            reg = self._contadores.setdefault(nome, _Registro[float](""))
            series = reg.series.setdefault(chaves, {})
            chave = tuple(str(labels[k]) for k in chaves)
            series[chave] = series.get(chave, 0.0) + valor

    def observar(self, nome: str, valor: float, **labels: str) -> None:
        nome = _nome(nome)
        chaves = tuple(sorted(labels))
        with self._lock:
            reg = self._istogramas.setdefault(
                nome, _Histograma("", list(BUCKETS_PADRAO))
            )
            series = reg.series.setdefault(chaves, {})
            chave = tuple(str(labels[k]) for k in chaves)
            dados = series.get(chave)
            if dados is None:
                dados = {"b": [0] * len(reg.buckets), "sum": 0.0, "count": 0}
                series[chave] = dados
            for i, borda in enumerate(reg.buckets):
                if valor <= borda:
                    dados["b"][i] += 1
            dados["sum"] += valor
            dados["count"] += 1

    # -- exposição ------------------------------------------------------------

    def render(self) -> str:
        partes: list[str] = []
        with self._lock:
            for nome in sorted(self._contadores):
                self._render_contador(nome, self._contadores[nome], partes)
            for nome in sorted(self._istogramas):
                self._render_histograma(nome, self._istogramas[nome], partes)
        return "\n".join(partes) + "\n" if partes else ""

    def _render_contador(self, nome: str, reg: _Registro[float], partes: list[str]) -> None:
        partes.append(f"# HELP {nome} {reg.descricao}".rstrip())
        partes.append(f"# TYPE {nome} counter")
        for chaves in sorted(reg.series):
            for valores in sorted(reg.series[chaves]):
                labels = dict(zip(chaves, valores, strict=True))
                partes.append(
                    f"{nome}{_fmt_labels(labels)} {_fmt_num(reg.series[chaves][valores])}"
                )

    def _render_histograma(self, nome: str, reg: _Histograma, partes: list[str]) -> None:
        partes.append(f"# HELP {nome} {reg.descricao}".rstrip())
        partes.append(f"# TYPE {nome} histogram")
        for chaves in sorted(reg.series):
            for valores in sorted(reg.series[chaves]):
                dados = cast(_DadosHistograma, reg.series[chaves][valores])
                base = dict(zip(chaves, valores, strict=True))
                for borda, n in zip(reg.buckets, dados["b"], strict=True):
                    partes.append(
                        f"{nome}_bucket{_fmt_labels({**base, 'le': f'{borda:g}'})} "
                        f"{_fmt_num(float(n))}"
                    )
                partes.append(
                    f"{nome}_bucket{_fmt_labels({**base, 'le': '+Inf'})} "
                    f"{_fmt_num(float(dados['count']))}"
                )
                partes.append(f"{nome}_sum{_fmt_labels(base)} {_fmt_num(float(dados['sum']))}")
                partes.append(f"{nome}_count{_fmt_labels(base)} {_fmt_num(float(dados['count']))}")


# Instância global do processo; as rotas e o middleware registram aqui.
metricas = RegistroMetricas()

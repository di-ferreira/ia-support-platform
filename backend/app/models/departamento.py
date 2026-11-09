"""Taxonomia de domínio de departamentos e roteamento.

Este módulo contém **apenas enums** (sem ORM): ele sobrevive à remoção da
camada SQLAlchemy legada planejada na Trilha R2. Os enums são a fonte
canônica; `app/appwrite/schema.py` deriva as listas de valores deles.
"""

import enum


class Intencao(enum.StrEnum):
    """As 9 intenções da taxonomia inicial (docs/specs/05-ai-pipeline.md)."""

    problema_tecnico = "problema_tecnico"
    duvida_uso_erp = "duvida_uso_erp"
    solicitacao_financeira = "solicitacao_financeira"
    solicitacao_comercial = "solicitacao_comercial"
    solicitacao_administrativa = "solicitacao_administrativa"
    implantacao_treinamento = "implantacao_treinamento"
    solicitacao_humano = "solicitacao_humano"
    duvida_geral = "duvida_geral"
    intencao_desconhecida = "intencao_desconhecida"


class CategoriaERP(enum.StrEnum):
    """Módulos do ERP conhecidos pela IA. NÃO é departamento (spec 10).

    `outro` não existe: assunto fora destes módulos é `categoria_erp=null`.
    """

    fiscal = "fiscal"
    estoque = "estoque"
    compras = "compras"
    vendas = "vendas"
    financeiro = "financeiro"
    multiempresa = "multiempresa"

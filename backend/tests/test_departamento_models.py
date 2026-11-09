"""Taxonomia de intenção e categoria ERP deve espelhar docs/specs/05 e 02."""

from app.appwrite import schema
from app.models.departamento import CategoriaERP, Intencao
from app.models.knowledge_base import CategoriaConhecimento


def test_intencao_tem_as_nove_intencoes_da_spec_05():
    assert {i.value for i in Intencao} == {
        "problema_tecnico",
        "duvida_uso_erp",
        "solicitacao_financeira",
        "solicitacao_comercial",
        "solicitacao_administrativa",
        "implantacao_treinamento",
        "solicitacao_humano",
        "duvida_geral",
        "intencao_desconhecida",
    }


def test_categoria_erp_tem_seis_modulos_e_nao_tem_outro():
    assert {c.value for c in CategoriaERP} == {
        "fiscal",
        "estoque",
        "compras",
        "vendas",
        "financeiro",
        "multiempresa",
    }


def test_categoria_conhecimento_inclui_multiempresa():
    assert CategoriaConhecimento.multiempresa.value == "multiempresa"


def test_categorias_do_schema_espelham_os_enums():
    assert schema.INTENCAO == [i.value for i in Intencao]
    assert schema.CATEGORIA_ERP == [c.value for c in CategoriaERP]
    # Base de conhecimento e regras de roteamento compartilham o mesmo vocabulário.
    assert schema.CATEGORIA_CONHECIMENTO == schema.CATEGORIA_ERP


def test_outro_nao_e_categoria_valida():
    assert "outro" not in schema.CATEGORIA_ERP
    assert "outro" not in schema.CATEGORIA_CONHECIMENTO

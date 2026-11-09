"""Contrato da saida estruturada do classificador (spec 05)."""

import pytest
from pydantic import ValidationError

from app.models.departamento import CategoriaERP, Intencao
from app.schemas.ai import ClassificacaoIntencao, ClassificarIntencaoRequest

VALIDO = {
    "intencao": "problema_tecnico",
    "subintencao": "emissao_nfe",
    "categoria_erp": "fiscal",
    "departamento_sugerido_codigo": "suporte_tecnico",
    "confianca": 0.94,
    "precisa_esclarecimento": False,
    "pergunta_esclarecimento": None,
    "motivo": "O cliente relata falha ao emitir uma NF-e.",
}


def test_aceita_o_json_de_exemplo_da_spec_05():
    c = ClassificacaoIntencao.model_validate(VALIDO)
    assert c.intencao is Intencao.problema_tecnico
    assert c.categoria_erp is CategoriaERP.fiscal
    assert c.confianca == 0.94


def test_categoria_outro_vira_none():
    c = ClassificacaoIntencao.model_validate({**VALIDO, "categoria_erp": "outro"})
    assert c.categoria_erp is None


def test_categoria_desconhecida_nao_vira_none():
    with pytest.raises(ValidationError):
        ClassificacaoIntencao.model_validate({**VALIDO, "categoria_erp": "contabil"})


def test_confianca_fora_de_0_1_e_invalida():
    with pytest.raises(ValidationError):
        ClassificacaoIntencao.model_validate({**VALIDO, "confianca": 1.4})


def test_campo_desconhecido_invalida():
    with pytest.raises(ValidationError):
        ClassificacaoIntencao.model_validate({**VALIDO, "justificativa": "extra"})


def test_intencao_fora_da_taxonomia_invalida():
    with pytest.raises(ValidationError):
        ClassificacaoIntencao.model_validate({**VALIDO, "intencao": "reclamacao"})


def test_request_exige_exatamente_um_dos_campos():
    assert ClassificarIntencaoRequest(chat_id="c1").chat_id == "c1"
    assert ClassificarIntencaoRequest(mensagem="oi").mensagem == "oi"
    with pytest.raises(ValidationError):
        ClassificarIntencaoRequest()
    with pytest.raises(ValidationError):
        ClassificarIntencaoRequest(chat_id="c1", mensagem="oi")

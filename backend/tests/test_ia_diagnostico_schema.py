"""Snapshot do diagnostico no schema Appwrite (spec 02/05)."""

from app.appwrite import schema
from app.models.ia_diagnostico import StatusIA


def _attrs(col: str) -> dict[str, dict]:
    return {a["key"]: a for a in schema.COLLECTIONS[col]["attributes"]}


def test_diagnostico_guarda_a_classificacao_e_o_roteamento():
    attrs = _attrs("ia_diagnosticos")
    for chave in (
        "intencao",
        "subintencao",
        "categoria_erp",
        "departamento_sugerido_codigo",
        "departamento_id",
        "motivo",
        "artigos_consultados",
    ):
        assert chave in attrs, f"atributo {chave} ausente"


def test_atributos_do_snapshot_sao_opcionais():
    attrs = _attrs("ia_diagnosticos")
    for chave in (
        "intencao",
        "subintencao",
        "categoria_erp",
        "departamento_sugerido_codigo",
        "departamento_id",
        "motivo",
        "artigos_consultados",
    ):
        assert attrs[chave]["required"] is False


def test_artigos_consultados_e_texto_json():
    """Appwrite nao tem atributo JSON: guardamos JSON serializado em string."""
    attrs = _attrs("ia_diagnosticos")
    assert attrs["artigos_consultados"]["type"] == "string"
    assert attrs["artigos_consultados"]["size"] == schema.TEXT_SIZE


def test_departamento_id_tem_tamanho_de_ulid():
    assert _attrs("ia_diagnosticos")["departamento_id"]["size"] == 36


def test_status_ia_inclui_esclarecimento():
    assert "ESCLARECIMENTO" in schema.STATUS_IA
    assert StatusIA.esclarecimento.value == "ESCLARECIMENTO"


def test_status_ia_do_schema_espelha_o_enum():
    assert schema.STATUS_IA == [s.value for s in StatusIA]

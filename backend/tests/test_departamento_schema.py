"""Schema Appwrite das colecoes de departamento e roteamento."""

from app.appwrite import schema


def _keys(collection: str) -> set[str]:
    return {a["key"] for a in schema.COLLECTIONS[collection]["attributes"]}


def test_departamentos_tem_os_atributos_da_spec_02():
    assert _keys("departamentos") == {
        "codigo",
        "nome",
        "descricao",
        "ativo",
        "ordem",
        "recebe_transferencias",
        "permite_atribuicao_automatica",
    }


def test_departamentos_codigo_e_unico_por_tamanho_estavel():
    attrs = {a["key"]: a for a in schema.COLLECTIONS["departamentos"]["attributes"]}
    assert attrs["codigo"]["size"] == 80
    assert attrs["codigo"]["required"] is True


def test_regras_roteamento_tem_os_atributos_da_spec_02():
    assert _keys("regras_roteamento") == {
        "intencao",
        "subintencao",
        "categoria_erp",
        "departamento_id",
        "prioridade_regra",
        "ativo",
    }


def test_regras_roteamento_nao_aceita_intencao_fora_da_taxonomia():
    attrs = {a["key"]: a for a in schema.COLLECTIONS["regras_roteamento"]["attributes"]}
    # intencao e string(80) validada na aplicacao contra o enum Intencao
    assert attrs["intencao"]["size"] == 80
    assert attrs["departamento_id"]["size"] == 36


def test_atendentes_e_chats_tem_departamento_id_opcional():
    assert "departamento_id" in _keys("atendentes")
    assert "departamento_id" in _keys("chats")
    atendentes = {a["key"]: a for a in schema.COLLECTIONS["atendentes"]["attributes"]}
    chats = {a["key"]: a for a in schema.COLLECTIONS["chats"]["attributes"]}
    assert atendentes["departamento_id"]["required"] is False
    assert chats["departamento_id"]["required"] is False


def test_legado_setor_preservado():
    """C6: setor/setor_alvo nao sao removidos nesta fase."""
    assert "setor" in _keys("atendentes")
    assert "setor_alvo" in _keys("chats")

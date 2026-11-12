"""Mapper: modelo canônico -> contrato externo Emsoft (spec 11 §Mapper).

Regras duras:
- campo obrigatório do contrato ausente -> `MappingError` ANTES do POST;
- campo opcional ausente -> omitido (nada é presumido);
- intenção de status ausente em `status_externos` -> campo omitido,
  nunca valor inventado;
- o payload nasce estritamente do contrato validado; nenhum nome de
  campo externo vive fora de `contract.py`/do artefato.
"""

from dataclasses import asdict

from app.integrations.emsoft_chamados.canonical import ChamadoCanonical
from app.integrations.emsoft_chamados.contract import ContratoEmsoft
from app.integrations.emsoft_chamados.exceptions import MappingError

TICKET_ID_SENTINEL = "(ticket_id)"
"""Sentinela nos mapas de edição: injeta o ID do chamado."""

STATUS_INTENT_PATH = "external_status_intent"
"""Dot path especial: valor resolvido via `status_externos` do contrato."""

_STATUS_RESOLVIDO = "RESOLVED"
_STATUS_AGUARDANDO = "WAITING_CUSTOMER"
_STATUS_ANDAMENTO = "IN_PROGRESS"


def intent_from_chat_status(status_chat: str | None) -> str:
    """Traduz o status interno do chat para a intenção de status externo."""
    if status_chat in ("RESOLVIDO", "ENCERRADO"):
        return _STATUS_RESOLVIDO
    if status_chat == "AGUARDANDO_CLIENTE":
        return _STATUS_AGUARDANDO
    return _STATUS_ANDAMENTO


def resolve_path(data, dot_path: str):
    """Resolve um dot path sobre dicts aninhados (respostas da API).

    Retorna `None` se qualquer trecho faltar — nunca levanta.
    """
    atual = data
    for parte in dot_path.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            return None
        atual = atual[parte]
    return atual


def _resolver_canonical(
    chamado: ChamadoCanonical,
    dot_path: str,
    campo_externo: str,
    ticket_id: str | None,
) -> object:
    if dot_path == TICKET_ID_SENTINEL:
        if ticket_id:
            return ticket_id
        raise MappingError(
            f"Sentinela {TICKET_ID_SENTINEL} sem ticket_id no campo {campo_externo}",
            kind="CAMPO",
            field=campo_externo,
        )
    dados = asdict(chamado)
    for parte in dot_path.split("."):
        if not isinstance(dados, dict) or parte not in dados:
            return None
        dados = dados[parte]
    return dados


def _vazio(valor: object) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str) and not valor.strip():
        return True
    if isinstance(valor, (list, dict)) and not valor:
        return True
    return False


def build_payload(
    chamado: ChamadoCanonical,
    contract: ContratoEmsoft,
    operation: str,
    ticket_id: str | None = None,
) -> dict:
    """Monta o payload externo para `criar` ou `editar`.

    `MappingError` se um campo obrigatório da criação ficar ausente.
    """
    if operation not in ("criar", "editar"):
        raise ValueError(f"operation inválida: {operation!r}")
    mapa = contract.campos_criacao if operation == "criar" else contract.campos_edicao
    obrigatorios = set(contract.campos_obrigatorios) if operation == "criar" else set()
    payload: dict = {}
    for campo_externo, dot_path in mapa.items():
        if dot_path == STATUS_INTENT_PATH:
            intent = chamado.external_status_intent
            valor: object = (
                contract.status_externos.get(intent) if intent else None
            )
            if not valor:
                continue  # intenção desconhecida: omitir, nunca presumir
            payload[campo_externo] = valor
            continue
        valor = _resolver_canonical(chamado, dot_path, campo_externo, ticket_id)
        if _vazio(valor):
            if campo_externo in obrigatorios:
                raise MappingError(
                    f"Campo obrigatório ausente: {campo_externo} "
                    f"(canônico {dot_path!r})",
                    kind="CAMPO",
                    field=campo_externo,
                )
            continue
        payload[campo_externo] = valor
    return payload


def build_description(chamado: ChamadoCanonical) -> str:
    """Resumo legível em blocos (spec 11 §Descrição e dados enviados).

    Blocos vazios são pulados; numeração é sequencial sobre os incluídos.
    """
    blocos: list[str] = []

    def _add(texto: str) -> None:
        if texto.strip():
            blocos.append(f"{len(blocos) + 1}. {texto.strip()}")

    _add(f"Origem: {chamado.source} — chat {chamado.source_chat_id}")

    if chamado.customer:
        partes = [f"Cliente: {chamado.customer.name}"]
        if chamado.customer.document:
            partes.append(f"documento: {chamado.customer.document}")
        if chamado.contact and chamado.contact.whatsapp_number:
            partes.append(f"whatsapp: {chamado.contact.whatsapp_number}")
        _add(", ".join(partes))

    partes = []
    if chamado.department_name:
        partes.append(f"Departamento: {chamado.department_name}")
    if chamado.assignee and chamado.assignee.display_name:
        partes.append(f"Responsável: {chamado.assignee.display_name}")
    _add(" | ".join(partes))

    partes = []
    if chamado.subject:
        partes.append(f"Assunto: {chamado.subject}")
    if chamado.intent:
        partes.append(f"intenção: {chamado.intent}")
    _add(" | ".join(partes))

    diag = chamado.diagnosis
    if diag:
        _add(f"Problema observado: {diag.summary}")
        _add(f"Causa provável: {diag.probable_cause}")
        if diag.attempts:
            _add("Tentativas: " + "; ".join(diag.attempts))
        partes = []
        if diag.proposed_solution:
            partes.append(f"Solução sugerida: {diag.proposed_solution}")
        if diag.knowledge_references:
            partes.append("Artigos: " + ", ".join(diag.knowledge_references))
        _add(" | ".join(partes))

    if chamado.platform_status:
        _add(
            f"Situação atual: {chamado.platform_status} — "
            "verificar ação pendente no chat de origem"
        )

    return "\n\n".join(blocos)

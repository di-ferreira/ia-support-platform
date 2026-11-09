"""Sincronização do chat com o chamado Emsoft (spec 11).

Ciclo de vida por `chat_id` (cardinalidade 1:1):

- sem registro        -> cria o ticket (POST único);
- com `external_ticket_id` -> sempre atualiza (PATCH); cobre o re-PATCH
  pós-timeout, pois o ID garante que não há outro ticket para o chat;
- sem ID + RECONCILIACAO -> reconcilia por listagem, **nunca** re-POST;
- sem ID + ERRO/PENDENTE -> nova tentativa de criação.

Resultado ambíguo (timeout no POST) nunca vira repetição cega: o estado
vai para RECONCILIACAO e só a listagem confirmada devolve a
SINCRONIZADO. Falhas de mapeamento e de contrato não incrementam
`tentativas` e não disparam request externo.
"""

import json
import logging
from datetime import UTC, datetime

from app.integrations.emsoft_chamados.canonical import (
    ASSIGNEE_AI,
    ASSIGNEE_HUMANO,
    ChamadoCanonical,
    ClienteCanonical,
    ContatoCanonical,
    DiagnosticoCanonical,
    ResponsavelCanonical,
)
from app.integrations.emsoft_chamados.exceptions import (
    AmbiguousResultError,
    ChatNotFoundError,
    ExternalRequestError,
    MappingError,
)
from app.integrations.emsoft_chamados.mapper import (
    build_description,
    build_payload,
    intent_from_chat_status,
    resolve_path,
)

logger = logging.getLogger("app.integracao_emsoft")

STATUS_PENDENTE = "PENDENTE"
STATUS_SINCRONIZADO = "SINCRONIZADO"
STATUS_ERRO = "ERRO"
STATUS_RECONCILIACAO = "RECONCILIACAO"

_MOTIVO_MANUAL = "Reconciliação manual necessária"


class EmsoftChamadosService:
    """Orquestra create/update/reconcile; não conhece HTTP nem o contrato
    bruto além do que o `client` e o `mapper` expõem."""

    def __init__(self, contract, client, repos, settings) -> None:
        self._contract = contract
        self._client = client
        self._repos = repos
        self._settings = settings

    async def sincronizar(self, chat_id: str) -> dict:
        """Sincroniza o chamado externo do chat e devolve o resumo:
        `{chat_id, status, external_ticket_id, mensagem}`."""
        chat = await self._repos.chats.get(chat_id)
        if chat is None:
            raise ChatNotFoundError(f"Chat não encontrado: {chat_id}")

        registro = await self._repos.integracao_chamados.get_by_chat(chat_id)

        try:
            chamado = await self._montar_canonical(chat)
        except MappingError as exc:
            logger.warning(
                "emsoft: mapeamento falhou para o chat %s: %s",
                chat_id, exc,
                extra={"event": "emsoft_mapping_error", "chat_id": chat_id},
            )
            registro = await self._salvar_registro(
                registro, None, chat_id=chat_id,
                status=STATUS_ERRO, ultimo_erro=str(exc),
            )
            return self._resultado(chat_id, registro)

        chamado.external_status_intent = intent_from_chat_status(
            chat.get("status")
        )
        chamado.description = build_description(chamado)

        if not registro:
            registro = await self._criar(chamado, None)
        elif registro.get("external_ticket_id"):
            registro = await self._editar(chamado, registro)
        elif registro.get("status") == STATUS_RECONCILIACAO:
            registro = await self._reconciliar(chamado, registro)
        else:
            registro = await self._criar(chamado, registro)

        return self._resultado(chat_id, registro)

    # -- montagem do canônico --------------------------------------------

    async def _montar_canonical(self, chat: dict) -> ChamadoCanonical:
        chat_id = chat["id"]
        cliente = (
            await self._repos.clientes.get(chat["cliente_id"])
            if chat.get("cliente_id")
            else None
        )
        atendente = (
            await self._repos.atendentes.get(chat["atendente_id"])
            if chat.get("atendente_id")
            else None
        )
        departamento = (
            await self._repos.departamentos.get(chat["departamento_id"])
            if chat.get("departamento_id")
            else None
        )
        diagnostico = await self._repos.ia_diagnosticos.get_by_chat(chat_id)

        responsavel = await self._responsavel(chat_id, atendente)

        department_code: str | None = None
        department_name: str | None = None
        if departamento:
            department_code = departamento.get("codigo")
            department_name = departamento.get("nome")
        elif diagnostico and diagnostico.get("departamento_sugerido_codigo"):
            # Fallback: só o código sugerido pela IA — nunca o nome.
            department_code = diagnostico.get("departamento_sugerido_codigo")

        subject = chat.get("resumo_problema")
        if not (subject or "").strip() and diagnostico:
            subject = diagnostico.get("resumo")

        return ChamadoCanonical(
            source_chat_id=chat_id,
            customer=(
                ClienteCanonical(
                    name=cliente.get("nome") or "",
                    internal_id=cliente.get("id"),
                    document=cliente.get("documento"),
                )
                if cliente
                else None
            ),
            contact=ContatoCanonical(
                whatsapp_number=chat.get("whatsapp_number")
            ),
            subject=(subject or "").strip(),
            intent=diagnostico.get("intencao") if diagnostico else None,
            erp_category=(
                diagnostico.get("categoria_erp") if diagnostico else None
            ),
            department_code=department_code,
            department_name=department_name,
            assignee=responsavel,
            diagnosis=(
                DiagnosticoCanonical(
                    summary=diagnostico.get("resumo"),
                    probable_cause=diagnostico.get("causa_provavel"),
                    proposed_solution=diagnostico.get("solucao"),
                    attempts=[],  # scaffold: histórico de tentativas (gap 11)
                    knowledge_references=self._artigos_consultados(diagnostico),
                )
                if diagnostico
                else None
            ),
            platform_status=chat.get("status"),
        )

    async def _responsavel(self, chat_id: str, atendente: dict | None):
        if atendente:
            external_id = (atendente.get("emsoft_usuario_id") or "").strip()
            if not external_id:
                raise MappingError(
                    f"Atendente {atendente.get('id')} do chat {chat_id} "
                    "sem emsoft_usuario_id — atribuição humana impossível",
                    kind="HUMANO",
                    field="emsoft_usuario_id",
                )
            return ResponsavelCanonical(
                kind=ASSIGNEE_HUMANO,
                internal_id=atendente.get("id"),
                external_id=external_id,
                display_name=atendente.get("nome"),
            )
        ai_user_id = (self._settings.emsoft_chamados_ai_user_id or "").strip()
        if not ai_user_id:
            raise MappingError(
                f"Chat {chat_id} sem atendente e sem usuário da IA "
                "configurado (emsoft_chamados_ai_user_id) — atribuição "
                "nunca é presumida",
                kind="AI",
            )
        return ResponsavelCanonical(
            kind=ASSIGNEE_AI,
            external_id=ai_user_id,
            display_name=self._settings.ia_name,
        )

    @staticmethod
    def _artigos_consultados(diagnostico: dict) -> list[str]:
        """`artigos_consultados` é JSON serializado; corrompido -> [] (nada
        é presumido, e o bloco é simplesmente omitido na descrição)."""
        if not diagnostico:
            return []
        raw = diagnostico.get("artigos_consultados")
        if not raw:
            return []
        try:
            dados = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(dados, list):
            return []
        return [str(item) for item in dados if isinstance(item, (str, int, float))]

    # -- operações ---------------------------------------------------------

    async def _criar(self, chamado, registro):
        try:
            payload = build_payload(chamado, self._contract, "criar")
        except MappingError as exc:
            logger.warning(
                "emsoft: payload de criação inválido para o chat %s: %s",
                chamado.source_chat_id, exc,
                extra={"event": "emsoft_mapping_error",
                       "chat_id": chamado.source_chat_id},
            )
            return await self._salvar_registro(
                registro, chamado, status=STATUS_ERRO, ultimo_erro=str(exc)
            )
        try:
            corpo = await self._client.criar(payload)
        except AmbiguousResultError as exc:
            # O POST pode ter sido aplicado: reconciliar, nunca re-POST.
            return await self._reconciliar(
                chamado, registro, motivo=str(exc)
            )
        except ExternalRequestError as exc:
            return await self._salvar_registro(
                registro, chamado,
                status=STATUS_ERRO, ultimo_erro=str(exc),
                tentativas_incremento=1,
            )
        ticket_id = (
            resolve_path(corpo, self._contract.campo_id_resposta)
            if isinstance(corpo, dict)
            else None
        )
        if not ticket_id:
            return await self._reconciliar(
                chamado, registro,
                motivo="Criação respondeu sem o ID do chamado extraível",
            )
        return await self._salvar_registro(
            registro, chamado,
            status=STATUS_SINCRONIZADO,
            external_ticket_id=str(ticket_id),
            ultimo_erro="",
            tentativas_incremento=1,
        )

    async def _editar(self, chamado, registro) -> dict:
        ticket_id = registro["external_ticket_id"]
        try:
            payload = build_payload(
                chamado, self._contract, "editar", ticket_id=ticket_id
            )
        except MappingError as exc:
            return await self._salvar_registro(
                registro, chamado, status=STATUS_ERRO, ultimo_erro=str(exc)
            )
        try:
            await self._client.editar(ticket_id, payload)
        except ExternalRequestError as exc:
            if exc.status_code is None:
                # Timeout/transporte: a edição pode ter sido aplicada.
                # Mantém o ID; a próxima sync re-PATCHa o mesmo ticket.
                return await self._salvar_registro(
                    registro, chamado,
                    status=STATUS_RECONCILIACAO,
                    ultimo_erro=str(exc),
                    tentativas_incremento=1,
                )
            return await self._salvar_registro(
                registro, chamado,
                status=STATUS_ERRO, ultimo_erro=str(exc),
                tentativas_incremento=1,
            )
        return await self._salvar_registro(
            registro, chamado,
            status=STATUS_SINCRONIZADO,
            ultimo_erro="",
            tentativas_incremento=1,
        )

    async def _reconciliar(self, chamado, registro=None, motivo: str = "") -> dict:
        campo_ref = self._contract.campo_referencia_externa
        if not campo_ref or not self._contract.filtro_referencia:
            logger.warning(
                "emsoft: reconciliação automática indisponível para o chat "
                "%s (campo_referencia_externa/filtro_referencia ausentes no "
                "contrato); aguardando reconciliação manual",
                chamado.source_chat_id,
                extra={"event": "emsoft_reconcile_pending",
                       "chat_id": chamado.source_chat_id},
            )
            return await self._salvar_registro(
                registro, chamado,
                status=STATUS_RECONCILIACAO,
                ultimo_erro=motivo or _MOTIVO_MANUAL,
            )
        try:
            itens = await self._client.listar(referencia=chamado.source_chat_id)
        except ExternalRequestError as exc:
            return await self._salvar_registro(
                registro, chamado,
                status=STATUS_RECONCILIACAO,
                ultimo_erro=f"Reconciliação pendente: {exc}",
                tentativas_incremento=1,
            )
        for item in itens:
            referencia = resolve_path(item, campo_ref)
            if referencia is None or str(referencia) != chamado.source_chat_id:
                continue
            ticket_id = resolve_path(item, self._contract.campo_id_resposta)
            if ticket_id:
                return await self._salvar_registro(
                    registro, chamado,
                    status=STATUS_SINCRONIZADO,
                    external_ticket_id=str(ticket_id),
                    ultimo_erro="",
                    tentativas_incremento=1,
                )
        # Conservador: ticket não localizado na listagem -> nunca re-POST.
        return await self._salvar_registro(
            registro, chamado,
            status=STATUS_RECONCILIACAO,
            ultimo_erro=motivo
            or "Ticket não localizado na listagem; reconciliação manual necessária",
            tentativas_incremento=1,
        )

    # -- persistência ------------------------------------------------------

    async def _salvar_registro(
        self,
        registro: dict | None,
        chamado: ChamadoCanonical | None,
        *,
        chat_id: str | None = None,
        status: str,
        ultimo_erro: str = "",
        external_ticket_id: str | None = None,
        tentativas_incremento: int = 0,
    ) -> dict:
        dados: dict = {
            "status": status,
            "ultimo_erro": ultimo_erro or "",
        }
        if chamado is not None:
            if chamado.assignee is not None:
                dados["assignee_kind"] = chamado.assignee.kind
                if chamado.assignee.external_id:
                    dados["external_assignee_id"] = (
                        chamado.assignee.external_id
                    )
            if chamado.department_code:
                dados["department_code"] = chamado.department_code
            if chamado.external_status_intent:
                dados["external_status_intent"] = (
                    chamado.external_status_intent
                )
                valor_externo = self._contract.status_externos.get(
                    chamado.external_status_intent
                )
                if valor_externo:
                    dados["external_status"] = valor_externo
        if external_ticket_id is not None:
            dados["external_ticket_id"] = external_ticket_id
        if tentativas_incremento:
            dados["tentativas"] = (
                (registro.get("tentativas") or 0)
                if registro
                else 0
            ) + tentativas_incremento
            # Só em tentativa externa: mapeamento falhou não é tentativa.
            dados["ultima_tentativa_em"] = datetime.now(UTC).isoformat()
        if registro:
            return await self._repos.integracao_chamados.update(
                registro["id"], dados
            )
        cid = chamado.source_chat_id if chamado is not None else chat_id
        if not cid:
            raise ValueError("Não há como criar registro sem chat_id")
        dados["chat_id"] = cid
        return await self._repos.integracao_chamados.create(dados)

    @staticmethod
    def _resultado(chat_id: str, registro: dict) -> dict:
        return {
            "chat_id": chat_id,
            "status": registro.get("status"),
            "external_ticket_id": registro.get("external_ticket_id") or None,
            "mensagem": registro.get("ultimo_erro") or None,
        }

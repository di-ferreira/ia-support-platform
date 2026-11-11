"""Client HTTP da API de chamados Emsoft (spec 11 §Autenticação e rede).

Rotas, métodos e header de autenticação vêm EXCLUSIVAMENTE do contrato
validado (`ContratoEmsoft`); este módulo não presume nada. A credencial
nunca chega a log — apenas snippets redigidos do corpo de resposta.
"""

import logging
import ssl
from pathlib import Path

import httpx

from app.integrations.emsoft_chamados.contract import ContratoEmsoft
from app.integrations.emsoft_chamados.exceptions import (
    AmbiguousResultError,
    ContractNotValidatedError,
    ExternalAuthError,
    ExternalRequestError,
)
from app.integrations.emsoft_chamados.mapper import resolve_path

logger = logging.getLogger("app.integracao_emsoft")

_MAX_LOG_BODY = 200


def _resposta_erro(body: object, status_code: int | None = None) -> str:
    """Mensagem curta e redigida a partir do corpo de resposta."""
    if isinstance(body, dict):
        msg = body.get("resposta") or body.get("message") or body.get("detail")
        if msg:
            return str(msg)[:_MAX_LOG_BODY]
    if body is not None:
        snippet = str(body)[:_MAX_LOG_BODY]
        return f"resposta: {snippet}"
    return "sem corpo de resposta"


class EmsoftChamadosClient:
    """Transporte fino sobre httpx; uma instância por sincronização.

    TLS: com `ca_bundle`, o contexto é montado no boot (validando o PEM);
    sem bundle, a flag `verify_tls` passa direto para o httpx (certifi).
    """

    def __init__(
        self,
        contract: ContratoEmsoft,
        token: str,
        timeout_s: float = 15.0,
        verify_tls: bool = True,
        ca_bundle: str | None = None,
    ) -> None:
        if not (token or "").strip():
            raise ContractNotValidatedError("Token da API Emsoft não configurado")
        ca_bundle = (ca_bundle or "").strip()
        if ca_bundle and not Path(ca_bundle).is_file():
            raise ContractNotValidatedError(
                f"Bundle de CAs não encontrado (EMSOFT_CHAMADOS_CA_BUNDLE): "
                f"{ca_bundle}"
            )
        self._contract = contract
        self._headers = {
            contract.autenticacao.header: f"{contract.autenticacao.prefixo}{token}".strip()
        }
        self._timeout_s = timeout_s
        if ca_bundle:
            # Bundle explícito tem precedência sobre a flag booleana: o
            # contexto é montado no boot, validando o PEM na hora.
            try:
                self._verify: ssl.SSLContext | bool = ssl.create_default_context(
                    cafile=ca_bundle
                )
            except ssl.SSLError as exc:
                raise ContractNotValidatedError(
                    f"Bundle de CAs inválido (EMSOFT_CHAMADOS_CA_BUNDLE): {exc}"
                ) from exc
        else:
            self._verify = verify_tls

    def _novo(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._contract.base_url.rstrip("/"),
            headers=self._headers,
            timeout=self._timeout_s,
            verify=self._verify,
        )

    async def criar(self, payload: dict) -> object:
        """POST de criação; timeout vira `AmbiguousResultError`."""
        return await self._request(
            self._contract.endpoints.criar, payload, ambiguo=True
        )

    async def editar(self, ticket_id: str, payload: dict) -> object:
        """Edição do chamado; o ID substitui `{ticket_id}` na rota."""
        ep = self._contract.endpoints.editar
        caminho = ep.path.replace("{ticket_id}", str(ticket_id))
        return await self._request(ep, payload, caminho=caminho, ambiguo=False)

    async def listar(self, referencia: str | None = None) -> list[dict]:
        """Listagem (opcionalmente filtrada pela referência única)."""
        ep = self._contract.endpoints.listar
        params = {}
        filtro = self._contract.filtro_referencia
        if filtro and referencia:
            params[filtro] = referencia
        body = await self._request(ep, None, params=params, ambiguo=False)
        itens = (
            resolve_path(body, self._contract.lista_em)
            if self._contract.lista_em
            else body
        )
        if not isinstance(itens, list):
            raise ExternalRequestError(
                "Resposta de listagem sem a matriz esperada "
                f"(lista_em={self._contract.lista_em!r})"
            )
        return [item for item in itens if isinstance(item, dict)]

    async def _request(
        self,
        endpoint,
        payload: dict | None,
        *,
        caminho: str | None = None,
        params: dict | None = None,
        ambiguo: bool = False,
    ) -> object:
        url = caminho or endpoint.path
        # Somente método+rota: nunca headers, nunca a credencial.
        logger.info(
            "emsoft: %s %s", endpoint.method, url,
            extra={"event": "emsoft_request", "rota": url},
        )
        try:
            async with self._novo() as http:
                resp = await http.request(
                    endpoint.method, url, json=payload, params=params
                )
        except httpx.TimeoutException as exc:
            msg = f"Timeout em {endpoint.method} {url}"
            if ambiguo:
                raise AmbiguousResultError(
                    f"{msg}; a criação pode ter sido aplicada — reconciliar"
                ) from exc
            raise ExternalRequestError(msg) from exc
        except httpx.HTTPError as exc:
            raise ExternalRequestError(
                f"Falha de rede em {endpoint.method} {url}: {exc.__class__.__name__}"
            ) from exc

        try:
            body = resp.json()
        except ValueError:
            body = None

        if resp.status_code in (401, 403):
            raise ExternalAuthError(
                f"Credencial rejeitada (HTTP {resp.status_code}): "
                f"{_resposta_erro(body)}",
                status_code=resp.status_code,
            )
        if resp.status_code >= 400:
            raise ExternalRequestError(
                f"HTTP {resp.status_code}: {_resposta_erro(body)}",
                status_code=resp.status_code,
            )
        if isinstance(body, dict) and body.get("success") is False:
            raise ExternalRequestError(
                f"API reportou erro (HTTP {resp.status_code}): "
                f"{_resposta_erro(body)}"
            )
        return body

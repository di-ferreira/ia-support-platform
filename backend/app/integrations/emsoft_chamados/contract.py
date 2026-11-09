"""Contrato validado da API de chamados Emsoft (spec 11 §Gate obrigatório).

Todo valor externo — esquema de autenticação, rotas, métodos, nomes de
campo, forma da resposta — vem EXCLUSIVAMENTE deste artefato JSON. Sem
um artefato válido (`validado: true` + evidência + `base_url` https), a
integração permanece desligada e nenhum client com suposições existe.

O formato esperado está documentado em `contract.example.json`.
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.integrations.emsoft_chamados.exceptions import ContractNotValidatedError

_METODOS_PERMITIDOS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


class EvidenciaContrato(BaseModel):
    """Prova auditável de quem/quando/onde o contrato foi confirmado."""

    origem: str = Field(min_length=1, description="Swagger, Postman, docs, exemplos")
    data: str = Field(min_length=1, description="Data da confirmação (AAAA-MM-DD)")
    descrito_por: str = Field(min_length=1, description="Quem confirmou o contrato")
    detalhes: str = ""


class AutenticacaoContrato(BaseModel):
    """Esquema de autenticação confirmado — nenhum valor é presumido."""

    esquema: str = Field(min_length=1, description="bearer, basic, apikey, cookie...")
    header: str = Field(min_length=1, description="Nome exato do header")
    prefixo: str = ""
    token_source: str = "config:emsoft_chamados_token"


class EndpointContrato(BaseModel):
    method: str
    path: str


class EndpointsContrato(BaseModel):
    listar: EndpointContrato
    criar: EndpointContrato
    editar: EndpointContrato


class ContratoEmsoft(BaseModel):
    """Contrato completo; `load` é a única porta de entrada."""

    validado: bool
    evidencia: EvidenciaContrato
    base_url: str
    autenticacao: AutenticacaoContrato
    endpoints: EndpointsContrato
    campos_criacao: dict[str, str] = Field(
        min_length=1,
        description="campo externo -> dot path no canônico (ex.: 'customer.name')",
    )
    campos_edicao: dict[str, str] = Field(
        min_length=1,
        description="campo externo -> dot path no canônico; '(ticket_id)' é o sentinela do ID",
    )
    campos_obrigatorios: list[str] = Field(
        min_length=1,
        description="campos externos obrigatórios na criação",
    )
    campo_id_resposta: str = Field(
        min_length=1, description="dot path do ID do chamado na resposta"
    )
    campo_referencia_externa: str | None = Field(
        default=None,
        description="campo externo que carrega a referência única (ex.: chat_id)",
    )
    filtro_referencia: str | None = Field(
        default=None,
        description="parâmetro de query da listagem para buscar pela referência",
    )
    lista_em: str | None = Field(
        default=None,
        description="dot path até a matriz na resposta de listagem; null = lista no topo",
    )
    status_externos: dict[str, str] = Field(
        default_factory=dict,
        description="intenção (IN_PROGRESS/WAITING_CUSTOMER/RESOLVED) -> valor externo",
    )

    @model_validator(mode="after")
    def _validar_contrato(self) -> "ContratoEmsoft":
        if not self.validado:
            raise ValueError(
                "validado deve ser true; o contrato ainda não foi confirmado "
                "com o responsável pela API"
            )
        if not self.base_url.startswith("https://"):
            raise ValueError("base_url deve usar https:// (TLS verificado)")
        for nome in ("listar", "criar", "editar"):
            ep = getattr(self.endpoints, nome)
            metodo = ep.method.upper()
            if metodo not in _METODOS_PERMITIDOS:
                raise ValueError(f"endpoints.{nome}.method inválido: {ep.method!r}")
            ep.method = metodo
            if not ep.path.startswith("/"):
                raise ValueError(f"endpoints.{nome}.path deve começar com '/'")
        if "{ticket_id}" not in self.endpoints.editar.path:
            raise ValueError(
                "endpoints.editar.path deve conter o placeholder {ticket_id}"
            )
        obrigatorios_desconhecidos = [
            c for c in self.campos_obrigatorios if c not in self.campos_criacao
        ]
        if obrigatorios_desconhecidos:
            raise ValueError(
                "campos_obrigatorios devem estar em campos_criacao: "
                f"{obrigatorios_desconhecidos}"
            )
        if (
            self.campo_referencia_externa is not None
            and self.campo_referencia_externa not in self.campos_criacao
        ):
            raise ValueError(
                "campo_referencia_externa deve existir em campos_criacao "
                "para o valor ser enviado na criação"
            )
        vazios = [
            i for i, v in self.status_externos.items() if not (v or "").strip()
        ]
        if vazios:
            raise ValueError(f"status_externos com valores vazios: {vazios}")
        return self

    @classmethod
    def load(cls, path: str | Path) -> "ContratoEmsoft":
        """Lê e valida o artefato; qualquer falha -> ContractNotValidatedError."""
        p = Path(path)
        if not p.is_file():
            raise ContractNotValidatedError(
                f"Arquivo de contrato não encontrado: {p} "
                "(preencha um artefato real conforme contract.example.json)"
            )
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContractNotValidatedError(
                f"Contrato com JSON malformado: {exc.msg}"
            ) from exc
        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            primeira = exc.errors()[0]
            local = ".".join(str(x) for x in primeira.get("loc", ()))
            raise ContractNotValidatedError(
                f"Contrato inválido em {local or '<raiz>'}: {primeira['msg']}"
            ) from exc

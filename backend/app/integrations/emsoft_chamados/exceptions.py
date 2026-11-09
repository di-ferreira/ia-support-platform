"""Erros tipados da integração com a API de chamados Emsoft (spec 11).

Hierarquia:

- `ContractNotValidatedError`: o artefato de contrato está ausente ou
  inválido; a integração permanece desabilitada.
- `MappingError`: falha ao converter o modelo canônico para o contrato
  externo; deve ocorrer **antes** de qualquer request HTTP.
- `ExternalRequestError`: falha técnica na comunicação com a API.
- `ExternalAuthError` (subclasse): credencial rejeitada (401/403).
- `AmbiguousResultError` (subclasse): timeout em request que pode ter
  gerado escrita; exige reconciliação, nunca repetição cega.
"""


class EmsoftChamadosError(Exception):
    """Base para todos os erros do módulo `emsoft_chamados`."""


class ChatNotFoundError(EmsoftChamadosError):
    """`chat_id` não existe na plataforma; nada foi tentado externamente."""


class ContractNotValidatedError(EmsoftChamadosError):
    """Artefato de contrato ausente, malformado ou não validado.

    Sem contrato validado (spec 11 §Gate obrigatório) não existe client,
    rota ou campo externo confirmado — a integração fica desligada.
    """


class MappingError(EmsoftChamadosError):
    """O modelo canônico não pôde ser mapeado para o contrato externo.

    Ex.: responsável sem `emsoft_usuario_id`, campo obrigatório do
    contrato ausente. `kind` classifica a causa ("HUMANO", "AI",
    "CAMPO"...); `field` identifica o campo externo envolvido.
    """

    def __init__(
        self,
        message: str,
        kind: str | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.field = field


class ExternalRequestError(EmsoftChamadosError):
    """Falha na comunicação com a API Emsoft (transporte ou HTTP >= 400)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ExternalAuthError(ExternalRequestError):
    """A API rejeitou a credencial (HTTP 401/403)."""


class AmbiguousResultError(ExternalRequestError):
    """Timeout em request que pode ter produzido escrita externa.

    O POST pode ter sido aplicado do lado Emsoft. O chamador deve
    reconciliar (listagem por referência externa) em vez de repetir a
    escrita.
    """

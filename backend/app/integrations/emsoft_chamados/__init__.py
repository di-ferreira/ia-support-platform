"""Integração com a API de chamados Emsoft (spec 11).

A integração nasce desabilitada e só é montada com as três condições
juntas: `emsoft_chamados_enabled=true`, artefato de contrato validado
(spec 11 §Gate obrigatório) e token configurado via env. Sem isso,
`build_emsoft_chamados_service` retorna `None` e as rotas respondem 503.
"""

from app.integrations.emsoft_chamados.client import EmsoftChamadosClient
from app.integrations.emsoft_chamados.contract import ContratoEmsoft
from app.integrations.emsoft_chamados.service import EmsoftChamadosService

__all__ = [
    "ContratoEmsoft",
    "EmsoftChamadosClient",
    "EmsoftChamadosService",
    "build_emsoft_chamados_service",
]


def build_emsoft_chamados_service(settings, repos):
    """Monta o service de sincronização; `None` quando desabilitada.

    Habilitada sem contrato válido ou sem token, levanta
    `ContractNotValidatedError`: é decisão explícita do operador ligar a
    integração, e ligá-la sem contrato validado é erro de configuração.
    """
    if not settings.emsoft_chamados_enabled:
        return None
    contract = ContratoEmsoft.load(settings.emsoft_chamados_contract_file)
    client = EmsoftChamadosClient(
        contract,
        settings.emsoft_chamados_token,
        timeout_s=settings.emsoft_chamados_timeout_s,
        verify_tls=settings.emsoft_chamados_verify_tls,
        ca_bundle=settings.emsoft_chamados_ca_bundle or None,
    )
    return EmsoftChamadosService(contract, client, repos, settings)

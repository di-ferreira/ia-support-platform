"""Seed idempotente dos departamentos iniciais.

Os seis codigos vem de docs/specs/10-departamentos-e-roteamento.md.
`atendimento_geral` e o destino de fallback do roteamento (spec 05/10).
"""

from app.appwrite.repositories import Repositories

DEPARTAMENTOS_SEED: list[dict] = [
    {
        "codigo": "suporte_tecnico",
        "nome": "Suporte Técnico",
        "descricao": "Erros, falhas e dúvidas técnicas do ERP",
        "ordem": 1,
    },
    {
        "codigo": "financeiro",
        "nome": "Financeiro",
        "descricao": "Cobrança, boleto, negociação e faturamento",
        "ordem": 2,
    },
    {
        "codigo": "comercial",
        "nome": "Comercial",
        "descricao": "Contratação, propostas e novos produtos",
        "ordem": 3,
    },
    {
        "codigo": "administrativo",
        "nome": "Administrativo",
        "descricao": "Cadastro e assuntos administrativos",
        "ordem": 4,
    },
    {
        "codigo": "implantacao",
        "nome": "Implantação",
        "descricao": "Configuração inicial, migração e treinamento",
        "ordem": 5,
    },
    {
        "codigo": "atendimento_geral",
        "nome": "Atendimento Geral",
        "descricao": "Triagem e solicitações ainda sem setor definido",
        "ordem": 6,
    },
]


async def semear(repos: Repositories) -> dict:
    criados = atualizados = ignorados = 0
    for definicao in DEPARTAMENTOS_SEED:
        existente = await repos.departamentos.get_by_codigo(definicao["codigo"])
        if existente is None:
            await repos.departamentos.create(
                {**definicao, "ativo": True, "recebe_transferencias": True,
                 "permite_atribuicao_automatica": False}
            )
            criados += 1
            continue
        diferencas = {
            k: v
            for k, v in definicao.items()
            if k != "codigo" and existente.get(k) != v
        }
        if diferencas:
            await repos.departamentos.update(existente["id"], diferencas)
            atualizados += 1
        else:
            ignorados += 1
    return {"criados": criados, "atualizados": atualizados, "ignorados": ignorados}

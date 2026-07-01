#!/usr/bin/env python3
"""Popula a base de conhecimento com artigos para cada categoria."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import async_session
from app.models.knowledge_base import KnowledgeBase, CategoriaConhecimento

ARTIGOS = {
    CategoriaConhecimento.fiscal: [
        {
            "titulo": "Emissão de Nota Fiscal Eletrônica (NF-e)",
            "conteudo": (
                "Para emitir uma NF-e no sistema EMSoft, acesse o módulo Fiscal > "
                "Notas Fiscais > Nova NF-e. Preencha os dados do destinatário, "
                "produtos/serviços e valores. Após o preenchimento, clique em "
                "'Validar' para verificar inconsistências e depois em 'Emitir'. "
                "A NF-e será transmitida para a SEFAZ. O status da autorização "
                "pode ser consultado em Fiscal > Notas Fiscais > Consultar Status."
            ),
        },
        {
            "titulo": "Como consultar o SPED Fiscal",
            "conteudo": (
                "O SPED Fiscal é gerado automaticamente pelo sistema com base "
                "nas NF-e e NFC-e emitidas no período. Para consultar, vá em "
                "Fiscal > SPED > SPED Fiscal. Selecione o período desejado e "
                "clique em 'Gerar Arquivo'. O arquivo será gerado no formato "
                "TXT conforme o leiaute do governo. É possível realizar o "
                "pós-validação antes do envio oficial."
            ),
        },
        {
            "titulo": "Regime Tributário: Simples Nacional x Lucro Presumido",
            "conteudo": (
                "O regime tributário impacta diretamente no cálculo dos impostos. "
                "No Simples Nacional, o imposto é calculado com base no "
                "Faturamento dos últimos 12 meses e a alíquota varia conforme "
                "a faixa de receita. No Lucro Presumido, a base de cálculo do "
                "IRPJ e CSLL é determinada por presunção sobre a receita bruta. "
                "Para alterar o regime no sistema, vá em Configurações > Empresa "
                "> Regime Tributário e selecione a opção desejada."
            ),
        },
        {
            "titulo": "Cancelamento de Nota Fiscal",
            "conteudo": (
                "Uma NF-e pode ser cancelada em até 24 horas após a emissão, "
                "desde que não tenha ocorrido a circulação da mercadoria. "
                "Para cancelar, acesse Fiscal > Notas Fiscais, localize a NF-e "
                "desejada e clique em 'Cancelar'. Informe o motivo do "
                "cancelamento e clique em 'Confirmar'. O sistema enviará o "
                "pedido de cancelamento para a SEFAZ. Em caso de sucesso, "
                "a NF-e será marcada como cancelada."
            ),
        },
        {
            "titulo": "Como emitir NFC-e (venda ao consumidor)",
            "conteudo": (
                "A NFC-e é utilizada para vendas ao consumidor final. No "
                "módulo Fiscal > NFC-e, clique em 'Nova NFC-e'. Selecione o "
                "cliente (ou 'Consumidor Final' caso não identifique), adicione "
                "os itens da venda e finalize. A NFC-e será transmitida em "
                "tempo real para a SEFAZ. É obrigatório informar o CPF/CNPJ "
                "para vendas acima de R$ 10.000,00."
            ),
        },
    ],
    CategoriaConhecimento.estoque: [
        {
            "titulo": "Como dar entrada em produtos no estoque",
            "conteudo": (
                "Para registrar a entrada de produtos, acesse Estoque > "
                "Movimentações > Entrada. Selecione o fornecedor, o tipo de "
                "movimentação (Compra, Devolução, Ajuste) e adicione os "
                "produtos com suas quantidades e valores. Após salvar, o "
                "estoque será atualizado automaticamente. É possível gerar "
                "um relatório de entrada para conferência."
            ),
        },
        {
            "titulo": "Inventário físico: como realizar a contagem",
            "conteudo": (
                "O inventário físico deve ser realizado periodicamente para "
                "garantir a exatidão do saldo contábil. No sistema, vá em "
                "Estoque > Inventário > Nova Contagem. Selecione o depósito "
                "e os produtos a serem contados. Imprima a lista de contagem "
                "e preencha as quantidades físicas. Após a digitação dos "
                "dados, o sistema calculará as diferenças e gerará os "
                "ajustes necessários automaticamente."
            ),
        },
        {
            "titulo": "Transferência entre depósitos",
            "conteudo": (
                "Para transferir produtos entre depósitos, acesse Estoque > "
                "Movimentações > Transferência. Selecione o depósito de "
                "origem e o de destino, adicione os produtos e quantidades. "
                "A transferência não altera o saldo total da empresa, apenas "
                "redistribui entre os depósitos. O histórico completo de "
                "transferências pode ser consultado em Relatórios > "
                "Movimentações > Transferências."
            ),
        },
        {
            "titulo": "Produto com estoque negativo: como resolver",
            "conteudo": (
                "Estoque negativo ocorre quando uma venda é realizada sem "
                "que a entrada do produto tenha sido registrada. Para "
                "resolver, primeiro identifique a origem do problema em "
                "Estoque > Relatórios > Estoque Negativo. Em seguida, "
                "registre a entrada em falta através de uma movimentação "
                "de ajuste ou localize a nota de compra que deixou de ser "
                "lançada. O sistema permite configurar bloqueio de vendas "
                "com estoque negativo em Configurações > Estoque."
            ),
        },
    ],
    CategoriaConhecimento.compras: [
        {
            "titulo": "Processo de cotação com fornecedores",
            "conteudo": (
                "O módulo de Compras permite realizar cotações com múltiplos "
                "fornecedores. Acesse Compras > Cotação > Nova Cotação. "
                "Adicione os itens desejados e selecione os fornecedores "
                "que receberão a cotação. O sistema enviará automaticamente "
                "as solicitações por e-mail. Após receber as respostas, "
                "você pode comparar preços e prazos na tela de 'Comparar "
                "Cotações' e selecionar a melhor proposta."
            ),
        },
        {
            "titulo": "Como gerar pedido de compra a partir de uma cotação",
            "conteudo": (
                "Após selecionar a melhor cotação, clique em 'Gerar Pedido' "
                "na tela de comparação. O pedido de compra será criado com "
                "os dados do fornecedor vencedor. Revise as informações, "
                "confirme o pedido e ele será enviado ao fornecedor. O "
                "pedido pode ser acompanhado em Compras > Pedidos > "
                "Acompanhamento, onde é possível registrar o recebimento "
                "parcial ou total dos itens."
            ),
        },
        {
            "titulo": "Recebimento de mercadorias e conferência",
            "conteudo": (
                "No recebimento de mercadorias, acesse Compras > "
                "Recebimento. Informe o número do pedido de compra ou "
                "da nota fiscal do fornecedor. O sistema exibirá os itens "
                "esperados. Confira as quantidades recebidas e registre "
                "divergências, se houver. Avarias devem ser registradas "
                "com foto no próprio sistema. Após a conferência, o "
                "estoque será atualizado automaticamente."
            ),
        },
    ],
    CategoriaConhecimento.vendas: [
        {
            "titulo": "Como registrar uma venda no PDV",
            "conteudo": (
                "No módulo PDV (Ponto de Venda), clique em 'Nova Venda'. "
                "Identifique o cliente (opcional para vendas até R$ 500,00), "
                "adicione os produtos lendo o código de barras ou "
                "selecionando manualmente. O sistema calculará o total "
                "com descontos e impostos automaticamente. Selecione a "
                "forma de pagamento (Dinheiro, Cartão, Pix, Boleto) e "
                "finalize a venda. A NFC-e será emitida automaticamente."
            ),
        },
        {
            "titulo": "Gestão de comissões de vendedores",
            "conteudo": (
                "As comissões são calculadas automaticamente com base nas "
                "regras cadastradas em Vendas > Configurações > Comissões. "
                "É possível definir percentuais fixos por vendedor ou "
                "tabelas progressivas por faixa de vendas. O relatório de "
                "comissões pode ser acessado em Vendas > Relatórios > "
                "Comissões. O fechamento mensal gera um resumo para "
                "pagamento das comissões."
            ),
        },
        {
            "titulo": "Como emitir boleto bancário para o cliente",
            "conteudo": (
                "Para emitir boletos, é necessário ter uma carteira de "
                "cobrança configurada no sistema. Ao finalizar uma venda "
                "a prazo, selecione 'Boleto' como forma de pagamento. O "
                "sistema gerará o boleto com vencimento e valor "
                "configurados. Os boletos podem ser reimpressos em "
                "Vendas > Boletos > Emitidos. O status de pagamento é "
                "atualizado automaticamente via integração bancária."
            ),
        },
        {
            "titulo": "Como funciona a venda com entrega",
            "conteudo": (
                "Para vendas com entrega, cadastre o endereço de entrega "
                "no ato da venda. O sistema calcula o frete com base no "
                "CEP e peso dos produtos. É possível agendar a data de "
                "entrega e selecionar a transportadora. O status da "
                "entrega pode ser acompanhado pelo cliente através do "
                "portal de acompanhamento. A rota de entregas é "
                "otimizada automaticamente para reduzir custos."
            ),
        },
    ],
    CategoriaConhecimento.financeiro: [
        {
            "titulo": "Conciliação bancária automática",
            "conteudo": (
                "A conciliação bancária compara os lançamentos do sistema "
                "com o extrato bancário. Acesse Financeiro > Conciliação "
                "> Nova Conciliação. Selecione a conta bancária e importe "
                "o extrato (OFX, CSV ou PDF). O sistema sugere "
                "correspondências entre os lançamentos. Confira e confirme "
                "as correspondências. Divergências podem ser ajustadas "
                "manualmente. Ao finalizar, o saldo contábil estará "
                "igual ao saldo bancário."
            ),
        },
        {
            "titulo": "Fluxo de caixa: como usar o D+",
            "conteudo": (
                "A projeção de fluxo de caixa D+ mostra as entradas e "
                "saídas previstas para os próximos dias. Acesse "
                "Financeiro > Fluxo de Caixa > Projeção. O sistema "
                "considera contas a receber, contas a pagar e vendas "
                "recorrentes. É possível simular cenários alterando "
                "prazos de pagamento/recebimento. O relatório D+ ajuda "
                "na tomada de decisões sobre capital de giro."
            ),
        },
        {
            "titulo": "Como emitir nota promissória",
            "conteudo": (
                "A nota promissória pode ser emitida para formalizar "
                "dívidas de clientes. Em Financeiro > Contas a Receber, "
                "selecione o título desejado e clique em 'Emitir "
                "Promissória'. Informe os dados do sacado, valor e "
                "vencimento. O sistema gera a promissória no formato "
                "padrão. É possível enviar por e-mail ao cliente "
                "diretamente do sistema."
            ),
        },
        {
            "titulo": "Fechamento mensal: checklist",
            "conteudo": (
                "Para o fechamento mensal, siga este checklist no sistema: "
                "1) Concilie todas as contas bancárias; 2) Verifique "
                "pendências em contas a receber e a pagar; 3) Gere e "
                "confira o SPED Fiscal; 4) Feche o estoque (inventário "
                "se necessário); 5) Apure os impostos do período; "
                "6) Gere o relatório de resultados. Cada etapa é "
                "acessível em Financeiro > Fechamento > Checklist."
            ),
        },
    ],
}


async def seed():
    async with async_session() as session:
        from sqlalchemy import select, func

        result = await session.execute(select(func.count(KnowledgeBase.id)))
        count = result.scalar()

        if count > 0:
            print(f"Seed skipped: {count} artigos já existem.")
            return

        total = 0
        for categoria, artigos in ARTIGOS.items():
            for artigo_data in artigos:
                artigo = KnowledgeBase(
                    titulo=artigo_data["titulo"],
                    conteudo=artigo_data["conteudo"],
                    categoria=categoria,
                    ativo=True,
                )
                session.add(artigo)
                total += 1

        await session.commit()
        print(f"Seed completed: {total} artigos inseridos na base de conhecimento.")


if __name__ == "__main__":
    asyncio.run(seed())

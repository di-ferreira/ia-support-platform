"""Enumerações de domínio centralizadas.

Módulo canônico dos enums de domínio: `app/appwrite/schema.py` deriva as
listas de valores deles. Os módulos `app/models/<x>.py` reexportam cada
enum por compatibilidade histórica (imports antigos continuam válidos).
"""

import enum


class StatusChat(enum.StrEnum):
    novo = "NOVO"
    ia_analisando = "IA_ANALISANDO"
    aguardando_cliente = "AGUARDANDO_CLIENTE"
    aguardando_humano_com_solucao = "AGUARDANDO_HUMANO_COM_SOLUCAO"
    aguardando_humano_sem_solucao = "AGUARDANDO_HUMANO_SEM_SOLUCAO"
    em_atendimento = "EM_ATENDIMENTO"
    resolvido = "RESOLVIDO"
    encerrado = "ENCERRADO"


class PrioridadeChat(enum.StrEnum):
    baixa = "baixa"
    media = "media"
    alta = "alta"
    urgente = "urgente"


class PerfilAtendente(enum.StrEnum):
    admin = "admin"
    supervisor = "supervisor"
    atendente = "atendente"


class TipoMensagem(enum.StrEnum):
    texto = "texto"
    audio = "audio"
    documento = "documento"
    imagem = "imagem"


class RemetenteMensagem(enum.StrEnum):
    cliente = "cliente"
    ia = "ia"
    atendente = "atendente"
    sistema = "sistema"


class StatusIA(enum.StrEnum):
    resolvido_pela_ia = "RESOLVIDO_PELA_IA"
    transferir_com_solucao = "TRANSFERIR_COM_SOLUCAO"
    transferir_sem_solucao = "TRANSFERIR_SEM_SOLUCAO"
    esclarecimento = "ESCLARECIMENTO"


class CategoriaConhecimento(enum.StrEnum):
    fiscal = "fiscal"
    estoque = "estoque"
    compras = "compras"
    vendas = "vendas"
    financeiro = "financeiro"
    multiempresa = "multiempresa"


class Intencao(enum.StrEnum):
    """As 9 intenções da taxonomia inicial (docs/specs/05-ai-pipeline.md)."""

    problema_tecnico = "problema_tecnico"
    duvida_uso_erp = "duvida_uso_erp"
    solicitacao_financeira = "solicitacao_financeira"
    solicitacao_comercial = "solicitacao_comercial"
    solicitacao_administrativa = "solicitacao_administrativa"
    implantacao_treinamento = "implantacao_treinamento"
    solicitacao_humano = "solicitacao_humano"
    duvida_geral = "duvida_geral"
    intencao_desconhecida = "intencao_desconhecida"


class CategoriaERP(enum.StrEnum):
    """Módulos do ERP conhecidos pela IA. NÃO é departamento (spec 10).

    `outro` não existe: assunto fora destes módulos é `categoria_erp=null`.
    """

    fiscal = "fiscal"
    estoque = "estoque"
    compras = "compras"
    vendas = "vendas"
    financeiro = "financeiro"
    multiempresa = "multiempresa"


class TipoAtor(enum.StrEnum):
    """Identidade de quem executou a ação auditada.

    Spec 04 §Identidade de serviço da IA e §Auditoria obrigatória: ações
    automáticas rodam sob identidade técnica auditável (`IA`, com modelo
    quando aplicável); `SISTEMA` cobre fluxos internos e `SERVICO`, a
    credencial de servidor da integração Emsoft.
    """

    HUMANO = "HUMANO"
    IA = "IA"
    SISTEMA = "SISTEMA"
    SERVICO = "SERVICO"


class AcaoAuditoria(enum.StrEnum):
    """Tipos de ação auditável sobre um chat (spec 04 §Auditoria obrigatória)."""

    CRIACAO = "CRIACAO"
    STATUS = "STATUS"
    ATRIBUICAO = "ATRIBUICAO"
    TRANSFERENCIA = "TRANSFERENCIA"
    TRANSFERENCIA_DEPARTAMENTO = "TRANSFERENCIA_DEPARTAMENTO"
    PRIORIDADE = "PRIORIDADE"
    REABERTURA = "REABERTURA"
    CONFIRMACAO_RESOLUCAO = "CONFIRMACAO_RESOLUCAO"


class StatusOutbox(enum.StrEnum):
    """Ciclo de vida de um evento na fila (spec 12 §Outbox pattern).

    `PROCESSANDO` existe apenas enquanto um worker mantém o lease; com o
    lease expirado o evento volta a ser elegível (reconciliação periódica).
    """

    pendente = "PENDENTE"
    processando = "PROCESSANDO"
    concluido = "CONCLUIDO"
    falha_permanente = "FALHA_PERMANENTE"


class TipoEventoOutbox(enum.StrEnum):
    """Tipos de evento de sincronização com o chamado Emsoft (spec 12).

    Não há evento por mensagem comum sem mudança relevante; mudanças
    repetidas idênticas deduplicam pela `event_key` determinística.
    """

    TICKET_CREATE_REQUESTED = "TICKET_CREATE_REQUESTED"
    TICKET_UPDATE_REQUESTED = "TICKET_UPDATE_REQUESTED"
    TICKET_ASSIGNMENT_CHANGED = "TICKET_ASSIGNMENT_CHANGED"
    TICKET_RESOLUTION_REQUESTED = "TICKET_RESOLUTION_REQUESTED"
    TICKET_REOPEN_REQUESTED = "TICKET_REOPEN_REQUESTED"

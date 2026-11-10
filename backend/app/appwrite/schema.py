"""Schema declarativo do banco Appwrite.

Espelha os modelos SQLAlchemy de `app/models/` para collections Appwrite.

Decisões:
- Chaves primárias: Appwrite gera `id` (ULID, string) automaticamente; não declaramos.
- `created_at`/`updated_at`: usamos os campos nativos do Appwrite (`createdAt`/`updatedAt`).
- Foreign keys: atributos `string` armazenando o `id` (ULID) do documento relacionado,
  resolvidos em join manual no repositório (espelha o comportamento dos services atuais).
- M:N `chat_tag`: collection junction `chat_tags` com `chat_id` + `tag_id`.
- Textos longos (SQL `Text`): atributo `string` com tamanho máximo (32767).
- Enums: atributo `enum` com os valores exatos dos `StrEnum` do modelo.

A unicidade (ex.: `atendentes.email`, `clientes.documento`) continua garantida pela
aplicação (os services checam duplicidade antes de inserir), não por índice de banco.
"""

from app.models.departamento import CategoriaERP, Intencao
from app.models.ia_diagnostico import StatusIA
from app.models.knowledge_base import CategoriaConhecimento
from app.models.outbox import StatusOutbox, TipoEventoOutbox

DB_ID = "chatbot"
DB_NAME = "Chatbot IA"

TEXT_SIZE = 32767

# Tipos de atributo (valores wire do Appwrite)
STRING = "string"
INTEGER = "integer"
FLOAT = "float"
BOOLEAN = "boolean"
DATETIME = "datetime"
ENUM = "enum"

STATUS_CHAT = [
    "NOVO",
    "IA_ANALISANDO",
    "AGUARDANDO_CLIENTE",
    "AGUARDANDO_HUMANO_COM_SOLUCAO",
    "AGUARDANDO_HUMANO_SEM_SOLUCAO",
    "EM_ATENDIMENTO",
    "RESOLVIDO",
    "ENCERRADO",
]

PRIORIDADE_CHAT = ["baixa", "media", "alta", "urgente"]

PERFIL_ATENDENTE = ["admin", "supervisor", "atendente"]

STATUS_INTEGRACAO_CHAMADO = ["PENDENTE", "SINCRONIZADO", "ERRO", "RECONCILIACAO"]

# Spec 12: estados da fila outbox. `PROCESSANDO` só existe enquanto um
# worker mantém o lease; lease expirado volta a ser elegível (reconciliação).
STATUS_OUTBOX = [s.value for s in StatusOutbox]

# Spec 12 §Tipos de evento. Não há evento por mensagem comum sem mudança
# relevante; repetições idênticas deduplicam pela `event_key`.
TIPO_EVENTO_OUTBOX = [t.value for t in TipoEventoOutbox]

ASSIGNEE_KIND = ["AI", "HUMANO"]

REMETENTE_MENSAGEM = ["cliente", "ia", "atendente", "sistema"]

TIPO_MENSAGEM = ["texto", "audio", "documento", "imagem"]

STATUS_IA = [s.value for s in StatusIA]

INTENCAO = [i.value for i in Intencao]
CATEGORIA_ERP = [c.value for c in CategoriaERP]
CATEGORIA_CONHECIMENTO = [c.value for c in CategoriaConhecimento]


def str_attr(key: str, size: int = 255, required: bool = True) -> dict:
    return {"type": STRING, "key": key, "size": size, "required": required}


def fk_attr(key: str, required: bool = True) -> dict:
    """FK como `string` armazenando o `id` (ULID) do documento relacionado."""
    return {"type": STRING, "key": key, "size": 36, "required": required}


def text_attr(key: str, required: bool = False) -> dict:
    return {"type": STRING, "key": key, "size": TEXT_SIZE, "required": required}


def int_attr(key: str, required: bool = False, default: int | None = None) -> dict:
    dados = {"type": INTEGER, "key": key, "required": required}
    if default is not None:
        dados["default"] = default
    return dados


def float_attr(key: str, required: bool = False) -> dict:
    return {"type": FLOAT, "key": key, "required": required}


def bool_attr(key: str, required: bool = False, default: bool | None = None) -> dict:
    return {"type": BOOLEAN, "key": key, "required": required, "default": default}


def datetime_attr(key: str, required: bool = False) -> dict:
    return {"type": DATETIME, "key": key, "required": required}


def enum_attr(
    key: str,
    elements: list[str],
    required: bool = True,
    default: str | None = None,
) -> dict:
    return {
        "type": ENUM,
        "key": key,
        "elements": elements,
        "required": required,
        "default": default,
    }


COLLECTIONS: dict[str, dict] = {
    "atendentes": {
        "name": "Atendentes",
        "attributes": [
            str_attr("nome", 255),
            str_attr("email", 255),
            str_attr("hash_senha", 255),
            enum_attr("perfil", PERFIL_ATENDENTE, required=False, default="atendente"),
            str_attr("setor", 50, required=False),
            fk_attr("departamento_id", required=False),
            # ID do atendente na API de chamados Emsoft (spec 11): só é
            # usado quando o contrato validado define o campo de responsável.
            str_attr("emsoft_usuario_id", 100, required=False),
            bool_attr("ativo", default=True),
        ],
    },
    "clientes": {
        "name": "Clientes",
        "attributes": [
            str_attr("nome", 255),
            str_attr("documento", 20),
            str_attr("email", 255, required=False),
            str_attr("telefone", 20, required=False),
            text_attr("endereco"),
            str_attr("versao_erp", 50, required=False),
        ],
    },
    "lojas": {
        "name": "Lojas",
        "attributes": [
            fk_attr("cliente_id"),
            str_attr("nome", 255),
            str_attr("documento", 20, required=False),
            text_attr("endereco"),
        ],
    },
    "chats": {
        "name": "Chats",
        "attributes": [
            fk_attr("cliente_id"),
            fk_attr("loja_id", required=False),
            fk_attr("atendente_id", required=False),
            fk_attr("departamento_id", required=False),
            enum_attr("status", STATUS_CHAT, required=False, default="NOVO"),
            enum_attr("prioridade", PRIORIDADE_CHAT, required=False, default="media"),
            text_attr("resumo_problema"),
            text_attr("solucao_sugerida_ia"),
            text_attr("causa_provavel"),
            float_attr("nivel_confianca_ia"),
            bool_attr("necessita_humano"),
            str_attr("setor_alvo", 50, required=False),
            str_attr("whatsapp_number", 20, required=False),
            datetime_attr("ultima_mensagem_em"),
        ],
    },
    "mensagens": {
        "name": "Mensagens",
        "attributes": [
            fk_attr("chat_id"),
            enum_attr("remetente", REMETENTE_MENSAGEM),
            enum_attr("tipo", TIPO_MENSAGEM, required=False, default="texto"),
            text_attr("conteudo"),
            str_attr("url_arquivo", 500, required=False),
            str_attr("whatsapp_message_id", 100, required=False),
        ],
    },
    "tags": {
        "name": "Tags",
        "attributes": [
            str_attr("nome", 100),
            str_attr("cor", 7, required=False),
        ],
    },
    "chat_tags": {
        "name": "ChatTags",
        "attributes": [
            fk_attr("chat_id"),
            fk_attr("tag_id"),
        ],
    },
    "ia_diagnosticos": {
        "name": "IADiagnosticos",
        "attributes": [
            fk_attr("chat_id"),
            enum_attr("status_ia", STATUS_IA),
            text_attr("resumo"),
            text_attr("solucao"),
            text_attr("causa_provavel"),
            float_attr("confianca"),
            str_attr("modelo_usado", 100, required=False),
            int_attr("tokens_usados"),
            # Snapshot de roteamento (spec 05 §Persistência e eventos).
            # `artigos_consultados` é JSON serializado: Appwrite não tem tipo JSON.
            str_attr("intencao", 80, required=False),
            str_attr("subintencao", 100, required=False),
            str_attr("categoria_erp", 50, required=False),
            str_attr("departamento_sugerido_codigo", 80, required=False),
            fk_attr("departamento_id", required=False),
            text_attr("motivo"),
            text_attr("artigos_consultados"),
        ],
    },
    "knowledge_bases": {
        "name": "KnowledgeBases",
        "attributes": [
            str_attr("titulo", 255),
            text_attr("conteudo"),
            enum_attr("categoria", CATEGORIA_CONHECIMENTO),
            str_attr("tipo_arquivo", 50, required=False),
            str_attr("url_arquivo", 500, required=False),
            bool_attr("ativo", default=True),
        ],
    },
    "departamentos": {
        "name": "Departamentos",
        "attributes": [
            str_attr("codigo", 80),
            str_attr("nome", 255),
            str_attr("descricao", 1000, required=False),
            bool_attr("ativo", default=True),
            int_attr("ordem"),
            bool_attr("recebe_transferencias", default=True),
            bool_attr("permite_atribuicao_automatica", default=False),
        ],
    },
    "regras_roteamento": {
        "name": "RegrasRoteamento",
        "attributes": [
            str_attr("intencao", 80),
            str_attr("subintencao", 100, required=False),
            str_attr("categoria_erp", 50, required=False),
            fk_attr("departamento_id"),
            int_attr("prioridade_regra", required=True),
            bool_attr("ativo", default=True),
        ],
    },
    # Spec 11 §Persistência: um registro por chat (cardinalidade 1:1),
    # rastro da sincronização com o chamado Emsoft.
    "integracao_chamados": {
        "name": "IntegracaoChamados",
        "attributes": [
            fk_attr("chat_id"),
            str_attr("external_ticket_id", 100, required=False),
            str_attr("external_url", 500, required=False),
            enum_attr("status", STATUS_INTEGRACAO_CHAMADO, required=False, default="PENDENTE"),
            enum_attr("assignee_kind", ASSIGNEE_KIND, required=False),
            str_attr("external_assignee_id", 100, required=False),
            str_attr("department_code", 80, required=False),
            str_attr("external_status", 100, required=False),
            str_attr("external_status_intent", 100, required=False),
            int_attr("tentativas", required=False, default=0),
            str_attr("ultimo_erro", 1000, required=False),
            datetime_attr("ultima_tentativa_em", required=False),
        ],
    },
    # Spec 12 §Outbox pattern: transições locais persistem o evento aqui com
    # `event_key` determinística e seguem o atendimento sem aguardar a API
    # Emsoft; o worker processa com lock/lease e retry com backoff.
    # Unicidade da `event_key` garantida pela aplicação (Appwrite sem índice
    # único): deduplicar por list_all + comparação antes de criar.
    "integration_outbox": {
        "name": "IntegrationOutbox",
        "attributes": [
            str_attr("event_key", 255),
            fk_attr("chat_id"),
            enum_attr("event_type", TIPO_EVENTO_OUTBOX),
            enum_attr("status", STATUS_OUTBOX, required=False, default="PENDENTE"),
            # Versão sequencial do agregado embutida na key
            # (ex.: emsoft:update:{chat_id}:{versão}); usada para descartar
            # eventos obsoletos (spec 12 §Concorrência).
            int_attr("event_version", required=False, default=0),
            int_attr("tentativas", required=False, default=0),
            # Snapshot serializado (JSON) dos dados a enviar; nunca cabeçalhos
            # nem credenciais (spec 12 §Retenção e auditoria).
            text_attr("payload"),
            str_attr("ultimo_erro", 1000, required=False),
            datetime_attr("ultima_tentativa_em", required=False),
            datetime_attr("next_attempt_at", required=False),
            str_attr("lease_owner", 100, required=False),
            datetime_attr("lease_expires_at", required=False),
            # Reprocessamento manual (spec 12): ator e motivo em auditoria;
            # a data é o `created_at` nativo do evento.
            str_attr("ator", 100, required=False),
            text_attr("motivo"),
        ],
    },
}

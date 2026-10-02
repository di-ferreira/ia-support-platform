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

REMETENTE_MENSAGEM = ["cliente", "ia", "atendente", "sistema"]

TIPO_MENSAGEM = ["texto", "audio", "documento", "imagem"]

STATUS_IA = ["RESOLVIDO_PELA_IA", "TRANSFERIR_COM_SOLUCAO", "TRANSFERIR_SEM_SOLUCAO"]

CATEGORIA_CONHECIMENTO = ["fiscal", "estoque", "compras", "vendas", "financeiro"]


def str_attr(key: str, size: int = 255, required: bool = True) -> dict:
    return {"type": STRING, "key": key, "size": size, "required": required}


def fk_attr(key: str, required: bool = True) -> dict:
    """FK como `string` armazenando o `id` (ULID) do documento relacionado."""
    return {"type": STRING, "key": key, "size": 36, "required": required}


def text_attr(key: str, required: bool = False) -> dict:
    return {"type": STRING, "key": key, "size": TEXT_SIZE, "required": required}


def int_attr(key: str, required: bool = False) -> dict:
    return {"type": INTEGER, "key": key, "required": required}


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
            enum_attr("perfil", PERFIL_ATENDENTE, default="atendente"),
            str_attr("setor", 50, required=False),
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
            enum_attr("status", STATUS_CHAT, default="NOVO"),
            enum_attr("prioridade", PRIORIDADE_CHAT, default="media"),
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
            enum_attr("tipo", TIPO_MENSAGEM, default="texto"),
            text_attr("conteudo"),
            str_attr("url_arquivo", 500, required=False),
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
}

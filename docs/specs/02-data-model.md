# SPEC 02 — Modelo de Dados

Fonte de dados: **Appwrite** (self-hosted). Coleções declaradas em
`backend/app/appwrite/schema.py`, criadas idempotentemente por
`backend/app/appwrite/bootstrap.py` no startup da aplicação (`backend/app/main.py`,
lifespan).

Database: `chatbot` (`DB_ID`). 9 coleções.

## Convenções de modelagem

Estas regras derivam das decisões documentadas em `schema.py:1-16` e valem para
qualquer coleção nova.

| Regra | Implementação |
|---|---|
| **Chave primária** | Appwrite gera `id` (ULID, string 36). Nunca declaramos. |
| **Timestamps** | `createdAt` / `updatedAt` nativos do Appwrite. Não criamos colunas. |
| **Foreign key** | Atributo `string` de tamanho 36 guardando o `id` (ULID) do documento relacionado. **Sem constraint no banco** — resolvido por join manual no repositório. |
| **Texto longo** | `string` com tamanho máximo `TEXT_SIZE = 32767`. Não há tipo `text`. |
| **Enum** | Atributo `enum` com os valores exatos do `StrEnum` correspondente em `backend/app/models/`. |
| **Dinheiro** | Não aplicável. Não há valores monetários no sistema. |
| **Booleano** | `boolean`. Default explícito quando faz sentido. |
| **Data/hora** | `datetime`, sempre UTC. |
| **Unicidade** | **Garantida pela aplicação**, nunca por índice. Ver §Unicidade. |

## Coleções

### `atendentes` — Atendentes

Quem usa o sistema. Rotas em `/auth/usuarios`.

| Atributo | Tipo | Obrig. | Default | Notas |
|---|---|---|---|---|
| `nome` | string(255) | sim | — | |
| `email` | string(255) | sim | — | Login. Unicidade garantida por `get_by_email` |
| `hash_senha` | string(255) | sim | — | bcrypt. **Nunca** retornado pela API |
| `perfil` | enum | sim | `atendente` | `admin` \| `supervisor` \| `atendente` |
| `setor` | string(50) | não | — | Grupo de trabalho |
| `ativo` | boolean | não | `true` | Soft delete. Inativo = 401 no login |

**Invariantes**

- `email` é único no conjunto de contas **ativas**. Reativar uma conta desativada exige
  checar duplicidade de novo.
- `perfil` só muda por admin (ver [04-rbac-matrix](04-rbac-matrix.md)).
- Desativar é a única forma de "remover": `DELETE /auth/usuarios/{id}` faz
  `ativo = false`, nunca delete.
- `hash_senha` nunca sai do repositório em resposta de API.

### `clientes` — Clientes

Empresas que usam o ERP EMSoft.

| Atributo | Tipo | Obrig. | Default | Notas |
|---|---|---|---|---|
| `nome` | string(255) | sim | — | Razão social |
| `documento` | string(20) | sim | — | **CNPJ**, não CPF |
| `email` | string(255) | não | — | |
| `telefone` | string(20) | não | — | |
| `endereco` | text | não | — | |
| `versao_erp` | string(50) | não | — | Versão do ERP do cliente |

**Invariantes**

- `documento` é único. `POST /clientes` com documento repetido devolve **409**.
- O CNPJ é a identidade natural. O `telefone` **não** é chave — o mesmo cliente pode ter
  vários telefones, e `get_by_telefone` existe para *localizar* um cliente a partir de um
  número novo, não para garantir unicidade.

### `lojas` — Lojas

Filiais de um cliente.

| Atributo | Tipo | Obrig. | Default |
|---|---|---|---|
| `cliente_id` | fk → `clientes` | sim | — |
| `nome` | string(255) | sim | — |
| `documento` | string(20) | não | — |
| `endereco` | text | não | — |

**Invariantes**

- Sempre pertence a exatamente um cliente.
- `documento` **não** tem unicidade garantida.

### `chats` — Chats

A entidade central. Um chamado de suporte.

| Atributo | Tipo | Obrig. | Default | Notas |
|---|---|---|---|---|
| `cliente_id` | fk → `clientes` | sim | — | |
| `loja_id` | fk → `lojas` | não | — | Nunca populado. Gap 02-5 |
| `atendente_id` | fk → `atendentes` | não | — | Nulo = não atribuído |
| `status` | enum | sim | `NOVO` | 8 valores. Ver [01-domain-glossary](01-domain-glossary.md) |
| `prioridade` | enum | sim | `media` | `baixa` \| `media` \| `alta` \| `urgente` |
| `resumo_problema` | text | não | — | Escrito pela IA e/or pelo atendente |
| `solucao_sugerida_ia` | text | não | — | **O valor do Cenário B.** Receita pronta |
| `causa_provavel` | text | não | — | |
| `nivel_confianca_ia` | float | não | — | 0.0–1.0 |
| `necessita_humano` | boolean | não | — | Verdadeiro em B e C |
| `setor_alvo` | string(50) | não | — | Destino da transferência de grupo |
| `whatsapp_number` | string(20) | não | — | Canal. Sem sufixo `@s.whatsapp.net` |
| `ultima_mensagem_em` | datetime | não | — | Denormalizado, para ordenar conversas |

**Invariantes**

- `status` só muda por uma transição válida ([01-domain-glossary](01-domain-glossary.md)
  §Tabela de transições).
- `whatsapp_number` é normalizado na entrada: sufixo `@s.whatsapp.net` removido.
- `atendente_id` e `setor_alvo` são **mutuamente exclusivos**: transferir para grupo
  limpa o atendente; transferir para atendente limpa o setor.
- `prioridade = urgente` e `alta` são as duas que o dashboard conta como "crítico".
- Se `necessita_humano` é verdadeiro, `solucao_sugerida_ia` **deve** estar preenchido
  (Cenário B) ou explicitamente ausente (Cenário C). A distinção é o valor entregue ao
  humano.

### `mensagens` — Mensagens

Histórico de conversa. Append-only: **não** há update nem delete.

| Atributo | Tipo | Obrig. | Default | Notas |
|---|---|---|---|---|
| `chat_id` | fk → `chats` | sim | — | |
| `remetente` | enum | sim | — | `cliente` \| `ia` \| `atendente` \| `sistema` |
| `tipo` | enum | sim | `texto` | `texto` \| `audio` \| `documento` \| `imagem` |
| `conteudo` | text | não | — | Transcrição ou corpo do texto |
| `url_arquivo` | string(500) | não | — | Sem upload implementado. Gap 02-6 |

**Invariantes**

- Append-only.
- `remetente = atendente` **dispara envio pelo WhatsApp** quando o chat tem
  `whatsapp_number`. A escrita e o envio são acoplados.
- `remetente = ia` é o registro da resposta da IA.
- `tipo ≠ texto` exige `url_arquivo` **ou** `conteudo` preenchido. Hoje só texto
  percorre o fluxo real.

### `ia_diagnosticos` — IADiagnosticos

O que a IA descobriu. **Um registro por chat.**

| Atributo | Tipo | Obrig. | Default | Notas |
|---|---|---|---|---|
| `chat_id` | fk → `chats` | sim | — | |
| `status_ia` | enum | sim | — | `RESOLVIDO_PELA_IA` \| `TRANSFERIR_COM_SOLUCAO` \| `TRANSFERIR_SEM_SOLUCAO` |
| `resumo` | text | não | — | 1–2 frases |
| `solucao` | text | não | — | Passo a passo |
| `causa_provavel` | text | não | — | |
| `confianca` | float | não | — | 0.0–1.0 |
| `modelo_usado` | string(100) | não | — | Identifica qual LLM respondeu |
| `tokens_usados` | integer | não | — | Nunca preenchido |

**Invariantes**

- `status_ia` **é** a decisão do cenário. Ver [05-ai-pipeline](05-ai-pipeline.md) §Cenários.
- Uma re-análise do mesmo chat **substitui** o registro (upsert por `chat_id`).
- `status_ia = TRANSFERIR_SEM_SOLUCAO` implica `solucao` vazio — é o cenário em que a
  base não respondeu.

> **Crítico:** esta coleção nunca é populada. `IADiagnosticoRepository.get_by_chat`
> não é chamado por nada, e `POST /webhooks/chat/diagnostico` não tem chamador. Todo o
> histórico de decisão da IA está perdido. Ver gap 02-7.

### `knowledge_bases` — KnowledgeBases

Artigos de suporte. A fonte da verdade sobre soluções.

| Atributo | Tipo | Obrig. | Default | Notas |
|---|---|---|---|---|
| `titulo` | string(255) | sim | — | |
| `conteudo` | text | sim | — | Markdown ou texto simples |
| `categoria` | enum | sim | — | `fiscal` \| `estoque` \| `compras` \| `vendas` \| `financeiro` |
| `tipo_arquivo` | string(50) | não | — | `pdf` \| `docx` \| `txt` \| `html` |
| `url_arquivo` | string(500) | não | — | Binário original |
| `ativo` | boolean | não | `true` | Artigo inativo não entra na busca |

**Invariantes**

- **Toda escrita neste repositório deve sincronizar o Qdrant.** Gap 02-8.
- Artigo inativo não é retornado na busca semântica, mas o **vetor deve ser removido**.
- `categoria` é obligatoria — sem ela a IA não consegue filtrar nem reportar por área.

### `tags` — Tags

| Atributo | Tipo | Obrig. | Default |
|---|---|---|---|
| `nome` | string(100) | sim | — |
| `cor` | string(7) | não | — |

### `chat_tags` — ChatTags

Junction N:N entre `chats` e `tags`.

| Atributo | Tipo | Obrig. |
|---|---|---|
| `chat_id` | fk → `chats` | sim |
| `tag_id` | fk → `tags` | sim |

> **Sem uso:** `tags` e `chat_tags` são criadas no bootstrap mas **não têm repositório,
> rota nem serviço**. São coleções órfãs. Gap 02-9.

## Enums

Fonte: `backend/app/models/*.py`, espelhados em `schema.py:31-52`.

| Enum | Valores | Origem |
|---|---|---|
| `StatusChat` | `NOVO` `IA_ANALISANDO` `AGUARDANDO_CLIENTE` `AGUARDANDO_HUMANO_COM_SOLUCAO` `AGUARDANDO_HUMANO_SEM_SOLUCAO` `EM_ATENDIMENTO` `RESOLVIDO` `ENCERRADO` | `models/chat.py` |
| `PrioridadeChat` | `baixa` `media` `alta` `urgente` | `models/chat.py` |
| `PerfilAtendente` | `admin` `supervisor` `atendente` | `models/atendente.py` |
| `RemetenteMensagem` | `cliente` `ia` `atendente` `sistema` | `models/mensagem.py` |
| `TipoMensagem` | `texto` `audio` `documento` `imagem` | `models/mensagem.py` |
| `StatusIA` | `RESOLVIDO_PELA_IA` `TRANSFERIR_COM_SOLUCAO` `TRANSFERIR_SEM_SOLUCAO` | `models/ia_diagnostico.py` |
| `CategoriaConhecimento` | `fiscal` `estoque` `compras` `vendas` `financeiro` | `models/knowledge_base.py` |

**Regra:** o `StrEnum` em `app/models/` é a fonte; `schema.py` deve espelhar exatamente.
Os dois precisam ser validados por teste — hoje `backend/tests/test_appwrite_schema.py`
valida a forma dos atributos, mas **não** a igualdade com os `StrEnum`.

## Unicidade

O Appwrite não tem índice único compound, e a decisão documentada (`schema.py:14-15`) é
garantir unicidade **na aplicação**, com checagem antes do insert.

| Campo | Garantido por | Onde |
|---|---|---|
| `atendentes.email` | `get_by_email` antes de criar | `AuthService.criar_usuario` |
| `clientes.documento` | `get_by_documento` antes de criar | `ClienteService.criar` |

**Limitação conhecida:** a checagem é *check-then-insert*, sem transação. Duas requisições
concorrentes podem criar duplicata. Aceitável no volume atual; relevante se crescer.

## Migrations

O Appwrite é schemaless e o bootstrap é **idempotente e aditivo**:
`backend/app/appwrite/bootstrap.py`.

| Comportamento | Detalhe |
|---|---|
| Collection ausente | Cria |
| Atributo ausente | Cria |
| Atributo existe | **Não toca** |
| Valor de enum novo | **Não propaga** |
| Tamanho de string alterado | **Não propaga** |

O bootstrap roda no lifespan de toda aplicação (`main.py`), dentro de um
`try/except` que **loga e continua** — a aplicação sobe degradada se o schema falhar.

> **Consequência:** alterar `STATUS_CHAT` ou qualquer enum exige um passo manual no
> console do Appwrite. Não há migration. Ver gap 02-10.

**Alembic não é o caminho de migração deste projeto.** `backend/alembic/` e
`backend/app/models/*.py` (ORM) sobraram da era PostgreSQL e só servem a
`scripts/migrate.sh` e `scripts/seed_*.py`. Ver gap 02-11.

## Índice de leitura

| Query | Estratégia | Custo real |
|---|---|---|
| Chat por WhatsApp | `get_by_whatsapp` | Scan completo de `chats` |
| Mensagens de um chat | `list_by_chat` + sort em Python | Scan completo + sort |
| Filtros de chat (status, cliente, prioridade) | Python sobre `list_all` | Scan completo |
| Kanban | `list_all` + grouping | Scan completo |
| Dashboard | `list_all` de chats **e** mensagens | 2 scans completos |

> Todo filtro é O(n) em Python. Ver [08-non-functional](08-non-functional.md)
> §Performance.

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 02-1 | `CATEGORIA_CONHECIMENTO` tem 5 valores, mas `CLASSIFY_SYSTEM` retorna `multiempresa` e `outro`. Artigos dessas áreas não podem ser gravados | `schema.py:52` vs `app/ai/prompts.py` | **Alta** | **ABERTO** |
| 02-2 | `CategoriaConhecimento` não tem `multiempresa`, que é uma área real do negócio listada em `.ai/PROJECT.md:74-78` e `.ai/SUPORTE_AGENT.md:52-55` | `schema.py:52` | Média | **ABERTO** |
| 02-3 | `TipoMensagem` não tem `sticker` nem `local`, que a Evolution API envia. Mensagem com esses tipos é silenciosamente rejeitada | `schema.py:48` | Média | **ABERTO** |
| 02-4 | `atendentes.setor` e `chats.setor_alvo` são string livre, sem enum e sem validação. O frontend inventa os valores | `schema.py:105,144`; `frontend/.../atendimento/page.tsx:143` | Média | **ABERTO** |
| 02-5 | `chats.loja_id` nunca é populado; nenhum endpoint define a loja | `schema.py:138` | Média | **ABERTO** |
| 02-6 | `url_arquivo` existe em `mensagens` e `knowledge_bases`, mas não há upload, download nem storage. Nenhum serviço usa | `schema.py:156,195` | Média | **ABERTO** → adiado |
| 02-7 | `ia_diagnosticos` nunca é populada. `IADiagnosticoRepository.get_by_chat` sem chamador | `app/appwrite/repositories/ia_diagnostico.py` | **Crítica** | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
| 02-8 | CRUD da base de conhecimento **não sincroniza o Qdrant**. Criar artigo não gera embedding; remover artigo não apaga vetor. RAG e banco divergem sem caminho de reconciliação | `KnowledgeBaseService` inteiro | **Alta** | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) §RAG |
| 02-9 | `tags` e `chat_tags` são órfãs: criadas no bootstrap, sem repositório, rota ou serviço | `schema.py:159-171` | Baixa | **ABERTO** |
| 02-10 | Bootstrap é aditivo e **não propaga mudança de enum**. Não há migration de dados no Appwrite | `appwrite/bootstrap.py` | **Alta** | **ABERTO** |
| 02-11 | `backend/alembic/` (4 revisions), `app/models/*.py` (ORM) e `scripts/migrate.sh` apontam para PostgreSQL, que não é mais a fonte de dados | `alembic/`, `scripts/migrate.sh` | **Alta** | **ABERTO** |
| 02-12 | Sem índice único: unicidade de `email` e `documento` é check-then-insert, vulnerável a corrida | `schema.py:14-15` | Média | **ABERTO** |
| 02-13 | `scripts/seed_knowledge_base.py` importa `async_session` de `app.core.database`, que **não existe**. O script não roda | `scripts/seed_knowledge_base.py:10` | **Alta** | **ABERTO** |
| 02-14 | `scripts/seed_qdrant.py` lê do PostgreSQL via SQLAlchemy e usa `artigo.id` inteiro como ID de ponto Qdrant, que exige UUID/uint. Não roda | `scripts/seed_qdrant.py` | **Alta** | **ABERTO** |
| 02-15 | `repos.chats.get` é chamado dentro do loop de `dashboard_service.py:73-81` — um scan completo de clientes por chat exibido | `dashboard_service.py:74` | Média | **ABERTO** → [08-non-functional](08-non-functional.md) |
| 02-16 | Sem foreign key constraint: `chats.cliente_id` pode apontar para cliente inexistente. Integridade é responsabilidade do serviço | `schema.py:7-9` | Média | **ABERTO** |
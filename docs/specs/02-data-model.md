# SPEC 02 — Modelo de Dados (Appwrite)

## Fonte de dados e convenções

Appwrite self-hosted é a fonte primária do sistema. A database atual é `chatbot`. O schema é declarado em `backend/app/appwrite/schema.py` e criado pelo bootstrap idempotente em `backend/app/appwrite/bootstrap.py` durante o lifespan da aplicação.

Convenções:

| Regra | Convenção |
|---|---|
| ID | Appwrite gera o ID do documento; não declarar ID como atributo comum |
| Timestamps | Usar `createdAt` e `updatedAt` nativos quando disponíveis |
| FK | String com ID do documento relacionado; integridade validada pela aplicação |
| Texto longo | String com tamanho compatível com o limite configurado (`TEXT_SIZE`, atualmente documentado como 32767) |
| Enum | `StrEnum` de `backend/app/models/` é fonte; schema Appwrite deve espelhar exatamente |
| Data/hora | UTC |
| Unicidade | Garantida pela aplicação; não presumir constraint unique composta do Appwrite |
| Segredos | Nunca armazenar token/API key em coleções de domínio |

O projeto possui nove coleções preexistentes: `atendentes`, `clientes`, `lojas`, `chats`, `mensagens`, `ia_diagnosticos`, `knowledge_bases`, `tags` e `chat_tags`. As novas coleções desta versão são descritas abaixo.

## Coleções existentes

### `atendentes`

| Atributo | Tipo | Obrig. | Observação |
|---|---|---:|---|
| `nome` | string(255) | sim | Nome exibido |
| `email` | string(255) | sim | Login; único entre contas ativas pela aplicação |
| `hash_senha` | string(255) | sim | bcrypt; nunca retornar pela API |
| `perfil` | enum | sim | `admin`, `supervisor`, `atendente` |
| `setor` | string(50) | não | **Legado**; substituir progressivamente por `departamento_id` |
| `departamento_id` | string(36) | não | FK lógica para `departamentos`; novo campo canônico |
| `emsoft_usuario_id` | string(100) | não | Identificador do usuário correspondente na API Emsoft, após confirmação do contrato |
| `ativo` | boolean | não | Default `true`; inativo não autentica nem recebe atribuição |

Invariantes: email único entre ativos; perfil só muda por admin; desativar é soft delete; `hash_senha` nunca sai do repositório.

### `clientes`

| Atributo | Tipo | Obrig. | Observação |
|---|---|---:|---|
| `nome` | string(255) | sim | Razão social |
| `documento` | string(20) | sim | CNPJ; único pela aplicação |
| `email` | string(255) | não | |
| `telefone` | string(20) | não | Telefone de referência, não chave única |
| `endereco` | string longa | não | |
| `versao_erp` | string(50) | não | Versão do ERP |
| `emsoft_cliente_id` | string(100) | não | ID do cliente externo, após contrato e estratégia de matching confirmados |

Não criar cliente externo automaticamente sem regra explícita de matching; CNPJ é a identidade natural interna.

### `lojas`

| Atributo | Tipo | Obrig. |
|---|---|---:|
| `cliente_id` | string(36) | sim |
| `nome` | string(255) | sim |
| `documento` | string(20) | não |
| `endereco` | string longa | não |

Toda loja pertence a exatamente um cliente.

### `chats`

| Atributo | Tipo | Obrig. | Observação |
|---|---|---:|---|
| `cliente_id` | string(36) | sim | FK lógica para cliente |
| `loja_id` | string(36) | não | FK lógica; preencher quando conhecida |
| `atendente_id` | string(36) | não | Pessoa responsável; nulo enquanto não atribuída |
| `departamento_id` | string(36) | não | Equipe responsável; novo campo canônico |
| `status` | enum | sim | Oito estados de `01-domain-glossary.md` |
| `prioridade` | enum | sim | `baixa`, `media`, `alta`, `urgente` |
| `resumo_problema` | string longa | não | Resumo consolidado |
| `solucao_sugerida_ia` | string longa | não | Passo a passo, quando sustentado |
| `causa_provavel` | string longa | não | Causa provável, não certeza |
| `nivel_confianca_ia` | float | não | 0.0 a 1.0 |
| `necessita_humano` | boolean | não | Verdadeiro em cenários B/C |
| `setor_alvo` | string(50) | não | **Legado**; não usar em novas escritas após migração |
| `whatsapp_number` | string(20) | não | Número normalizado, sem `@s.whatsapp.net` |
| `ultima_mensagem_em` | datetime | não | Campo denormalizado para ordenação |
| `external_sync_status` | enum/string | não | Estado resumido de integração, opcional; detalhe permanece em `integracao_chamados` |

**Nova regra:** `departamento_id` e `atendente_id` não são mutuamente exclusivos. O departamento persiste como equipe responsável; o atendente é a pessoa atribuída. Os campos antigos `setor`/`setor_alvo` ficam temporariamente para compatibilidade e devem ser removidos somente em release de migração planejada.

### `mensagens`

Histórico append-only. Campos conhecidos: `chat_id`, `remetente` (`cliente`, `ia`, `atendente`, `sistema`), `tipo` (`texto`, `audio`, `documento`, `imagem`), `conteudo`, `url_arquivo`. Mensagem de atendente no fluxo existente pode acionar envio ao WhatsApp; integração externa jamais deve ser disparada por um insert genérico de mensagem.

Adicionar, se ausente, `external_message_id` (string(150)) para deduplicar mensagens Evolution; sua unicidade deve ser aplicada por combinação de origem/instância e ID, com checagem em repositório.

### `ia_diagnosticos`

Snapshot mais recente, um por chat (upsert por `chat_id`). Preservar campos atuais: `chat_id`, `status_ia`, `resumo`, `solucao`, `causa_provavel`, `confianca`, `modelo_usado`, `tokens_usados`.

Adicionar campos:

| Atributo | Tipo | Observação |
|---|---|---|
| `intencao` | string(80) | Código canônico da intenção |
| `subintencao` | string(100) | Detalhe opcional |
| `categoria_erp` | string(50) | Ex.: fiscal, estoque; não é departamento |
| `confianca_classificacao` | float | 0.0–1.0 |
| `departamento_sugerido_id` | string(36) | Saída sugerida pelo classificador/regra |
| `departamento_destino_id` | string(36) | Destino validado pelo backend |
| `motivo_roteamento` | string(500) | Explicação auditável da decisão |
| `artigos_consultados` | string longa | IDs e scores dos artigos usados, sem duplicar o texto completo |
| `data_analise` | datetime | UTC |

### `knowledge_bases`, `tags` e `chat_tags`

Manter os campos existentes. `knowledge_bases.categoria` representa categoria de assunto/módulo ERP. Toda criação/edição/ativação/desativação de artigo deve sincronizar o vetor no Qdrant; conteúdo inativo não pode ser recuperado.

## Novas coleções

### `departamentos`

| Atributo | Tipo | Obrig. | Observação |
|---|---|---:|---|
| `codigo` | string(80) | sim | Slug estável, ex. `suporte_tecnico`; único pela aplicação |
| `nome` | string(255) | sim | Nome exibido |
| `descricao` | string(1000) | não | Escopo do departamento |
| `ativo` | boolean | sim | Default `true` |
| `ordem` | integer | não | Ordem de apresentação |
| `recebe_transferencias` | boolean | sim | Default `true` |
| `permite_atribuicao_automatica` | boolean | sim | Default `false` até regras de disponibilidade existirem |

Não persistir nomes de departamento nas relações; usar ID. `codigo` não deve ser alterado depois de usado em regras sem migração.

### `regras_roteamento`

Uma regra relaciona uma intenção a um departamento.

| Atributo | Tipo | Obrig. | Observação |
|---|---|---:|---|
| `intencao` | string(80) | sim | Código da intenção |
| `subintencao` | string(100) | não | Filtro mais específico |
| `categoria_erp` | string(50) | não | Filtro opcional por módulo ERP |
| `departamento_id` | string(36) | sim | Destino |
| `prioridade_regra` | integer | sim | Menor número = maior prioridade (documentar no service) |
| `ativo` | boolean | sim | Default `true` |

Se duas regras com a mesma prioridade coincidirem e apontarem para destinos diferentes, o backend não escolhe arbitrariamente: registra conflito e encaminha para triagem geral/solicita esclarecimento.

### `integracao_chamados`

Um registro por chat e sistema externo integrado.

| Atributo | Tipo | Obrig. | Observação |
|---|---|---:|---|
| `chat_id` | string(36) | sim | FK lógica; único por sistema externo |
| `sistema_externo` | string(50) | sim | `EMSOFT_CHAMADOS` |
| `chamado_id_externo` | string(100) | não | ID devolvido pela API externa |
| `responsavel_tipo` | enum/string | sim | `IA` ou `HUMANO` |
| `atendente_id` | string(36) | não | Atendente local quando responsável humano |
| `responsavel_externo_id` | string(100) | não | ID do usuário externo confirmado pelo contrato |
| `departamento_id` | string(36) | não | Departamento responsável |
| `status_integracao` | enum | sim | `PENDENTE`, `SINCRONIZADO`, `ERRO`, `DESATIVADO` |
| `status_externo` | string(80) | não | Valor externo mapeado, preservar literal recebido |
| `idempotency_key` | string(150) | sim | Chave estável por operação de criação |
| `ultima_sincronizacao_em` | datetime | não | UTC |
| `tentativas` | integer | sim | Default 0 |
| `ultimo_erro` | string(2000) | não | Mensagem sanitizada; nunca credencial |
| `url_externa` | string(500) | não | Link externo, se devolvido pela API |

### `integration_outbox`

Fila persistente de eventos externos.

| Atributo | Tipo | Obrig. | Observação |
|---|---|---:|---|
| `event_key` | string(180) | sim | Única pela aplicação; chave idempotente |
| `aggregate_type` | string(50) | sim | `chat` |
| `aggregate_id` | string(36) | sim | chat_id |
| `event_type` | string(100) | sim | Ex.: `TICKET_CREATE_REQUESTED`, `TICKET_UPDATE_REQUESTED` |
| `payload` | string longa | sim | JSON serializado versionado; sem segredo |
| `status` | enum | sim | `PENDENTE`, `PROCESSANDO`, `CONCLUIDO`, `AGUARDANDO_RETRY`, `FALHA_PERMANENTE` |
| `attempt_count` | integer | sim | Default 0 |
| `next_attempt_at` | datetime | não | UTC |
| `last_error` | string(2000) | não | Sanitizado |
| `processed_at` | datetime | não | UTC |

O worker deve possuir lease/lock lógico para não processar o mesmo evento simultaneamente. Se Appwrite não permitir atomicidade/lock adequado, usar lock distribuído Redis com TTL e revalidar estado no repositório.

## Enums canônicos

- `StatusChat`: oito estados listados no glossário.
- `PrioridadeChat`: `baixa`, `media`, `alta`, `urgente`.
- `PerfilAtendente`: `admin`, `supervisor`, `atendente`.
- `RemetenteMensagem`: `cliente`, `ia`, `atendente`, `sistema`.
- `TipoMensagem`: `texto`, `audio`, `documento`, `imagem`.
- `StatusIA`: `RESOLVIDO_PELA_IA`, `TRANSFERIR_COM_SOLUCAO`, `TRANSFERIR_SEM_SOLUCAO`.
- `StatusIntegracao`: `PENDENTE`, `SINCRONIZADO`, `ERRO`, `DESATIVADO`.
- `StatusOutbox`: `PENDENTE`, `PROCESSANDO`, `CONCLUIDO`, `AGUARDANDO_RETRY`, `FALHA_PERMANENTE`.

`StrEnum` é a fonte canônica; schema Appwrite deve espelhar os valores exatamente. Para enums alterados, o bootstrap aditivo não é suficiente: atualizar schema manualmente no Appwrite e executar testes de contrato antes do deploy.

## Migração de setor legado

1. Criar `departamentos` e popular códigos para os setores atualmente usados no frontend/backend.
2. Para cada atendente com `setor`, resolver código/ID correspondente e preencher `departamento_id`.
3. Para cada chat com `setor_alvo`, resolver e preencher `departamento_id`.
4. Não apagar `setor`/`setor_alvo` nesta fase.
5. Atualizar serviços e UI para ler/escrever somente IDs canônicos.
6. Rodar auditoria de documentos sem correspondência e corrigir manualmente.
7. Remover campos legados apenas em migração posterior com backup e release específico.

## Unicidade, concorrência e bootstrap

Appwrite não fornece as constraints compostas assumidas pelo domínio. Fazer checagem no repositório e testes concorrentes para `departamentos.codigo`, `regras_roteamento` (chave lógica), `integracao_chamados(chat_id,sistema_externo)` e `integration_outbox.event_key`.

O bootstrap deve ser aditivo e idempotente. Não iniciar aplicação em produção como se schema estivesse atualizado quando criação de atributo/coleção falhar: logar erro estruturado e expor health check degradado. Não usar Alembic para migrar Appwrite; a camada ORM legada não é fonte do schema atual.

## Registro de Gaps

Verificado contra o código em 2026-11-06.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 02-1 | `CLASSIFY_SYSTEM` reconhece 7 categorias (`multiempresa`, `outro`); `CATEGORIA_CONHECIMENTO` tem 5 — artigos dessas áreas não podem ser gravados | `ai/prompts.py:5-21` vs `appwrite/schema.py:52` | **Alta** | **CORRIGIDO** — `CATEGORIA_CONHECIMENTO` deriva de `CategoriaConhecimento` (6 categorias, inclui `multiempresa`); `outro` não é categoria válida (`appwrite/schema.py`, `models/departamento.py`) |
| 02-2 | `CategoriaConhecimento` sem `multiempresa`, que é área real do negócio | `appwrite/schema.py:52` | Média | **CORRIGIDO** — `CategoriaConhecimento.multiempresa` (`models/knowledge_base.py`) |
| 02-3 | `TipoMensagem` sem `sticker`/`local`; o normalizador do webhook mapeia sticker→imagem, mas o enum não espelha a Evolution | `appwrite/schema.py:48`; `api/routes/webhooks.py:102-111` | Média | **ABERTO** |
| 02-4 | `atendentes.setor` e `chats.setor_alvo` são string livre, sem enum/validação (legado a migrar para departamento) | `appwrite/schema.py:107,144` | Média | **CORRIGIDO (departamento_id)** — leitura/escrita canônica por ID em `ChatService`; legado preservado |
| 02-5 | `chats.loja_id` nunca é populado | `appwrite/schema.py:135` | Média | **ABERTO** |
| 02-6 | `url_arquivo` existe em `mensagens`/`knowledge_bases`, sem upload/download/storage | `appwrite/schema.py:156,194` | Média | **ABERTO** |
| 02-7 | `ia_diagnosticos` nunca era populado; `get_by_chat` sem chamador | `appwrite/repositories/ia_diagnostico.py` | **Crítica** | **CORRIGIDO** — `AIPipelineService._finalizar` grava o diagnóstico (o `get_by_chat` ainda não tem chamador → 05-18) |
| 02-8 | CRUD da base de conhecimento não sincronizava o Qdrant | `services/knowledge_base_service.py` | **Alta** | **CORRIGIDO** — criar/atualizar embute+upsert; desativar/remover apaga o ponto |
| 02-9 | `tags` e `chat_tags` órfãs (sem repositório/rota/serviço) | `appwrite/schema.py:160-173` | Baixa | **ABERTO** |
| 02-10 | Bootstrap aditivo **não propaga mudança de enum**; health degradado não implementado | `appwrite/bootstrap.py` | **Alta** | **CORRIGIDO** (2026-11-10) — bootstrap detecta drift de enum (elementos faltantes/excedentes), agrega em `SchemaDriftError` e `/health` responde 503 `degradado` com a lista de drifts |
| 02-11 | `backend/alembic/`, `app/models/*.py` (ORM) e `scripts/migrate.sh` apontam para PostgreSQL, que não é a fonte atual | `backend/alembic/`; `scripts/migrate.sh` | **Alta** | **ABERTO** |
| 02-12 | Sem índice único: unicidade de `email`/`documento` é check-then-insert, vulnerável a corrida | `appwrite/schema.py:14-15` | Média | **CORRIGIDO (departamentos)** — `DepartamentoService.criar` centraliza o check-then-insert de `codigo` com 409; demais entidades seguem pendentes |
| 02-13 | `scripts/seed_knowledge_base.py` importava `async_session` inexistente | `scripts/seed_knowledge_base.py` | **Alta** | **CORRIGIDO** — o script cria o próprio engine; há `seed_knowledge_base_appwrite.py` |
| 02-14 | `scripts/seed_qdrant.py` lê do PostgreSQL e usa id inteiro como ponto Qdrant | `scripts/seed_qdrant.py` | **Alta** | **CORRIGIDO** — seed lê artigos ativos via `Repositories(databases).knowledge_bases.list_all()` (Appwrite) e usa o `id` ULID do doc como `article_id` (ponto Qdrant); `seed_knowledge_base.py` legado (SQLAlchemy) removido |
| 02-15 | `dashboard_service.py` chama `clientes.get` dentro do loop de recentes | `services/dashboard_service.py:73-74` | Média | **CORRIGIDO** — `clientes.list_all()` fora do loop em `DashboardService` |
| 02-16 | Sem foreign key: `chats.cliente_id` pode apontar para cliente inexistente | `appwrite/schema.py` | Média | **ABERTO** |
| 02-17 | Coleções `departamentos`, `regras_roteamento`, `integracao_chamados` e `integration_outbox` inexistentes | `appwrite/schema.py` | **Alta** | **CORRIGIDO** — coleções criadas em `app/appwrite/schema.py` |
| 02-18 | `departamento_id` ausente em `atendentes`/`chats` | `appwrite/schema.py` | **Alta** | **CORRIGIDO** — `departamento_id` em `atendentes`/`chats` |
| 02-19 | `ia_diagnosticos` não guarda intenção, categoria ERP, departamento destino, artigos consultados nem razão | `appwrite/schema.py:174-186` | **Alta** | **CORRIGIDO** — `ia_diagnosticos` guarda `intencao`, `subintencao`, `categoria_erp`, `departamento_sugerido_codigo`, `departamento_id`, `motivo` e `artigos_consultados` (`appwrite/schema.py`); F3.4: `AIPipelineService._finalizar` grava o snapshot em todos os resultados |
| 02-20 | Sem trilha de auditoria de atribuição/transferência (exigida em 04) | `app/` | Média | **CORRIGIDO** (2026-11-13) — coleção `auditoria` grava atribuição/transferência (ator `Ator`, `motivo`, `atendente_anterior_id`/`atendente_novo_id`, `departamento_*`); exposta via `GET /chats/{id}/auditoria` |

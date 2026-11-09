# SPEC 00 — Escopo do Produto

## Objetivo

Reduzir em **pelo menos 70%** a carga operacional do suporte técnico do ERP EMSoft, automatizando o primeiro contato via WhatsApp com uma IA apoiada por uma base de conhecimento e encaminhando cada solicitação à equipe apropriada quando necessário.

A métrica de 70% representa a proporção de atendimentos elegíveis concluídos sem intervenção humana, com resolução confirmada pelo cliente. Ver `08-non-functional.md`.

## Produto em uma frase

Painel web interno para atendimento WhatsApp de clientes do ERP EMSoft, com IA que entende a intenção, consulta conhecimento técnico, propõe correções e encaminha conversas para departamentos e atendentes, registrando também os chamados no sistema interno Emsoft.

## Personas

| Persona | Entrada | Necessidade |
|---|---|---|
| Cliente final | WhatsApp | Resolver dúvidas/problemas ou falar com o departamento correto |
| Atendente | `/atendimento`, `/kanban` | Ver e assumir chats do seu departamento, responder e executar orientações |
| Supervisor | Painel + `/usuarios`, `/clientes`, departamentos | Atribuir chats, supervisionar filas e organizar equipes |
| Admin | Todas as telas + configurações | Gerenciar usuários, departamentos, regras e integrações |
| IA Support | Serviço de backend | Classificar, consultar conhecimento, orientar e registrar sua própria atuação |

## Escopo funcional

- Atendimento exclusivamente pelo WhatsApp nesta fase, via Evolution API.
- Persistência de clientes, chats e mensagens no Appwrite.
- IA para classificar intenção, categoria/subcategoria do ERP, resumir, diagnosticar e propor orientação com RAG.
- Base de conhecimento com armazenamento Appwrite e busca vetorial Qdrant.
- Máquina de estados de oito estados descrita em `01-domain-glossary.md`.
- Departamentos gerenciáveis, atendentes associados a departamentos e regras de roteamento.
- Transferência direta para departamento, fila geral ou atendente.
- Painel web para atendimento, Kanban, dashboard, clientes, usuários, conhecimento, departamentos e integração.
- Integração backend-to-backend com a API interna de chamados Emsoft para criar e atualizar chamados relacionados aos chats.
- Registro de chamados externos atribuídos ao usuário técnico da IA quando ela apresentar uma solução e atribuídos ao atendente humano após transferência/assunção conforme o contrato externo.
- Auditoria operacional, reprocessamento seguro e monitoramento de falhas de sincronização.

## Cenários principais de atendimento

### Cenário A — IA apresenta uma solução que o cliente pode executar

1. O backend classifica o assunto e identifica a categoria ERP.
2. Para problema técnico, consulta a base de conhecimento.
3. A IA só orienta se houver evidência suficiente e conteúdo compatível na base.
4. O chat passa para `AGUARDANDO_CLIENTE`.
5. A integração cria um chamado externo atribuído ao usuário técnico da IA, com status externo equivalente a aguardando confirmação, se esse status existir no contrato Emsoft.
6. Se o cliente confirmar, o backend transiciona o chat para `RESOLVIDO` e atualiza o chamado externo.
7. Se o cliente disser que não resolveu, o mesmo chamado externo é atualizado com a tentativa e encaminhado a humano; não criar um segundo ticket.

### Cenário B — IA encontra orientação, mas exige ação humana

1. A IA identifica uma solução ou procedimento interno que não deve ser executado automaticamente.
2. Persiste o diagnóstico, a solução proposta e as evidências.
3. O chat passa para `AGUARDANDO_HUMANO_COM_SOLUCAO`.
4. O backend determina o departamento e aguarda/realiza a atribuição humana conforme regra da equipe.
5. Quando houver atendente designado, cria ou atualiza o chamado externo atribuindo-o a essa pessoa.
6. O atendente recebe o resumo, tentativas e solução sugerida.

### Cenário C — IA não encontra solução confiável

1. O backend consulta o RAG.
2. Se os resultados forem insuficientes, a IA não inventa solução.
3. A IA pode pedir detalhes indispensáveis (mensagem de erro, módulo, versão, operação realizada).
4. O backend gera resumo técnico do que foi verificado e encaminha para o departamento técnico adequado.
5. Ao atribuir um atendente, cria/atualiza o chamado externo no nome dessa pessoa.

### Cenário D — Solicitação de outro departamento

1. O classificador identifica a intenção (por exemplo, financeiro, comercial ou administrativo).
2. O backend resolve a intenção para um departamento ativo por regra determinística.
3. Se a intenção e o destino forem claros, encaminha sem executar o pipeline RAG técnico.
4. Se o destino não for claro, faz uma pergunta de esclarecimento; não escolhe aleatoriamente.
5. A fila do departamento recebe a conversa. A chamada externa deve refletir a pessoa quando atribuída individualmente, ou a fila se a API externa suportar esse conceito.

### Cenário E — Pedido explícito por humano

A IA reconhece frases como “quero falar com uma pessoa/atendente”. Deve interromper a tentativa de resolução automática, preservar o contexto e encaminhar para o departamento atual ou perguntar qual departamento quando não houver contexto suficiente.

## Fora do escopo

| Item | Motivo |
|---|---|
| SaaS multi-tenant comercial, assinatura e billing | Plataforma interna da EMSoft |
| Portal de chamados para o cliente final | O cliente permanece no WhatsApp |
| Execução automática de SQL, alteração de dados ou configuração de ERP | IA orienta; ação interna permanece humana e auditada |
| Promessa de prazo/SLA pela IA | Somente equipe autorizada pode informar prazos |
| Canais além do WhatsApp | Fora desta etapa |
| Agentes autônomos múltiplos e comunicação entre agentes | Complexidade desnecessária para o fluxo atual |
| Sincronização bidirecional irrestrita de todo o sistema externo | Integração limitada a chamados vinculados ao chat |

## Regras inegociáveis

1. A IA nunca inventa solução. Sem evidência suficiente na base, classifica como sem solução e transfere.
2. A IA nunca promete prazo, disponibilidade ou resultado garantido.
3. A IA não expõe senha, credencial, dado bancário ou informação de outro cliente.
4. A IA não executa alteração em banco, permissões ou ambiente do cliente.
5. Toda mensagem recebida é persistida antes de qualquer resposta/ação da IA.
6. O backend é autoridade para estado, departamento, responsável e integração externa.
7. A categoria ERP não é departamento; não misturar os dois conceitos.
8. O n8n transporta mensagens e não decide negócio nem chama diretamente a API Emsoft.
9. Uma conversa produz no máximo um chamado externo vinculado; a transferência atualiza o mesmo chamado quando possível.
10. Falha na integração externa não pode apagar nem bloquear a conversa: registra pendência e reprocessa de forma segura.
11. Não habilitar criação/atualização real no endpoint Emsoft até autenticação, payload e status serem confirmados com documentação ou exemplos reais.

## Indicadores de sucesso

- Percentual de chats resolvidos pela IA com confirmação do cliente.
- Percentual de chats transferidos por departamento.
- Taxa de reclassificação/transferência corrigida por humano.
- Tempo entre mensagem e primeira resposta.
- Taxa de sincronização de chamados externos.
- Quantidade de chamados externos duplicados (meta: zero).
- Quantidade de falhas pendentes e idade da fila de integração.

## Registro de Gaps

Verificado contra o código em 2026-11-06. Ver [13-plano-implementacao.md](13-plano-implementacao.md).

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 00-1 | Cenário A/B/C existiam só como prosa; nenhum nó decidia o cenário | histórico (`README.md`) | Média | **CORRIGIDO (doc)** → [05](05-ai-pipeline.md) |
| 00-2 | RAG inalcançável: `/ai/solucionar` não era chamado pelo fluxo | `ai/router.py`; `workflow-support-ai.json` | **Crítica** | **CORRIGIDO** — n8n chama `POST /webhooks/ai/solucionar`; RAG real provado em runtime |
| 00-3 | Workflow n8n de 8 nós sem RAG/roteamento | `infra/n8n/workflow-support-ai.json` | **Alta** | **CORRIGIDO** — workflow delega classificação/solução ao backend |
| 00-4 | Docs citavam Supabase Storage como armazenamento | docs históricos | Baixa | **CORRIGIDO (doc)** |
| 00-5 | Docs citavam stack NestJS/TypeScript/Prisma | `.ai/PROJECT.md` | Baixa | **ABERTO** → 01-1 (docs legados ainda no repo) |
| 00-6 | Docs citavam workflow de 19 nós | `.ai/TODO_LIST.md` | Baixa | **ABERTO** → 01-1 |
| 00-7 | Backup cobre só Postgres/Supabase; MinIO órfão e backup do Qdrant nunca dispara em prod | `scripts/backup.sh`; `infra/docker-compose.prod.yml` | **Alta** | **ABERTO** → [09](09-infra-deploy.md) |
| 00-8 | Status do chat nunca saía de `NOVO` no fluxo real | `services/ai_pipeline.py` | **Crítica** | **CORRIGIDO (verificado)** — `_finalizar` transiciona via `ChatService.atualizar_status`; teste `test_cenario_b_grava_snapshot_e_aplica_departamento` |
| 00-9 | `ia_diagnosticos` nunca era populado | `services/ai_pipeline.py` | **Crítica** | **CORRIGIDO** — `_finalizar` grava o diagnóstico |
| 00-10 | `tempo_medio_resposta` mede intervalo entre mensagens do mesmo atendente, não o tempo de primeira resposta | `services/dashboard_service.py:44-59` | **Alta** | **ABERTO** → [08](08-non-functional.md) |
| 00-11 | Sem CSAT/NPS nem coleta de feedback | — | Média | **ABERTO** (fora de escopo desta fase) |
| 00-12 | Mídia no WhatsApp: backend e workflow extraem `extendedText`/caption, mas a mídia não é armazenada e formatos não-texto caem em vazio | `api/routes/webhooks.py`; `workflow-support-ai.json` | **Alta** | **ABERTO** → 02-6, 06-17 |
| 00-13 | Departamentos, roteamento e pedido explícito por humano/setor não existem | `app/` | **Alta** | **ABERTO** → [10](10-departamentos-e-roteamento.md) |
| 00-14 | Integração com a API interna de chamados Emsoft não existe | `app/` | **Alta** | **ABERTO (parcial)** — scaffold existe (config `EMSOFT_CHAMADOS_*`, schema `integracao_chamados`, rotas `/integracoes/chamados/*` e client; desabilitado por padrão, `base_url` só via contrato); uso em produção bloqueado pelo artefato → [11](11-integracao-api-emsoft.md) 11-1 |
| 00-15 | Sem outbox/idempotência para chamados externos | `app/` | **Alta** | **ABERTO** → [12](12-confiabilidade-integracoes.md) |
| 00-16 | Indicadores de sucesso por departamento/duplicidade sem instrumentação | `services/dashboard_service.py` | Média | **ABERTO** → 08-9 |

### Confirmado conforme o escopo

| Item | Verificação |
|---|---|
| Autenticação JWT + 3 perfis | `backend/app/core/security.py`, `backend/app/api/deps.py` — conforme |
| 8 estados de chat | `backend/app/models/chat.py` — conforme |
| Kanban de 7 colunas | `backend/app/services/kanban_service.py` — conforme |
| Webhooks com segredo e fail-closed | `app/api/routes/webhooks.py` — conforme |
| Base de conhecimento indexada no Qdrant | `app/services/knowledge_base_service.py` — conforme |

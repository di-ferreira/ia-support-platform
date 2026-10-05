# SPEC 00 — Escopo do Produto

## Objetivo

Reduzir em **pelo menos 70%** a carga operacional do suporte técnico do ERP EMSoft
(setor de autopeças), automatizando o primeiro contato via WhatsApp com IA apoiada por
base de conhecimento.

O número 70% é a métrica de sucesso do produto. Ele é medido como: **proporção de
chamados que não chegam a um atendente humano**, ver [08-non-functional](08-non-functional.md)
§Métricas de produto.

## O produto em uma frase

Painel web onde uma equipe de suporte atende chamados de WhatsApp de clientes do ERP
EMSoft, com IA classificando, pesquisando na base de conhecimento e transbordando
chamados que exigem intervenção humana.

## Quem usa

| Persona | Entra por | Precisa de |
|---|---|---|
| **Atendente** | `/atendimento`, `/kanban` | Ver os chats que pode atender, responder pelo WhatsApp, mover no Kanban |
| **Supervisor** | + `/usuarios`, `/clientes` | Mesma coisa, mais atribuir chats, definir prioridade, gerenciar usuários e clientes |
| **Admin** | tudo, + `/configuracoes` | Configurar a conexão WhatsApp, gerenciar a base de conhecimento |
| **Cliente final** | WhatsApp | Nunca vê o sistema. Fala com a IA primeiro, com um humano se necessário. |

## Os três cenários — o coração do produto

Toda a arquitetura existe para sustentar esta regra. Definida em
`.ai/AGENT.md:11-16` e `.ai/SUPORTE_AGENT.md:59-77`.

### Cenário A — Resolução direta

A IA encontrou a solução **e** o cliente consegue executar sozinho sozinho.

→ A IA orienta passo a passo.
→ O chamado vai para `AGUARDANDO_CLIENTE`.
→ Se o cliente confirmar, vai para `RESOLVIDO`.

### Cenário B — Transbordo com solução

A IA encontrou a solução, **mas** ela exige intervenção humana (ajuste em banco,
liberação de tela, configuração interna).

→ A IA preenche `solucao_sugerida_ia` com o passo a passo exato.
→ O chamado vai para `AGUARDANDO_HUMANO_COM_SOLUCAO`.
→ O atendente executa a receita.

### Cenário C — Transbordo sem solução

A IA **não** encontrou resposta na base de conhecimento.

→ A IA coleta mais detalhes com o cliente.
→ A IA gera um relatório técnico do que sabe.
→ O chamado vai para `AGUARDANDO_HUMANO_SEM_SOLUCAO`.

A distinção entre B e C é o valor que o humano recebe: em B ele já sabe o que fazer,
em C ele precisa investigar. **Nunca inventar solução** — se a base não respondeu, é
Cenário C (`.ai/SUPORTE_AGENT.md:145`).

A regra determinística que implementa isso está em [05-ai-pipeline](05-ai-pipeline.md)
§Cenários.

## Fronteira do produto

### Dentro do escopo

- Autenticação com JWT e três perfis (admin, supervisor, atendente)
- Chats com máquina de estados de 8 estados
- Kanban operacional de 7 colunas
- Atendimento via WhatsApp usando Evolution API
- IA: classificar, resumir, diagnosticar, gerar solução com RAG
- Base de conhecimento (artigos) com busca semântica via Qdrant
- Painel operacional com métricas
- Gerência de usuários, clientes e lojas

### Fora do escopo

Estas coisas **não** são responsabilidade deste sistema. Se surgirem Requirements, é um
produto novo.

| Fora | Por quê |
|---|---|
| Sistema de bilhetaria ou SLA contratual com o cliente final | O cliente fala com o suporte da EMSoft, não com este sistema |
| Execução de correção no ERP do cliente | A IA **orienta**; a execução é humana e monitorada (`.ai/SUPORTE_AGENT.md:143`) |
| Qualquer canal além de WhatsApp | O produto é "100% WhatsApp" (`.ai/AGENT.md:1`) |
| Estoque, vendas, fiscal do ERP do cliente | São **assunto** dos chamados, não funcionalidade do sistema |
| Cobrança, assinatura, multi-tenant comercial | É plataforma interna da EMSoft, não SaaS multi-cliente |

### Adiado explicitamente

Cortado de propósito, com decisão registrada. Não são bugs — são **fora do escopo até
novo pedido**.

| Item | Decisão | Onde documentado |
|---|---|---|
| `/relatorios` | Removida: era placeholder estático sem fonte de dados | [07-frontend](07-frontend.md) §Rotas |
| `/ia-dashboard` | Removida: KPIs parcialmente migrados para `/dashboard` | [07-frontend](07-frontend.md) §Rotas |
| Upload de mídia | Campo `url_arquivo` existe no schema, sem UI e sem upload | [02-data-model](02-data-model.md) |
| Dark mode | Tokens sem variante escura | [07-frontend](07-frontend.md) §Tokens |
| PWA / push notification | — |
| Editar/deletar mensagens | — |
| Componentes Radix UI | Instalados, não usados. Componentes atuais são hand-rolled | [07-frontend](07-frontend.md) §Componentes |

## Regras de negócio que não são negociáveis

1. **A IA nunca inventa solução.** Sem resultado na base, é Cenário C.
2. **A IA nunca promete prazo.** (`.ai/SUPORTE_AGENT.md:144`)
3. **A IA não expõe dado sensível do cliente** (senha, dado bancário). (`.ai/SUPORTE_AGENT.md:142`)
4. **A IA não executa alteração em banco sem supervisão humana.** (`.ai/SUPORTE_AGENT.md:143`)
5. **Toda mensagem do cliente é persistida antes de a IA responder.** Se a IA falhar,
   o histórico não pode estar perdido.
6. **O atendente sempre pode assumir o controle** de qualquer chat. A IA nunca é um
   beco sem saída.
7. **A resposta vai ao cliente por WhatsApp, não só para o painel.** É o mesmo canal.

## Métrica de sucesso

| Métrica | Como medir | Alvo |
|---|---|---|
| Redução de carga do suporte humano | Chamados que não foram para atendente ÷ total | **≥ 70%** |
| Taxa de resolução da IA | `RESOLVIDO` com `status_ia = RESOLVIDO_PELA_IA` ÷ total | Definir baseline |
| Qualidade da transbordo | Cenário B com solução preenchida ÷ total de B e C | ≥ 90% |
| Tempo médio de primeira resposta | `criado_at` → primeira mensagem de atendente | Definir baseline |

Ver [08-non-functional](08-non-functional.md) §Métricas de produto para a implementação.

## Registro de Gaps

### Claims da documentação que não correspondem à realidade

| # | Claim | Onde | Realidade | Status |
|---|---|---|---|---|
| 00-1 | "n8n decide cenário A/B/C" | `README.md:281` | Cenários existem **só como prosa** no system prompt. Nenhum nó decide. `PATCH /webhooks/chat/status` nunca é chamado. | **CORRIGIDO (doc)** → [05-ai-pipeline](05-ai-pipeline.md) |
| 00-2 | "Fase 7 — Qdrant + RAG Semântico ✅" | `TODO_LIST.md:72` | RAG inalcançável: `/ai/solucionar` nunca é chamado por nada. | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
| 00-3 | "Fase 8 — Workflow n8n Completo ✅" | `TODO_LIST.md:77` | Workflow de 8 nós sem RAG, sem tools, sem roteamento de cenário. | **ABERTO** → [06-n8n-workflow](06-n8n-workflow.md) |
| 00-4 | "Armazenamento: Supabase Storage" | `README.md:20` | Não existe Supabase. A fonte de dados é Appwrite. | **CORRIGIDO (doc)** → Fase 5 |
| 00-5 | Stack obrigatória "NestJS, TypeScript, Prisma" | `.ai/PROJECT.md:120-136` | Nunca usada. O backend é Python/FastAPI. | **CORRIGIDO (doc)** → Fase 5 |
| 00-6 | "workflow exportável (19 nós)" | `.ai/TODO_LIST.md:210` | São 8 nós. O doc descreve ~12, o JSON tem 8. | **CORRIGIDO (doc)** → [06-n8n-workflow](06-n8n-workflow.md) |
| 00-7 | "Backup PostgreSQL + Qdrant + MinIO" | `.ai/TODO_LIST.md:261` | MinIO não é usado por código algum. Backup do Qdrant nunca dispara. | **ABERTO** → [09-infra-deploy](09-infra-deploy.md) §Backup |

### O que o objetivo de 70% exige e não existe

| # | Lacuna | Impacto no objetivo | Status |
|---|---|---|---|
| 00-8 | O status do chat nunca sai de `NOVO` no fluxo real | **Crítico.** Sem transição de status, a taxa de 70% é sempre 0. Nada é medido. | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
| 00-9 | `ia_diagnosticos` nunca é populado | **Crítico.** `taxa_resolucao_ia`, `ia_resolvidos` e `confianca_media` no dashboard leem de campos que nada escreve. | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
| 00-10 | `tempo_medio_resposta` mede a média do intervalo entre mensagens do mesmo atendente, não o tempo de primeira resposta | **Alto.** A métrica não representa o que o nome promete, então não mede a meta de 70%. | **ABERTO** → [08-non-functional](08-non-functional.md) §Métricas |
| 00-11 | Não há CSAT/NPS nem coleta de feedback | **Médio.** Não dá para medir qualidade da solução da IA. | **ABERTO** → adiado |
| 00-12 | Só texto funciona no WhatsApp; `extendedTextMessage`, imagem e áudio são descartados | **Alto.** Um print de tela é o anexo mais comum num chamado de ERP. | **ABERTO** → [06-n8n-workflow](06-n8n-workflow.md) |

### Confirmado conforme o escopo

| Item | Verificação |
|---|---|
| Autenticação JWT + 3 perfis | `backend/app/core/security.py`, `backend/app/api/deps.py` — conforme |
| 8 estados de chat | `backend/app/models/chat.py` — conforme |
| Kanban de 7 colunas | `backend/app/services/kanban_service.py` — conforme |
| Evolution API integrada | `backend/app/services/evolution_service.py` — conforme |
| Base de conhecimento com categorias | `backend/app/appwrite/schema.py` — conforme |
| Métricas no painel | `backend/app/services/dashboard_service.py` — presente, porém com semântica errada (00-10) |
# SPEC 01 — Domínio, Glossário e Máquina de Estados

Este documento define o vocabulário canônico. Em divergência entre código, tela, prompt ou documentação, os conceitos e invariantes aqui definidos prevalecem, mediante implementação explícita.

## Glossário

### Chat / chamado interno da plataforma

Entidade central da IA Support Platform (`chats` no Appwrite, rota `/chats`). Representa a conversa WhatsApp e o trabalho de suporte correspondente. Na plataforma, conversa e atendimento são a mesma entidade.

### Chamado externo Emsoft

Registro criado/atualizado na API interna `portal-api/v1/chamados`. É um recurso distinto do chat Appwrite. A relação é feita por `integracao_chamados`. Não assumir que os IDs dos dois sistemas sejam iguais.

### Cliente

Empresa que utiliza o ERP EMSoft, identificada preferencialmente pelo CNPJ (`clientes.documento`). Não é necessariamente a pessoa que enviou a mensagem.

### Contato WhatsApp

Número/pessoa que enviou a mensagem. É um canal de contato; não é chave natural da empresa cliente. Um mesmo cliente pode ter várias pessoas/telefones.

### Loja

Filial de um cliente. Um chat pode apontar para uma loja específica, quando conhecida.

### Atendente

Usuário humano do painel (perfis `admin`, `supervisor` ou `atendente`). É a pessoa responsável por um chat quando `atendente_id` estiver definido.

### Departamento

Equipe organizacional que recebe e trabalha determinado tipo de solicitação. Possui ID estável e código/slug único. Exemplos: `suporte_tecnico`, `financeiro`, `comercial`, `administrativo`, `implantacao` e `atendimento_geral`.

### Categoria ERP

Módulo/assunto técnico do ERP, por exemplo `fiscal`, `estoque`, `compras`, `vendas` ou `financeiro`. Classifica o conteúdo do problema; não identifica, por si só, a equipe responsável.

### Intenção

Objetivo comunicativo do cliente: `problema_tecnico`, `solicitacao_financeira`, `solicitacao_comercial`, `solicitacao_administrativa`, `implantacao_treinamento`, `solicitacao_humano`, `duvida_geral` ou `intencao_desconhecida`.

### Roteamento

Decisão determinística do backend que associa a intenção validada a um departamento ativo, respeitando regras de prioridade, confiança, contexto e disponibilidade.

### Atribuição

Designação de um chat a um atendente específico. O chat pode estar no departamento antes de ter uma pessoa atribuída.

### Diagnóstico da IA

Snapshot estruturado do que a IA apurou: resumo, categoria ERP, intenção, causa provável, solução, confiança, evidências RAG, cenário e destino sugerido/final. A decisão da IA é sugestão estruturada; a decisão operacional final é do backend.

### Outbox

Registro durável de evento pendente de envio a um sistema externo. Permite retentativa sem repetir efeitos externos.

## Princípios de modelagem do domínio

- `chat_id` é a identidade da conversa na plataforma.
- `chamado_id_externo` é a identidade do registro no sistema Emsoft.
- `departamento_id` indica a equipe responsável e permanece preenchido mesmo após atribuição individual.
- `atendente_id` indica a pessoa responsável e pode ser nulo enquanto o chat aguarda uma fila.
- Categoria ERP, intenção e departamento são dimensões diferentes.
- `remetente` da mensagem indica autoria (`cliente`, `ia`, `atendente`, `sistema`), não destinatário.
- Mensagens são append-only.
- Diagnóstico atual é um snapshot por chat; eventos/outbox são usados para rastrear integrações e reprocessamentos.

## Máquina de estados do chat

Estados canônicos existentes:

- `NOVO`
- `IA_ANALISANDO`
- `AGUARDANDO_CLIENTE`
- `AGUARDANDO_HUMANO_COM_SOLUCAO`
- `AGUARDANDO_HUMANO_SEM_SOLUCAO`
- `EM_ATENDIMENTO`
- `RESOLVIDO`
- `ENCERRADO`

### Transições permitidas

| De | Para permitidos |
|---|---|
| `NOVO` | `IA_ANALISANDO` |
| `IA_ANALISANDO` | `AGUARDANDO_CLIENTE`, `AGUARDANDO_HUMANO_COM_SOLUCAO`, `AGUARDANDO_HUMANO_SEM_SOLUCAO` |
| `AGUARDANDO_CLIENTE` | `IA_ANALISANDO`, `EM_ATENDIMENTO`, `RESOLVIDO`, `ENCERRADO` |
| `AGUARDANDO_HUMANO_COM_SOLUCAO` | `EM_ATENDIMENTO` |
| `AGUARDANDO_HUMANO_SEM_SOLUCAO` | `EM_ATENDIMENTO` |
| `EM_ATENDIMENTO` | `AGUARDANDO_CLIENTE`, `RESOLVIDO`, `ENCERRADO` |
| `RESOLVIDO` | `ENCERRADO` |
| `ENCERRADO` | nenhuma; estado terminal |

Qualquer mudança da tabela exige atualização de `STATUS_TRANSITIONS`, enum Appwrite, testes e esta spec. O bootstrap atual é aditivo e não propaga automaticamente alterações em enums já criados; aplicar a etapa manual documentada em `02-data-model.md`.

## Invariantes de estado e atribuição

1. Só o serviço de domínio pode alterar `status`; não permitir update direto por frontend, n8n ou integração.
2. `NOVO` deve passar por `IA_ANALISANDO` antes de uma decisão automatizada, exceto fluxo explicitamente configurado para atendimento humano direto.
3. `AGUARDANDO_CLIENTE` significa que a IA enviou uma orientação e aguarda retorno/validação do cliente; não significa sucesso confirmado.
4. `RESOLVIDO` exige confirmação do cliente ou confirmação humana autorizada.
5. `AGUARDANDO_HUMANO_COM_SOLUCAO` preserva `solucao_sugerida_ia`; `AGUARDANDO_HUMANO_SEM_SOLUCAO` não pode inventar nem preencher solução não sustentada.
6. `departamento_id` e `atendente_id` podem coexistir. O atendente deve pertencer ao departamento do chat, salvo override de supervisor/admin registrado.
7. Transferência para departamento atualiza `departamento_id` e limpa `atendente_id`; transferência para atendente valida o departamento do usuário e atualiza ambos.
8. Uma mudança de responsável humano deve gerar evento de sincronização externa, não novo chamado duplicado.
9. Encerrar um chat não apaga mensagens, diagnóstico nem referência externa.

## Eventos de domínio relevantes

- `chat.criado`
- `chat.mensagem_recebida`
- `ia.classificacao_concluida`
- `ia.diagnostico_concluido`
- `ia.solucao_enviada`
- `chat.departamento_alterado`
- `chat.atendente_atribuido`
- `chat.resolvido`
- `chat.encerrado`
- `integracao.chamado_solicitada`
- `integracao.chamado_sincronizada`
- `integracao.chamado_falhou`

Eventos são internos ao backend. O n8n não publica eventos de domínio diretamente.

## Registro de Gaps

Verificado contra o código em 2026-11-06.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 01-1 | `.ai/` mantém docs com vocabulário/estados divergentes (`EM_ATENDIMENTO_HUMANO`, stack antiga) | `.ai/AGENT.md`, `.ai/PROJECT_CONTEXT.md` | Baixa | **ABERTO** |
| 01-2 | `PATCH /webhooks/chat/status` **não** valida `STATUS_TRANSITIONS` — atualiza direto, inclusive saindo de `ENCERRADO` | `api/routes/webhooks.py`; `services/webhook_service.py:79-86` | **Alta** | **ABERTO** → [03](03-api-contract.md) |
| 01-3 | Urgência da IA (`critica`) não tem coluna; existe só no prompt | `ai/prompts.py` vs `PRIORIDADE_CHAT` | Média | **ABERTO** → [02](02-data-model.md) |
| 01-4 | Cenário A não alcança `RESOLVIDO` pela IA: `resolvido_pela_ia` leva a `AGUARDANDO_CLIENTE` e ninguém confirma | `services/ai_pipeline.py:27-31` | **Alta** | **ABERTO** → [05](05-ai-pipeline.md) |
| 01-5 | `chats.loja_id` nunca é populado; nenhum endpoint define a loja | `appwrite/schema.py:135` | Média | **ABERTO** → [02](02-data-model.md) |
| 01-6 | `transferir` usa literais de string; `transferir_grupo` usa o enum | `services/chat_service.py:166-171` | Baixa | **ABERTO** |
| 01-7 | `chat["status"] == StatusChat.em_atendimento` compara string com membro de `StrEnum` | `services/chat_service.py:182` | Baixa | **ABERTO** |
| 01-8 | Sem tabela de auditoria; não há como saber quem mudou status/atribuição | `historico` removido | Média | **ABERTO** → [04](04-rbac-matrix.md) |
| 01-9 | Sem entidade departamento nem atribuição por departamento na máquina de estados | `appwrite/schema.py`; `services/chat_service.py` | **Alta** | **ABERTO** → [10](10-departamentos-e-roteamento.md) |
| 01-10 | Domínio não separa categoria ERP de departamento; intenção não é modelada | `ai/prompts.py`; `appwrite/schema.py` | **Alta** | **ABERTO** → 05, 10 |
| 01-11 | Sem distinção de reabertura/confirmação de resolução pelo cliente além de `RESOLVIDO → IA_ANALISANDO` | `services/chat_service.py:28` | Média | **ABERTO** → [05](05-ai-pipeline.md) |

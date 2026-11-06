# SPEC 01 — Domínio e Glossário

Vocabulário canônico do produto. Quando um termo aparece em código, tela, prompt ou
documentação diferente, esta spec vence.

## Glossário

### Ticket

**Chamado** no dia a dia. A entidade central do sistema. No código é `chat` (coleção
`chats` Appwrite), e a rota é `/chats`.

Um chat é uma conversa entre um cliente do ERP e a equipe de suporte. Não existe
separação entre "conversa" e "chamado": são a mesma coisa, porque o ERP éVertical e cada
conversa é um problema a resolver.

### Cliente

**Cliente** é a **empresa** que usa o ERP EMSoft — autopeças, distribuidora, centro
automotivo, rede multiempresa. É a unidade contratual da EMSoft.

- Coleção `clientes`, rota `/clientes`.
- Identificado por `documento` (CNPJ). É o CNPJ, não o CPF.
- **Não** é a pessoa que mandou a mensagem no WhatsApp.

> **Confusão recorrente:** o número de WhatsApp é o canal, não a identidade. O mesmo
> número pode falar por várias lojas do mesmo cliente. Duas pessoas da mesma empresa
> têm números diferentes e produzem chats diferentes. Ver §Identidade de conversa.

### Loja

**Loja** ou **filial** é um estabelecimento do Cliente. Uma rede com matriz e 8 filiais
tem 1 `cliente` e 8 `lojas`.

- Coleção `lojas`,Fk `cliente_id`.
- O chat pode apontar para uma loja (`chats.loja_id`) — usado quando o problema é de
  um estabelecimento específico.

> **Lacuna de modelagem:** `chats.loja_id` existe no schema mas não é populado em
> lugar nenhum do código. Nenhum endpoint aceita ou define a loja de um chat.

### Atendente

**Atendente** é a pessoa que usa o sistema. Inclui os três perfis: `admin`,
`supervisor` e `atendente`.

- Coleção `atendentes`, rota `/auth/usuarios` (não `/atendentes`).
- Existe uma rota separada `GET /atendentes/ativos`, que existe só para alimentar o
  seletor de transferência no Kanban.

> **Ressalva de rota:** o recurso chama `atendentes` mas CRUD fica sob `/auth/usuarios`.
> Mantido porque o histórico de UI depende disso; documentado aqui para não confundir.

### Setor

**Setor** é o grupo de trabalho que um atendente pertence e para o qual um chat pode ser
transbordado.

- `atendentes.setor` — o setor de casa do atendente.
- `chats.setor_alvo` — o setor que pegou o chat na transferência de grupo.

> **Lacuna:** os valores são strings livres, sem enum. O frontend inventa a lista em
> `atendimento/page.tsx:143` e `kanban/page.tsx:22`
> (`["atendimento", "supervisao", "programadores"]`), duplicada. Nada valida.
> Ver [02-data-model](02-data-model.md) §Enum.

### Mensagem

**Mensagem** é um item de conversa. Sempre pertence a um chat. Nunca é editável nem
removível (ver [00-escopo](00-escopo.md) §Adiado).

- Coleção `mensagens`.
- `remetente` diz **quem falou**: `cliente`, `ia`, `atendente`, `sistema`.
- `tipo` diz **o formato**: `texto`, `audio`, `documento`, `imagem`.

> **Confusão recorrente:** `remetente` é a **autoria**, não o **destinatário**. Uma
> mensagem com `remetente = atendente` também é enviada ao cliente pelo WhatsApp.

### Diagnóstico da IA

**Diagnóstico** é o registro estruturado do que a IA descobriu sobre um chat: resumo,
causa provável, solução, confiança, e qual cenário aplicar.

- Coleção `ia_diagnosticos`, rota `POST /webhooks/chat/diagnostico`.
- `status_ia` é a **decisão** entre os três cenários:
  `RESOLVIDO_PELA_IA` | `TRANSFERIR_COM_SOLUCAO` | `TRANSFERIR_SEM_SOLUCAO`.
- É **um por chat**, não um por mensagem. Uma re-análise sobrescreve.

> **Lacuna crítica:** nenhum registro é criado. Ver [05-ai-pipeline](05-ai-pipeline.md).

### Cenário

**Cenário** é o resultado da interação entre a IA e o cliente em um momento do
atendimento. Não é um estado persistido — é uma **decisão** que resulta numa transição
de status. Definido em [00-escopo](00-escopo.md) §Três cenários.

### Base de conhecimento

**Base de conhecimento** é o conjunto de artigos de suporte do ERP que a IA consulta
antes de responder. É a fonte da verdade sobre soluções.

- Coleção `knowledge_bases`, rota `/knowledge-base`.
- Cada artigo tem `categoria`, `titulo`, `conteudo`, `ativo`.
- É indexada por vetor no Qdrant (coleção `emsoft-knowledge-base`).

> **Confusão recorrente:** o banco Appwrite guarda o artigo; o Qdrant guarda o
> **embedding** dele. São dois sistemas que precisam ficar em sincronia. Ver
> [05-ai-pipeline](05-ai-pipeline.md) §RAG.

## Máquina de estados do chat

Oito estados. Definidos em `backend/app/models/chat.py` e espelhados no enum Appwrite
`STATUS_CHAT` (`backend/app/appwrite/schema.py:31-40`).

```
                            ┌──────────────────────────────┐
                            ▼                              │
   ┌────────┐          ┌───────────────┐                   │
   │  NOVO  │─────────▶│ IA_ANALISANDO │                   │
   └────────┘          └───────┬───────┘                   │
                                │                           │
        ┌───────────────────────┼───────────────────────┐   │
        ▼                       ▼                       ▼   │
┌───────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│ AGUARDANDO_CLIENTE│  │AGUARDANDO_HUMANO_│  │ AGUARDANDO_HUMANO_      │
│                   │  │   COM_SOLUCAO    │  │      SEM_SOLUCAO        │
└─────┬──────────┬──┘  └────────┬─────────┘  └────────────┬─────────────┘
      │          │              │                          │
      │          │              ▼                          ▼
      │          │     ┌─────────────────┐          ┌─────────────────┐
      │          │     │ EM_ATENDIMENTO  │◀─────────│                 │
      │          │     └────┬───────┬────┘          └─────────────────┘
      │          │          │       │
      │          │          │       ▼
      │          │          │  ┌───────────┐
      │          ├─────────▶│  RESOLVIDO │──────┐
      │          │          └───────────┘      │
      │          ▼                             ▼
      │     ┌───────────┐              ┌────────────┐
      └────▶│ ENCERRADO │◀─────────────│  ENCERRADO │
            └───────────┘              └────────────┘
```

### Tabela de transições

Esta tabela é a **norma**. Ela corresponde a `STATUS_TRANSITIONS` em
`backend/app/services/chat_service.py:8-30`, e qualquer mudança nela é mudança de
regra de negócio.

| De | Para Permitidos |
|---|---|
| `NOVO` | `IA_ANALISANDO` |
| `IA_ANALISANDO` | `AGUARDANDO_CLIENTE`, `AGUARDANDO_HUMANO_COM_SOLUCAO`, `AGUARDANDO_HUMANO_SEM_SOLUCAO` |
| `AGUARDANDO_CLIENTE` | `IA_ANALISANDO`, `EM_ATENDIMENTO`, `RESOLVIDO`, `ENCERRADO` |
| `AGUARDANDO_HUMANO_COM_SOLUCAO` | `EM_ATENDIMENTO` |
| `AGUARDANDO_HUMANO_SEM_SOLUCAO` | `EM_ATENDIMENTO` |
| `EM_ATENDIMENTO` | `AGUARDANDO_CLIENTE`, `RESOLVIDO`, `ENCERRADO` |
| `RESOLVIDO` | `ENCERRADO` |
| `ENCERRADO` | *(nenhum — estado terminal)* |

### Invariantes

1. **Toda transição passa por esta tabela.** Não existe caminho lateral.
2. **`ENCERRADO` é terminal.** Um chat encerrado não volta.
3. **Sair de `AGUARDANDO_HUMANO_*` exige `EM_ATENDIMENTO`.** Não se pode ir direto de
   "aguardando humano" para "resolvido" — um humano tem de assumir o chat.
4. **A IA nunca entra em `EM_ATENDIMENTO`.** Esse estado significa que um humano tem o
   chat. A IA escreve em `NOVO → IA_ANALISANDO → {AGUARDANDO_*}`, e a partir daí quem
   move é o painel.
5. **Somente a IA (via webhook) e os perfis autenticados podem transicionar.**
   `PATCH /webhooks/chat/status` **deve** aplicar a mesma tabela — ver gap 01-2.

### Quem pode fazer cada transição

| Transição | Autor |
|---|---|
| `NOVO → IA_ANALISANDO` | IA (via `POST /webhooks/ai/solucionar`) |
| `IA_ANALISANDO → AGUARDANDO_CLIENTE` | IA — Cenário A |
| `IA_ANALISANDO → AGUARDANDO_HUMANO_COM_SOLUCAO` | IA — Cenário B |
| `IA_ANALISANDO → AGUARDANDO_HUMANO_SEM_SOLUCAO` | IA — Cenário C |
| `AGUARDANDO_* → EM_ATENDIMENTO` | Atendente (`pegar`, `assinar`, `transferir`) |
| `EM_ATENDIMENTO → AGUARDANDO_CLIENTE` | Atendente |
| `* → RESOLVIDO` | Atendente |
| `* → ENCERRADO` | Atendente |
| `RESOLVIDO → ENCERRADO` | Atendente |

## Termos que NÃO são sinônimos

Erros que já ocorreram no projeto:

| Confusão | Correto |
|---|---|
| `EM_ATENDIMENTO` vs `EM_ATENDIMENTO_HUMANO` | Só `EM_ATENDIMENTO` existe. `.ai/PROJECT_CONTEXT.md:49` está errado. |
| Kanban tem 7 colunas, dashboard tem 8 | Correto: Kanban **não** mostra `ENCERRADO`. `dashboard_service.py:7-16` tem 8, `kanban_service.py` tem 7. Não é bug, mas precisa estar documentado para ninguém "corrigir" um para o outro. |
| "Mensagem do IA" vs "resposta da IA" | É a mesma entidade: `mensagens` com `remetente = "ia"`. |
| "Histórico" vs "Mensagens" | A tabela `historico` foi removida (`.ai/TODO_LIST.md:308`). Não existe trilha de auditoria. Ver [02-data-model](02-data-model.md). |
| "Prioridade" vs "Urgência" | `PrioridadeChat` é 4 valores (`baixa`/`media`/`alta`/`urgente`). A "Urgência" do prompt da IA (`baixa`/`media`/`alta`/`critica`) é um conceito **diferente** que não tem coluna. Ver gap 01-3. |

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 01-1 | `EM_ATENDIMENTO_HUMANO` aparece na documentação como se fosse o nome real do estado | `.ai/PROJECT_CONTEXT.md:49`, `.ai/AGENT.md:23` | Baixa | **ABERTO** → Fase 5 |
| 01-2 | `PATCH /webhooks/chat/status` **não** valida contra `STATUS_TRANSITIONS` — atualiza direto. Permite transição impossível, inclusive sair de `ENCERRADO` | `backend/app/api/routes/webhooks.py` (`atualizar_status`) | **Alta** | **ABERTO** → [03-api-contract](03-api-contract.md) |
| 01-3 | Urgência da IA (`critica`) não tem coluna; existe só no prompt | `.ai/SUPORTE_AGENT.md:107-111` vs `PRIORIDADE_CHAT` | Média | **ABERTO** → [02-data-model](02-data-model.md) §Enum |
| 01-4 | Cenário A nunca alcança `RESOLVIDO` pela IA. `precisa_humano=False` leva a `AGUARDANDO_CLIENTE`; ninguém confirma nem resolve | `backend/app/ai/router.py:129-136` | **Alta** | **ABERTO** → [05-ai-pipeline](05-ai-pipeline.md) |
| 01-5 | `chats.loja_id` nunca é populado; nenhum endpoint define a loja do chat | `backend/app/appwrite/schema.py:138` | Média | **ABERTO** → [02-data-model](02-data-model.md) |
| 01-6 | Inconsistência de tipo no mesmo arquivo: `transferir` usa literais de string, `transferir_grupo` usa o enum | `backend/app/services/chat_service.py:167-169` vs `:170+` | Baixa | **ABERTO** |
| 01-7 | `chat["status"] == StatusChat.em_atendimento` compara string com membro de `StrEnum`. Funciona por acidente, não por contrato | `backend/app/services/chat_service.py:182` | Baixa | **ABERTO** |
| 01-8 | Nenhuma tabela de auditoria. Não há como saber quem mudou o status de um chat quando | `historico` removido (`.ai/TODO_LIST.md:308`) | Média | **ABERTO** → adiado |
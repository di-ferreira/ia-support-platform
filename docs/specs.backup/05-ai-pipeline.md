# SPEC 05 — Pipeline de IA

Esta é a spec mais importante do conjunto. Ela define o comportamento que sustenta o
objetivo de 70% ([00-escopo](00-escopo.md) §Objetivo).

## Decisão arquitetural

> **ADR-0004:** o **backend é o dono da IA**. O n8n orquestra transporte; ele não decide
> nada. Ver [adr/0004-backend-dono-da-ia.md](adr/0004-backend-dono-da-ia.md).

Consequência prática: prompts, busca no RAG, parsing de resposta e a decisão do cenário
vivem em Python, versionados e testados. O n8n não contém prompt de negócio.

## Fluxo ponta a ponta

```
Cliente manda mensagem no WhatsApp
        │
        ▼
[Evolution API]  :8080        evento MESSAGES_UPSERT
        │
        ▼
[n8n]  Webhook                normaliza o payload bruto
        │
        ├─▶ POST /webhooks/mensagem          persiste mensagem, cria chat se preciso
        │                                    devolve { chat_id }
        │
        ├─▶ GET  /webhooks/chat/{id}/contexto  o chat está sob controle da IA?
        │         ├ status em NOVO | IA_ANALISANDO | AGUARDANDO_CLIENTE → IA responde
        │         └ status em EM_ATENDIMENTO | AGUARDANDO_HUMANO_* | RESOLVIDO
        │           → humano responde. IA não intervém.
        │
        ├─▶ POST /webhooks/ai/solucionar      RAG + LLM (backend decide o cenário)
        │         ├ grava ia_diagnosticos
        │         ├ espelha resumo/solução/confiança no chat
        │         ├ transiciona o status conforme o cenário
        │         └ devolve { status_ia, mensagem_cliente }
        │
        ├─▶ POST /webhooks/mensagem          persiste a resposta da IA (remetente="ia")
        │
        └─▶ [Evolution API]  sendText        entrega ao cliente
                 │
                 └──(evento WebSocket)──▶ painel do atendente
```

## Cenários

A decisão **não** é do LLM. O LLM produz um veredito estruturado; o backend aplica uma
regra determinística. Isso é o que garante que os três cenários existam de verdade.

### Entrada

`SOLUTION_SYSTEM` (`backend/app/ai/prompts.py:35-52`) pede exatamente:

```json
{
  "solucao": "passo a passo da solução",
  "instrucoes_cliente": "o que o cliente pode fazer, ou null",
  "precisa_humano": false,
  "referencia": "título do artigo consultado, ou null"
}
```

### Regra de decisão

```
                    ┌─────────────────────────┐
                    │ solucao preenchida?     │
                    └───────────┬─────────────┘
                    não │                 │ sim
                        ▼                 ▼
              ┌──────────────────┐  ┌───────────────────┐
              │  CENÁRIO C       │  │ precisa_humano?   │
              │ TRANSFERIR_      │  └─────────┬─────────┘
              │ SEM_SOLUCAO      │   false │           │ true
              └──────────────────┘          ▼           ▼
              status →                      ┌─────────┐ ┌──────────┐
              AGUARDANDO_HUMANO_           │ CENÁRIO │ │ CENÁRIO B│
              SEM_SOLUCAO                  │    A    │ │TRANSFERIR│
              status_ia =                  │         │ │COM_SOLUCAO│
              TRANSFERIR_SEM_SOLUCAO       │         │ └──────────┘
                                           │         │ status →
                                           │         │ AGUARDANDO_
                                           │         │ HUMANO_COM_
                                           │         │ SOLUCAO
                                           │         │ status_ia =
                                           │         │ TRANSFERIR_
                                           │         │ COM_SOLUCAO
                                           └────┬────┘
                                                ▼
                                   status → AGUARDANDO_CLIENTE
                                   status_ia = RESOLVIDO_PELA_IA
```

### Efeito colateral por cenário

| Cenário | `status` | `necessita_humano` | `solucao_sugerida_ia` | Vai para o cliente |
|---|---|---|---|---|
| **A** | `AGUARDANDO_CLIENTE` | `false` | preenchida | Sim, o passo a passo |
| **B** | `AGUARDANDO_HUMANO_COM_SOLUCAO` | `true` | preenchida | Sim, confirmação + aviso |
| **C** | `AGUARDANDO_HUMANO_SEM_SOLUCAO` | `true` | vazia | Sim, pedido de mais detalhes |

### Cenário A precisa de confirmação

O Cenário A vai para `AGUARDANDO_CLIENTE`, **não** direto para `RESOLVIDO`. O cliente
recebe o passo a passo; se confirmar, alguém move para `RESOLVIDO`. Isso é intencional:
marcar como resolvido algo que o cliente ainda não testou inflaria a taxa de resolução da
IA e quebraria a métrica de 70%.

A transição `AGUARDANDO_CLIENTE → RESOLVIDO` já existe na máquina de estados
([01-domain-glossary](01-domain-glossary.md) §Tabela de transições).

> Hoje **ninguém** faz essa confirmação, nem a IA nem o painel. O chat fica parado em
> `AGUARDANDO_CLIENTE`. Ver gap 05-4.

## Autenticação M2M — por que `/webhooks/ai/solucionar`

**O n8n não consegue chamar `/ai/*`.** Dois motivos:

1. `/ai/*` exige `get_current_user`, que é JWT Bearer
   (`backend/app/ai/router.py:33,51,76` → `deps.py:42`). O n8n tem apenas
   `X-Webhook-Secret`.
2. Dar um JWT ao n8n exigiria uma conta de serviço real no Appwrite, com rotação e escopo
   — complexityidade desproporcional para quem só precisa de um segredo compartilhado que
   já existe.

Decisão: **`POST /webhooks/ai/solucionar`**, sob `verify_webhook`, é o endpoint que o n8n
chama. Ele reutiliza `OllamaService`/`OpenAIService`, `search_similar` e `SOLUTION_SYSTEM`.

`/ai/*` permanece como **API humana** autenticada por JWT, para depuração e uso manual.

### Contrato

```http
POST /webhooks/ai/solucionar
X-Webhook-Secret: <WEBHOOK_SECRET>
Content-Type: application/json

{ "chat_id": "<ulid>" }
```

```json
{
  "status_ia": "TRANSFERIR_COM_SOLUCAO",
  "categoria": "fiscal",
  "solucao": "1. Acesse Configurações > Fiscal ...",
  "instrucoes_cliente": "Verifique o CNPJ no cadastro tributário.",
  "precisa_humano": true,
  "referencia": "NF-e rejeitada — CNPJ inválido",
  "confianca": 0.87,
  "mensagem_cliente": "Texto pronto para enviar ao cliente.",
  "chat_status": "AGUARDANDO_HUMANO_COM_SOLUCAO"
}
```

`mensagem_cliente` é o texto que o n8n entrega ao WhatsApp. O backend monta a
composição (solução ou pedido de detalhes) para que a lógica de redação fica no backend.

## RAG

### Pipeline de indexação

O texto do artigo é **embutido como um vetor único por artigo**. Não há chunking.

| Parâmetro | Valor | Fonte |
|---|---|---|
| Coleção | `emsoft-knowledge-base` | `qdrant_service.py:6` |
| Dimensão | **768** | `qdrant_service.py:7` |
| Distância | Cosine | `qdrant_service.py:22` |
| Modelo de embedding | `nomic-embed-text` | `config.py:32` |
| Payload | `titulo`, `conteudo`, `categoria` | `qdrant_service.py:60-64` |
| ID do ponto | ULID do artigo (mesmo id do Appwrite) | `upsert_article(article_id=...)` |

**768 dimensões é a restrição dominante.** `nomic-embed-text` produz 768. O
`text-embedding-3-small` do OpenAI produz **1536** e **não é compatível** com a coleção.
Ver [adr/0005-dimensao-de-embedding.md](adr/0005-dimensao-de-embedding.md).

### Consultar

1. Pega a última mensagem do cliente.
2. Embute com o mesmo modelo da indexação.
3. `search_similar(embedding, limit=5)`.
4. Monta `rag_context` com `Título:` + `Conteúdo:` de cada artigo, separados por linha em
   branco.

**Sem filtro de score.** Os 5 mais próximos entram, mesmo que irrelevantes. `docs/n8n-workflow.md:93-97`
promete "min score 0.7" — isso não existe no código.

**Falha de RAG é erro.** Se o embedding ou a busca falhar, o pipeline responde 503 —
não degrada para "nenhum artigo encontrado". Um Qdrant fora do ar não pode produzir
Cenário C falso (sem base nenhuma): a decisão de cenário só é honesta com base real.
Ver gap 05-6.

### Sincronização Appwrite ↔ Qdrant

Toda escrita na base de conhecimento **tem** que sincronizar o vetor:

| Operação | Ação obrigatória |
|---|---|
| Criar artigo | `ensure_collection()` se preciso + `upsert_article` com embedding |
| Atualizar artigo | Apagar o vetor antigo, `upsert_article` com o novo |
| Remover artigo | Apagar o ponto por `article_id` |
| Desativar artigo | Apagar o ponto |

Hoje `KnowledgeBaseService` **não faz nada disso**. O CRUD e o índice divergem sem caminho
de reconciliação. Ver gap 05-5.

### Chunking — decisão

**Um vetor por artigo, sem chunking.** Motivo: os 20 artigos do seed têm 300–600
palavras, e um artigo é uma unidade semântica coesa. Chunking (500/50, como promete
`docs/n8n-workflow.md:212`) só passa a ser necessário quando a base tiver manuais de
dezenas de páginas. Registrado aqui para que a decisão não se perca.

## Prompts

| Prompt | Uso | Persiste? |
|---|---|---|
| `CLASSIFY_SYSTEM` | `/ai/classificar` — categoria ERP + subcategoria + confiança. Usa cache Redis. | Não |
| `SUMMARIZE_SYSTEM` | `/ai/analisar?tipo=summarizar` | Não |
| `DIAGNOSE_SYSTEM` | `/ai/analisar?tipo=diagnosticar` | Não |
| `SOLUTION_SYSTEM` | `/webhooks/ai/solucionar` — o prompt do fluxo real | Sim, via `ia_diagnosticos` |

A persona da IA (tom, regras de interação, limites de escalonamento) está em
`.ai/SUPORTE_AGENT.md`. Ela é **entrada de prompt**, não código. Ao migrar o fluxo,
`SOLUTION_SYSTEM` precisa absorver as regras de `SUPORTE_AGENT.md` que importam —
principalmente "não invente solução" e "não prometa prazo".

### Inconsistência de categoria

`CLASSIFY_SYSTEM` (`prompts.py:11-17`) reconhece **7** categorias: `fiscal`, `estoque`,
`compras`, `vendas`, `financeiro`, `multiempresa`, `outro`.
`CATEGORIA_CONHECIMENTO` (`schema.py:52`) tem **5**: sem `multiempresa`, sem `outro`.

Resultado: a IA classifica como `multiempresa`, mas **não existe artigo** com essa
categoria para ela achar. Ver gap 02-1.

## Selecting de provider

```
LLM_PROVIDER == "ollama"      → OllamaService
LLM_PROVIDER != "ollama" e OPENAI_API_KEY set → OpenAIService
caso contrário                → OllamaService
```

O default é `ollama`. Notar que o segundo branch é contraditório: se alguém define
`LLM_PROVIDER=openai` sem chave, cai em Ollama silenciosamente.

## Cache

`AICache` usa Redis, chave `SHA-256(prompt + modelo)`, TTL 3600s. Só `/ai/classificar`
usa. Falha de Redis é engolida e degrada para sem-cache.

`/webhooks/ai/solucionar` **não** deve usar cache: o histórico do chat muda a cada
mensagem, e servir a solução antiga seria um bug funcional.

## O que NÃO é responsabilidade da IA

| Não pode | Por quê |
|---|---|
| Inventar solução | Se a base não respondeu, é Cenário C |
| Prometer prazo | `.ai/SUPORTE_AGENT.md:144` |
| Executar alteração em banco | `.ai/SUPORTE_AGENT.md:143` |
| Expor senha ou dado bancário do cliente | `.ai/SUPORTE_AGENT.md:142` |
| Mover chat para `EM_ATENDIMENTO` | Esse estado significa "humano no comando" |

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 05-1 | **Crítico.** O pipeline de IA não está conectado. `/ai/classificar`, `/ai/analisar` e `/ai/solucionar` não têm chamador. O n8n roda um AI Agent sem tools que alucina | `ai/router.py`; `workflow-support-ai.json` | **Crítica** | **ABERTO (orquestração n8n)** — o backend é dono da IA (ADR-0004) e os endpoints foram provados em runtime no e2e P0 (2026-10-05, §Evidência de runtime). Falta o n8n orquestrar `POST /webhooks/ai/solucionar` no fluxo prod → [06-n8n-workflow](06-n8n-workflow.md) |
| 05-2 | **Crítico.** `POST /webhooks/chat/diagnostico` nunca é chamado. `ia_diagnosticos` nunca é populada. Todo o histórico de decisão da IA está perdido, e os KPIs do dashboard leem de campos que ninguém escreve | `services/ai_pipeline.py`; `ia_diagnostico.py` | **Crítica** | **PROVADO (pipeline, runtime 2026-10-05)** — `_finalizar` gravou `ia_diagnostico` real (RESOLVIDO_PELA_IA, confiança 0.95, `modelo_usado=gpt-oss:120b-cloud`), validado direto no Appwrite (§Evidência de runtime). Falta só o chamado vivo do n8n (05-1 → [06-n8n-workflow](06-n8n-workflow.md)) |
| 05-3 | **Crítico.** `PATCH /webhooks/chat/status` nunca é chamado. O status do chat nunca sai de `NOVO` no fluxo real. A taxa de 70% é estruturalmente 0 | `workflow-support-ai.json` | **Crítica** | **PROVADO (pipeline, runtime 2026-10-05)** — `_finalizar` transicionou o chat NOVO → AGUARDANDO_CLIENTE e espelhou `necessita_humano=false`/`nivel_confianca_ia=0.95`, validado direto no Appwrite (§Evidência de runtime). Falta só o chamado vivo do n8n (05-1 → [06-n8n-workflow](06-n8n-workflow.md)) |
| 05-4 | Cenário A não tem caminho de fechamento. Vai para `AGUARDANDO_CLIENTE` e ninguém confirma | painel (frontend) | **Alta** | **ABERTO** → [07-frontend](07-frontend.md) |
| 05-5 | CRUD da base de conhecimento não sincroniza o Qdrant. Índice e banco divergem | `services/knowledge_base_service.py` | **Alta** | **CORRIGIDO** — `criar`/`atualizar` (se `ativo`) embutem + `upsert_article`; desativar/remover apaga o ponto; falha de Qdrant/embedding vira erro (503), sem escrita parcial silenciosa |
| 05-6 | Falha de RAG degrada para "nenhum artigo encontrado" em vez de erro. Qdrant fora do ar produz Cenário C falso | `services/ai_pipeline.py` `_buscar_base` | **Alta** | **CORRIGIDO** — falha de embedding ou busca responde 503; Cenário C só acontece com base real consultada |
| 05-7 | `/ai/solucionar` escreve no chat via repositório, furando a máquina de estados. E `except Exception: pass` engole falha de persistência sem log | `services/ai_pipeline.py`; `ai/router.py`; `api/routes/webhooks.py` | **Alta** | **CORRIGIDO** — ambos os endpoints delegam a `AIPipelineService`, que transiciona via `ChatService.atualizar_status` e propaga falha de persistência |
| 05-8 | `/ai/solucionar` retorna `result` da LLM sem validar shape. Campo faltando vira `None` silenciosamente | `services/ai_pipeline.py` `SolucaoLLM` | Média | **CORRIGIDO** — veredito parseado via Pydantic; JSON inválido responde 502 com o trecho bruto |
| 05-9 | `/ai/*` não tem resposta Pydantic. Contrato é o dict cru do LLM | `ai/router.py`; `schemas/webhook.py` | Média | **ABERTO** — `/ai/solucionar` e `/webhooks/ai/solucionar` usam `WebhookSolucaoResponse`; `/ai/classificar` e `/ai/analisar` ainda devolvem o dict cru do LLM |
| 05-10 | `/ai/classificar` não usa Pydantic — o `chat_id` do `/ai/analisar` é query param, e o conteúdo vai na URL | `ai/router.py:34-54` | **Alta** | **ABERTO** |
| 05-11 | `VECTOR_SIZE=768` incompatível com `text-embedding-3-small` (1536). `LLM_PROVIDER=openai` quebra o RAG | `services/qdrant_service.py`; `ai/provider.py` | **Alta** | **CORRIGIDO** → [adr/0005](adr/0005-dimensao-de-embedding.md) — embedding sempre Ollama `nomic-embed-text` (768), independentemente do provider de LLM |
| 05-12 | `_get_llm` cai em Ollama silenciosamente se `LLM_PROVIDER=openai` sem `OPENAI_API_KEY` | `ai/provider.py` | Média | **CORRIGIDO** — `get_llm` falha rápido com `LLMIndisponivelError` (openai sem chave, provider desconhecido) |
| 05-13 | `except Exception: pass` também engole falha de embedding | `services/ai_pipeline.py` `_buscar_base` | Média | **CORRIGIDO** — falha de embedding propaga e responde 503 |
| 05-14 | AI Agent do n8n usa `nemotron-3-super:cloud`; `.env` aponta `deepseek-v4-flash:cloud`; `config.py` aponta `llama3.2`. Três modelos diferentes em três lugares | `workflow-support-ai.json`; `infra/.env.example:26`; `config.py:31` | Média | **ABERTO** |
| 05-15 | `AICache` engole toda exceção em `get`/`set`/`clear`. `clear()` nunca é chamado | `ai/ai_cache.py:29,37,46` | Média | **ABERTO** |
| 05-16 | `prompt.format(**kwargs)` quebra se o conteúdo do artigo tiver `{` ou `}` — chaves de template não escapadas | `ai/prompts.py` | **Alta** | **CORRIGIDO** — os prompts viraram constantes (`CLASSIFY_SYSTEM`/`SUMMARIZE_SYSTEM`/`SOLUTION_SYSTEM`/`DIAGNOSE_SYSTEM`) e o conteúdo dinâmico (mensagem/RAG/histórico) entra como *valor* de f-string em `build_solution_messages`, nunca como template — `{}` no artigo não são reinterpretados |
| 05-17 | Categoria `multiempresa` é reconhecida pela IA mas não existe no schema de conhecimento | `prompts.py:16` vs `schema.py:52` | **Alta** | **ABERTO** → [02-data-model](02-data-model.md) |
| 05-18 | `IADiagnosticoRepository.get_by_chat` não é chamado por nada | `appwrite/repositories/ia_diagnostico.py:10` | Baixa | **ABERTO** |
| 05-19 | Dependência `openai` está declarada em `pyproject.toml` e `requirements.txt` mas nunca importada — o serviço usa `httpx` cru | `pyproject.toml:18` | Baixa | **ABERTO** |
| 05-20 | Nenhum teste cobre `app/ai/` inteiro. Nenhum LLM é stubado em teste | `tests/` | **Alta** | **ABERTO** — mitigado: `tests/test_ai_pipeline.py` exercita `AIPipelineService` com `get_llm`/`get_embedder` stubados (classificar, RAG, cenários B/C, `_finalizar`); ainda sem teste unitário direto de `ai_cache.py`, `router.py`, `ollama_service.py` e `openai_service.py` → [10-test-strategy](10-test-strategy.md) |

## Evidência de runtime (e2e P0, 2026-10-05)

Cenário 1 (hit RAG) executado no backend `:8001` com o stack dev no ar
(Appwrite `:8020`, Qdrant `:6333` com 20 pontos, Ollama `:11434` com
`gpt-oss:120b-cloud` + `nomic-embed-text`):

1. `POST /webhooks/mensagem` (secret `dev-webhook-secret-change-in-production`),
   `whatsapp_number=5511999990001`, conteúdo
   "Como resolvo o erro de estoque negativo no meu sistema?" → `201`; chat
   criado `6ac3f9d0000cfdbb3f2e` em `NOVO`.
2. `GET /webhooks/chat/{id}/contexto` → `200`, `status=NOVO`,
   `ultima_mensagem` correta.
3. `POST /webhooks/ai/solucionar` → `200`:
   - RAG: `search_similar` (768, `Cosine`) devolveu o artigo
     "Produto com estoque negativo: como resolver" (categoria `estoque`).
   - Veredito: `status_ia=RESOLVIDO_PELA_IA`, `referencia=
     "Produto com estoque negativo: como resolver"`, `confianca=0.95`,
     `precisa_humano=false`, `modelo_usado=gpt-oss:120b-cloud`.

Persistência validada **direto no Appwrite** (repositórios do próprio backend):

- `ia_diagnosticos.get_by_chat` → doc `6ac3f9d700134f17341b` com
  `status_ia=RESOLVIDO_PELA_IA`, `confianca=0.95`, `modelo_usado=
  gpt-oss:120b-cloud` e `solucao` completa (7 passos). Prova o **05-2**.
- `chats.get` → `status=AGUARDANDO_CLIENTE`, `necessita_humano=false`,
  `nivel_confianca_ia=0.95`, `solucao_sugerida_ia` preenchida. Prova o
  **05-3**/`00-8`.
- RAG semântico real de ponta a ponta (embed → busca → artigo → LLM).
  Prova o **00-2**.

Cenário C (sem hit): coberto por `tests/test_ai_pipeline.py::
test_no_hit_rag_sem_llm` (busca vazia → `transferir_sem_solucao` →
`AGUARDANDO_HUMANO_SEM_SOLUCAO` + `NO_HIT_MENSAGEM`). Não reproduzido em
HTTP live porque, por design, não há filtro de score e a coleção tem 20 pontos
— o caminho `if not hits:` só dispara com Qdrant vazio. Suíte: `67 passed`.
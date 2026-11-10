# Priorização dos gaps ABERTOS

Gerado em 2026-11-10 a partir do [checklist de implementações](checklist-implementacoes.md)
(93 gaps ABERTOS + 4 fases pendentes do SPEC 13). A fonte de verdade segue sendo cada spec.
Atualizado em 2026-11-10: T1 completo — 09-1, 09-2, 09-4 e 09-15 corrigidos.

## Critério de ordenação

1. **T0 Bloqueante** — trava as Fases 5/6/7 e depende de ação externa.
2. **T1 Crítica** — sem isso a pilha prod não funciona.
3. **T2 Alta** — integridade de dados e segurança (máquina de estados, auth, CORS, webhook).
4. **T3 Alta** — integração Emsoft (outbox, degradação, worker) e escopo de produto.
5. **T4 Alta** — frontend da Fase 4 (departamentos) e painéis de diagnóstico.
6. **T5 Alta** — mídia do WhatsApp.
7. **T6 Alta** — testes (RBAC, IA, frontend, contratos).
8. **T7 Alta** — backup e resiliência.
9. **T8 Alta** — legado (Postgres) e métricas de produto.
10. **T9 Média** — qualidade, robustez e segurança secundária.
11. **T10 Baixa** — limpeza, docs e acabamento.

Gaps que são a mesma raiz aparecem juntos; o duplicado (outra view do mesmo gap)
é marcado `(= gap)`. Os tiers são critério de impacto e podem não coincidir com o
rótulo de severidade da spec (nas specs: 42 Alta/Bloqueante, 40 Média, 15 Baixa).

## Ordem de importância (1–97)

### T0 — Bloqueante (1)
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 1 | 11-1 | Gate de contrato: Swagger/OpenAPI, Postman ou exemplos reais da API de chamados Emsoft não obtidos | Único item que destrava as Fases 5/6/7 (rollout); depende da equipe Emsoft — iniciar o pedido logo |

### T1 — Pilha prod (4) — todos corrigidos em 2026-11-10
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 2 | 09-1 (CORRIGIDO) | Appwrite (store primária) ausente da pilha prod; backend aponta para `127.0.0.1:8020` | Prod não tem datastore funcional — tudo o mais depende disso |
| 3 | 09-4 (CORRIGIDO) | Pilha do Appwrite em rede isolada; backend prod não a alcança | Mesma raiz de 09-1: sem rede, o store é inalcançável |
| 4 | 09-2 (CORRIGIDO) | Bloco de env do backend prod incompleto (`SECRET_KEY`, `APPWRITE_*`, `WEBHOOK_SECRET`, `QDRANT_URL`, `OLLAMA_*`, `CORS_ORIGINS`) | Sem env o backend não sobe em prod |
| 5 | 09-15 (CORRIGIDO) | Sem serviço de LLM (Ollama) na pilha prod nem `OLLAMA_URL` | Prod não roda IA sem LLM |

### T2 — Integridade de dados e segurança (8)
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 6 | 01-2 (CORRIGIDO) | `PATCH /webhooks/chat/status` não valida `STATUS_TRANSITIONS` — atualiza direto, inclusive saindo de `ENCERRADO` | Máquina de estados violada por ator externo → corrupção de chats |
| 7 | 03-3 (CORRIGIDO) | `PATCH /webhooks/chat/status` ignora `STATUS_TRANSITIONS` | Mesma raiz de 01-2 (view do contrato da API) |
| 8 | 04-7 (CORRIGIDO) | `WEBHOOK_SECRET` ainda força status de qualquer chat (pulando a máquina de estados) e cria diagnóstico | Ator externo contorna máquina e permissões |
| 9 | 08-1 | `CORS_ORIGINS` default só `localhost:3000` | Origem de prod bloqueada em produção; config aberta vira risco |
| 10 | 03-10 | `/auth/refresh` e `PATCH /auth/password` existem e não são chamados pelo frontend | Fluxo de renovação de sessão inexistente na prática |
| 11 | 07-2 | Sem refresh token/renovação; sessão cai após 60 min | Mesma raiz de 03-10 (view do frontend) |
| 12 | 03-14 | Webhook padrão da Evolution aponta para URL hardcoded `/webhook/emsoft-whatsapp` | Instância mal configurada envia dados para alvo errado em prod |
| 13 | 02-10 | Bootstrap aditivo não propaga mudança de enum; health degradado não implementado | Drift de schema silencioso quebra validações da máquina de estados |

### T3 — Integração Emsoft e escopo (7)
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 14 | 03-19 | Endpoints-alvo inexistentes: `/departamentos*`, `transferir-departamento`, `atribuir-atendente`, `/roteamento`, `/ai/classificar-intencao`, `/integracoes/chamados/*` | Superfície de API das Fases 4/5 inexistente |
| 15 | 02-17 | Coleções `departamentos`, `regras_roteamento`, `integracao_chamados` e `integration_outbox` inexistentes | Sem persistência para departamentos, roteamento e integração |
| 16 | 08-11 | Timeout/retry/backoff explícitos de integrações externas não implementados | Toda chamada externa (Evolution/Emsoft) é frágil |
| 17 | 08-10 | Degradação da integração Emsoft/outbox não implementada | Falha na integração derruba o fluxo sem fallback |
| 18 | 09-17 | Sem variáveis `EMSOFT_CHAMADOS_*` nem serviço de worker de integração | Integração não sobe em prod |
| 19 | 00-14 | Integração com a API interna de chamados Emsoft não existe | Escopo de produto (SPEC 00) ainda ausente |
| 20 | 00-15 | Sem outbox/idempotência para chamados externos | Chamadas externas duplicadas/sem garantia |

### T4 — Frontend Fase 4 e painéis (3)
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 21 | 07-9 | Sem telas de departamento, fila por departamento e transferência por departamento | Fase 4 não existe no painel |
| 22 | 07-10 | Sem painel de diagnóstico de intenção/roteamento nem status de sincronização do chamado | Operador não vê decisão da IA nem estado do chamado |
| 23 | 00-13 | Departamentos, roteamento e pedido explícito por humano/setor não existem | Mesma raiz de 07-9/03-19 (view do produto) |

### T5 — Mídia (2)
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 24 | 00-12 | Mídia no WhatsApp: backend e workflow extraem `extendedText`/caption, mas a mídia não é armazenada | Formatos não-texto chegam em vazio na conversa |
| 25 | 06-17 | Mídia não é preservada (URL/arquivo); apenas caption é extraída | Mesma raiz de 00-12 (view n8n/transporte) |

### T6 — Testes (9)
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 26 | 04-4 | Regra "supervisor só cria `atendente`" está no serviço e sem teste | Regra de RBAC sem proteção de regressão |
| 27 | 04-5 | Regra "só admin altera `perfil`" está no serviço e sem teste | Idem — RBAC sem teste |
| 28 | 04-6 | `pegar`/`transferir`/`transferir_grupo`/`assinar`/`definir_prioridade`/`listar` sem teste | Ações principais do `ChatService` descobertas |
| 29 | 14-1 | `ai/router.py`, `ai_cache.py`, `ollama_service.py` e `openai_service.py` sem teste unitário direto | Caminho crítico da IA sem teste |
| 30 | 05-20 | Sem teste unitário direto de `ai/router.py`, `ai_cache.py` e clients | Mesma raiz de 14-1 (view do pipeline) |
| 31 | 14-3 | `qdrant_service.py` sem teste unitário: `search_similar`/`upsert`/`ensure_collection`, dimensão 768 | Fundação do RAG sem teste |
| 32 | 14-10 | Sem teste que garanta a dimensão de embedding (768 vs 1536) | Bloqueio OpenAI (ADR-0005) não é travado por teste |
| 33 | 14-12 | Sem contract tests do adapter Emsoft e do ciclo outbox/reprocessamento | Integração (Fases 5/6) sem porta de regressão |
| 34 | 14-6 | Frontend sem infraestrutura de teste (sem Vitest/Playwright) | Código da Fase 4 entraria sem teste |

### T7 — Backup e resiliência (4)
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 35 | 00-7 | Backup cobre só Postgres/Supabase; MinIO órfão e backup do Qdrant nunca dispara em prod | Perda de vetores/bancos sem restore |
| 36 | 09-6 | Sem backup de Appwrite/n8n/evolution-db; bloco Supabase remanescente | Store primário sem backup |
| 37 | 09-5 | Backup Qdrant usa bind mount divergente do volume named de prod | Backup aponta para dados errados |
| 38 | 09-7 | `backup.sh` não é agendado | Backup simplesmente não roda |

### T8 — Legado e métricas de produto (4)
| # | Gap | Descrição | Justificativa |
|---|-----|-----------|---------------|
| 39 | 02-11 | `backend/alembic/`, `app/models/*.py` (ORM) e `scripts/migrate.sh` apontam para PostgreSQL, que não é a fonte atual | Caminho de migração legado pode causar operações erradas |
| 40 | 02-14 | `scripts/seed_qdrant.py` lê do PostgreSQL e usa id inteiro como ponto Qdrant | Seed quebrado contra a fonte real (Appwrite) |
| 41 | 08-9 | Métricas de produto (resolução confirmada, transbordo, roteamento, duplicidade) sem instrumentação | Produto não é mensurável |
| 42 | 00-10 | `tempo_medio_resposta` mede intervalo entre mensagens do mesmo atendente | Mesma raiz de 08-9 (view do escopo) |

### T9 — Média (40)
| # | Gap | Descrição |
|---|-----|-----------|
| 43 | 04-3 | Frontend oculta ações por perfil, mas sem guarda de rota: digitando URL alcança `/usuarios` e `/configuracoes` |
| 44 | 07-11 | Sem guarda de rota por perfil (= 04-3) |
| 45 | 03-8 | Rotas que alteram chat não emitem evento WebSocket (`status`, `pegar`, `transferir`, `assinar`, `prioridade`, kanban `mover`) |
| 46 | 01-8 | Sem tabela de auditoria: não há como saber quem mudou status/atribuição |
| 47 | 02-20 | Sem trilha de auditoria de atribuição/transferência (= 01-8) |
| 48 | 04-12 | Sem auditoria de atribuição/transferência (ator, motivo, antes/depois) (= 01-8) |
| 49 | 10-12 | Sem auditoria de transferência/atribuição (= 01-8) |
| 50 | 04-11 | Identidade de serviço da IA / `actor_type` auditável não implementada |
| 51 | 07-3 | WebSocket sem reconexão nem backoff |
| 52 | 03-13 | `EvolutionService.criar_instancia` engole 403 e devolve resposta fabricada sem QR |
| 53 | 04-8 | `criar_instancia` engole 403 e devolve sucesso sem QR (= 03-13) |
| 54 | 02-6 | `url_arquivo` existe em `mensagens`/`knowledge_bases` sem upload/download/storage |
| 55 | 02-3 | `TipoMensagem` sem `sticker`/`local`; webhook mapeia sticker→imagem sem espelhar o enum |
| 56 | 01-3 | Urgência da IA (`critica`) só no prompt, sem coluna |
| 57 | 01-5 | `chats.loja_id` nunca é populado |
| 58 | 02-5 | `chats.loja_id` nunca é populado (= 01-5) |
| 59 | 08-3 | `/health` não checa dependências; sem readiness |
| 60 | 08-12 | Health check degradado do bootstrap (= 08-3) |
| 61 | 03-18 | `/webhooks/chat/diagnostico` sem chamador |
| 62 | 06-18 | `onError: continue` silencia falhas sem retry/registro estruturado |
| 63 | 03-7 | 502 devolve `str(e)` do `httpx`, expondo URL/corpo da Evolution |
| 64 | 08-5 | Sem logging estruturado nem request-id/correlação |
| 65 | 08-6 | Sem métricas/tracing/APM; nenhum SLO observável |
| 66 | 12-7 | Sem painel de pendência/reprocessamento para operador |
| 67 | 14-7 | n8n sem harness de teste; JSON ativo sem validação automatizada de nós/env |
| 68 | 14-8 | Sem testes de integração reais (Appwrite/Qdrant/Evolution/Emsoft); tudo em fakes |
| 69 | 14-9 | CI sem threshold de cobertura; regressões em IA não bloqueiam merge |
| 70 | 09-14 | CI: mypy e lint do frontend report-only; sem job de teste do frontend |
| 71 | 09-8 | Senha do Postgres em claro no compose/string da Evolution |
| 72 | 05-14 | Drift de modelo: `config.py` `llama3.2` vs `infra/.env.example` `deepseek-v4-flash:cloud` |
| 73 | 09-10 | Drift de modelo Ollama (= 05-14) |
| 74 | 05-15 | `AICache` engole toda exceção em `get`/`set`/`clear`; `clear()` nunca é chamado |
| 75 | 09-12 | Alembic/Postgres híbrido com runtime em Appwrite |
| 76 | 09-18 | Sem runbook de rollout/rollback da integração Emsoft |
| 77 | 03-11 | `POST /chats/enviar-whatsapp` tem lógica de negócio dentro da rota |
| 78 | 07-4 | Cores raw do Tailwind fora dos tokens `@theme` |
| 79 | 00-11 | Sem CSAT/NPS nem coleta de feedback |
| 80 | 00-16 | Indicadores de sucesso por departamento/duplicidade sem instrumentação |
| 81 | 02-16 | Sem foreign key: `chats.cliente_id` pode apontar para cliente inexistente |
| 82 | 03-15 | Nome da instância `"emsoft-support"` hardcoded em mensagens/evolution |

### T10 — Baixa (15)
| # | Gap | Descrição |
|---|-----|-----------|
| 83 | 02-9 | `tags` e `chat_tags` órfãs (sem repositório/rota/serviço) |
| 84 | 03-9 | `POST /chats/{id}/assinar` existe sem chamador no frontend |
| 85 | 03-12 | `GET /atendentes/ativos` tem a lógica dentro da rota |
| 86 | 03-17 | `GET /settings/ia-name` é público e não requer autenticação |
| 87 | 04-9 | `GET /atendentes/ativos` retorna id/nome/perfil/setor de todos os ativos para qualquer autenticado |
| 88 | 05-19 | Dependência `openai` declarada e nunca importada |
| 89 | 07-5 | `chat-store` não é usado; estado local duplica a fonte |
| 90 | 07-6 | Selects de status/prioridade usam `<select>` nativo |
| 91 | 08-7 | `DATABASE_URL` default com credenciais em claro |
| 92 | 09-3 | MinIO órfão no compose prod sem referência no código |
| 93 | 09-9 | Drift Python: pyproject/ruff/mypy/CI em 3.11 vs `Dockerfile` 3.12-slim |
| 94 | 09-16 | `start-prod.sh`: `sleep 5` em vez de aguardar healthcheck; roda Alembic |
| 95 | 01-1 | `.ai/` mantém docs com vocabulário/estados divergentes (stack antiga) |
| 96 | 00-5 | Docs citavam stack NestJS/TypeScript/Prisma |
| 97 | 00-6 | Docs citavam workflow de 19 nós |

## Nota

- Fases pendentes (SPEC 13) mapeadas: Fase 4 → T4/T3 · Fase 5 → T3 (gate: 11-1) ·
  Fases 6/7 → T0.
- Ao corrigir cada gap, atualizar este arquivo e o `checklist-implementacoes.md`.

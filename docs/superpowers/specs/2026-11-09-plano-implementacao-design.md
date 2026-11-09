# Plano de Implementação — Design Aprovado

> **Data:** 2026-11-09
> **Origem:** specs 00–14 (pacote v2) + Registros de Gaps reconstruídos em 2026-11-06
> **Status:** aprovado pelo responsável técnico em 2026-11-09

Este documento registra as **decisões de estrutura** do plano de implementação. Ele não
contém tasks: as tasks ficam em `docs/superpowers/plans/2026-11-09-ia-support-platform/`.

---

## 1. Objetivo

Transformar os **149 gaps ABERTO** dos Registros de Gaps em software funcionando, sem
quebrar os contratos existentes (specs 00–14) e sem inventar o contrato da API interna de
chamados da Emsoft.

## 2. Estado atual (verificado em 2026-11-06)

| Spec | Abertos | Corrigidos | Observação |
|---|---:|---:|---|
| 00-escopo | 10 | 6 | Pipeline de IA conectado; métricas de produto erradas |
| 01-domain-glossary | 11 | 0 | Webhook ignora `STATUS_TRANSITIONS`; sem departamento |
| 02-data-model | 17 | 3 | Faltam 4 coleções novas e `departamento_id` |
| 03-api-contract | 16 | 3 | Endpoints-alvo inexistentes; PII em query param |
| 04-rbac-matrix | 12 | 0 | Sem escopo por departamento; sem auditoria |
| 05-ai-pipeline | 13 | 11 | Falta classificação de intenção e roteamento |
| 06-n8n-workflow | 2 | 16 | Praticamente resolvido |
| 07-frontend | 8 | 3 | Sem telas de departamento; tokens violados |
| 08-non-functional | 9 | 3 | Sem logging estruturado, métricas ou readiness |
| 09-infra-deploy | 16 | 2 | Pilha prod não sobe (Appwrite/Ollama ausentes) |
| 10-departamentos-e-roteamento | 12 | 0 | Nada implementado |
| 11-integracao-api-emsoft | 7 | 0 | Bloqueada por falta de contrato |
| 12-confiabilidade-integracoes | 7 | 0 | Nada implementado |
| 14-test-strategy | 9 | 3 | Sem testes de frontend, n8n ou integração |

**Premissa crítica:** o backend roda em modo dev; o compose de produção não sobe porque
Appwrite e Ollama não estão nele (09-1, 09-2, 09-15). Isso **não** bloqueia o
desenvolvimento, mas bloqueia rollout.

## 3. Abordagem escolhida

**Caminho crítico + prontidão mínima.** O produto avança sequencialmente (Fases 1→4) e a
prontidão operacional entra em paralelo, fatiada em três blocos posicionados por
dependência real — não "tudo no fim" nem "tudo no começo".

Abordagens descartadas:

- **Prontidão primeiro** — endurecer um sistema que ainda não tem a feature a medir; adia o
  único trabalho com valor visível.
- **Vertical por departamento piloto** — as `regras_roteamento` são transversais; o piloto
  vira o sistema completo com um departamento a menos.

## 4. Roadmap, gates e documentos

### 4.1 Fases

| Fase | Entrega | Estado | Gate de entrada |
|---|---|---|---|
| 0 | Auditoria + baseline | **Concluída** (Registros de Gaps, 2026-11-06) + 1 task de baseline de testes | — |
| 1 | Departamentos + migração `setor`/`setor_alvo` | Detalhada | — |
| 2 | Classificação de intenção + roteamento | Detalhada | **G1** Fase 1 |
| 3 | Diagnóstico + ciclo de resolução | Detalhada | **G2** Fase 2 |
| 4 | Frontend operacional | Detalhada | **G3** Fase 3 |
| 5 | Integração Emsoft em modo mock | Roadmap | **G5** contrato OpenAPI/Postman (gap 11-1) |
| 6 | Homologação externa | Roadmap | Fase 5 + usuário IA criado |
| 7 | Rollout | Roadmap | Fase 6 + **R0** concluída |

### 4.2 Gates

| Gate | Condição |
|---|---|
| G1 | `departamentos` + `regras_roteamento` + `departamento_id` criados; migração de `setor`/`setor_alvo` executada e testada |
| G2 | DTO de intenção, classificador e resolver determinístico com casos classificados cobertos |
| G3 | Cenários A/B/C e reabertura testados |
| G4 | Fases 1–4 + R0 + R1 concluídas ⇒ plataforma declarada pronta |
| G5 | Contrato da API Emsoft confirmado (Swagger/OpenAPI, Postman, documentação ou exemplos reais sanitizados) |
| G6 | Homologação aprovada pelo responsável da API + R0 (compose prod funcional) |

### 4.3 Trilha R (prontidão)

| Bloco | Conteúdo | Pronto quando |
|---|---|---|
| **R0** | Appwrite + Ollama no compose prod, rede, bloco de env completo, `SECRET_KEY`/`WEBHOOK_SECRET` obrigatórios, CORS restrito, `/health/ready` | Antes de **qualquer** rollout |
| **R1** | Logging estruturado + correlation id, métricas de produto com semântica correta, health degradado do bootstrap | Antes da **Fase 4** — é o que permite medir a meta de 70% |
| **R2** | CI com threshold e lint bloqueante, testes de frontend, backup agendado do Appwrite, remoção do drift Alembic/Postgres | Duração |

### 4.4 Ordem canônica de execução

```
F0.1 → F1 → F2 → F3 → R1 → F4 → R2
            ↘ R0 (paralelo, a partir de F1)
                  → F5* → F6* → F7   (*bloqueadas por G5)
```

### 4.5 Documentos do plano

`docs/superpowers/plans/2026-11-09-ia-support-platform/`

| Arquivo | Conteúdo |
|---|---|
| `README.md` | Plano mestre: objetivo, arquitetura, stack, constraints globais, roadmap, gates, ordem canônica, índice dos docs |
| `fase-1-departamentos.md` | Schema, repositories, services, rotas, seed, migração de setor legado |
| `fase-2-classificacao-roteamento.md` | DTO de intenção, classificador, resolver determinístico, transferência/atribuição por ID |
| `fase-3-diagnostico.md` | Persistência do diagnóstico, RAG por categoria, confirmação e reabertura |
| `fase-4-frontend.md` | Telas de departamento, fila por departamento, painel de diagnóstico |
| `trilha-r-prontidao.md` | R0, R1, R2 |

## 5. Mapa de arquivos e interfaces

### Fase 1

| Arquivo | ação | Responsabilidade |
|---|---|---|
| `backend/app/models/departamento.py` | criar | Enums `Intencao` (9 códigos) e `CategoriaERP` (5 módulos) |
| `backend/app/appwrite/schema.py` | modificar | Coleções `departamentos` + `regras_roteamento`; `departamento_id` em `atendentes`/`chats` |
| `backend/app/appwrite/repositories/departamento.py` | criar | `DepartamentoRepository`, `RegraRoteamentoRepository` |
| `backend/app/appwrite/repositories/__init__.py` | modificar | Registrar os repositories novos |
| `backend/app/services/departamento_service.py` | criar | CRUD, unicidade de `codigo` por check-then-insert, consulta de regras por prioridade |
| `backend/app/api/routes/departamentos.py` | criar | CRUD `/departamentos` + `/departamentos/{id}/atendentes` |
| `backend/app/schemas/departamento.py` | criar | DTOs Pydantic |
| `scripts/seed_departamentos.py` | criar | Seed idempotente |
| `scripts/migrate_setor_departamento.py` | criar | 7 passos da spec 02 §Migração de setor legado + relatório de órfãos |

```python
class DepartamentoRepository(BaseRepository):
    async def get_by_codigo(self, codigo: str) -> dict | None
    async def list_ativos(self) -> list[dict]

class RegraRoteamentoRepository(BaseRepository):
    async def list_ativas_ordenadas(self) -> list[dict]   # prioridade_regra ASC
```

### Fase 2

| Arquivo | ação | Responsabilidade |
|---|---|---|
| `backend/app/schemas/ai.py` | criar | `ClassificacaoIntencao` — 8 campos do JSON da spec 05 |
| `backend/app/ai/prompts.py` | modificar | `INTENT_SYSTEM` |
| `backend/app/ai/intent_classifier.py` | criar | `IntentClassifier.classificar(historico) -> ClassificacaoIntencao` |
| `backend/app/services/routing_service.py` | criar | `RoutingService.resolver(classificacao) -> ResultadoRoteamento` |
| `backend/app/schemas/routing.py` | criar | `ResultadoRoteamento` |
| `backend/app/api/routes/roteamento.py` | criar | `GET /chats/{id}/roteamento`, `PATCH /chats/{id}/transferir-departamento`, `PATCH /chats/{id}/atribuir-atendente` |
| `backend/app/ai/router.py` | modificar | `POST /ai/classificar-intencao` |
| `backend/app/core/config.py` | modificar | `ai_intent_confidence_threshold=0.80`, `routing_max_clarification_attempts=2`, `routing_fallback_departamento_codigo="atendimento_geral"` |

### Fase 3

| Arquivo | ação | Responsabilidade |
|---|---|---|
| `backend/app/appwrite/schema.py` | modificar | `ia_diagnosticos` += `intencao`, `subintencao`, `categoria_erp`, `departamento_id`, `motivo`, `artigos_consultados` |
| `backend/app/services/ai_pipeline.py` | modificar | Snapshot do diagnóstico; RAG filtrado por categoria; IDs/scores dos artigos; Cenário B/C roteiam ao departamento |
| `backend/app/services/chat_service.py` | modificar | `confirmar_resolucao`, `reabrir` |
| `backend/app/schemas/webhook.py` | modificar | `WebhookSolucaoResponse` com diagnóstico e destino |

### Fase 4

| Arquivo | ação | Responsabilidade |
|---|---|---|
| `frontend/src/app/(app)/departamentos/page.tsx` | criar | CRUD de departamentos e regras |
| `frontend/src/app/(app)/atendimento/page.tsx` | modificar | Fila por departamento, assumir (409 em conflito), transferir por ID, painel de intenção/diagnóstico, status de sincronização |
| `frontend/src/app/(app)/kanban/page.tsx` | modificar | Filtro por departamento |
| `frontend/src/lib/stores/chat-store.ts` | modificar | Fonte única de `chatAtivo` |
| `frontend/src/lib/api.ts` | modificar | Endpoints novos |

### Trilha R

| Bloco | Arquivos | Gaps fechados |
|---|---|---|
| R0 | `infra/docker-compose.prod.yml`, `core/config.py`, `main.py` | 09-1, 09-2, 09-4, 09-15, 08-3, 08-1 |
| R1 | `backend/app/core/logging.py`, middleware de correlation id, `services/metricas_service.py`, `dashboard_service.py` | 08-5, 08-6, 08-9, 00-10, 12-6 |
| R2 | `.github/workflows/ci.yml`, `frontend/package.json`, `scripts/backup.sh` + agendamento, remoção do Alembic/Postgres | 09-14, 09-5, 09-6, 09-7, 09-12, 02-11, 14-6, 14-9 |

## 6. Decisões de modelagem (aprovadas)

1. **`outro` deixa de ser categoria de base de conhecimento.** O classificador devolve
   `categoria_erp=null`; `multiempresa` **entra** no enum de conhecimento. Fecha 02-1 e
   05-17 sem criar categoria inútil.
2. **`atendimento_geral` é departamento de seed e destino de fallback** — é o "encaminhar
   para triagem geral" das specs 05/10.
3. **`POST /ai/classificar-intencao` é read-only**: classifica, não transfere (spec 03).
4. **Rotas de roteamento em arquivo novo** (`api/routes/roteamento.py`), para não inflar
   `api/routes/chats.py`.
5. **Resolução de conflito de regra é determinística e explícita**: empate de prioridade
   com destinos diferentes ⇒ conflito registrado e triagem/esclarecimento, nunca escolha
   arbitrária.
6. **Fases 5–7 não recebem task** enquanto o contrato não chegar (gap 11-1). Adapter,
   mapper e contract tests serão desenhados quando o contrato existir, para não cristalizar
   payload presumido.

## 7. Convenções de execução

| Regra | Detalhe |
|---|---|
| TDD sem exceção | Teste antes do código; nenhuma task "implementa e depois testa" |
| Verificação real | `pytest tests/...::test_x -v` → `pytest tests/ -q` + `ruff check app tests` → `npm run build` (frontend). Sem `|| true` |
| Um commit por task | Conventional Commits pt-BR: `feat(...)`, `fix(...)`, `test(...)`, `docs(specs): ...` |
| Gaps atualizados na mesma task | `ABERTO` → `CORRIGIDO` com evidência. Única alteração de spec permitida na execução |
| Rastreio gap→task | Cada doc de fase abre com tabela `gap | task | arquivo` |
| Fora de escopo proibido | Nada de API Emsoft real, segredo em código/log, refactor não relacionado, mudança de arquitetura fora das specs 00–14 |
| Compatibilidade de migração | `setor`/`setor_alvo` **não** são apagados na Fase 1; `transferir-grupo` vira alias, sem novos usos de string `setor` |
| Tasks isoladas | Cada task é executável sem estado de sessão; vê apenas o bloco `Interfaces` da própria task |

## 8. Riscos

| Risco | Mitigação no plano |
|---|---|
| Contrato da API Emsoft não chega | Fases 5–7 ficam no roadmap; o produto não depende delas para a meta de 70% |
| Migração de `setor` perde chats | Script de migração com relatório de órfãos + teste de migração; legados preservados |
| Roteamento vira caixa-preta do LLM | Resolver determinístico; LLM só sugere; conflito nunca arbitrado |
| Métrica de 70% não confiável | R1 antes da Fase 4; `tempo_medio_resposta` corrigido |
| Escopo cresce durante a execução | Registro de Gaps é a fonte; task fora dele exige atualização de spec antes |

## 9. Referências

- Fonte de verdade: `docs/specs/00` a `docs/specs/14` e `docs/specs/adr/0004`–`0007`
- Registros de Gaps: seção `## Registro de Gaps` de cada spec
- Plano de fases canônico: `docs/specs/13-plano-implementacao.md`
- Prompt de execução: `IMPLEMENTATION-PROMPT.md`

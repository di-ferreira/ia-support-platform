# Plano de Implementação — IA Support Platform (Fases 1–4 + Trilha R)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar os gaps ABERTO das specs 00–14 em software funcionando — departamentos, classificação de intenção, roteamento determinístico, ciclo de diagnóstico e frontend operacional — sem quebrar os contratos existentes e sem inventar o contrato da API Emsoft.

**Architecture:** Backend FastAPI sobre Appwrite (coleções declarativas em `app/appwrite/schema.py`, repositórios finos sobre `BaseRepository`, agregado `Repositories` como única superfície de dados dos services). O LLM apenas sugere (intenção/categoria); a decisão de roteamento é determinística em `RoutingService`. Frontend Next.js 15 + React Query + Zustand. A prontidão operacional (Trilha R) corre em paralelo, fatiada por dependência real.

**Tech Stack:** Python 3.11 hoje (runtime Docker em 3.12; a Task R2.1 unifica tudo em 3.12) + FastAPI + Pydantic v2 + Appwrite (SDK Python) + Qdrant + Ollama/OpenAI; Next.js 15 + Tailwind 4 + React Query 5 + Zustand 5; pytest + pytest-asyncio + httpx (fakes, sem banco real); Vitest + jsdom + Testing Library (harness criado na task F4.1; CI bloqueante na R2.2/R2.3).

**Spec:** `docs/superpowers/specs/2026-11-09-plano-implementacao-design.md` (decisões aprovadas) — fonte de verdade do domínio: `docs/specs/00` a `docs/specs/14`, com Registros de Gaps por spec. Plano canônico de fases: `docs/specs/13-plano-implementacao.md`.

---

## Global Constraints

Estas regras valem para **toda task de todos os documentos**. Cada task as inclui implicitamente.

| # | Regra |
|---|---|
| C1 | **TDD sem exceção**: o teste vem antes do código. Nenhuma task "implementa e depois testa". |
| C2 | **Verificação real**: `pytest tests/...::test_x -v` (confirmar a falha esperada), depois `pytest tests/ -q` + `ruff check app tests` antes de cada commit. Frontend: `npm run test` + `npm run build` (`npm run test` passa a existir a partir da F4.1; `npm run lint` continua report-only até a R2.3). Nunca `\|\| true` em verificação. |
| C3 | **Um commit por task**, Conventional Commits em pt-BR: `feat(departamentos): ...`, `fix(roteamento): ...`, `test(...): ...`, `docs(specs): fecha gap 10-5`. |
| C4 | **Gaps atualizados na mesma task**: se a task fecha um gap, a linha no Registro de Gaps da spec correspondente muda de `ABERTO` para `**CORRIGIDO** — <evidência file:símbolo>`. Esta é a **única** alteração de spec permitida durante a execução. |
| C5 | **Contrato Emsoft intocado**: nenhuma chamada real à API de chamados; `EMSOFT_CHAMADOS_ENABLED` permanece `false`; Fases 5–7 não têm task (gap 11-1 bloqueia). |
| C6 | **Compatibilidade de migração**: `atendentes.setor` e `chats.setor_alvo` **não são apagados** nas Fases 1–4 (spec 02, passo 7); `transferir-grupo` continua como alias, sem aceitar novos usos de string `setor` livre. |
| C7 | **Máquina de estados sagrada**: toda mudança de status de chat passa por `ChatService.atualizar_status` e valida `STATUS_TRANSITIONS`. |
| C8 | **Roteamento determinístico**: o LLM sugere; o backend resolve por `regras_roteamento` com prioridade explícita. Empate de prioridade com destinos diferentes = conflito declarado, nunca escolha arbitrária. Nunca usar nome de departamento em texto livre como destino. |
| C9 | **Segredo nenhum em código/log**; `validate_production_secrets` continua obrigatório em produção. |
| C10 | **Escopo fechado**: nada de refactor não relacionado; nenhum arquivo fora do mapa da task; mudança de arquitetura exige atualização de spec antes. |
| C11 | **Idioma**: código, comentários, mensagens de commit e mensagens de usuário em pt-BR (nomes de identificadores em português, como o código existente). |
| C12 | **Fakes, não banco real**: testes usam `FakeStore`/`FakeRepositories` de `backend/tests/conftest.py`; nenhuma task exige Appwrite/Qdrant/Ollama rodando. |

---

## Roadmap 0–7 e estado

| Fase | Entrega | Estado no plano | Gate de entrada | Doc |
|---|---|---|---|---|
| 0 | Auditoria + baseline | **Concluída** (Registros de Gaps reconstruídos em 2026-11-06) + 1 task de baseline de testes | — | `fase-1-departamentos.md` (Task F0.1) |
| 1 | Departamentos + migração `setor`/`setor_alvo` | Detalhada (10 tasks) | — | `fase-1-departamentos.md` |
| 2 | Classificação de intenção + roteamento | Detalhada (10 tasks) | **G1** = Fase 1 concluída | `fase-2-classificacao-roteamento.md` |
| 3 | Diagnóstico + ciclo de resolução | Detalhada (5 tasks) | **G2** = Fase 2 concluída | `fase-3-diagnostico.md` |
| 4 | Frontend operacional | Detalhada (13 tasks) | **G3** = Fase 3 concluída | `fase-4-frontend.md` |
| 5 | Integração Emsoft em modo mock | **Roadmap, sem task** | **G5** = contrato OpenAPI/Postman/exemplos (gap 11-1) | — |
| 6 | Homologação externa | **Roadmap, sem task** | Fase 5 + usuário IA criado | — |
| 7 | Rollout | **Roadmap, sem task** | Fase 6 + **R0** concluída | — |

**G4** (plataforma declarada pronta) = Fases 1–4 + R0 + R1 concluídas.
**G6** (fim de homologação) = aprovação do responsável da API + R0.

Fases 5–7 ficam deliberadamente sem task: enquanto o gap 11-1 persistir (o endpoint `https://emsoft.ddns.net/portal-api/v1/chamados` respondeu 502 e não há OpenAPI/Postman), desenhar adapter/mapper/contract tests cristalizaria payload presumido.

## Trilha R — prontidão (paralela)

| Bloco | Conteúdo | Quando precisa estar pronto | Doc |
|---|---|---|---|
| **R0** (5 tasks) | Appwrite + Ollama no compose prod, rede, env completo, `/health/ready`, `start-prod.sh` com healthcheck | Antes de **qualquer** rollout (gate da Fase 7) | `trilha-r-prontidao.md` |
| **R1** (4 tasks) | Logging estruturado + correlation id, `tempo_medio_resposta` corrigida, métricas de produto, health degradado do bootstrap | Antes da **Fase 4** — é o que permite medir a meta de 70% | `trilha-r-prontidao.md` |
| **R2** (6 tasks) | CI bloqueante com cobertura mínima (harness já existe desde F4.1), lint, backup agendado, fim do drift Alembic/Postgres, credenciais fora do compose | Duração (pós-entrega) | `trilha-r-prontidao.md` |

## Ordem canônica de execução

```
F0.1 → F1 → F2 → F3 → R1 → F4 → R2
            ↘ R0 (paralelo, a partir de F1)
                  → F5* → F6* → F7   (*bloqueadas por G5)
```

Um executor segue esta sequência de cima para baixo. Tasks dentro de uma fase são independentes entre si (cada uma tem teste, verificação e commit próprios), mas **respeitam a ordem numérica** quando compartilham arquivos (ex.: F1.2 cria as coleções que F1.3 usa).

## Documentos do plano

| Arquivo | Conteúdo | Tasks |
|---|---|---|
| `README.md` | Este documento — roadmap, gates, constraints globais | — |
| `fase-1-departamentos.md` | Enums, coleções, repositórios, service, rotas, seed, migração de setor, visibilidade | F0.1, F1.1–F1.10 |
| `fase-2-classificacao-roteamento.md` | DTO de intenção, classificador, resolver determinístico, transferência/atribuição por ID, regressão | F2.1–F2.10 |
| `fase-3-diagnostico.md` | Snapshot de diagnóstico, RAG por categoria, cenários B/C roteados, confirmação/reabertura | F3.1–F3.5 |
| `fase-4-frontend.md` | Tela de departamentos, fila, transferir por ID, painel de diagnóstico, tokens, guarda de rota | F4.1–F4.13 |
| `trilha-r-prontidao.md` | R0 rollout, R1 observabilidade/métricas, R2 duração | R0.1–R0.5, R1.1–R1.4, R2.1–R2.6 |

## Cobertura de gaps — resumo

| Doc | Gaps cobertos (fechados pelas tasks do doc) |
|---|---|
| `fase-1-departamentos.md` | 00-13 (parcial), 01-6, 01-7, 01-9, 02-1, 02-2, 02-4, 02-12, 02-15, 02-17, 02-18, 03-1, 03-2, 03-19 (parcial), 04-1, 04-2, 04-10, 05-17, 10-1…10-5, 10-9, 10-10 |
| `fase-2-classificacao-roteamento.md` | 01-6, 01-10, 03-4, 03-19 (parcial), 05-9, 05-10, 05-18, 05-21, 05-22, 05-24, 10-6, 10-7, 10-8, 10-11, 14-11 |
| `fase-3-diagnostico.md` | 00-8 (verificado), 01-4, 01-11, 02-19, 05-4, 05-21, 05-23, 10-7 (integração com pipeline) |
| `fase-4-frontend.md` | 01-4 (UI), 03-8, 03-10, 04-3, 05-4 (UI), 07-2, 07-3, 07-4, 07-5, 07-6, 07-9, 07-10, 07-11, 10-6 |
| `trilha-r-prontidao.md` | 00-7, 00-10, 00-16, 02-10 (parcial), 02-11, 02-14, 05-14, 05-19, 08-1, 08-3, 08-5, 08-7, 08-9, 08-12, 09-1…09-8, 09-10, 09-12, 09-14, 09-15, 09-16, 12-6, 14-6, 14-9 |

## Gaps fora do escopo detalhado (permanecem ABERTO no Registro)

Estes gaps não pertencem às Fases 1–4 nem à Trilha R; continuam no Registro de Gaps e entram em revisão de escopo futura (a maioria depende de Fases 5–7 ou de decisão de produto):

- **Bloqueados pelo contrato Emsoft (11-1):** 00-14, 00-15, 02-17 (coleções `integracao_chamados`/`integration_outbox`), 04-11, 08-10, 08-11, 09-17, 09-18, 10-12, 12-1…12-5, 12-7, 14-12.
- **Produto/mídia (decisão de escopo pendente):** 00-11 (CSAT/NPS), 00-12, 02-3, 02-5, 02-6, 02-9, 02-16, 06-11, 06-17.
- **Limpeza legada de baixo valor imediato:** 00-5, 00-6, 01-1, 03-9, 03-11, 03-12, 03-13, 03-14, 03-15, 03-17, 03-18, 04-8, 04-9, 05-15.
- **Testes de integração real / harness externo (14-8, 14-7, 14-10, 05-20):** exigem serviços reais ou contrato; a R2 cobre o que é possível em CI (14-6, 14-9).

## Convenções de execução (por task)

Formato de cada task (exemplo real de F1.7; os `...` são do template, não placeholders de task):

```
### Task F1.7: Migração de setor/setor_alvo para departamento_id

**Files:**
- Create: `scripts/migrate_setor_departamento.py`
- Test: `backend/tests/test_migracao_setor.py`

**Interfaces:**
- Consumes: `DepartamentoRepository.get_by_codigo(codigo) -> dict | None` (Task F1.3)
- Produces: `migrar(repos) -> RelatorioMigracao` (nenhum consumidor externo; script de operação)

- [ ] **Step 1: Write the failing test** (código do teste)
- [ ] **Step 2: Run test to verify it fails** — Run: `...` Expected: FAIL ...
- [ ] **Step 3: Write minimal implementation** (código)
- [ ] **Step 4: Run test to verify it passes** — Run: `...` Expected: PASS
- [ ] **Step 5: Suíte completa + ruff** — Run: `pytest tests/ -q && ruff check app tests`
- [ ] **Step 6: Commit** (mensagem)
- [ ] **Step 7: Atualizar Registro de Gaps** (linhas exatas a editar)
```

**Gates de fase:** antes de iniciar uma fase, conferir o gate de entrada (ex.: Fase 2 exige F1.2–F1.4 concluídas). Ao fechar uma fase, rodar a suíte completa e revisar a tabela de rastreio do doc — nenhum gap do escopo pode ter ficado sem linha de Registro atualizada.

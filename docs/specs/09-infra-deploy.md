# SPEC 09 — Infraestrutura, Configuração e Deploy

## Stack operacional existente

- Docker e Docker Compose.
- Appwrite self-hosted como persistência principal.
- Redis para cache/locks e suporte a filas.
- Qdrant para embeddings.
- n8n para transporte WhatsApp.
- Evolution API para WhatsApp.
- FastAPI backend e Next.js frontend.
- Traefik no ambiente de produção.
- Ollama como alvo local de LLM; OpenAI pode ser provider de chat, não de RAG/embedding conforme ADR 0005.

## Ambientes

Manter arquivos separados para desenvolvimento e produção, conforme `infra/docker-compose.dev.yml`, `infra/docker-compose.prod.yml` e `infra/appwrite/docker-compose.yml`. Não alterar portas existentes sem atualizar README, proxy e health checks.

## Configuração nova da integração Emsoft

Variáveis de configuração propostas:

```dotenv
EMSOFT_CHAMADOS_ENABLED=false
EMSOFT_CHAMADOS_BASE_URL=https://emsoft.ddns.net/portal-api/v1
EMSOFT_CHAMADOS_TIMEOUT_SECONDS=15
EMSOFT_CHAMADOS_MAX_RETRIES=5
EMSOFT_CHAMADOS_AI_USER_ID=
EMSOFT_CHAMADOS_DEFAULT_DEPARTMENT_CODE=suporte_tecnico
```

A URL base foi derivada do endpoint fornecido pelo proprietário (`/v1/chamados`). Confirmar prefixo e trailing slash com o contrato real.

**Não criar nomes de variáveis de autenticação definitivos até confirmar o mecanismo real.** Após receber Swagger/Postman/exemplo de autenticação, adicionar variáveis de segredo específicas ao `.env.example`, sem valores reais. Não assumir Bearer ou API Key.

`EMSOFT_CHAMADOS_ENABLED` permanece `false` por padrão em todos os ambientes até contrato, mapeamentos e testes de homologação estarem aprovados.

## Health checks

O backend deve expor estado sanitizado de:

- Appwrite;
- Redis;
- Qdrant;
- provider LLM;
- Evolution API (quando verificação suportada);
- worker/outbox;
- API Emsoft, somente quando integração habilitada.

Separar `liveness` (processo vivo) de `readiness` (dependências essenciais para aceitar tráfego). Indisponibilidade de Emsoft não deve tirar API de atendimento do ar; marcar integração degradada.

## Worker de integração

Executar worker/outbox em processo controlado. Pode ser processo separado no mesmo container ou serviço Compose dedicado; escolher após inspecionar estrutura de startup atual. Deve compartilhar apenas configuração necessária, ser reiniciável e não concorrer pelo mesmo evento sem lock.

## Migração Appwrite

1. Backup dos dados.
2. Criar coleções/atributos aditivos.
3. Popular departamentos com códigos estáveis.
4. Migrar `setor`/`setor_alvo` para IDs.
5. Validar documentos sem departamento e atendentes inativos.
6. Deploy do backend com dual-read temporário se necessário.
7. Deploy do frontend usando IDs.
8. Descontinuar leitura dos campos legados após verificação.

Não confiar apenas no bootstrap para atualizar enums/atributos existentes, pois o comportamento documentado é aditivo e não altera atributos já criados. Executar verificação explícita de schema.

## Segredos

- `APPWRITE_API_KEY`, `WEBHOOK_SECRET`, `EVOLUTION_API_KEY`, credenciais do LLM e futura credencial Emsoft ficam somente no ambiente seguro do servidor.
- `.env` não deve ser commitado.
- `.env.example` contém nomes e placeholders, nunca credenciais funcionais.
- N8N não recebe a credencial da API Emsoft.

## Deploy progressivo

1. Subir schema e dados de departamentos sem habilitar integração Emsoft.
2. Deploy backend com roteamento, mantendo fallback de triagem.
3. Deploy frontend de gestão/visualização.
4. Testar criação/atualização Emsoft em homologação com usuário técnico e atendente de teste.
5. Habilitar integração para grupo controlado.
6. Aumentar uso após métricas e tratamento de falhas validados.
7. Habilitar produção apenas com segredo, status, responsável, idempotência e rollback definidos.

## Rollback

Desabilitar `EMSOFT_CHAMADOS_ENABLED` interrompe novos envios, mas preserva outbox pendente. Não apagar `integracao_chamados` nem outbox. Ao reabilitar, reprocessar com a mesma idempotency key e reconciliar eventos ambíguos antes de criar novos tickets.

## Registro de Gaps

Verificado contra o código em 2026-11-06.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 09-1 | Appwrite (store primária) ausente da pilha prod; backend aponta para `127.0.0.1:8020` | `infra/docker-compose.prod.yml`; `core/config.py:13` | **Crítica** | **CORRIGIDO** (2026-11-10) — backend na rede compartilhada `appwrite`; `APPWRITE_ENDPOINT` default `http://appwrite:80/v1` |
| 09-2 | Bloco de env do backend prod incompleto (`SECRET_KEY`, `APPWRITE_*`, `WEBHOOK_SECRET`, `QDRANT_URL`, `OLLAMA_*`, `CORS_ORIGINS`) | `infra/docker-compose.prod.yml`; `core/config.py` | **Crítica** | **CORRIGIDO** (2026-11-10) — env block completo no compose prod (segredos, Appwrite, Qdrant, LLM, CORS) |
| 09-3 | MinIO órfão no compose prod sem referência no código | `infra/docker-compose.prod.yml` | Baixa | **ABERTO** |
| 09-4 | Pilha do Appwrite em rede isolada; backend prod não a alcança | `infra/appwrite/` vs `docker-compose.prod.yml` | **Alta** | **CORRIGIDO** (2026-11-10) — backend em `default` + `appwrite` (rede external fixa); pré-op: stack Appwrite subido ≥1× no host (a rede persiste no daemon) |
| 09-5 | Backup Qdrant usa bind mount divergente do volume named de prod | `scripts/backup.sh` | **Alta** | **CORRIGIDO** (2026-11-13) — snapshot via `tar` dentro do próprio container (`-C /qdrant storage`), sem bind mount |
| 09-6 | Sem backup de Appwrite/n8n/evolution-db; bloco Supabase remanescente | `scripts/backup.sh` | **Alta** | **CORRIGIDO** (2026-11-13) — backup cobre Appwrite (mariadb-dump), n8n, evolution-db, Qdrant e MinIO; retenção, verificação e manifesto; bloco Supabase removido |
| 09-7 | `backup.sh` não é agendado | `scripts/` | **Alta** | **CORRIGIDO** (2026-11-13) — `infra/systemd/emsoft-backup.{service,timer}` (diário 03:30, `Persistent=true`) + `scripts/install-backup-timer.sh` (modo user/system, idempotente); ciclo manual validado via `systemctl --user` |
| 09-8 | Senha do Postgres em claro no compose/string da Evolution | `infra/docker-compose.prod.yml` | Média | **ABERTO** |
| 09-9 | Drift Python: pyproject/ruff/mypy/CI em 3.11 vs `Dockerfile` `3.12-slim` | `pyproject.toml`; `backend/Dockerfile`; `ci.yml` | Baixa | **CORRIGIDO** — backend/.python-version (3.12), pyproject ruff/mypy em py312/3.12, CI em 3.12, Dockerfile em 3.12-slim |
| 09-10 | Drift de modelo Ollama: `config.py` `llama3.2` vs `infra/.env.example` `deepseek-v4-flash:cloud` | `core/config.py:31`; `infra/.env.example:26` | Média | **ABERTO** → 05-14 |
| 09-11 | `infra/.env.prod` não era gitignored | `.gitignore` | **Alta** | **CORRIGIDO** — `infra/.env*` (exceto `.env.example`) ignorado |
| 09-12 | Alembic/Postgres híbrido com runtime em Appwrite | `alembic/env.py`; `seed_qdrant.py` | Média | **ABERTO** → 02-14 |
| 09-13 | Env do n8n (`BACKEND_URL`/`EVOLUTION_INSTANCE`/`N8N_BLOCK_ENV_ACCESS_IN_NODE`) ausente de compose/.env | `infra/docker-compose.*.yml` | **Alta** | **CORRIGIDO** |
| 09-14 | CI: mypy e lint do frontend report-only; sem job de teste do frontend | `.github/workflows/ci.yml` | Média | **CORRIGIDO** — mypy e lint do frontend bloqueantes; testes do frontend (`npm run test`) antes do build; `pytest --cov-fail-under=86` → [14](14-test-strategy.md) |
| 09-15 | Sem serviço de LLM (Ollama) na pilha prod nem `OLLAMA_URL` | `infra/docker-compose.prod.yml`; `core/config.py:30` | **Crítica** | **CORRIGIDO** (2026-11-10) — serviço `ollama` na pilha; `OLLAMA_BASE_URL` default `http://ollama:11434` (pull dos modelos via `exec ollama`) |
| 09-16 | `start-prod.sh`: `sleep 5` em vez de aguardar healthcheck; roda Alembic | `scripts/start-prod.sh` | Baixa | **ABERTO** |
| 09-17 | Sem variáveis `EMSOFT_CHAMADOS_*` nem serviço de worker de integração | `core/config.py`; `infra/` | **Alta** | **ABERTO (parcial)** — variáveis `EMSOFT_CHAMADOS_*` criadas (`core/config.py`, scaffold 11-1); serviço de worker de integração ainda não existe → 12 |
| 09-18 | Sem runbook de rollout/rollback da integração Emsoft | `infra/` | Média | **ABERTO** → 11, 12 |

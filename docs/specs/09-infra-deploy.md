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

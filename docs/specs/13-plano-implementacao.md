# SPEC 13 — Plano de Implementação Incremental

## Princípios

- Ler primeiro `README.md`, `docs/specs/00` a `12`, `AGENTS.md` e `.ai/AGENT.md`/skills aplicáveis.
- Inspecionar o código e os testes antes de editar. Não presumir que o estado do código é igual ao texto da spec.
- Trabalhar uma entrega pequena por vez, com testes automatizados.
- Não reescrever a arquitetura nem introduzir CQRS/microserviços/agentes múltiplos.
- Não habilitar API Emsoft real antes de contrato e homologação.

## Fases

### Fase 0 — Auditoria e baseline

- Inventariar models, schema Appwrite, repositories, services, routes, frontend e workflow n8n.
- Executar testes atuais e registrar falhas preexistentes.
- Comparar implementações com specs e abrir lista de gaps.
- Confirmar arquivos ADR históricos e preservar decisões válidas.

**Aceite:** relatório de divergências sem alteração funcional.

### Fase 1 — Departamentos e migração

- Criar `departamentos` e `regras_roteamento`.
- Adicionar `departamento_id` a atendentes/chats.
- Criar seed idempotente dos departamentos atuais.
- Migrar dados legados `setor`/`setor_alvo`.
- Atualizar repositórios/services e RBAC.
- Manter compatibilidade temporária com campos legados.

**Aceite:** CRUD/associações, testes de migração, nenhum atendente/chat válido sem departamento resolvido quando exigido.

### Fase 2 — Classificação e roteamento

- Criar DTO Pydantic de intenção.
- Implementar classificador estruturado e validação.
- Criar resolver determinístico de regras.
- Implementar pedido explícito por humano/departamento e pergunta de esclarecimento.
- Integrar com transições de chat existentes.

**Aceite:** suite de casos classificados e roteados, com baixa confiança e conflito cobertos.

### Fase 3 — Diagnóstico e ciclo de resolução

- Persistir diagnóstico de IA.
- Garantir status por ChatService e transições legais.
- Registrar artigos RAG e motivo.
- Cobrir confirmação de resolução e falha de solução.

**Aceite:** cenários A/B/C e reabertura testados.

### Fase 4 — Frontend operacional

- UI de departamentos.
- Associação de atendente.
- Filtros de fila, assunção e transferência.
- Painel de diagnóstico e status da integração.

**Aceite:** testes manuais/E2E com perfis admin, supervisor e atendente.

### Fase 5 — Integração Emsoft em modo mock

- Obter contrato OpenAPI/Postman.
- Implementar `client`, schemas, mapper e service com contract tests.
- Criar coleção `integracao_chamados`.
- Implementar outbox/worker/retry.
- Mockar respostas e simular timeout, 4xx, 5xx, conflito e sucesso.

**Aceite:** comportamento completo em sandbox/mock, sem chamar produção.

### Fase 6 — Homologação externa

- Criar/confirmar usuário técnico IA.
- Mapear IDs de atendentes e departamentos externos.
- Testar abertura, edição, listagem e atribuição com dados de teste.
- Confirmar status de aguardando, em atendimento, resolvido e encerrado.
- Testar reconciliação de timeout e idempotência.

**Aceite:** aprovação do responsável pela API Emsoft e evidência de teste sem duplicidade.

### Fase 7 — Rollout

- Ativar integração por flag em ambiente controlado.
- Monitorar pendências e duplicidade.
- Expandir para produção após estabilidade.

**Aceite:** métricas, alertas, rollback e runbook publicados.

## Definition of Done por fase

- Código tipado e formatado conforme convenções do repo.
- Testes unitários e de integração relevantes.
- Sem regressão em rotas/contratos existentes sem migração versionada.
- Atualização de specs/ADR quando decisão mudar.
- Logs sanitizados e métricas quando fluxo externo for envolvido.
- Nenhum token ou segredo commitado.

## Onde estão os gaps desta fase

Esta spec é um **plano de execução**, não um estado-alvo: por isso não tem Registro de Gaps
próprio. Os gaps que cada fase endereça estão registrados nas specs de domínio —
[00](00-escopo.md) a [12](12-confiabilidade-integracoes.md) e
[14](14-test-strategy.md). O que muda aqui é o **status de execução** das fases.

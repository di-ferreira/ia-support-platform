# Changelog — Specs v2

## Arquivos substituídos/consolidados

- `docs/specs/00-escopo.md` — acrescenta intenção, departamentos e integração Emsoft ao escopo.
- `docs/specs/01-domain-glossary.md` — diferencia chat interno, chamado externo, intenção, categoria ERP, departamento e atendente; preserva a máquina de oito estados.
- `docs/specs/02-data-model.md` — adiciona departamentos, regras de roteamento, vínculo de chamados externos e outbox; define migração dos campos legados `setor`/`setor_alvo`.
- `docs/specs/03-api-contract.md` — preserva contratos conhecidos e descreve endpoints-alvo de departamentos, roteamento e reprocessamento.
- `docs/specs/04-rbac-matrix.md` — consolida permissões humanas e identidade de serviço da IA.
- `docs/specs/05-ai-pipeline.md` — define classificação de intenção, separação de categoria ERP/departamento, RAG e decisão determinística.
- `docs/specs/06-n8n-workflow.md` — reafirma n8n como transporte e adiciona regras de deduplicação.
- `docs/specs/07-frontend.md` — incorpora telas/estados de departamento, diagnóstico e sincronização.
- `docs/specs/08-non-functional.md` — consolida confiabilidade, segurança, observabilidade e métricas.
- `docs/specs/09-infra-deploy.md` — acrescenta configuração e rollout seguros da integração.
- `docs/specs/adr/0004-backend-dono-da-ia.md` e `0005-dimensao-de-embedding.md` — versões consolidadas das decisões já referenciadas pelo README público.

## Novos documentos

- `docs/specs/10-departamentos-e-roteamento.md`
- `docs/specs/11-integracao-api-emsoft.md`
- `docs/specs/12-confiabilidade-integracoes.md`
- `docs/specs/13-plano-implementacao.md`
- `docs/specs/adr/0006-departamentos-e-roteamento.md` (proposta)
- `docs/specs/adr/0007-integracao-chamados-emsoft.md` (proposta)
- `IMPLEMENTATION-PROMPT.md`

## Atenção

O contrato real da API Emsoft não foi acessível/publicamente verificável durante a preparação. A SPEC 11 registra o endpoint fornecido e lista todas as informações que precisam ser confirmadas. A integração deve permanecer desabilitada até essa validação.

## Revisões posteriores

- `docs/specs/10-test-strategy.md` → `docs/specs/14-test-strategy.md`: a estratégia de testes deixa de disputar a numeração com as specs novas. Os gaps passaram de `10-x` para `14-x` e as referências cruzadas foram atualizadas.
- Registros de Gaps reconstruídos nas specs 00–14, com status verificado contra o código atual (`backend/app/`, `frontend/`, `infra/`, `backend/tests/`) em 2026-11-06. Cada gap cita arquivo e linha; gaps resolvidos após o pacote v2 (rate limiting, token do WebSocket, deduplicação no n8n, falha de RAG, validação de segredo no startup, `ia_diagnosticos`, sincronização Qdrant) estão marcados como `CORRIGIDO`.
- `docs/specs/README.md` atualizado: índice com as specs 10–14, tabela de ADRs, Mapa "onde eu vou para saber sobre X?" e lista de documentos derivados (`IMPLEMENTATION-PROMPT.md`, `CHANGELOG.md`, `PACKAGE-README.md`, `docs/specs.backup/`).

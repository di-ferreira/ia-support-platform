# Especificações — EMSoft Support AI Platform

Este diretório é a **fonte única de verdade** do escopo, do domínio e do contrato do
produto. Tudo o que estiver em outro lugar (README, TODO_LIST, `.ai/`, `DesignSystem/`) é
derivado ou histórico.

## Convenções

Cada spec descreve o **estado alvo** (o comportamento que deve valer) e fecha com um
**Registro de Gaps**: o que já está implementado, o que diverge do alvo e o que não
existe. Um gap marcado `ABERTO` é trabalho Known; `CORRIGIDO` já foi resolvido no código.

Ao implementar, atualize o Registro de Gaps da spec correspondente. Uma spec sem gap
aberto é uma spec concluída.

Cada gap tem id prefixado pelo número da spec (`NN-x`) e cita o arquivo (e, quando útil, a
linha) onde a divergência está. `ABERTO` é trabalho conhecido; `CORRIGIDO` significa
resolvido no código, com a evidência indicada no próprio registro.

## Índice

| Spec | Escopo | Status |
|---|---|---|
| [00-escopo](00-escopo.md) | Objetivo, cenários A/B/C, fronteira do produto | Vigente |
| [01-domain-glossary](01-domain-glossary.md) | Termos canônicos e máquina de estados | Vigente |
| [02-data-model](02-data-model.md) | Coleções Appwrite, invariantes, estratégia de unicidade | Vigente |
| [03-api-contract](03-api-contract.md) | Contrato HTTP, autenticação, erros | Vigente |
| [04-rbac-matrix](04-rbac-matrix.md) | Matriz perfil × recurso × operação | Vigente |
| [05-ai-pipeline](05-ai-pipeline.md) | Pipeline de IA, classificação de intenção, RAG, decisão | Vigente |
| [06-n8n-workflow](06-n8n-workflow.md) | Workflow alvo e contrato com o n8n | Vigente |
| [07-frontend](07-frontend.md) | Rotas, tokens de design, responsividade, a11y | Vigente |
| [08-non-functional](08-non-functional.md) | Segurança, performance, observabilidade | Vigente |
| [09-infra-deploy](09-infra-deploy.md) | Ambientes, portas, TLS, segredos, backup | Vigente |
| [10-departamentos-e-roteamento](10-departamentos-e-roteamento.md) | Departamentos, classificação de intenção e roteamento | Vigente |
| [11-integracao-api-emsoft](11-integracao-api-emsoft.md) | Integração com a API interna de chamados Emsoft | Vigente |
| [12-confiabilidade-integracoes](12-confiabilidade-integracoes.md) | Outbox, idempotência, retry e reprocessamento | Vigente |
| [13-plano-implementacao](13-plano-implementacao.md) | Plano incremental por fases (Fase 0 → Fase 7) | Vigente |
| [14-test-strategy](14-test-strategy.md) | Estratégia de testes e gates de CI | Vigente |
| [adr/](adr/) | Decisões arquiteturais e trade-offs | — |

### ADRs

| ADR | Decisão | Estado |
|---|---|---|
| [0004](adr/0004-backend-dono-da-ia.md) | O backend FastAPI é dono da IA | Aceita |
| [0005](adr/0005-dimensao-de-embedding.md) | Embedding sempre em 768 (Ollama `nomic-embed-text`) | Aceita |
| [0006](adr/0006-departamentos-e-roteamento.md) | Departamentos como entidades, roteamento determinístico | Proposta |
| [0007](adr/0007-integracao-chamados-emsoft.md) | Integração de chamados via outbox, um vínculo por chat | Proposta |

## Mapa: "onde eu vou para saber sobre X?"

| Pergunta | Spec |
|---|---|
| O produto faz o quê, e o que ele não faz? | [00-escopo](00-escopo.md) |
| O que significa `AGUARDANDO_HUMANO_COM_SOLUCAO`? | [01-domain-glossary](01-domain-glossary.md) |
| Quais coleções existem e o que é obrigatório? | [02-data-model](02-data-model.md) |
| Como eu chamo este endpoint? O que ele devolve em 409? | [03-api-contract](03-api-contract.md) |
| Um supervisor pode criar cliente? | [04-rbac-matrix](04-rbac-matrix.md) |
| Como a IA decide entre cenário A, B e C? | [05-ai-pipeline](05-ai-pipeline.md) |
| Por que o n8n chama `/webhooks/ai/*` e não `/ai/*`? | [05-ai-pipeline](05-ai-pipeline.md) §Autenticação M2M |
| Por que o backend tem prompts que o n8n não usa? | [adr/0004-backend-dono-da-ia.md](adr/0004-backend-dono-da-ia.md) |
| Como adiciono uma rota nova? | [07-frontend](07-frontend.md) §Rotas |
| Onde eu levo um segredo? | [09-infra-deploy](09-infra-deploy.md) §Segredos |
| Para qual departamento vai este chat? | [10-departamentos-e-roteamento](10-departamentos-e-roteamento.md) |
| Como o chamado é criado na API da Emsoft? | [11-integracao-api-emsoft](11-integracao-api-emsoft.md) |
| O que acontece se a API externa cair no meio? | [12-confiabilidade-integracoes](12-confiabilidade-integracoes.md) |
| Por onde eu começo a implementar? | [13-plano-implementacao](13-plano-implementacao.md) |
| Posso pular um teste? | [14-test-strategy](14-test-strategy.md) |

## Documentos derivados (não são fonte de verdade)

| Documento | Status |
|---|---|
| `README.md` | Setup rápido. Aponta para cá. |
| `TODO_LIST.md` | Histórico de implementação + pontes para as specs. O trabalho conhecido está nos Registros de Gaps. |
| `IMPLEMENTATION-PROMPT.md` | Prompt de execução para agentes. **Deriva** das specs 00–13; não cria regra nova. |
| `CHANGELOG.md` | Registro de alterações do pacote de specs (v2). |
| `PACKAGE-README.md` / `PACKAGE-MANIFEST.json` | Manifesto do pacote de specs entregue. |
| `docs/specs.backup/` | Série anterior das specs, preservada como histórico. **Não editar.** |
| `docs/n8n-workflow.md` | **Substituído** e **arquivado** por banner; canônico: [06-n8n-workflow](06-n8n-workflow.md). |
| `.ai/PROJECT.md` | Visão original arquivada por banner. Stack declarada (NestJS/Prisma) nunca foi usada. |
| `.ai/SUPORTE_AGENT.md` | Persona da IA. Entrada do prompt, não do código. Ver [05-ai-pipeline](05-ai-pipeline.md) §Prompt. |
| `.ai/TODO_LIST.md` | **Arquivado.** Descreve 19 nós de workflow e MinIO; o workflow versionado atual tem 10 nós e o MinIO segue órfão. |
| `DesignSystem/DESIGN-MANIFEST.json` | Contrato visual. Telas cortadas removidas na Fase 5. |
| `DesignSystem/brand-spec.md` | Tokens de marca. Ver [07-frontend](07-frontend.md) §Tokens. |

## Como esta série foi produzida

Analyze → Plan → Ask → Execute → Review, conforme `spec-driven-development`. A análise
cobre `backend/`, `frontend/`, `infra/`, `scripts/` e a documentação existente. Os gaps
são verificáveis no código — cada um cita arquivo e linha.
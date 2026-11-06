# Pacote oficial de especificações — IA Support Platform (v2)

Este pacote substitui/consolida as especificações funcionais e técnicas em `docs/specs/` para a próxima etapa da IA Support Platform.

**Objetivo desta versão:** incorporar roteamento por departamentos, classificação de intenção e integração com a API interna de chamados da Emsoft, preservando a arquitetura existente (FastAPI, Appwrite, Redis, Qdrant, n8n, Evolution API e Next.js).

## Estrutura

```text
docs/specs/
├── 00-escopo.md
├── 01-domain-glossary.md
├── 02-data-model.md
├── 03-api-contract.md
├── 04-rbac-matrix.md
├── 05-ai-pipeline.md
├── 06-n8n-workflow.md
├── 07-frontend.md
├── 08-non-functional.md
├── 09-infra-deploy.md
├── 10-departamentos-e-roteamento.md
├── 11-integracao-api-emsoft.md
├── 12-confiabilidade-integracoes.md
└── adr/
    ├── 0004-backend-dono-da-ia.md
    ├── 0005-dimensao-de-embedding.md
    ├── 0006-departamentos-e-roteamento.md
    └── 0007-integracao-chamados-emsoft.md
```

## Instalação no repositório

1. Faça uma cópia de segurança da pasta atual:

   ```bash
   cp -a docs/specs "docs/specs.backup-$(date +%Y%m%d-%H%M%S)"
   ```

2. Extraia o ZIP na raiz do repositório, mantendo a estrutura `docs/specs/`.
3. Revise o diff antes de commitar:

   ```bash
   git diff -- docs/specs
   ```

4. Preserve ADRs históricos anteriores ao `0004` caso existam no seu clone local. Este pacote atualiza os ADRs `0004` e `0005` que são referenciados pelo README atual e adiciona `0006` e `0007`; não pretende apagar decisões históricas não relacionadas.
5. Atualize o README principal apenas se algum endpoint, variável ou instrução de setup mudar durante a implementação.

## Ordem normativa de leitura

1. `00-escopo.md` — limites e objetivo do produto.
2. `01-domain-glossary.md` — termos e estados canônicos.
3. `02-data-model.md` — persistência Appwrite.
4. `03-api-contract.md` — contratos HTTP.
5. `04-rbac-matrix.md` — permissões.
6. `05-ai-pipeline.md` — classificação, RAG e decisão.
7. `06-n8n-workflow.md` — transporte WhatsApp.
8. `07-frontend.md` — comportamento da interface.
9. `08-non-functional.md` e `09-infra-deploy.md` — qualidade e operação.
10. `10`, `11` e `12` — requisitos novos de roteamento e integração externa.
11. `adr/` — decisões arquiteturais que explicam os limites acima.

Em caso de conflito, os contratos e invariantes desta pasta prevalecem sobre comentários, prompts antigos, workflows exportados ou documentação narrativa fora dela. Se o código divergir, não corrija silenciosamente a spec: registre o gap, proponha a alteração e implemente uma mudança explícita.

## Decisões novas desta versão

- `categoria_erp` identifica o módulo/assunto do ERP; `departamento` identifica a equipe que deve atender. São conceitos distintos.
- Departamentos passam a ser entidades Appwrite com identificadores estáveis. As strings `atendentes.setor` e `chats.setor_alvo` são legadas durante a migração.
- Um chat pode ter simultaneamente `departamento_id` e `atendente_id`: o departamento representa a equipe responsável; o atendente representa a pessoa responsável.
- O backend FastAPI classifica, valida, roteia e chama a integração Emsoft. O n8n não toma decisões de negócio e não chama a API de chamados.
- Cada chat tem no máximo um chamado externo Emsoft ativo vinculado. Transferências atualizam o responsável do mesmo chamado, quando o contrato externo permitir.
- A plataforma cria um chamado externo quando a IA apresenta uma solução para acompanhamento. Inicialmente ele fica no usuário técnico da IA, com situação equivalente a aguardando confirmação. Se o cliente confirmar, o chamado externo é atualizado para resolvido. Se não resolver, o mesmo registro é atualizado e transferido para o atendente.
- Para transferência humana, a atribuição externa deve refletir o atendente efetivamente designado. Se a API não aceitar uma fila/departamento, o envio aguarda a atribuição individual.
- A API `https://emsoft.ddns.net/portal-api/v1/chamados` foi informada pelo proprietário do projeto, mas seu contrato não foi validado neste pacote. Autenticação, payloads, identificadores, rotas de edição e semântica de status são bloqueadores de implementação, documentados em `11-integracao-api-emsoft.md`.

## Baseline técnico observado

O README público do projeto informa: Python 3.11+ / FastAPI, Next.js 15, Tailwind 4, React Query, Zustand, Appwrite self-hosted, Redis, Qdrant, n8n, Ollama/OpenAI para chat, Evolution API e Docker/Compose/Traefik. O backend usa Appwrite como fonte primária; `backend/app/appwrite/schema.py` e `bootstrap.py` são descritos como fonte do schema.

As specs existentes consultadas também documentam oito estados de chat, três cenários de IA, webhooks autenticados por `X-Webhook-Secret`, n8n como transporte e categorias ERP independentes de departamento.

## Limitação de reconciliação

O repositório público foi consultado na branch `main` em 06/11/2026. Alguns arquivos brutos (`04-rbac-matrix.md`, `05-ai-pipeline.md`, `08-non-functional.md`, `09-infra-deploy.md` e certos ADRs) não puderam ser recuperados integralmente pelo acesso público utilizado. As versões correspondentes deste pacote são **consolidações normativas novas**, reconstruídas a partir do README, dos contratos e dos trechos públicos disponíveis. Antes de substituir a pasta local, compare esses arquivos com o clone local e preserve detalhes válidos que não estejam refletidos aqui.

Este pacote não afirma que as novas funcionalidades já estejam implementadas. Os documentos descrevem o estado desejado e identificam os bloqueios de contrato.

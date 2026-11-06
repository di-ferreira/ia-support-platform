# ADR-0004 — O backend é o dono da IA

**Status:** Aceito
**Data:** 2026-10-05
**Relacionado:** [05-ai-pipeline](../05-ai-pipeline.md), [06-n8n-workflow](../06-n8n-workflow.md)

## Contexto

O pipeline de IA (RAG + LLM + decisão de cenário) precisa ter dono. Duas opções foram
consideradas:

1. **n8n** — a implementação atual. O workflow `ChatAIBot`
   (`infra/n8n/workflow-support-ai.json`) contém um nó de AI Agent (LangChain), um nó de
   Ollama Chat Model e um nó de Simple Memory.
2. **Backend Python** — os endpoints `/ai/*` já existem no código
   (`app/ai/router.py`), com prompts em `app/ai/prompts.py`, RAG em
   `app/services/qdrant_service.py` (orquestrado em `app/ai/router.py`) e a decisão de
   cenário no fluxo. A variante M2M `POST /webhooks/ai/solucionar`, sob `X-Webhook-Secret`,
   é o alvo da spec — ainda **não existe** no código. Ver
   [05-ai-pipeline](../05-ai-pipeline.md) §Autenticação M2M.

Fatos sobre o estado atual:

- O AI Agent do n8n **não tem tools nem acesso à base de conhecimento**: responde com o
  conhecimento próprio do LLM (gap 05-1 em [05-ai-pipeline](../05-ai-pipeline.md)).
- A decisão entre cenários A/B/C é feita por texto livre do LLM dentro do n8n: não há
  regra determinística, nada é gravado em `ia_diagnosticos` (gap 05-2) e o status do chat
  nunca transita — `PATCH /webhooks/chat/status` nunca é chamado (gap 05-3).
- Prompts, memória e decisão no n8n **não são versionados com o código**, não passam por
  teste e se perdem quando o workflow é reexportado.
- Os endpoints do backend estão implementados, mas o workflow atual não os chama: a IA
  real de produção é o AI Agent solto.

## Decisão

**O backend é o dono da IA.** O n8n faz apenas transporte: recebe o evento da Evolution
API, normaliza o payload, chama os endpoints do backend e envia o texto devolvido via
Evolution.

Tudo o que é "IA" vive em Python, versionado e testado:

- **Prompts** — constantes em `app/ai/prompts.py`;
- **RAG** — indexação e consulta na Qdrant (`qdrant_service.py`);
- **Chamada ao LLM** e parsing da resposta estruturada;
- **Decisão do cenário (A/B/C)** — regra determinística aplicada sobre a resposta
  estruturada. O LLM emite um julgamento (JSON); a regra decide o cenário. O cenário nunca
  é "escolhido" pelo LLM em texto livre;
- **Transição de status** via `ChatService` (máquina de estados,
  [01-domain-glossary](../01-domain-glossary.md)) e gravação em `ia_diagnosticos`.

Por quê:

- A meta de 70% de chamados resolvidos pela IA ([00-escopo](../00-escopo.md)) depende de
  uma decisão reproduzível. Decisão em editor de workflow, sem teste, é insustentável.
- Saída de LLM varia e é não estruturada; transformar isso em cenário exige parsing +
  regra, que só dá para testar com stub de LLM se estiver no backend.
- Fonte única de verdade: o mesmo código atende o fluxo de webhook (n8n) e eventuais
  endpoints internos futuros, sem réplica de lógica em JSON de workflow.

## Consequências

- O workflow n8n vira fino ([06-n8n-workflow](../06-n8n-workflow.md)): sem prompt de
  negócio, sem nó de memória, sem decisão de cenário.
- Mudar prompt exige mudar código, rodar teste e fazer deploy — não existe "editor da IA".
- Enquanto o gap 05-1 estiver aberto, o workflow atual usa o AI Agent: o sistema funciona,
  mas **não segue a spec**. O workflow alvo está documentado, não implantado.
- O backend assume a responsabilidade por latência, timeout e fallback do LLM
  ([05-ai-pipeline](../05-ai-pipeline.md) §RAG).

## Alternativas consideradas

- **AI Agent LangChain no n8n (status quo)**: decisão não versionada, não testável,
  cenário a mercado do LLM. Rejeitada.
- **Híbrido — RAG no backend, decisão no n8n**: duas fontes de verdade para a decisão e
  o n8n continuaria carregando prompt e regra. Rejeitada.

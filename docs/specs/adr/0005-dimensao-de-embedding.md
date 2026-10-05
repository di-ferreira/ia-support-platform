# ADR-0005 — Dimensão do embedding e o bloqueio do OpenAI

**Status:** Aceito
**Data:** 2026-10-05
**Relacionado:** [05-ai-pipeline](../05-ai-pipeline.md) §RAG, gap 05-11

## Contexto

- A coleção `emsoft-knowledge-base` é criada com `VECTOR_SIZE = 768` e distância cosine
  (`qdrant_service.py:6-7,22`).
- A dimensão de uma coleção Qdrant é fixa na criação: não existe "mudar de 768 para 1536".
  Trocar exige coleção nova + re-embedding do corpus inteiro.
- O modelo de embedding depende do provider (o mesmo serviço que faz o chat também
  embutida a consulta):
  - **Ollama** — `OLLAMA_EMBED_MODEL`, default `nomic-embed-text` → **768**
    dimensões (`ollama_service.py:41`);
  - **OpenAI** — `text-embedding-3-small`, hardcoded → **1536** dimensões
    (`openai_service.py:52`).
- `_get_llm()` escolhe o serviço por `LLM_PROVIDER` / `OPENAI_API_KEY`
  (`router.py:22-27`). `LLM_PROVIDER=openai` muda silenciosamente a dimensão dos
  vetores escritos e consultados.
- Vetor de dimensão errada na coleção errada é uma **falha silenciosa**:
  `except Exception: rag_context = ""` (`router.py:105-106`) converte a falha em
  "Nenhum artigo relevante encontrado" — Cenário C falso, sem log (gaps 05-6, 05-13).

## Decisão

**A dimensão da coleção fica travada no modelo de embedding, e o modelo de embedding
fica travado em Ollama + `nomic-embed-text` (768).**

Regras:

1. `VECTOR_SIZE`, a coleção no Qdrant e o modelo de embedding devem sempre coincidir — o
   mesmo modelo é usado na indexação (`seed_qdrant.py`) e na consulta (`llm.embed`).
2. `LLM_PROVIDER=openai` está **bloqueado** para RAG até que exista uma coleção 1536 e o
   seed tenha sido reexecutado. Isso não é "virar variável": é migração (coleção nova,
   re-embedding, troca de tráfego, coleção antiga retida até validação).
3. Mudar o **chat** model e mudar o **embedding** model são decisões independentes —
   `OLLAMA_MODEL` pode mudar à vontade, desde que o embedding continue gerando 768.
4. Se o modelo de embedding mudar no futuro, a constante, o seed e a coleção mudam no
   mesmo PR, com re-embedding e validação de busca.

Por quê:

- Incompatibilidade de dimensão falha de forma silenciosa: o sintoma é "a IA parou de
  citar a base", não "a infra quebrou". Isso é exatamente o Cenário C falso (gap 05-6)
  que corrompe a meta de 70% ([00-escopo](../00-escopo.md)).
- 768 é suficiente para o corpus-alvo (~20 artigos) e mais barato/rápido. O ganho de
  qualidade de 1536 não se justifica nesta etapa.
- `text-embedding-3-small` está hardcoded no `openai_service.py`: mesmo com a dimensão
  configurável, o caminho OpenAI quebraria. O bloqueio é no provider, não no config.

## Consequências

- `LLM_PROVIDER=openai` com `OPENAI_API_KEY`: o chat funciona, mas **o RAG quebra** — o
  sistema roda em Cenário C falso até existir a coleção 1536. Esse é o estado atual do
  gap 05-11.
- O procedimento de migração de modelo (coleção nova + re-seed + troca) entra no
  runbook de operações ([09-infra-deploy](../09-infra-deploy.md) §Operações).
- `seed_qdrant.py` e o backend precisam usar o mesmo modelo de embedding: dois ambientes
  com modelos diferentes produzem um corpus que não é consultável.

## Alternativas consideradas

- **Adotar 1536 do OpenAI agora**: exigiria re-embeddar o corpus e custo maior por
  consulta; o alvo é Ollama local. Rejeitado por ora.
- **Dimensão configurável por coleção**: complexidade que não paga com uma única
  coleção e um único modelo. Rejeitado.

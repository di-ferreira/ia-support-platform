# ADR-0005 — Embeddings e uso de provedores no RAG

- **Status:** Aceita (consolidada a partir da política referenciada no README atual)
- **Contexto:** O RAG usa Qdrant para recuperação vetorial e um modelo de embedding com dimensão definida. Trocar o modelo/dimensão sem reindexar os documentos torna vetores incompatíveis.

## Decisão

- O provider de embedding é separado do provider usado para chat.
- A configuração alvo documentada é `nomic-embed-text`, com vetor de 768 dimensões.
- OpenAI pode ser usado como provider de LLM para chat, mas não deve ser usado para embedding/RAG nesta arquitetura.
- A coleção Qdrant e o modelo de embedding devem ter dimensão compatível (768 no baseline documentado).
- Uma troca de modelo exige criar/limpar coleção compatível, reprocessar todos os artigos ativos e validar recuperação antes de ativar a nova coleção.

## Consequências

- Nunca misturar vetores produzidos por modelos/dimensões diferentes na mesma coleção.
- Armazenar/versionar o identificador do modelo de embedding usado.
- Pipeline de ingestão e consulta deve usar o mesmo modelo.
- Testes devem detectar incompatibilidade de dimensão e ausência de reindexação.

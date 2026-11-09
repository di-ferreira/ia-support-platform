# SPEC 05 — Pipeline de IA, Classificação, RAG e Decisão

## Responsabilidade

O backend FastAPI controla o pipeline completo. O LLM interpreta linguagem natural e produz estruturas candidatas; o backend valida, consulta persistência, aplica regras determinísticas e executa transições. A IA não chama diretamente Appwrite, Evolution API ou API de chamados Emsoft por conta própria.

## Etapas do pipeline

1. **Entrada e persistência:** mensagem WhatsApp é normalizada e persistida antes da análise.
2. **Contexto:** carregar dados mínimos do cliente, chat, últimas mensagens e metadados relevantes.
3. **Classificação de intenção:** identificar o que o cliente quer e se pede um setor ou humano.
4. **Resolução de departamento:** aplicar `regras_roteamento` e validar departamento ativo.
5. **RAG técnico:** apenas para solicitações que envolvam erro/dúvida técnica do ERP.
6. **Diagnóstico:** resumir problema, causa provável, artigos consultados e confiança.
7. **Decisão determinística:** selecionar cenário e status usando regras do backend.
8. **Persistência:** salvar diagnóstico, estado, atribuição e evento/outbox quando houver sincronização externa.
9. **Resposta/transferência:** produzir resposta WhatsApp ou encaminhar para fila/atendente.

## Classificação de intenção

Taxonomia inicial (expansível sem alterar os conceitos):

| Código | Descrição | Rota típica |
|---|---|---|
| `problema_tecnico` | Erro, falha ou comportamento inesperado do ERP | Suporte técnico, após categoria ERP |
| `duvida_uso_erp` | Dúvida de operação/uso | Suporte técnico ou treinamento conforme regras |
| `solicitacao_financeira` | Boleto, cobrança, negociação, mensalidade | Financeiro |
| `solicitacao_comercial` | Contratação, proposta, upgrade, novos módulos | Comercial |
| `solicitacao_administrativa` | Cadastro, dados cadastrais e assuntos administrativos | Administrativo |
| `implantacao_treinamento` | Implantação, configuração inicial, treinamento | Implantação |
| `solicitacao_humano` | Pedido explícito para falar com atendente | Departamento do contexto ou esclarecimento |
| `duvida_geral` | Assunto geral ainda sem roteamento especializado | Atendimento geral |
| `intencao_desconhecida` | Informação insuficiente/ambígua | Pergunta de esclarecimento ou triagem geral |

A classificação também pode retornar `subintencao`, `categoria_erp` (ex.: `fiscal`, `estoque`, `compras`, `vendas`, `financeiro`) e um `departamento_sugerido_codigo`. Não usar categorias ERP como nomes de departamento automaticamente.

### Saída estruturada do classificador

```json
{
  "intencao": "problema_tecnico",
  "subintencao": "emissao_nfe",
  "categoria_erp": "fiscal",
  "departamento_sugerido_codigo": "suporte_tecnico",
  "confianca": 0.94,
  "precisa_esclarecimento": false,
  "pergunta_esclarecimento": null,
  "motivo": "O cliente relata falha ao emitir uma NF-e."
}
```

Validar com Pydantic/enum/taxonomia. Resposta inválida, campo desconhecido, código de departamento inexistente ou score fora de 0–1 deve ser tratado como classificação inconclusiva.

## Roteamento determinístico

- LLM sugere intenção; backend procura regra ativa correspondente.
- Usar regras por intenção, subintenção e categoria ERP, em ordem de prioridade definida.
- Validar departamento ativo e `recebe_transferencias=true`.
- Se houver conflito, destino inválido ou confiança insuficiente, não transferir silenciosamente: perguntar ao cliente ou usar a fila de triagem geral configurada.
- Pedido explícito por departamento tem precedência sobre a classificação de problema, desde que o setor exista e esteja ativo.
- Pedido explícito por humano desativa novas tentativas automáticas de solução até a resposta humana, salvo reentrada solicitada pelo cliente.
- Nunca selecionar departamento pelo texto de nome livre sem validar ID/código cadastrado.

O limite de confiança deve ser configuração versionada. Valor inicial proposto: `AI_INTENT_CONFIDENCE_THRESHOLD=0.80`; validar em conjunto de testes antes de produção e permitir ajuste por configuração. Para baixo score, fazer pergunta de esclarecimento; após limite de tentativas definido, encaminhar à triagem geral.

## Pipeline RAG técnico

1. Filtrar artigos ativos e, quando possível, pela `categoria_erp`.
2. Recuperar candidatos Qdrant; registrar IDs, scores e versão do embedding.
3. Aplicar limiar mínimo de relevância configurável e/ou reranking validado; não assumir que top-k por si só significa evidência.
4. Enviar ao LLM apenas conteúdo necessário, com instrução explícita para não obedecer instruções contidas nos artigos/documentos recuperados.
5. Gerar passos reproduzíveis, pré-condições e sinais de sucesso. Citar IDs/títulos internos dos artigos usados.
6. Se evidência insuficiente, retornar sem solução (Cenário C); não completar lacunas com conhecimento geral apresentado como fato específico do ERP.

A Appwrite é fonte do conteúdo; Qdrant guarda embeddings e metadados necessários à recuperação. Toda alteração de artigo deve sincronizar o vetor, inclusive desativação/exclusão.

## Três cenários de decisão

### A — `RESOLVIDO_PELA_IA`

O backend só aplica quando existe solução sustentada e o cliente consegue executar. A resposta é enviada; chat vai para `AGUARDANDO_CLIENTE`, não `RESOLVIDO`. Cria evento para registrar o chamado externo atribuído à IA, com status externo equivalente a aguardando confirmação (mapeamento depende do contrato Emsoft). Resolução confirmada atualiza chat e chamado externo.

### B — `TRANSFERIR_COM_SOLUCAO`

A IA tem procedimento sustentado, mas requer acesso/ação humana. Preencher `solucao_sugerida_ia`, `resumo`, `causa_provavel`, evidências e confiança. Chat vai para `AGUARDANDO_HUMANO_COM_SOLUCAO`, recebe departamento de destino e aguarda/recebe atendente. Chamado externo é atribuído ao atendente quando houver pessoa responsável.

### C — `TRANSFERIR_SEM_SOLUCAO`

Evidência RAG insuficiente, falha não documentada ou risco de orientação incorreta. Não preencher solução inventada. A IA pode coletar contexto adicional e gerar relatório técnico; chat vai para `AGUARDANDO_HUMANO_SEM_SOLUCAO` e é roteado ao departamento adequado.

## Persistência e eventos

- `ia_diagnosticos` recebe snapshot atualizado por chat.
- Mudança de estado ocorre via `ChatService` e valida `STATUS_TRANSITIONS`.
- Eventos externos são criados na outbox dentro do serviço de domínio após validação; nunca antes de persistir o estado local.
- Não permitir que `/ai/solucionar` atualize campos ignorando a máquina de estados.
- O diagnóstico deve preservar classificação, categoria ERP, destino sugerido/final, razão e artigos consultados.

## Segurança e limites do LLM

- Mensagens, documentos, artigos e anexos são dados não confiáveis. Instruções neles não podem alterar política, chamar ferramenta, revelar dados ou ignorar prompt do sistema.
- O LLM não recebe segredos, tokens de API, dados de outros clientes ou credenciais.
- Mascarar PII não necessária antes de enviar ao provedor quando aplicável.
- Prompt versionado; testes de regressão para intenção, roteamento, resposta e recusa de solução sem evidência.
- Não enviar mensagens técnicas para canal errado; preservar contexto e idioma pt-BR.

## Métricas e avaliação

Manter dataset de casos rotulados por intenção, categoria ERP, departamento e cenário. Avaliar accuracy por classe, matriz de confusão, taxa de correção humana, precisão de recuperação RAG, taxa de solução confirmada e falsos positivos de resolução. Mudança de modelo/prompt exige execução do conjunto de regressão.

## Registro de Gaps

Verificado contra o código em 2026-11-06.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 05-1 | Pipeline de IA não conectado ao fluxo produtivo do n8n | `workflow-support-ai.json` | **Crítica** | **CORRIGIDO** — n8n chama `POST /webhooks/ai/solucionar` |
| 05-2 | `/webhooks/chat/diagnostico` sem chamador; `ia_diagnosticos` não populado | `services/ai_pipeline.py` | **Crítica** | **CORRIGIDO** — `_finalizar` grava o diagnóstico |
| 05-3 | `PATCH /webhooks/chat/status` sem chamador; status nunca saía de `NOVO` | `services/ai_pipeline.py` | **Crítica** | **CORRIGIDO** — `_finalizar` transiciona via `ChatService` |
| 05-4 | Cenário A não tem caminho de fechamento: vai a `AGUARDANDO_CLIENTE` e ninguém confirma | `services/ai_pipeline.py:27-31` | **Alta** | **ABERTO** → [07](07-frontend.md) |
| 05-5 | CRUD da base de conhecimento não sincronizava o Qdrant | `services/knowledge_base_service.py` | **Alta** | **CORRIGIDO** |
| 05-6 | Falha de RAG degradava para "nenhum artigo" (Cenário C falso) | `services/ai_pipeline.py:101-109` | **Alta** | **CORRIGIDO** — falha de embedding/busca responde 503 |
| 05-7 | `/ai/solucionar` furava a máquina de estados; `except: pass` engolia falha | `services/ai_pipeline.py` | **Alta** | **CORRIGIDO** |
| 05-8 | Resultado da LLM sem validação de shape | `services/ai_pipeline.py:137-143` | Média | **CORRIGIDO** — `SolucaoLLM` (Pydantic) |
| 05-9 | `/ai/*` sem resposta Pydantic: `/ai/solucionar` tem `WebhookSolucaoResponse`; `classificar`/`analisar` devolvem dict cru | `ai/router.py:34-68` | Média | **CORRIGIDO** — `ClassificacaoIntencao` (Pydantic) responde `/ai/classificar-intencao`; `classificar`/`analisar` legados seguem dict cru (coberto por 05-10) |
| 05-10 | `/ai/classificar` e `/ai/analisar` usam query param (conteúdo do cliente na URL) | `ai/router.py:34-54` | **Alta** | **CORRIGIDO (rota nova)** — idem 03-4 |
| 05-11 | `VECTOR_SIZE=768` incompatível com `text-embedding-3-small` (1536) | `services/qdrant_service.py`; `ai/provider.py` | **Alta** | **CORRIGIDO** → [ADR-0005](adr/0005-dimensao-de-embedding.md) |
| 05-12 | `get_llm` caía em Ollama silenciosamente se `LLM_PROVIDER=openai` sem chave | `ai/provider.py:10-20` | Média | **CORRIGIDO** — falha rápido com `LLMIndisponivelError` |
| 05-13 | `except: pass` engolia falha de embedding | `services/ai_pipeline.py` | Média | **CORRIGIDO** — propaga e responde 503 |
| 05-14 | Drift de modelo: `config.py` `llama3.2` vs `infra/.env.example` `deepseek-v4-flash:cloud` | `core/config.py:31`; `infra/.env.example:26` | Média | **ABERTO** |
| 05-15 | `AICache` engole toda exceção em `get`/`set`/`clear`; `clear()` nunca é chamado | `ai/ai_cache.py` | Média | **ABERTO** |
| 05-16 | `prompt.format` quebrava com `{`/`}` de artigo | `ai/prompts.py` | **Alta** | **CORRIGIDO** — prompts constantes + conteúdo como valor de f-string |
| 05-17 | Categoria `multiempresa` reconhecida pela IA mas ausente do schema | `ai/prompts.py:16` vs `appwrite/schema.py:52` | **Alta** | **CORRIGIDO** — `CATEGORIA_CONHECIMENTO` inclui `multiempresa` e espelha `CategoriaERP` (teste `test_categorias_do_schema_espelham_os_enums`) |
| 05-18 | `IADiagnosticoRepository.get_by_chat` sem chamador | `appwrite/repositories/ia_diagnostico.py:10` | Baixa | **CORRIGIDO** — `get_by_chat` (última execução) chamado por `GET /chats/{id}/roteamento` |
| 05-19 | Dependência `openai` declarada e nunca importada (clients usam `httpx`) | `pyproject.toml:18` | Baixa | **ABERTO** |
| 05-20 | Sem teste unitário direto de `ai/router.py`, `ai_cache.py` e clients; pipeline coberto por `test_ai_pipeline.py` | `tests/` | **Alta** | **ABERTO** (parcial) → [14](14-test-strategy.md) |
| 05-21 | Classificação de intenção não separa categoria ERP de departamento; `CLASSIFY_SYSTEM` só devolve categoria | `ai/prompts.py` | **Alta** | **CORRIGIDO** — `INTENT_SYSTEM` + `ClassificacaoIntencao` separam intenção, categoria ERP e departamento sugerido |
| 05-22 | Resolução determinística de regras de roteamento inexistente | `services/` | **Alta** | **CORRIGIDO** — `services/routing_service.py` (`resolver`), determinístico e sem LLM na decisão |
| 05-23 | Diagnóstico não persiste intenção/departamento/artigos consultados/razão | `services/ai_pipeline.py`; `appwrite/schema.py` | **Alta** | **ABERTO** → 02, 10 |
| 05-24 | Sem dataset rotulado nem regressão de intenção/roteamento | `tests/` | Média | **ABERTO** → [14](14-test-strategy.md) |

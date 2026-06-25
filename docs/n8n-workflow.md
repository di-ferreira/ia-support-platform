# Fluxo n8n — EMSoft Support AI

## Visão Geral

O n8n atua como o **cérebro da operação**, orquestrando:

1. Recebimento de mensagens do WhatsApp (via Evolution API)
2. Consulta ao estado do chat na API interna
3. Busca na base de conhecimento (RAG via Qdrant)
4. Classificação e diagnóstico por IA (OpenAI/Ollama)
5. Atualização do status e salvamento do diagnóstico
6. Resposta automática ou transferência para humano

---

## Arquitetura do Workflow

```
Evolution API → Webhook → Extrair Dados
                                ↓
                     Consultar Contexto do Chat
                                ↓
                      ┌── Chat Existe? ──┐
                      ↓                   ↓
              Salvar Mensagem      Criar Novo Chat
                      ↓                   ↓
                   IA Deve Analisar?
                      ↓           ↓
                  [SIM]        [NÃO → Já é humano, ignorar]
                      ↓
              Buscar RAG (Qdrant)
                      ↓
              IA Analisar (LLM)
                      ↓
              Parsear JSON da IA
                      ↓
              Salvar Diagnóstico (API)
                      ↓
              ┌─ Roteamento por Cenário ─┐
              ↓           ↓              ↓
         Cenário A   Cenário B      Cenário C
         (Resolver)  (Transferir    (Transferir
          +Responder) com Solução)   sem Solução)
```

---

## Nós do Workflow

### 1. Webhook de Entrada — Evolution API
| Campo | Valor |
|---|---|
| Método | `POST` |
| Path | `/webhook/emsoft-whatsapp` |
| Autenticação | None (ou header fixo se configurado) |

**Configuração na Evolution API:**
```json
{
  "webhook": {
    "url": "https://n8n.internal:5678/webhook/emsoft-whatsapp",
    "events": ["messages.upsert"],
    "enable": true
  }
}
```

### 2. Extrair Dados da Mensagem
Campos extraídos do payload da Evolution API:
- `whatsapp_number` — número do cliente (sem @s.whatsapp.net)
- `conteudo` — texto da mensagem
- `tipo` — texto, audio, imagem, documento

### 3. Consultar Contexto do Chat
`GET {{API_URL}}/webhooks/chat/{{whatsapp_number}}/contexto`

Retorna o estado atual do chat ou `404` se não existir.

### 4. Chat Existe? (IF Node)
- **True**: Chat existe → salvar mensagem
- **False**: Novo número → criar chat + salvar mensagem

### 5. Salvar / Criar Mensagem
`POST {{API_URL}}/webhooks/mensagem`

Se `chat_id` for informado, adiciona ao chat existente.
Se não, cria novo chat com base no `whatsapp_number`.

### 6. IA Deve Analisar? (IF Node)
Analisa apenas se status for: `NOVO`, `IA_ANALISANDO`, `AGUARDANDO_CLIENTE`
Se já estiver em atendimento humano, pula a IA.

### 7. Buscar RAG — Qdrant
Coleção: `emsoft-knowledge-base`
- Query: conteúdo da mensagem do cliente
- Limite: 5 resultados
- Minimum score: 0.7

### 8. IA — Classificar e Diagnosticar (LLM Chain)

**Prompt do Sistema:**
```
Você é um especialista em suporte técnico do ERP EMSoft para autopeças.

Contexto da base de conhecimento:
{{rag_context}}

Mensagem do cliente:
{{mensagem_cliente}}

Com base nas informações acima, classifique e responda APENAS com JSON:

{
  "status_ia": "RESOLVIDO_PELA_IA | TRANSFERIR_COM_SOLUCAO | TRANSFERIR_SEM_SOLUCAO",
  "resumo_problema": "breve resumo do problema relatado",
  "causa_provavel": "causa provável identificada (ou null)",
  "solucao_encontrada": "solução sugerida (ou null)",
  "nivel_confianca": 0.95,
  "necessita_humano": false
}
```

**Modelo:** `gpt-4o-mini` (OpenAI) ou `llama3.2` (Ollama local)

### 9. Parsear JSON da IA
Converte a string JSON de saída da IA em campos estruturados usando `JSON.parse()`.

### 10. Salvar Diagnóstico
`POST {{API_URL}}/webhooks/chat/diagnostico`

Envia o diagnóstico completo da IA para a API:
```json
{
  "chat_id": 123,
  "status_ia": "RESOLVIDO_PELA_IA",
  "resumo": "NF-e rejeitada por CST incorreto",
  "solucao": "Ajustar CST para 00 no cadastro do produto",
  "causa_provavel": "Produto cadastrado com CST 60 ao invés de 00",
  "confianca": 0.95
}
```

### 11. Roteamento por Cenário (Switch Node)

| Saída | Cenário | Ação |
|---|---|---|
| `RESOLVIDO_PELA_IA` | A — IA resolveu | Status → RESOLVIDO + Responder cliente |
| `TRANSFERIR_COM_SOLUCAO` | B — Precisa de humano | Status → AGUARDANDO_HUMANO_COM_SOLUCAO |
| `TRANSFERIR_SEM_SOLUCAO` | C — IA não sabe | Status → AGUARDANDO_HUMANO_SEM_SOLUCAO |

### 12. Cenário A — Responder Cliente
`POST {{EVOLUTION_API_URL}}/message/sendText/{{EVOLUTION_INSTANCE}}`

Envia a solução encontrada diretamente para o WhatsApp do cliente.

---

## Variáveis de Ambiente do n8n

```env
# API do backend
API_URL=http://backend:8000
API_TOKEN=seu-token-jwt

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Ollama (fallback local)
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2

# Qdrant
QDRANT_URL=http://qdrant:6333

# Evolution API
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_INSTANCE=emsoft-support

# MinIO
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

---

## Pipeline de Ingestão — Base de Conhecimento

### Workflow de Upload de Documentos

```
Webhook (upload) → Extrair Texto → Chunking → Embedding → Inserir no Qdrant
```

### Estratégia de Chunking

| Parâmetro | Valor |
|---|---|
| Chunk size | 500 tokens |
| Chunk overlap | 50 tokens |
| Separator | `\n\n` |
| Embedding model | `text-embedding-3-small` (OpenAI) |

### Metadados por Chunk

```json
{
  "categoria": "fiscal | estoque | compras | vendas | financeiro",
  "titulo": "Título do documento",
  "fonte": "manual | faq | procedimento",
  "data_upload": "2026-06-25"
}
```

### Coleção Qdrant

**Nome:** `emsoft-knowledge-base`
**Dimensão:** 1536 (text-embedding-3-small)
**Distância:** Cosine

```http
# Criar coleção
PUT http://qdrant:6333/collections/emsoft-knowledge-base
{
  "vectors": {
    "size": 1536,
    "distance": "Cosine"
  }
}
```

### Script de Ingestão para Documentos em Massa

```bash
#!/bin/bash
# Uso: ./ingest-docs.sh docs/
for file in "$1"/*.{pdf,docx,txt,html}; do
  [ -f "$file" ] || continue
  echo "Ingestão: $file"
  curl -X POST http://localhost:5678/webhook/ingest-knowledge \
    -F "file=@$file" \
    -F "categoria=fiscal" \
    -F "titulo=$(basename "$file")"
done
```

---

## Instalação Rápida

### 1. Importar Workflow
1. Acesse `http://localhost:5678`
2. **Workflows → Add Workflow → Import from File**
3. Selecione `infra/n8n/workflow-support-ai.json`

### 2. Configurar Credenciais no n8n
- **HTTP Header Auth**: Criar credential com nome `EMSoft API Token`
- **OpenAI**: Criar credential com sua API Key
- **Qdrant**: Criar credential com URL `http://qdrant:6333`

### 3. Configurar Variáveis de Ambiente no n8n
Adicione em **Settings → Environment Variables**:
```
API_URL, API_TOKEN, OPENAI_API_KEY, QDRANT_URL,
EVOLUTION_API_URL, EVOLUTION_INSTANCE
```

### 4. Ativar Webhook na Evolution API
```bash
curl -X POST http://localhost:8080/webhook/set/emsoft-support \
  -H "Content-Type: application/json" \
  -d '{
    "webhookUrl": "http://n8n:5678/webhook/emsoft-whatsapp",
    "events": ["messages.upsert"]
  }'
```

---

## Testando o Workflow

### Enviar Webhook Manualmente
```bash
curl -X POST http://localhost:5678/webhook/emsoft-whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "body": {
      "data": {
        "key": { "remoteJid": "5511999999999@s.whatsapp.net" },
        "message": { "conversation": "NF-e 1234 rejeitada com erro de CST" }
      }
    }
  }'
```

### Fluxo Esperado
1. Webhook recebe a mensagem
2. Consulta API → chat não existe → cria
3. Busca RAG → encontra artigo sobre CST
4. IA classifica: `RESOLVIDO_PELA_IA` (confiança 0.92)
5. Salva diagnóstico + atualiza status para RESOLVIDO
6. Envia solução de volta para o WhatsApp

---

## Troubleshooting

| Problema | Causa | Solução |
|---|---|---|
| Webhook não dispara | Evolution API não configurada | Verificar webhook na Evolution API |
| Chat não encontrado | Número sem cadastro | Cliente precisa estar cadastrado no CRM |
| RAG não retorna resultados | Coleção vazia ou sem chunks | Executar pipeline de ingestão |
| Erro no parse do JSON | LLM não retornou JSON válido | Ajustar o prompt, adicionar few-shot examples |
| Status não atualiza | Token API inválido | Verificar `API_TOKEN` nas env vars do n8n |

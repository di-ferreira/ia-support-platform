# SPEC 11 — Integração com a API Interna de Chamados Emsoft

## Objetivo

Criar e atualizar chamados no sistema interno Emsoft a partir dos chats da IA Support Platform, mantendo o vínculo entre os dois sistemas e atribuindo o registro à IA ou ao atendente humano correto.

## Endpoint informado

Base informada pelo proprietário:

`https://emsoft.ddns.net/portal-api/v1/chamados`

O usuário informou que a API permite abrir, editar e listar chamados. A disponibilidade, autenticação, métodos, payloads, códigos de status, identificadores e regras de atribuição **não foram confirmados** neste documento. Uma tentativa de consulta pública ao endpoint retornou 502 no ambiente de pesquisa; isso não comprova indisponibilidade da API em execução normal.

## Gate obrigatório antes da implementação real

Não escrever o client final nem enviar POST/PATCH de produção antes de obter pelo menos um dos seguintes:

- Swagger/OpenAPI da API;
- coleção Postman;
- documentação interna;
- exemplos reais sanitizados de criação, listagem, edição e resposta.

Confirmar especificamente:

| Dado | Questão a confirmar |
|---|---|
| Autenticação | Bearer, Basic, API Key, cookie/sessão ou outro? |
| Listagem | Método/rota, paginação e filtro por ID/referência externa |
| Criação | Método/rota e campos obrigatórios |
| Edição | Método/rota e campos atualizáveis |
| ID | Nome/tipo do identificador do chamado |
| Cliente | ID externo, CNPJ ou outro vínculo |
| Contato | Nome, telefone, e-mail; quais são obrigatórios? |
| Responsável | Como informar ID do atendente humano? |
| IA | Como apontar o usuário técnico da IA? |
| Departamento | A API aceita departamento/fila ou somente atendente? |
| Status | Estados válidos e transições permitidas |
| Descrição | Campo, limite e suporte a texto longo/HTML/Markdown |
| Duplicidade | Suporte a idempotency key ou referência externa única? |
| Resposta | Estrutura JSON e códigos HTTP de sucesso/erro |
| Limites | Rate limit, timeout esperado e indisponibilidade |

O pacote não assume `Authorization: Bearer`, POST de criação, PATCH de atualização ou qualquer nome de campo externo.

## Arquitetura

```text
ChatService / ResolutionService / TransferService
                     |
                     v
             Domain Event / Outbox
                     |
                     v
       EmsoftChamadosIntegrationService
                     |
          +----------+-----------+
          |                      |
          v                      v
    Canonical Mapper       Emsoft API Client
          |                      |
          +----------+-----------+
                     |
                     v
        integracao_chamados (Appwrite)
```

Módulo proposto:

```text
backend/app/integrations/emsoft_chamados/
├── client.py       # HTTP, auth e tratamento técnico
├── schemas.py      # DTOs externos depois de conhecer OpenAPI
├── mapper.py       # modelo canônico -> contrato Emsoft
├── service.py      # create/update/reconcile
├── config.py       # configuração validada
└── exceptions.py   # erros de integração tipados
```

O frontend e n8n não chamam essa API. O client roda no backend/worker.

## Modelo canônico interno

Antes de mapear para a API externa, construir DTO independente do fornecedor:

```json
{
  "source": "IA_SUPPORT_PLATFORM",
  "source_chat_id": "<appwrite-chat-id>",
  "customer": {
    "internal_id": "<cliente-id>",
    "name": "Razão social",
    "document": "CNPJ"
  },
  "contact": {
    "whatsapp_number": "5511999999999"
  },
  "subject": "Erro na emissão de NF-e",
  "description": "Resumo e histórico relevante",
  "intent": "problema_tecnico",
  "erp_category": "fiscal",
  "department_code": "suporte_tecnico",
  "assignee": {
    "kind": "AI",
    "internal_id": null,
    "external_id": "<id-externo-confirmado>"
  },
  "diagnosis": {
    "summary": "Resumo do diagnóstico",
    "probable_cause": "Causa provável",
    "proposed_solution": "Passo a passo apoiado na base",
    "attempts": ["Tentativa 1", "Tentativa 2"],
    "knowledge_references": ["<artigo-id>"]
  },
  "platform_status": "AGUARDANDO_CLIENTE",
  "external_status_intent": "WAITING_CUSTOMER_CONFIRMATION"
}
```

Este é contrato interno ilustrativo; o mapper converte para o contrato externo após validação.

## Política de criação e atualização

### IA apresentou solução executável pelo cliente

- Criar chamado externo vinculado ao chat, atribuído ao usuário técnico IA.
- Conteúdo: cliente/contato, assunto, resumo, diagnóstico, solução, artigos, origem e ID do chat.
- Estado externo desejado: equivalente a aguardando confirmação do cliente, se houver status correspondente.
- Ao cliente confirmar: atualizar o mesmo chamado para o estado externo equivalente a resolvido/concluído.
- Ao cliente informar que não resolveu: atualizar o mesmo chamado, acrescentar tentativa e transferir responsável para atendente quando atribuído.

### IA transferiu com solução ou sem solução

- A conversa fica em estado humano e é vinculada ao departamento.
- Se API Emsoft suportar fila/departamento: criar o chamado no departamento e atualizar responsável após assunção.
- Se a API exigir um usuário individual: aguardar o atendente assumir/ser atribuído e só então criar o chamado no nome dele.
- O texto deve indicar se existe solução sugerida ou se o caso exige investigação.

### Pedido de outro departamento

- Criar/atualizar chamado no departamento correspondente.
- Não adicionar diagnóstico técnico irrelevante.
- Atribuir a pessoa efetivamente responsável assim que conhecida; não usar usuário IA como responsável de uma solicitação humana, exceto quando a IA ainda estiver conduzindo a triagem e a política tiver sido explicitamente aprovada.

### Transferência/alteração de atendente

- Atualizar o chamado externo existente.
- Não criar novo ticket a cada mudança de pessoa/setor.
- Se API não permitir edição do responsável, registrar limitação e apresentar ao supervisor; não mascarar como sincronizado.

## Regra de cardinalidade

Uma conversa (`chat_id`) tem no máximo um chamado externo ativo em `EMSOFT_CHAMADOS`. O vínculo é persistido em `integracao_chamados` antes de novas atualizações. Se chat for encerrado e reaberto, reusar o chamado externo, exceto se regra formal do sistema externo exigir novo ticket e houver ADR aprovada.

## Mapeamento de responsáveis

- IA: usuário técnico externo configurado e verificado; não presumir nome/ID.
- Humano: `atendentes.emsoft_usuario_id` para o usuário local atribuído.
- Departamento: mapear `departamentos.codigo` para ID/código externo somente depois de consultar API.
- Se ID externo ausente/inativo, não atribuir a usuário genérico silenciosamente. Marcar erro de mapeamento e notificar admin/supervisor.

## Descrição e dados enviados

Gerar resumo legível com blocos:

1. Origem e ID do chat.
2. Cliente e contato.
3. Departamento e responsável.
4. Assunto e intenção.
5. Problema observado.
6. Diagnóstico/causa provável.
7. Tentativas realizadas.
8. Solução sugerida e artigos (quando existirem).
9. Resultado atual e ação esperada do atendente.

Enviar somente dados necessários. Evitar copiar todo o histórico por padrão; incluir resumo e mensagens relevantes. O link para o chat interno pode ser incluído se houver URL segura/autorizada.

## Mapper

`mapper.py` recebe modelo canônico e cria DTO externo estritamente tipado. Não construir JSON de API dentro de `ChatService`. Campos obrigatórios ausentes devem falhar antes do POST com erro de mapeamento, não enviar payload incompleto.

## Autenticação e rede

- Credencial externa só no backend via secret manager/env.
- Verificar TLS/certificado; nunca desabilitar verificação SSL em produção.
- Timeout e limites configuráveis.
- Redigir `Authorization`, cookies e tokens dos logs.
- Não expor endpoint externo diretamente no frontend.

## Respostas e reconciliação

Após criar, persistir ID retornado, status, URL e metadados úteis. Se a resposta for ambígua (timeout após possível criação), consultar listagem por referência externa ou chave idempotente, se suportado, antes de repetir POST.

Se API não permitir pesquisa por `source_chat_id`, negociar com o responsável pelo sistema um campo externo de referência único. Sem mecanismo confiável para saber se o POST foi aplicado, não repetir automaticamente em timeout ambíguo; encaminhar para reconciliação manual.

## Critérios de aceite

- Integração é configurável e começa desabilitada.
- Client não contém auth/rotas/campos presumidos; todos vêm do contrato validado.
- IA cria um único ticket de serviço vinculado ao chat, no usuário IA verificado.
- Cliente confirmar atualiza o mesmo ticket para resolvido.
- Transferência humana cria/atualiza ticket no usuário atribuído.
- Transferência de departamento/atendente não duplica ticket.
- Falha externa gera estado pendente/erro, sem perder chat.
- Logs e UI não exibem credenciais.
- Testes usam mock da API e nunca produção.

## Registro de Gaps

Verificado contra o código em 2026-11-09. O scaffold da integração (contrato, adapter, coleção, config, rotas e reconciliação) existe e nasce desabilitado; falta apenas o artefato de contrato real (11-1) para uso em produção.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 11-1 | Gate de contrato: Swagger/OpenAPI, Postman ou exemplos reais da API de chamados **não obtidos** (probe 2026-11-09: endpoint vivo, envelope 401, sem Swagger público; re-probe 2026-11-10: endpoint vivo com 401 "Token de autenticação não fornecido", sem Swagger público (404), **cadeia de certificado TLS incompleta** — detalhes no [pedido de contrato](../pedido-contrato-api-emsoft.md)) | — | **Bloqueante** | **ABERTO (parcial)** — mecanismo do artefato implementado e testado (`contract.py`, `contract.example.json`, 18 testes passando); falta o artefato real preenchido e confirmado pelo responsável pela API — pedido formal criado em 2026-11-10 |
| 11-2 | Adapter/client `app/integrations/emsoft_chamados/` inexistente | `app/` | **Alta** | **CORRIGIDO** — contrato, client (timeout no POST → ambíguo, sem log de `Authorization`), mapper canônico e service |
| 11-3 | Coleção `integracao_chamados` inexistente | `appwrite/schema.py` | **Alta** | **CORRIGIDO** |
| 11-4 | Config `EMSOFT_CHAMADOS_*` inexistente | `core/config.py` | **Alta** | **CORRIGIDO** — enabled off por padrão; guard `verify_tls` em produção |
| 11-5 | Identidade IA (`EMSOFT_CHAMADOS_AI_USER_ID`) e mapeamento de atendentes/departamentos ausente | `core/config.py`; `app/` | **Alta** | **CORRIGIDO** — config + responsável canônico (atendente do chat ou IA) em `service._responsavel` |
| 11-6 | Endpoints `/integracoes/chamados/*` (consulta/reprocessamento) inexistentes | `api/routes/` | **Alta** | **CORRIGIDO** — `/status`, `/tickets`, `/{chat_id}/sincronizar` (503 quando off, 403 para atendente) |
| 11-7 | Reconciliação de timeout ambíguo e idempotência externa inexistentes | `app/` | **Alta** | **CORRIGIDO (escopo 11)** — reconciliação por listagem + re-PATCH pelo ID, nunca re-POST cego; confiabilidade mais ampla segue em [12](12-confiabilidade-integracoes.md) |

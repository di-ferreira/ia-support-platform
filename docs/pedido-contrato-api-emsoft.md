# Pedido de Contrato — API de Chamados Emsoft (gap 11-1)

**Status:** ABERTO (parcial) — mecanismo interno pronto, artefato externo pendente
**Aberto em:** 2026-11-10 (T0 do plano de priorização)
**Referência:** [SPEC 11 — Integração com a API Interna de Chamados Emsoft](specs/11-integracao-api-emsoft.md), §Gate obrigatório

## Por que este pedido é bloqueante

O scaffold da integração está completo e testado (contrato, client, mapper, service,
rotas, reconciliação — gaps 11-2 a 11-7 corrigidos). A plataforma nasce com a
integração **desligada** e nenhuma rota, método ou nome de campo é presumido:
tudo vem exclusivamente de um artefato de contrato validado.

As **Fases 5/6/7 (rollout)** não recebem task enquanto não obtivermos pelo menos
um destes artefatos (spec 11 §Gate obrigatório):

- Swagger/OpenAPI da API;
- coleção Postman;
- documentação interna;
- exemplos reais sanitizados de criação, listagem, edição e resposta.

## O que pedir

1. **Preferencial:** Swagger/OpenAPI (export) ou a documentação interna da
   `portal-api` (base informada: `https://emsoft.ddns.net/portal-api`).
2. **Alternativa:** coleção Postman, ou exemplos reais sanitizados de criação,
   listagem, edição e resposta.
3. **Se nenhum artefato existir:** confirmação formal, item por item, da tabela
   abaixo, assinada pelo responsável pela API.

## Dados a confirmar (tabela da spec 11)

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

## Como entregar (formato do contrato)

A plataforma consome os dados confirmados num JSON que já é validado por código:

- **Modelo (preencher):** `backend/app/integrations/emsoft_chamados/contract.example.json`
- **Validação:** `backend/app/integrations/emsoft_chamados/contract.py` — exige
  `validado: true`, bloco `evidencia` completo (`origem`, `data`, `descrito_por`,
  `detalhes`), `base_url` https e `endpoints.editar.path` com `{ticket_id}`.
- **Ponto de entrada:** env `EMSOFT_CHAMADOS_CONTRACT_FILE` (caminho do arquivo).

Passos de entrega:

1. Copiar `contract.example.json` para `contract.json` (ou outro nome) e substituir
   **todos** os `PREENCHER` pelos valores reais confirmados.
2. Definir `"validado": true` e preencher `evidencia` com a origem da confirmação
   (ex.: "Swagger em …", "Postman exportado em …"), a data, quem confirmou e detalhes.
3. Entregar o arquivo ao projeto chatbot-ia (repositório ou direto ao responsável).
4. Do nosso lado: posicionar o arquivo, apontar `EMSOFT_CHAMADOS_CONTRACT_FILE` e
   só então iniciar as Fases 5/6/7.

> Observação: o `base_url` no modelo é ilustrativo. Confirmar também o host real
> usado em produção (a base informada é via `ddns.net` — ver se há domínio interno).

## Evidências de probes (somente leitura; nada foi escrito na API)

### Probe de 2026-11-09 (registrada na spec 11)

- Endpoint vivo: envelope 401 `{"success":false,...}` em `GET /v1/chamados` sem auth.
- CORS expõe `Authorization` entre os headers permitidos.
- Sem Swagger público.
- Consulta pública anterior retornou 502 (não comprova indisponibilidade em operação).

### Probe de 2026-11-10 (reprovação)

| Verificação (todas `GET`, sem credencial) | Resultado |
|---|---|
| `GET /portal-api/` | **200** `{"message":"API is working!","status":"success"}` |
| `GET /portal-api/v1/chamados` | **401** `{"success":false,"resposta":"Token de autenticação não fornecido."}` |
| `GET /portal-api/docs` · `/openapi.json` · `/swagger.json` | **404** (sem Swagger público) |
| CORS `Access-Control-Allow-Methods` | `GET, POST, PUT, DELETE, OPTIONS, PATCH` |
| CORS `Access-Control-Allow-Headers` (candidatos a header de auth — **não confirmados**) | inclui `Authorization`, `X-Auth-Token`, `X-Access-Token` |

**Constatação TLS (reportar à equipe):** o servidor apresenta apenas o
certificado-leaf `CN=emsoft.ddns.net` (Let's Encrypt, válido 2026-10-05 a
2027-01-03) **sem a cadeia intermediada** (issuer `CN=YR2`). Consequência:

- `openssl s_client` → `Verify return code: 21 (unable to verify the first certificate)`;
- clientes padrão (`curl`, `fetch` do Node.js) falham a verificação
  (`curl: (60) SSL certificate problem`);
- a probe de 2026-11-10 só obteve respostas com verificação TLS desativada.

**Recomendação:** publicar a cadeia completa no servidor (`fullchain.pem` do
Let's Encrypt). Enquanto não for feita, o nosso client precisaria de CA explícita
(ou `EMSOFT_CHAMADOS_VERIFY_TLS=false`, bloqueado por guard em produção).

## O que NÃO será feito enquanto o contrato não chegar (restrição C5)

- Nenhuma chamada real de produção (**POST/PATCH**) à API de chamados — apenas
  probes `GET` de descoberta, como as acima.
- `EMSOFT_CHAMADOS_ENABLED` permanece `false`; as rotas respondem 503.
- Fases 5–7 (spec 13) não recebem task enquanto 11-1 persistir.

## Estado do mecanismo interno (verificado em 2026-11-10)

- `contract.py` + `contract.example.json`: prontos — testes
  `backend/tests/test_integracao_emsoft_chamados.py` (18 passando).
- Client/service/rotas: prontos (11-2 a 11-7), desligados por padrão;
  habilitar sem contrato válido ou token é erro de configuração explícito
  (`ContractNotValidatedError`).
- **Falta, apenas:** o artefato real preenchido e confirmado pelo responsável
  pela API — que é exatamente o objeto deste pedido.

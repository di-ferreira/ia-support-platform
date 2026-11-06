# ADR-0007 — Integração de chamados Emsoft via adapter e outbox

- **Status:** Proposta para aprovação após validação do contrato externo
- **Contexto:** A IA Support Platform precisa criar/atualizar chamados no sistema interno Emsoft. A API externa é independente e seu contrato ainda não foi disponibilizado/confirmado.

## Decisão proposta

- Somente backend FastAPI comunica com a API Emsoft.
- Criar adapter (`client`, `mapper`, `service`) para isolar o contrato externo.
- Persistir pedidos de sincronização em outbox e processar assincronamente.
- Um chat possui no máximo um chamado externo vinculado por integração.
- Solução apresentada pela IA cria ticket com usuário técnico da IA e estado aguardando confirmação, se o contrato externo tiver estado equivalente.
- Confirmação do cliente atualiza o mesmo ticket para resolvido.
- Transferência/assunção humana atualiza o mesmo ticket para o responsável externo correspondente.
- Se API não suportar fila, criação para humano aguarda atribuição individual.
- Segredos ficam no backend; n8n/frontend nunca recebem credencial.

## Condições para implementação

A decisão só pode ser considerada aceita para produção depois de validar autenticação, métodos, DTOs, IDs, status, atribuição e estratégia de idempotência no Swagger/Postman ou exemplos reais de sandbox. Não inferir `Bearer`, `POST`, `PATCH`, nomes de campos ou estados externos.

## Consequências

- Consistência entre Appwrite e Emsoft é eventual, não transacional.
- Falhas são registradas e reprocessadas sem bloquear a conversa.
- Timeouts ambíguos exigem reconciliação antes de repetir criação.
- Métricas e alertas de outbox passam a ser parte da operação.

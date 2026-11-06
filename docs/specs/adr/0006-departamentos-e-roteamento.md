# ADR-0006 — Departamentos como entidades e roteamento determinístico

- **Status:** Proposta para aprovação antes da Fase 1
- **Contexto:** O modelo atual usa strings livres `atendentes.setor` e `chats.setor_alvo`. Isso duplica nomes no frontend e não separa equipe responsável de pessoa atribuída. Além disso, categoria ERP e departamento têm semânticas distintas.

## Decisão proposta

- Criar coleção `departamentos` com código estável e ID Appwrite.
- Criar `regras_roteamento` relacionando intenção/categoria/subintenção a departamento.
- Usar `atendentes.departamento_id` e `chats.departamento_id` como referências canônicas.
- Manter `chats.atendente_id` opcional e compatível com `departamento_id`.
- Manter `setor` e `setor_alvo` temporariamente como legado de migração.
- O LLM classifica/sugere; backend valida regra e executa transferência.

## Alternativas consideradas

1. Continuar com strings livres: rejeitada por risco de inconsistência e difícil governança.
2. Usar categoria ERP como departamento: rejeitada porque fiscal/estoque/vendas descrevem o assunto e não necessariamente a equipe responsável.
3. Fazer o LLM escolher livremente o nome do setor: rejeitada por não ser determinística nem validável.

## Consequências

- Exige migração aditiva no Appwrite e atualização frontend/backend.
- `departamento_id` persiste quando atendente é atribuído.
- Conflitos/intenções ambíguas precisam de esclarecimento ou triagem geral.

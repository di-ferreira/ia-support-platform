# Prompt de execução para OpenCode / agente de programação

Você é responsável por implementar a IA Support Platform respeitando a fonte oficial `docs/specs/`.

## Regras obrigatórias

1. Antes de editar, leia `README.md`, `docs/specs/00` a `13`, todos os ADRs disponíveis, `AGENTS.md`, `docs/specs/` e `.ai/PROJECT.md` e skills do repositório.
2. Inspecione os arquivos reais; não assuma que documentação e código estão sincronizados.
3. Implemente somente uma fase/tarefa por vez. Não desenvolva todo o pacote em uma única alteração.
4. Preserve stack e arquitetura: FastAPI, Appwrite, Redis, Qdrant, n8n, Evolution API, Next.js. Não introduza microserviços, CQRS ou agentes autônomos sem decisão aprovada.
5. Backend é autoridade para classificação validada, roteamento, estado, autorização e integrações.
6. n8n é transporte WhatsApp; nunca colocar nele prompt de negócio, lógica de departamento ou chamada à API Emsoft.
7. Diferencie intenção, categoria ERP e departamento.
8. Não chame API Emsoft nem invente autenticação, rotas, campos ou status. O desenvolvimento real depende de contrato OpenAPI/Postman/exemplos sanitizados. Até lá, implemente interface, mocks e contract tests.
9. Não duplicar chamado externo. Um chat tem um vínculo externo por integração; transferências atualizam o mesmo registro.
10. Use outbox/idempotência; timeout de criação exige reconciliação antes de novo POST.
11. Toda transição de estado passa pelo serviço de domínio e valida `STATUS_TRANSITIONS`.
12. Testes primeiro para regras de domínio. Não reduzir cobertura nem esconder falhas preexistentes.
13. Nunca exibir, logar ou commitar segredos.

## Processo para cada tarefa

1. Resuma o comportamento atual com arquivos e símbolos reais.
2. Liste divergências entre código e SPEC relevante.
3. Proponha plano mínimo de alteração.
4. Escreva/ajuste testes para o comportamento esperado.
5. Implemente em camadas (schema/repository/service/route/UI conforme necessário).
6. Execute testes e verificações relevantes; informe resultados reais.
7. Atualize a SPEC/ADR se uma decisão aprovada mudar.
8. Entregue resumo, arquivos alterados, testes executados e pendências.

## Primeira tarefa recomendada

Executar somente a Fase 0 de `13-plano-implementacao.md`: auditoria da implementação atual e relatório de divergências. Não editar código funcional nessa primeira tarefa.

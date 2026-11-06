# ADR-0004 — Backend é o dono da inteligência e das decisões de IA

- **Status:** Aceita (consolidada a partir da decisão já referenciada no README e nas specs atuais)
- **Contexto:** A solução utiliza n8n para integrar Evolution API, backend, LLM e WhatsApp. Colocar prompts e decisões de negócio no workflow torna comportamento difícil de testar, versionar e auditar.

## Decisão

O backend FastAPI é a única autoridade para:

- classificação de intenção e categoria ERP;
- construção de contexto e consulta RAG;
- diagnóstico e geração de orientação;
- escolha entre resolução, pergunta adicional e transferência;
- aplicação de transições de estado;
- seleção/validação de departamento e responsável;
- criação de eventos e sincronização de chamados externos.

O n8n limita-se a receber eventos WhatsApp, chamar endpoints do backend e enviar a resposta indicada pelo backend.

## Consequências

- Regras são implementadas em serviços testáveis e versionados.
- O workflow n8n não contém prompts de negócio, mapeamento de departamento ou credencial Emsoft.
- Mudanças na IA são testadas no backend e em datasets de avaliação.
- Outros canais futuros devem chamar o mesmo backend, sem duplicar decisão de negócio.
- O LLM produz propostas estruturadas; o backend valida e executa ações.

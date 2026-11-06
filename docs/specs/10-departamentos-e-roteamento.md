# SPEC 10 — Departamentos, Classificação de Intenção e Roteamento

## Objetivo

Permitir que a IA entenda o assunto do cliente, diferencie assunto do ERP de destino organizacional e encaminhe para equipe e atendente corretos.

## Modelo organizacional

- Departamento é entidade cadastrável (`departamentos`).
- Atendente tem um departamento principal nesta fase (`atendentes.departamento_id`).
- Chat guarda departamento responsável (`chats.departamento_id`) e atendente responsável opcional (`chats.atendente_id`).
- Um chat pode estar em um departamento sem atendente atribuído.
- Um atendente atribuído deve ser ativo e pertencer ao departamento, salvo override de supervisor/admin justificado e auditado.

Departamentos iniciais sugeridos (cadastro de seed, configurável):

| Código | Nome | Uso |
|---|---|---|
| `suporte_tecnico` | Suporte Técnico | Erros, falhas e dúvidas técnicas do ERP |
| `financeiro` | Financeiro | Cobrança, boleto, negociação e faturamento da relação comercial |
| `comercial` | Comercial | Contratação, propostas e novos produtos |
| `administrativo` | Administrativo | Cadastro e assuntos administrativos |
| `implantacao` | Implantação | Configuração inicial, migração e treinamento |
| `atendimento_geral` | Atendimento Geral | Triagem e solicitações ainda sem setor definido |

Não criar departamentos adicionais automaticamente com base em texto livre.

## Separação das três dimensões

Exemplo: “Não consigo emitir uma NF-e”.

- Intenção: `problema_tecnico`.
- Categoria ERP: `fiscal`.
- Departamento: `suporte_tecnico`.

Exemplo: “Quero negociar uma mensalidade”.

- Intenção: `solicitacao_financeira`.
- Categoria ERP: `null` ou assunto financeiro contratual (não inferir módulo ERP).
- Departamento: `financeiro`.

## Regras de roteamento

1. Pedido explícito de falar com um setor reconhecido tem precedência.
2. Intenção classificada é resolvida por `regras_roteamento`, não por nome gerado livremente pelo LLM.
3. `categoria_erp` refina a regra de suporte técnico; não define automaticamente o departamento.
4. Destino deve existir e estar ativo.
5. Regra mais específica (intenção + subintenção + categoria ERP) vence regra genérica, segundo prioridade determinística.
6. Se houver conflito empatado, pedir esclarecimento ou encaminhar a `atendimento_geral` conforme regra configurada.
7. Confiança de intenção abaixo do threshold configurado exige esclarecimento, salvo pedido explícito claro.
8. Após duas perguntas sem informação suficiente (limite configurável), encaminhar à triagem geral.
9. Quando cliente pede humano, parar ciclo de diagnóstico automático e preservar histórico.
10. Quando chat muda de departamento, limpar atendente atual; quando um atendente assume, manter departamento e atribuir `atendente_id`.
11. Transferência entre pessoas do mesmo departamento mantém o departamento.
12. Transferência interdepartamental atualiza departamento e remove responsável antigo até nova atribuição.

## Processo de assunção

- Fila de departamento lista chats sem `atendente_id` e que estejam em estados humanos.
- Atendente clica “Assumir”; backend valida ativo, departamento, estado e ausência de conflito.
- Backend atribui `atendente_id`, mantém `departamento_id`, registra evento e agenda update do chamado Emsoft.
- Se outro atendente assumir simultaneamente, uma única operação vence; a outra recebe 409.

## Transferência humana imediata

Supervisor/admin pode atribuir diretamente a um atendente de destino. O backend valida compatibilidade e registra motivo. Quando a API Emsoft exigir ID externo de usuário, resolver por `atendentes.emsoft_usuario_id`; se ausente, marcar integração como bloqueada/erro de mapeamento e não atribuir a uma pessoa diferente.

## Classificação ambígua

Cliente: “Preciso resolver uma situação com vocês”.

Resposta esperada: pergunta curta para determinar se é problema no sistema, financeiro, comercial ou outro. Não transferir arbitrariamente.

Cliente: “Quero falar com o comercial”.

Resposta esperada: roteamento direto para `comercial`, sem consulta RAG.

Cliente: “Quero falar com uma pessoa”.

Resposta esperada: se já existe departamento contextual válido, encaminhar para ele; caso contrário, perguntar qual área ou encaminhar para triagem geral conforme configuração.

## Critérios de aceite

- Departamento pode ser criado/editado/desativado por admin.
- Supervisor e atendente só visualizam o escopo permitido.
- Categoria ERP não é exibida nem persistida como departamento.
- Chat em fila possui `departamento_id` e `atendente_id=null`.
- Chat assumido possui ambos os IDs.
- Transferência atualiza departamento/responsável e histórico de auditoria.
- Destino inválido/inativo nunca é aceito pelo backend.
- Conflito de atribuição concorrente resulta em apenas um responsável.
- Testes cobrem intenções conhecidas, ambíguas, baixa confiança e pedido explícito por humano.

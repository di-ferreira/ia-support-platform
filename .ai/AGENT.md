Você é um Arquiteto de Software Sênior, Especialista em IA/RAG e Engenheiro Full-Stack. Estou desenvolvendo uma aplicação própria e simplificada (baseada nos conceitos de multiatendimento e Kanban do Chatwoot), focada 100% no canal WhatsApp. 

O objetivo principal da aplicação é automatizar e otimizar o SUPORTE TÉCNICO de um ERP voltado para o setor de AUTOPEÇAS (carros e motos). Nossa equipe de suporte lida diariamente com dúvidas sobre o sistema, homologação de recursos e resolução de erros/rejeições fiscais ou operacionais.

Minha infraestrutura e stack de microsserviços serão:
1. Aplicação Própria (Backend + Frontend): Painel onde os atendentes humanos respondem as mensagens e movem os chamados em um Kanban de suporte.
2. Evolution API: Gateway de conexão nativa com o WhatsApp.
3. n8n (Self-hosted): O orquestrador dos fluxos de mensagens, condições e integração com a IA.
4. Modelo de IA (LLM) + Banco de Vetores (RAG): Alimentado com nossos arquivos de documentação, base de conhecimento e manuais de erro do ERP.

REGRAS DE NEGÓCIO DO PROCESSO DE ATENDIMENTO (O fluxo que precisamos construir):
- Primeiro Contato: A IA atende o cliente no WhatsApp e tenta entender a dúvida ou o erro relatado.
- Consulta ao RAG: A IA busca na base de conhecimento a resolução para aquele problema específico de autopeças/ERP.
- Cenário A (Resolução Direta): Se a IA encontrar a solução e for algo orientativo que o próprio cliente possa fazer, ela instrui o cliente e encerra o chamado se resolvido.
- Cenário B (Transbordo com Resolução): Se a IA encontrar a resolução, mas o problema exigir intervenção humana (ex: ajuste em banco de dados ou liberação de tela), ela envia o chamado para um atendente no painel, anexando um resumo do problema e a forma exata de resolvê-lo.
- Cenário C (Transbordo sem Resolução): Se a IA NÃO encontrar a resposta na base de conhecimento, ela deve coletar o máximo de detalhes com o cliente e transferir o chamado para o atendente humano com um relatório detalhado do erro.

Por favor, me guie no desenho da arquitetura, modelagem e codificação desse projeto de forma modular. Divida nossa jornada nas seguintes fases sequenciais e aguarde minha confirmação antes de passar para a próxima:

---

FASE 1: ARQUITETURA DE ESTADOS DO CHAMADO E ESTRATÉGIA DE RAG
1. Proponha a máquina de estados ideal para o "Status do Chat" no banco de dados para cobrir perfeitamente as regras de negócio (Ex: 'IA_ANALISANDO', 'AGUARDANDO_HUMANO_COM_SOLUCAO', 'AGUARDANDO_HUMANO_SEM_SOLUCAO', 'EM_ATENDIMENTO_HUMANO', 'RESOLVIDO').
2. Explique como estruturar o pipeline de RAG dentro do n8n (arquivos de texto, PDFs, embeddings e estratégia de chunking para manuais do ERP) para garantir que a IA diferencie erros parecidos.
3. Me pergunte quais tecnologias pretendo usar no Backend e Frontend da minha aplicação para que as próximas fases venham na linguagem correta.

FASE 2: MODELAGEM DO BANCO DE DADOS (SQL) PARA SUPORTE ERP
1. Crie o esquema de banco de dados (tabelas essenciais): Atendentes, Clientes/Lojas de Autopeças, Mensagens (histórico), Chats/Chamados (com os status mapeados na Fase 1, além de campos para 'resumo_do_erro' e 'solucao_sugerida_pela_ia') e Etapas_Kanban.
2. Forneça os scripts DDL de criação dessas tabelas de forma otimizada.

FASE 3: ENGENHARIA DO WORKFLOW NO N8N (O CÉREBRO DA OPERAÇÃO)
1. Desenhe a lógica estrutural (nós/nodes) do workflow do n8n que fará a interceptação da mensagem da Evolution API e a consulta à nossa API interna para verificar se o chat está sob controle da IA ou do Humano.
2. Explique como configurar o Prompt do nó de IA (Advanced AI) no n8n para que ele formate o JSON de saída corretamente para a nossa API contendo o diagnóstico do erro quando precisar transferir para o humano.

FASE 4: ESPECIFICAÇÃO DA API REST (BACKEND)
1. Desenhe os endpoints essenciais para o n8n atualizar o banco de dados (ex: salvar mensagem, atualizar status do chat, injetar o resumo/solução da IA no chamado).
2. Desenhe os endpoints para o Frontend (listar chamados pendentes, filtrar por chamados onde a IA já achou a solução vs chamados críticos sem solução, enviar mensagem de volta usando a Evolution API).

FASE 5: INTERFACE DO PAINEL E KANBAN DE SUPORTE (FRONTEND)
1. Estruture a lógica da tela de atendimento, mostrando visualmente para o atendente o "resumo do problema" e o "guia de solução" gerados pela IA no topo do chat.
2. Estruture o painel Kanban para que o supervisor de suporte veja quais chamados estão na fila urgentes (sem solução da IA) e quais já entram na fila com a receita de bolo pronta para o técnico executar.

---

Para começarmos, faça uma breve análise técnica sobre como essa arquitetura com n8n e RAG mitigará o gargalo do suporte técnico do ERP e me apresente as propostas e discussões da FASE 1.

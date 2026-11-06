# SPEC 07 — Frontend (Painel de Atendimento)

## Responsabilidade

O frontend Next.js exibe e coleta ações do operador. Não contém prompt, classificador, RAG, regra de roteamento ou chamada direta à API Emsoft. Todas as regras são aplicadas no backend FastAPI.

## Stack declarada

- Next.js 15 App Router.
- React 19 e TypeScript 5.6.
- Tailwind CSS 4.
- Zustand 5 para estado local.
- TanStack Query 5 para server state/cache.
- Componentes próprios e Radix primitives; lucide-react.
- WebSocket para eventos em tempo real, com polling de fallback.
- Design tokens referenciados em `DesignSystem/brand-spec.md` e aplicados por `frontend/src/app/globals.css`.

Não assumir troca de stack durante esta iniciativa.

## Rotas existentes

Manter `/login`, `/atendimento`, `/kanban`, `/dashboard`, `/conhecimento`, `/cliente`, `/usuarios` e `/configuracoes`. Não recriar rotas já removidas do escopo sem decisão formal.

## Novas capacidades de UI

### Gestão de departamentos

Adicionar seção `/departamentos` ou aba em `/configuracoes`, conforme padrão de navegação atual:

- listar departamentos ativos/inativos;
- criar/editar nome, descrição, ordem e recebimento de transferência;
- desativar sem apagar referências;
- visualizar atendentes associados;
- impedir exclusão/desativação incompatível com regra de negócio, explicando dependências.

### Associação de atendentes

No formulário de usuário, selecionar departamento por ID entre departamentos ativos. Se houver suporte a múltiplos departamentos futuramente, modelar associação N:N em spec própria; nesta versão manter um departamento principal por atendente, salvo se código atual provar o contrário.

### Atendimento / Inbox

O painel de IA deve mostrar, quando disponível:

- intenção e subintenção;
- categoria ERP;
- departamento sugerido e departamento final;
- justificativa do roteamento;
- resumo/causa provável;
- solução sugerida e artigos consultados;
- nível de confiança como dado auxiliar, nunca como prova de correção;
- status e responsável atual;
- estado da sincronização externa, ID/link do chamado Emsoft e erro sanitizado para perfis autorizados.

Ações: transferir departamento, atribuir atendente, confirmar resolução, informar que não resolveu e solicitar intervenção humana. Ações devem chamar endpoints; não atualizar estado local como se a API tivesse confirmado antes da resposta.

### Kanban

- Filtrar por departamento e/ou responsável segundo RBAC.
- Indicar chats sem atendente e com integração externa pendente/erro.
- Preservar ordenação por prioridade e data.
- Não duplicar o mesmo chat em várias colunas por causa do vínculo externo.

### Dashboard

Adicionar métricas por departamento, cenário de IA, solução confirmada e saúde da integração Emsoft. Todos os dados respeitam o escopo RBAC; corrigir eventual exposição de KPIs globais para perfis sem autorização.

### Configuração da integração

Exibir somente estado habilitado/desabilitado, conectividade conhecida, últimas sincronizações e filas pendentes. Não mostrar token, header de autenticação ou payload sensível. A edição de credenciais é operacional via ambiente/secret manager, não via UI na primeira versão.

## Cache e tempo real

- TanStack Query é a fonte de server state.
- Invalidar `chats`, `mensagens`, `dashboard`, `departamentos` e `integracoes` ao receber eventos relevantes.
- WebSocket precisa de reconexão com backoff exponencial e polling de fallback.
- Não gravar JWT em query string do WebSocket na nova implementação; adotar mecanismo autenticado compatível com servidor/proxy.
- Atualizar interface após resposta confirmada do backend.

## Estados de interface obrigatórios

Cada tela deve contemplar carregando, vazio, erro, sucesso e validação. Integração pendente não deve bloquear o chat; exibir status de sincronização separado.

## Design system

Usar tokens existentes; evitar cores raw de Tailwind fora do tema. Priorizar consistência de componentes para selects, badges, feedback e estados de carregamento. Não introduzir biblioteca visual completa sem necessidade.

## Acessibilidade e conteúdo

- Labels explícitos e navegação por teclado.
- Status com texto/ícone, nunca apenas cor.
- Dados técnicos devem ser legíveis e copiáveis.
- Resumo gerado por IA deve ser identificável como sugestão automática até revisão humana.

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

Rotas: `/login`, `/atendimento`, `/kanban`, `/dashboard`, `/conhecimento`, `/cliente`, `/usuarios`, `/departamentos` (nova) e `/configuracoes`. Não recriar rotas já removidas do escopo sem decisão formal.

Estado atual (2026-11-11): `/departamentos` foi criada como rota própria (link na sidebar, visível a todos; escrita restrita a admin) e `/atendimento` foi reorganizado em três colunas — inbox com filtro por departamento, conversa e painel de diagnóstico/sincronização.

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

**Estado (2026-11-11):** o inbox entregue cobre os itens acima (com filtro por departamento e painel de sincronização lendo os endpoints locais da integração). Kanban e dashboard ainda não exibem departamento nem saúde da integração; os itens das seções seguintes permanecem como alvo.

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

## Registro de Gaps

Verificado contra o código em 2026-11-06.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 07-1 | Token JWT do WebSocket na query string | `hooks/use-chat-socket.ts` | **Alta** | **CORRIGIDO** — token enviado como 1ª mensagem |
| 07-2 | Sem refresh token/renovação; sessão cai após 60 min | `lib/stores/auth-store.ts`; `core/config.py:20` | **Alta** | **CORRIGIDO** (2026-11-10) — `refresh_token` persistido no storage; interceptor em `api.ts` renova a sessão via `POST /auth/refresh` em 401 (retry único); em falha limpa o storage e volta para `/login` |
| 07-3 | WebSocket sem reconexão nem backoff | `hooks/use-chat-socket.ts` | Média | **CORRIGIDO** (2026-11-12) — reconexão automática com backoff exponencial + jitter (1s → teto 30s) em `lib/reconnect.ts` (função pura `proximoBackoff` testável), reset ao reconectar, status `conectado`/`reconectando` exposto ao hook e invalidação central de query por evento recebido |
| 07-4 | Cores raw do Tailwind (`green/red/blue/gray`) fora dos tokens `@theme` | `(app)/atendimento/page.tsx`, `dashboard/page.tsx`, demais telas | Média | **CORRIGIDO** (2026-11-12) — 8 tokens semânticos `--color-status-*` (e `-soft`) em `@theme` de `globals.css`; nenhum `.tsx` usa cor raw de estado/neutra (varredura travada por `tokens.test.ts`) |
| 07-5 | `chat-store` (`chatAtivo`) não é usado; estado local duplica a fonte | `lib/stores/chat-store.ts` vs `(app)/atendimento/page.tsx:15` | Baixa | **CORRIGIDO** (2026-11-12) — `chat-store` (Zustand) como fonte única do chat ativo: `chatAtivo` (id + objeto) no store, seleção/troca/limpeza só nele, evento `chat_atualizado` atualiza o chat ativo sem refetch; `useState` local removido da página de atendimento |
| 07-6 | Selects de status/prioridade usam `<select>` nativo | `(app)/atendimento/page.tsx:226,235` | Baixa | **CORRIGIDO** (2026-11-12) — `Select`/`SelectItem` sobre `@radix-ui/react-select` em `components/ui/select.tsx` (teclado, `aria-label` e foco visíveis); os 8 selects nativos do app migrados; 3 testes em `select.test.tsx` |
| 07-7 | Manifest referenciava `relatorios.html` fora de escopo | `DESIGN-MANIFEST.json` | Média | **CORRIGIDO** |
| 07-8 | Manifest referenciava `ia-dashboard.html` fora de escopo | `DESIGN-MANIFEST.json` | Média | **CORRIGIDO** |
| 07-9 | Sem telas de departamento, fila por departamento e transferência por departamento | `frontend/src/app/` | **Alta** | **CORRIGIDO** (2026-11-11) — `/departamentos` (CRUD admin, atendentes, regras, fila com "Assumir" via `PATCH /chats/{id}/pegar`), filtro por departamento no inbox e transferência via `PATCH /chats/{id}/transferir-departamento` → [10](10-departamentos-e-roteamento.md) |
| 07-10 | Sem painel de diagnóstico de intenção/roteamento nem status de sincronização do chamado | `(app)/atendimento/page.tsx` | **Alta** | **CORRIGIDO** (2026-11-11) — painel lê `GET /chats/{id}/roteamento` (intenção/categoria/destinos/motivo/confiança/artigos) e `GET /integracoes/chamados/{chat_id}` (visão limitada ao atendente responsável, reprocessar admin/supervisor); ações de transferir/atribuir/confirmar/não resolveu/solicitar humano → 10, 11 |
| 07-11 | Sem guarda de rota por perfil | `(app)/layout.tsx` | Média | **ABERTO** → [04](04-rbac-matrix.md) |

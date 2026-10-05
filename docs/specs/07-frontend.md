# SPEC 07 — Frontend (painel do atendente)

O frontend é o painel web do atendente. Ele não contém regra de negócio nem prompt de IA:
consome a API REST do backend, reflete o estado do chat em tempo real via WebSocket, e aplica
o DesignSystem `DesignSystem/`. A decisão é [adr/0004-backend-dono-da-ia.md](adr/0004-backend-dono-da-ia.md).

## Stack

| Camada | Tecnologia | Versão |
|---|---|---|
| Framework | Next.js (App Router, `"use client"`) | 15.x |
| Runtime | React | 19.x |
| Linguagem | TypeScript | 5.6.x |
| Estilo | Tailwind CSS (`@theme`) | 4.x |
| Estado | Zustand | 5.x |
| Server state / cache | TanStack Query | 5.x |
| UI base | Radix UI + primitivos próprios em `components/ui` | — |
| Ícones | lucide-react | 0.460 |
| Gráficos | recharts | 3.x |
| Tempo real | WebSocket nativo (`use-chat-socket`) | — |

Não há router de navegação por sidebar com guards de rota por perfil: a restrição de acesso
é feita no backend (RBAC). O frontend apenas redireciona para `/login` quando não há token.

## Rotas

Grupo de rotas `(app)` com layout autenticado (`(app)/layout.tsx`).

| Rota | Tela | Papel | Estado |
|---|---|---|---|
| `/login` | Login | Autenticação, guarda entrada | Implementada |
| `/` | Redireciona para `/atendimento` | Entrada | Implementada |
| `/atendimento` | Inbox + chat + painel IA | Operação principal | Implementada |
| `/kanban` | Quadro de status | Visão pipeline | Implementada |
| `/dashboard` | KPIs e gráficos | Gestão | Implementada |
| `/conhecimento` | Base de conhecimento | Artigos RAG | Implementada |
| `/cliente` | Clientes | CRM básico | Implementada |
| `/usuarios` | Usuários | Gestão de contas | Implementada |
| `/configuracoes` | Configurações | Config | Implementada |

O `DesignSystem/DESIGN-MANIFEST.json` lista **9 telas** de produto, incluindo `ia-dashboard.html`
e `relatorios.html`. Essas duas **não existem** no app — o usuário as cortou do escopo. O
manifest ainda as referencia, o que é drift. Ver gaps 07-7 e 07-8.

## Autenticação

- O login obtém um JWT que é gravado em `localStorage.token` (`lib/stores/auth-store.ts`).
- `(app)/layout.tsx` chama `GET /auth/me` com o token; se falhar, limpa o token e manda para
  `/login`. Se passar, popula o store com `perfil` (usado para rótulos, não para guards).
- Todo pedido HTTP injeta `Authorization: Bearer <token>` em `lib/api.ts`.
- O WebSocket recebe o token por **query string**: `ws://…/ws/chat/{id}?token=…`
  (`hooks/use-chat-socket.ts`). Isso expõe o token na URL/headers de proxy — ver gap 07-1.
- Não há refresh token no cliente, nem renovação automática. O token expira em 60 min
  (`access_token_expire_minutes`), o que encerra a sessão silenciosamente em uso longo —
  ver gap 07-2.

## Camada de dados

`lib/api.ts` expõe `api.get/post/patch/delete` genéricos sobre `fetch`.

- Base em `NEXT_PUBLIC_API_URL` (padrão `http://localhost:8000`).
- Erro vira `throw new Error(detail)`; quem trata é o `onError` do TanStack mutation.
- Padrão de cache: `useQuery` com `refetchInterval: 30000` para listas (`chats`, `mensagens`,
  `dashboard`) e invalidação dirigida por `queryKey` ao receber eventos WebSocket
  (`nova_mensagem`, `status_update`, `diagnostico`).

Stores Zustand: `auth-store`, `chat-store`, `sidebar-store`. `chat-store` é hoje um par de
arrays simples; `atendimento/page.tsx` mantém `chatAtivo` em `useState` local, não no store —
o store `chatAtivo` não é usado. Ver gap 07-5.

## Tempo real

`use-chat-socket(chatId)` abre `WebSocket /ws/chat/{chatId}` por chat ativo. Ao receber
`nova_mensagem`, `status_update` ou `diagnostico`, invalida os queries do chat. Há polling
paralelo de 30 s como rede de segurança. A reconexão é **ausente**: `onclose` só fecha,
`onerror` fecha, não há reabertura nem backoff. Ver gap 07-3.

## Design tokens

Fonte de verdade declarada: `DesignSystem/brand-spec.md`. Fonte de verdade aplicada:
`frontend/src/app/globals.css` via `@theme`.

| Token | `globals.css` (`@theme`) |
|---|---|
| `primary-500` | `#063778` (azul-escuro) |
| `primary-600` | `#052f66` |
| `accent-400` | `#f97316` (laranja) |
| `success` | `#16a34a` |
| `warning` | `#d97706` |
| `danger` | `#dc2626` |
| `info` | `#2563eb` |
| `font-sans` | Inter |
| `font-mono` | JetBrains Mono |

Os componentes usam tanto a escala `primary-*` quanto `gray-*`/`green-*`/`red-*`/`blue-*`
raw do Tailwind (ex.: `text-green-500`, `bg-red-500`, `border-red-300`). Há, portanto, cores
que **não passam pelos tokens** do design system. Ver gap 07-4.

## Componentes

Primitivos próprios sobre Radix em `components/ui/`: `button`, `badge`, `card`, `input`,
`select`. `components/layout/`: `sidebar`, `header`. `components/providers.tsx` monta o
QueryClient.

Não há biblioteca de UI pronta (shadcn/ui completo); os primitivos são o suficiente, mas
partes da UI (ex.: selects de status/prioridade em `atendimento`) usam `<select>` nativo
inline em vez do componente `components/ui/select`. Ver gap 07-6.

## Estados obrigatórios por tela

Cada tela de produto deve ter: vazio, carregando, erro, sucesso e (quando houver formulário)
validação. `atendimento` já implementa vazio e erro (banner fixo) e carregamento
(`Loader2`). As demais têm vazio/erro em graus variados — auditar por tela na implementação.

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 07-1 | Token JWT passado na query string do WebSocket (`?token=`), exposto em URL/headers de proxy | `hooks/use-chat-socket.ts:18` | **Alta** | **ABERTO** |
| 07-2 | Sem refresh token / renovação. Sessão cai após 60 min sem avisar o atendente | `auth-store.ts`, `config.py:20` | **Alta** | **ABERTO** |
| 07-3 | WebSocket sem reconexão nem backoff; queda de conexão mata o tempo real até o polling de 30 s | `hooks/use-chat-socket.ts:51-57` | Média | **ABERTO** |
| 07-4 | Cores raw do Tailwind (`green/red/blue/gray`) fora dos tokens `@theme`; inconsistência com o DesignSystem | `atendimento/page.tsx`, `dashboard/page.tsx` | Média | **ABERTO** |
| 07-5 | `chat-store` (`chatAtivo`) não é usado; estado local duplica a fonte de verdade | `chat-store.ts` vs `atendimento/page.tsx:15` | Baixa | **ABERTO** |
| 07-6 | Selects de status/prioridade usam `<select>` nativo em vez de `components/ui/select`; quebra de padrão visual | `atendimento/page.tsx:226-247` | Baixa | **ABERTO** |
| 07-7 | Manifest referencia `relatorios.html` fora de escopo | `DESIGN-MANIFEST.json` | Média | **ABERTO** → Fase 5 |
| 07-8 | Manifest referencia `ia-dashboard.html` fora de escopo | `DESIGN-MANIFEST.json` | Média | **ABERTO** → Fase 5 |

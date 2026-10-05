# SPEC 04 — Matriz de RBAC

Três perfis. A autorização é aplicada em duas camadas: **dependência de rota** e
**regra dentro do serviço**.

| Dependência | Comportamento |
|---|---|
| `get_current_user` (`backend/app/api/deps.py:42`) | Exige JWT válido + usuário ativo. 401 se falhar. |
| `require_perfil("admin", "supervisor")` (`deps.py:49`) | Além do acima, exige que o `perfil` esteja na lista. 403 se não. |

O `perfil` **nunca** vem do token: o backend relê o usuário do Appwrite a cada requisição
(`deps.py:34-37`). Desativar a conta invalida o token imediatamente, sem esperar expirar.

## Matriz

| Operação | `atendente` | `supervisor` | `admin` |
|---|:---:|:---:|:---:|
| **Autenticação** ||||
| `POST /auth/login` | ✅ | ✅ | ✅ |
| `POST /auth/refresh` | ✅ | ✅ | ✅ |
| `GET /auth/me` | ✅ | ✅ | ✅ |
| `PATCH /auth/password` | ✅ | ✅ | ✅ |
| **Usuários** ||||
| `GET /auth/usuarios` | ❌ | ✅ | ✅ |
| `POST /auth/usuarios` (perfil `atendente`) | ❌ | ✅ | ✅ |
| `POST /auth/usuarios` (perfil `supervisor`/`admin`) | ❌ | ❌ | ✅ |
| `GET /auth/usuarios/{id}` | ❌ | ✅ | ✅ |
| `PATCH /auth/usuarios/{id}` (nome, email, setor, ativo) | ❌ | ✅ | ✅ |
| `PATCH /auth/usuarios/{id}` (alterar `perfil`) | ❌ | ❌ | ✅ |
| `DELETE /auth/usuarios/{id}` | ❌ | ❌ | ✅ |
| **Clientes e lojas** ||||
| `GET /clientes`, `GET /clientes/{id}` | ✅ | ✅ | ✅ |
| `POST /clientes` | ❌ | ✅ | ✅ |
| `PATCH /clientes/{id}` | ❌ | ✅ | ✅ |
| `GET /clientes/{id}/lojas` | ✅ | ✅ | ✅ |
| `POST /clientes/{id}/lojas` | ❌ | ✅ | ✅ |
| **Chats** ||||
| `GET /chats` | ✅ filtrado | ✅ tudo | ✅ tudo |
| `GET /chats/{id}` | ⚠️ ver §Filtro | ⚠️ ver §Filtro | ✅ |
| `POST /chats` | ✅ | ✅ | ✅ |
| `PATCH /chats/{id}/status` | ✅ filtrado | ✅ | ✅ |
| `PATCH /chats/{id}/assinar` | ❌ | ✅ | ✅ |
| `PATCH /chats/{id}/prioridade` | ❌ | ✅ | ✅ |
| `PATCH /chats/{id}/pegar` | ✅ | ✅ | ✅ |
| `PATCH /chats/{id}/transferir` | ✅ só o próprio | ✅ | ✅ |
| `PATCH /chats/{id}/transferir-grupo` | ✅ | ✅ | ✅ |
| **Mensagens** ||||
| `GET /chats/{id}/mensagens` | ⚠️ ver §Filtro | ⚠️ ver §Filtro | ✅ |
| `POST /chats/{id}/mensagens` | ✅ | ✅ | ✅ |
| `POST /chats/enviar-whatsapp` | ✅ | ✅ | ✅ |
| **Operação** ||||
| `GET /dashboard` | ⚠️ **não filtrado** | ⚠️ não filtrado | ✅ |
| `GET /kanban` | ✅ filtrado | ✅ tudo | ✅ tudo |
| `PATCH /kanban/mover` | ✅ filtrado | ✅ | ✅ |
| `GET /knowledge-base`, `GET /knowledge-base/{id}` | ✅ | ✅ | ✅ |
| `POST`/`PATCH`/`DELETE /knowledge-base` | ❌ | ✅ | ✅ |
| `GET /atendentes/ativos` | ✅ | ✅ | ✅ |
| **IA (uso humano)** ||||
| `POST /ai/classificar`, `/ai/analisar`, `/ai/solucionar` | ✅ | ✅ | ✅ |
| **Webhooks (n8n)** ||||
| Todas `/webhooks/**` | — | — | — |
| **Evolution API** ||||
| Todas `/evolution/**` | ❌ | ❌ | ✅ |
| **Operação** ||||
| `GET /health`, `GET /settings/ia-name` | ✅ público | ✅ público | ✅ público |

## Regras dentro do serviço

A dependência de rota resolve o caso comum. Estas regras só podem ser aplicadas no
serviço, porque dependem do **dado sendo modificado**:

| Regra | Implementação |
|---|---|
| Supervisor só cria `atendente` | `AuthService.criar_usuario` |
| Só admin altera `perfil` | `AuthService.atualizar_usuario` |
| Só admin desativa | Dependência de rota |
| Atendente só transfere chat que é dele | `ChatService.transferir` |
| `pegar` falha se o chat já é de outro | `ChatService.pegar` |

## Filtro de visibilidade de chat

O `atendente` não vê a fila inteira. Ele vê:

1. Chats **sem** `atendente_id` cujo `setor_alvo` é igual ao seu `setor`, **ou** cujo
   `setor_alvo` é nulo (chat novo, sem setor ainda).
2. Os chats **que já são dele**.

Aplica-se em `GET /chats` e `GET /kanban`. Está implementado em `ChatService.listar` e
`KanbanService.obter_kanban`.

## Regras de frontend

A UI **reflete** a matriz, mas não a impõe. O backend é a única autoridade.

| Regra de UI | Onde |
|---|---|
| Link "Usuários" só para admin e supervisor | `components/layout/sidebar.tsx` |
| Link "Configurações" só para admin | `components/layout/sidebar.tsx` |
| Toggle Ativo/Inativo só para admin | `app/(app)/usuarios/page.tsx` |
| Indicador de status do WhatsApp só para admin | `components/layout/header.tsx` |
| Botão "Pegar" só quando o chat está livre | `app/(app)/atendimento/page.tsx`, `app/(app)/kanban/page.tsx` |

> `frontend/` oculta ações em vez de desabilitá-las, e não há guarda de rota por perfil.
> Um atendente que digitar `/usuarios` na barra de endereço chega à página — a API
> recusa, a tela fica vazia. Ver gap 04-3.

## Registro de Gaps

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 04-1 | `GET /dashboard` **não** aplica filtro de visibilidade. Atendente lê contagem global, `taxa_resolucao_ia`, `confianca_media` e o nome dos clientes dos 10 chats mais recentes, inclusive de outros setores | `routes/dashboard.py`, `dashboard_service.py` | **Alta** | **ABERTO** |
| 04-2 | `GET /chats/{id}`, `GET /chats/{chat_id}/mensagens` e `GET /clientes/{id}` **não** checam posse. Um atendente que descubra o id de um chat de outro setor lê tudo | `routes/chats.py`, `routes/mensagens.py`, `routes/clientes.py` | **Alta** | **ABERTO** |
| 04-3 | Frontend oculta ações por perfil em vez de desabilitar, e não tem guarda de rota. Digitando a URL, o atendente alcança `/usuarios` e `/configuracoes` (a API recusa, a tela fica vazia) | `sidebar.tsx`, `(app)/layout.tsx` | Média | **ABERTO** → [07-frontend](07-frontend.md) |
| 04-4 | Regra "supervisor só cria `atendente`" está no serviço, mas **não há teste** que confirme o 403 | `AuthService.criar_usuario`; sem teste em `tests/` | **Alta** | **ABERTO** → [10-test-strategy](10-test-strategy.md) |
| 04-5 | Regra "só admin altera `perfil`" está no serviço, **sem teste** | `AuthService.atualizar_usuario`; sem teste | **Alta** | **ABERTO** → [10-test-strategy](10-test-strategy.md) |
| 04-6 | `ChatService` cobre 4 dos 9 métodos em teste. `assinar`, `definir_prioridade`, `transferir`, `transferir_grupo`, `pegar` (taken) e `listar` (filtro) não têm teste | `tests/test_chat_service.py` | **Alta** | **ABERTO** → [10-test-strategy](10-test-strategy.md) |
| 04-7 | `WEBHOOK_SECRET` dá poder de **forçar o status de qualquer chat**, pulando a máquina de estados, e de **criar diagnóstico falso** em qualquer chat. Um segredo vazado é acesso total aos dados | `routes/webhooks.py`, `verify_webhook` | **Alta** | **ABERTO** → [08-non-functional](08-non-functional.md) |
| 04-8 | `EvolutionService.criar_instancia` engole 403 e devolve sucesso. O painel recebe 200 sem QR e não consegue distinguir "criado" de "recusado" | `evolution_service.py` | Média | **ABERTO** |
| 04-9 | `GET /atendentes/ativos` retorna dados de todos os atendentes ativos (id, nome, perfil, setor) para qualquer autenticado. Provavelmente aceitável, mas não está declarado como intencional | `routes/atendentes.py` | Baixa | **ABERTO** |
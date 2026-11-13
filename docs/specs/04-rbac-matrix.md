# SPEC 04 — Matriz de Permissões (RBAC)

## Perfis existentes

- `admin`: controle total da plataforma e configurações.
- `supervisor`: operação e gestão de equipe, sem poderes administrativos reservados ao admin.
- `atendente`: atendimento dentro do escopo de chats e departamento autorizado.

Não criar um perfil humano adicional para representar a IA. A IA é uma identidade de serviço interna, sem login interativo e sem acesso ao painel.

## Matriz de permissões

| Recurso/ação | Admin | Supervisor | Atendente |
|---|---:|---:|---:|
| Visualizar dashboard | Todos os dados | Dados dos departamentos permitidos | Apenas escopo próprio/departamento |
| Ver chats | Todos | Departamentos gerenciados | Chats do departamento/atribuição permitidos |
| Assumir chat | Sim | Sim | Se estiver disponível no seu departamento e sem responsável incompatível |
| Atribuir chat a outra pessoa | Sim | Sim, dentro de equipes gerenciadas | Não; pode solicitar transferência conforme política |
| Transferir departamento | Sim | Sim, dentro do escopo | Pode transferir o próprio chat conforme regra da operação |
| Alterar prioridade | Sim | Sim | Conforme permissão operacional já existente; default não alterar crítica sem regra |
| Encerrar/resolver | Sim | Sim | Chats sob sua responsabilidade |
| Gerenciar clientes | Sim | Sim | Leitura |
| Gerenciar atendentes | Sim | Criar/editar atendente conforme política; não alterar perfil admin | Não |
| Gerenciar departamentos | Sim | Leitura | Leitura de departamentos disponíveis |
| Gerenciar regras de roteamento | Sim | Leitura | Não |
| Configurar integração Emsoft | Sim | Leitura de saúde/status | Não |
| Reprocessar integração | Sim | Sim | Não |
| Ver diagnóstico e resumo IA | Sim | Sim | Chats visíveis ao atendente |
| Editar base de conhecimento | Sim | Sim | Não |
| Ver tokens/segredos | Não via UI; apenas configuração operacional controlada | Não | Não |

A tabela deve ser adaptada à matriz de permissões já implementada, sem ampliar acesso implicitamente. Qualquer diferença em código precisa ser refletida nos testes e nesta matriz.

## Regras de escopo

1. A autorização é aplicada no backend; esconder botão no frontend não é controle de segurança.
2. Supervisor só administra departamento(s) autorizados. O modelo atual não registra escopo múltiplo de supervisor; nesta etapa usar lista/associação explícita se o requisito existir. Não inferir permissão por nome de setor.
3. Atendente só pode assumir chat de departamento ao qual está associado, salvo transferência autorizada.
4. Atendente só pode alterar/encerrar chat dentro do escopo e se for responsável, exceto ação explicitamente concedida.
5. Admin pode mover qualquer chat e gerenciar departamentos/regras.
6. Dashboard, exportações, Kanban, busca e endpoints de detalhe devem aplicar o mesmo escopo; corrigir a ausência de filtro de visibilidade no dashboard identificada no contrato atual.
7. `departamento_id` do chat e do atendente devem ser comparados no serviço de atribuição; não confiar em `departamento_id` vindo apenas do frontend.

## Identidade de serviço da IA

- A IA não autentica no endpoint de usuário e não utiliza JWT pessoal de funcionário.
- As ações automáticas são executadas pelo backend sob identidade técnica auditável (`actor_type=SYSTEM/IA`).
- A integração Emsoft usa credencial de servidor com privilégio mínimo.
- O identificador externo do usuário IA é configuração (`EMSOFT_CHAMADOS_AI_USER_ID`) ou mapeamento administrável protegido; nunca hardcode em frontend.
- Usuário de serviço externo deve ser criado/confirmado no sistema Emsoft por administrador. Não criar conta externa automaticamente por API sem contrato e autorização.

## Auditoria obrigatória

Registrar ator, chat, ação, data/hora, departamento anterior/novo, atendente anterior/novo e motivo. Não registrar senha, token ou conteúdo integral sensível. Para ações automáticas, `actor_type=IA` e modelo/versão quando aplicável.

## Registro de Gaps

Verificado contra o código em 2026-11-06.

| # | Gap | Onde | Severidade | Status |
|---|---|---|---|---|
| 04-1 | `GET /dashboard` não aplica filtro de visibilidade; atendente lê KPIs globais e nomes de clientes | `api/routes/dashboard.py`; `services/dashboard_service.py` | **Alta** | **CORRIGIDO** — `DashboardService.obter_dashboard(user=...)` aplica escopo por departamento |
| 04-2 | `GET /chats/{id}`, `/chats/{id}/mensagens` e `/clientes/{id}` não checam posse | `api/routes/chats.py`; `mensagens.py`; `clientes.py` | **Alta** | **CORRIGIDO** — `ChatService.pode_ver_chat` + `obter_com_escopo` em `/chats/{id}`, `/chats/{id}/mensagens`, `/clientes/{id}` |
| 04-3 | Frontend oculta ações por perfil e não tem guarda de rota; digitando a URL alcança `/usuarios` e `/configuracoes` | `components/layout/sidebar.tsx`; `(app)/layout.tsx` | Média | **ABERTO** → [07](07-frontend.md) |
| 04-4 | Regra "supervisor só cria `atendente`" está no serviço e sem teste | `services/auth_service.py`; coberto por `tests/test_rbac_usuarios.py` | **Alta** | **CORRIGIDO** — teste cobre o 403 do supervisor e o 201 para `atendente` |
| 04-5 | Regra "só admin altera `perfil`" está no serviço e sem teste | `services/auth_service.py`; coberto por `tests/test_rbac_usuarios.py` | **Alta** | **CORRIGIDO** — teste cobre o 403 do supervisor, o 200 do admin e atualização sem `perfil` |
| 04-6 | `ChatService` cobre transições, mas `pegar`/`transferir`/`transferir_grupo`/`assinar`/`definir_prioridade`/`listar` (filtro) seguem sem teste | `tests/test_chat_service.py` | **Alta** | **CORRIGIDO** — `tests/test_chat_service.py` cobre pegar, transferir, transferir_grupo, assinar, definir_prioridade e listar (filtros/escopo), com happy path e negação |
| 04-7 | `WEBHOOK_SECRET` ainda força status de qualquer chat (pulando a máquina de estados) e cria diagnóstico; mitigado por fail-closed e rate limit | `api/routes/webhooks.py` | **Alta** | **CORRIGIDO** (2026-11-10) — atualização de status delegada à máquina de estados (400 em transição inválida, 404 em chat inexistente); diagnóstico em chat `ENCERRADO` bloqueado (400) → 01, 03 |
| 04-8 | `EvolutionService.criar_instancia` engole 403 e devolve sucesso sem QR | `services/evolution_service.py:31-34` | Média | **CORRIGIDO** (2026-11-13) — 403 na criação consultado via `get_status`: instância existente → `{..., "ja_existia": true, "status": ...}`; credencial recusada (404) → `EvolutionAuthError` mapeado para HTTP 403 na rota; coberto por `tests/test_evolution_criar_instancia.py` |
| 04-9 | `GET /atendentes/ativos` retorna id/nome/perfil/setor de todos os ativos para qualquer autenticado | `api/routes/atendentes.py` | Baixa | **CORRIGIDO** (2026-11-13) — escopo por departamento (regra 6): admin/supervisor veem todos os ativos; atendente, apenas os do seu departamento + ele mesmo; sem departamento, só ele mesmo |
| 04-10 | Escopo por departamento não é aplicado (departamento não existe) | `services/chat_service.py` | **Alta** | **CORRIGIDO** — `ChatService.listar` filtra por `departamento_id` |
| 04-11 | Identidade de serviço da IA / `actor_type` auditável não implementada | `app/` | Média | **CORRIGIDO** (2026-11-13) — `Ator` com `TipoAtor` (HUMANO/IA/SISTEMA/SERVICO) em todo registro da coleção `auditoria`; webhook de status grava `Ator.servico("n8n")`; visível em `GET /chats/{id}/auditoria` |
| 04-12 | Sem auditoria de atribuição/transferência (ator, motivo, antes/depois) | `app/` | Média | **CORRIGIDO** (2026-11-13) — `AuditoriaService.registrar` nas ações de atribuição/transferência com `Ator`, `motivo` e valores anterior/novo; exposto via `GET /chats/{id}/auditoria` |
| 04-13 | chat ENCERRADO podia ser assumido/atribuído (`pegar`/`assinar`/`atribuir_atendente`) | `services/chat_service.py` | Média | **CORRIGIDO** — 409 "Chat encerrado não pode ser atribuído" nas três ações; coberto por `tests/test_chat_service.py` |
| 04-14 | `PATCH /chats/{id}/status` e `PATCH /chats/{id}/prioridade` não exigiam posse: atendente de outro departamento mutava chamado alheio (prioridade já tinha guarda de perfil, mas sem checagem de posse no serviço) | `services/chat_service.py`; `api/routes/chats.py` | **Alta** | **CORRIGIDO** (2026-11-13) — `atualizar_status`/`definir_prioridade` aceitam `user` (keyword-only, opcional); quando informado, `pode_ver_chat` falso → 403 "Sem acesso a este chamado"; chamadas internas/webhooks seguem sem `user` e sem checagem; coberto por `tests/test_rbac_escopo_atendentes.py` |

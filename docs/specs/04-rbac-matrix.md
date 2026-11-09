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
| 04-2 | `GET /chats/{id}`, `/chats/{id}/mensagens` e `/clientes/{id}` não checam posse | `api/routes/chats.py`; `mensagens.py`; `clientes.py` | **Alta** | **ABERTO** |
| 04-3 | Frontend oculta ações por perfil e não tem guarda de rota; digitando a URL alcança `/usuarios` e `/configuracoes` | `components/layout/sidebar.tsx`; `(app)/layout.tsx` | Média | **ABERTO** → [07](07-frontend.md) |
| 04-4 | Regra "supervisor só cria `atendente`" está no serviço e sem teste | `services/auth_service.py`; sem teste | **Alta** | **ABERTO** → [14](14-test-strategy.md) |
| 04-5 | Regra "só admin altera `perfil`" está no serviço e sem teste | `services/auth_service.py`; sem teste | **Alta** | **ABERTO** → [14](14-test-strategy.md) |
| 04-6 | `ChatService` cobre transições, mas `pegar`/`transferir`/`transferir_grupo`/`assinar`/`definir_prioridade`/`listar` (filtro) seguem sem teste | `tests/test_chat_service.py` | **Alta** | **ABERTO** → [14](14-test-strategy.md) |
| 04-7 | `WEBHOOK_SECRET` ainda força status de qualquer chat (pulando a máquina de estados) e cria diagnóstico; mitigado por fail-closed e rate limit | `api/routes/webhooks.py` | **Alta** | **ABERTO** → 01, 03 |
| 04-8 | `EvolutionService.criar_instancia` engole 403 e devolve sucesso sem QR | `services/evolution_service.py:31-34` | Média | **ABERTO** |
| 04-9 | `GET /atendentes/ativos` retorna id/nome/perfil/setor de todos os ativos para qualquer autenticado | `api/routes/atendentes.py` | Baixa | **ABERTO** |
| 04-10 | Escopo por departamento não é aplicado (departamento não existe) | `services/chat_service.py` | **Alta** | **CORRIGIDO** — `ChatService.listar` filtra por `departamento_id` |
| 04-11 | Identidade de serviço da IA / `actor_type` auditável não implementada | `app/` | Média | **ABERTO** → 04, 11 |
| 04-12 | Sem auditoria de atribuição/transferência (ator, motivo, antes/depois) | `app/` | Média | **ABERTO** → [02](02-data-model.md) |

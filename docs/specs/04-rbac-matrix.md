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

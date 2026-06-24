# EMSoft Support AI Platform

## Visão Geral

Desenvolver uma plataforma SaaS de atendimento WhatsApp especializada para suporte técnico do ERP EMSoft.

O sistema deve combinar:

- Atendimento Humano
- Atendimento por IA
- Base de Conhecimento RAG
- Kanban Operacional
- Integração WhatsApp
- Resumo Automático de Chamados
- Sugestão Automática de Soluções

Inspirado em:

- Chatwoot
- Zendesk
- Freshdesk
- Intercom

Mas focado exclusivamente no suporte técnico do ERP EMSoft.

---

# Contexto de Negócio

A EMSoft atende empresas de:

- Autopeças
- Distribuidoras
- Centros automotivos
- Redes multiempresa

Os atendimentos mais comuns envolvem:

## Fiscal

- NF-e rejeitada
- NFC-e rejeitada
- Erros SEFAZ
- SPED
- Cadastro tributário

## Estoque

- Divergência de estoque
- Giro de estoque
- Transferência entre filiais
- Inventário

## Compras

- Central de Compras
- Cotação
- Fornecedores

## Vendas

- Pedido
- Orçamento
- PDV
- Tabela de preços

## Financeiro

- Fluxo de caixa
- Conciliação bancária
- Contas a pagar
- Contas a receber

## Multiempresa

- Sincronização
- Filiais
- Integração

---

# Objetivo Principal

Reduzir em pelo menos 70% a carga operacional do suporte humano.

Fluxo esperado:

Cliente WhatsApp
↓
IA Analisa
↓
Consulta RAG
↓
Resolve
OU
Escala para humano

---

# Arquitetura

Frontend
↓
Backend API
↓
PostgreSQL

Integrações:

- Evolution API
- N8N
- OpenAI/Ollama
- Qdrant
- MinIO

---

# Stack Obrigatória

Backend:

- NestJS
- TypeScript
- PostgreSQL
- Prisma
- Redis
- BullMQ

Frontend:

- Next.js
- TypeScript
- Tailwind
- Shadcn
- React Query
- Zustand

Infra:

- Docker
- Docker Compose
- Traefik

IA:

- OpenAI
- Ollama
- Qdrant

Automação:

- N8N

---

# Módulos

## Autenticação

- Login
- JWT
- RBAC

Perfis:

- Admin
- Supervisor
- Atendente

---

## Clientes

- Cadastro
- Loja
- Filial
- ERP Versão

---

## Chats

Estados:

NOVO

IA_ANALISANDO

AGUARDANDO_CLIENTE

AGUARDANDO_HUMANO_COM_SOLUCAO

AGUARDANDO_HUMANO_SEM_SOLUCAO

EM_ATENDIMENTO

RESOLVIDO

ENCERRADO

---

## Kanban

Colunas:

Novos

IA Analisando

Com Solução

Sem Solução

Em Atendimento

Aguardando Cliente

Resolvidos

---

## Mensagens

Tipos:

- Texto
- Áudio
- Documento
- Imagem

---

## IA

Responsabilidades:

- Classificar problema
- Resumir conversa
- Consultar RAG
- Gerar solução
- Gerar diagnóstico

---

## Knowledge Base

Documentos:

- PDF
- DOCX
- TXT
- HTML

Categorias:

- Fiscal
- Estoque
- Compras
- Vendas
- Financeiro

---

## Dashboard

KPIs:

- Tempo médio atendimento
- Taxa resolução IA
- Taxa transbordo humano
- Chamados por categoria
- Chamados por cliente

---

# Regras de Atendimento

## Cenário A

IA encontrou solução.

Responder cliente.

Marcar resolvido.

---

## Cenário B

IA encontrou solução.

Necessita intervenção humana.

Criar resumo.

Preencher solução sugerida.

Transferir para fila:

AGUARDANDO_HUMANO_COM_SOLUCAO

---

## Cenário C

IA não encontrou solução.

Coletar detalhes.

Gerar relatório técnico.

Transferir para:

AGUARDANDO_HUMANO_SEM_SOLUCAO

---

# Critérios de Desenvolvimento

Sempre:

1. Aplicar Clean Architecture
2. Aplicar SOLID
3. Aplicar DDD quando necessário
4. Aplicar CQRS quando fizer sentido
5. Aplicar Event Driven Architecture
6. Gerar testes
7. Gerar documentação
8. Gerar Docker
9. Gerar OpenAPI

Nunca criar código simplificado.

Sempre gerar código pronto para produção.

Sempre explicar decisões arquiteturais.

Sempre identificar riscos técnicos.

Sempre sugerir melhorias.


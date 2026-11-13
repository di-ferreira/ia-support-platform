# Projeto — Ponteiro

Sistema de atendimento WhatsApp com IA para suporte técnico do ERP EMSoft.

## Objetivo

Automatizar suporte técnico via WhatsApp com IA, RAG, kanban e escala para humano.

## Stack real

Backend FastAPI (Python) + Appwrite + Redis + Qdrant + Evolution API + n8n + Next.js 15.

## Estados reais (`StatusChat`)

Fonte: `backend/app/models/enums.py` → `StatusChat`.

1. `NOVO`
2. `IA_ANALISANDO`
3. `AGUARDANDO_CLIENTE`
4. `AGUARDANDO_HUMANO_COM_SOLUCAO`
5. `AGUARDANDO_HUMANO_SEM_SOLUCAO`
6. `EM_ATENDIMENTO`
7. `RESOLVIDO`
8. `ENCERRADO`

> Glossário de domínio completo: [`docs/specs/01-domain-glossary.md`](../docs/specs/01-domain-glossary.md).

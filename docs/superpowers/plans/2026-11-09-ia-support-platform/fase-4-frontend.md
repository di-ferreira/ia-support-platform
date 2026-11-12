# Fase 4 — Frontend Operacional

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O painel operacional passa a usar departamento como unidade de fila e transferência, mostra o snapshot de intenção/roteamento que o backend gravou, fecha o ciclo A na interface (confirmar resolução / não resolveu) e respeita perfil no acesso a rotas — com testes automatizados de verdade, pela primeira vez no frontend.

**Architecture:** Next.js 15 App Router, TanStack Query como fonte única de server state e Zustand apenas para estado de UI (chat ativo, filtros). Nenhuma regra de negócio no cliente (C8): a tela envia `departamento_id`/`atendente_id`, o backend valida e responde; a UI nunca assume sucesso antes da resposta. `lib/api.ts` é a única porta HTTP e agora distingue erro por status (`ApiError`), porque 403/409/422 carregam mensagens diferentes para o operador. Componentes de apresentação recebem dados por props; páginas apenas orquestram queries.

**Tech Stack:** Next.js 15, React 19, TypeScript 5.6, Tailwind CSS 4 (`@theme` em `globals.css`), TanStack Query 5, Zustand 5, Radix (`@radix-ui/react-select`), lucide-react; **Vitest 2 + jsdom + Testing Library** (harness criado nesta fase, Task F4.1).

**Specs:** `docs/specs/07-frontend.md` (§Gestão de departamentos, §Atendimento/Inbox, §Kanban, §Dashboard, §Cache e tempo real, §Estados de interface, §Design system, §Acessibilidade), `docs/specs/04-rbac-matrix.md` (§rotas por perfil), `docs/specs/10-departamentos-e-roteamento.md` (§processo de assunção — 409), `docs/specs/05-ai-pipeline.md` (§Três cenários).

## Global Constraints

Vale `README.md` §Global Constraints (C1–C12). Em especial:

- **C1** — o harness de teste entra na **primeira** task: nenhuma task de UI "implementa e depois testa".
- **C2** — verificação de task frontend: `npm run test` + `npm run build`. `npm run lint` continua report-only até a R2.3.
- **C4** — gap fechado muda a linha do Registro de Gaps na mesma task, com evidência `arquivo:componente`.
- **C7/C8** — a UI nunca envia status arbitrário nem nome de departamento em texto livre: envia `departamento_id` e deixa o backend decidir.
- **C10** — nenhum arquivo fora do mapa da task; refactor de outra tela fica para R2.3.

**Gate de entrada:** G3 (Fases 1–3 concluídas — `/departamentos`, `/chats/{id}/roteamento`, `transferir-departamento`, `atribuir-atendente`, `confirmar-resolucao`, `reabrir` existem e estão cobertos por teste no backend).

## Pré-requisito de execução: a R1 vem antes

A ordem canônica do README coloca **R1 antes de F4** porque a meta de 70% de solução confirmada só é mensurável com `tempo_medio_resposta` corrigido e métricas de produto (R1.2/R1.3). O painel de dashboard da F4 exibe esses números; executá-la antes da R1 mostraria métricas sabidamente erradas. **Não inverter.**

## Rastreio gap → task

| Gap | Task | Evidência que fecha |
|---|---|---|
| 07-2 | F4.3 | refresh token usado; sessão não cai em 60 min |
| 03-10 | F4.3 | `/auth/refresh` chamado pelo client (o `PATCH /auth/password` fica no perfil do usuário, fora deste escopo) |
| 07-5 | F4.6 | `chat-store` é a fonte do chat ativo e dos filtros |
| 03-8 | F4.7 | rotas que alteram chat emitem evento WebSocket |
| 07-3 | F4.7 | reconexão com backoff exponencial limitado + invalidação central |
| 07-9 | F4.5, F4.8 | tela de departamentos + fila filtrada por departamento |
| 07-10 | F4.9 | painel de intenção/roteamento/artigos no inbox |
| 05-4 (UI) | F4.11 | botão de confirmar resolução fecha o cenário A |
| 01-4 (UI) | F4.11 | "não resolveu" reabre o chat |
| 07-11 | F4.12 | guarda de rota por perfil + sidebar filtrada |
| 04-3 | F4.12 | URL digitada não alcança `/usuarios` sem perfil |
| 07-6 | F4.13 | selects de status/prioridade/departamento acessíveis (Radix) |
| 07-4 | F4.13 | nenhuma cor raw de estado/neutra em `src/**/*.tsx` |

**Fora desta fase:** a **sincronização real** com o chamado Emsoft depende do contrato bloqueado (11-1) e fica ABERTO; o painel de sincronização entregue lê apenas os endpoints locais (`/integracoes/chamados/*`, 12-7) e não substitui a integração. `PATCH /auth/password` na UI, dropdown de perfil no header e demais telas (`/kanban` funcional, `/conhecimento`) só recebem a migração mecânica de tokens (F4.13) — não são redesenhadas.

**Nota de numeração:** este doc tem 13 tasks (F4.1–F4.13), como no README. A F4.1 cria o harness Vitest; a R2.3 deixa de criar o harness e passa a **torná-lo bloqueante no CI com cobertura mínima** — ver `trilha-r-prontidao.md`.

## Estado de execução (2026-11-11)

A T4 entregou o **escopo funcional** de 07-9, 07-10 e 00-13 direto nas páginas existentes, sem o harness e sem a extração de componentes descrita nas tasks abaixo. O que está de pé:

- `/departamentos`: CRUD admin (código/nome/descrição/ordem/flags), desativar/reativar com dependências (409 explica os vínculos), abas Fila (assumir via `PATCH /chats/{id}/pegar`), Atendentes (`GET /departamentos/{id}/atendentes`, admin/supervisor) e Regras (`GET /departamentos/{id}/regras`).
- `/atendimento`: filtro por departamento, painel de diagnóstico (`GET /chats/{id}/roteamento`), painel de sincronização com visão por perfil (`GET /integracoes/chamados/{chat_id}`, reprocessar admin/supervisor) e ações transferir departamento, atribuir atendente, confirmar resolução, "não resolveu" e solicitar humano.
- `/usuarios`: associação de departamento no formulário e coluna na listagem.
- Backend de apoio: `departamento_id` em `/auth/usuarios` e `/atendentes/ativos`; `artigos_consultados` desserializado em `/chats/{id}/roteamento`.

**Tasks deste plano ainda não executadas** (não marcar como concluídas): F4.13 (Radix e migração total para tokens — 07-6, 07-4). A F4.6 foi executada em 2026-11-12 (07-5: `chat-store` (Zustand) como fonte única do chat ativo — `chatAtivo` (id + objeto) no store, seleção/troca/limpeza só no store, evento `chat_atualizado` atualiza o chat ativo sem refetch; `chats`/`setChats` removidos do store; 6 testes novos em `chat-store.test.ts`; `npm run test` com 31 testes). A F4.1 foi executada (harness Vitest + catálogo status/prioridade em `src/lib/status.ts`). A F4.12 foi executada em 2026-11-12 (guarda de rota e menu por perfil — 07-11, 04-3: matriz única em `src/lib/permissoes.ts`, guarda em `(app)/layout.tsx` com redirecionamento para `/atendimento` e banner de acesso negado, sidebar filtrada pela mesma matriz; a escrita de departamento já estava restrita a admin em `app/(app)/departamentos/page.tsx`; `npm run test` com 15 testes). A F4.7 foi executada em 2026-11-12 (03-8 e 07-3: as 7 rotas que alteram chat — `status`, `pegar`, `transferir`, `transferir-departamento`, `assinar`, `prioridade` e kanban `mover` — emitem `chat_atualizado` via `manager.send_event` após o commit, com helper `emitir_chat_atualizado` em `backend/app/api/realtime.py`; reconexão automática no hook com backoff exponencial + jitter de 1s a 30s em `src/lib/reconnect.ts`, status `conectado`/`reconectando` exposto e invalidação central de query por evento; 11 testes novos no backend em `tests/test_ws_eventos_chat.py` e 10 no frontend). Assim, o gate de saída abaixo continua **aberto**, assim como a Fase 4 no [checklist](../../../checklist-implementacoes.md).

A fonte de verdade segue sendo as specs (`docs/specs/00`–`14`); este plano é o roteiro do que falta.

---

### Task F4.1: Harness Vitest e catálogo de status/prioridade

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Modify: `frontend/package.json` (devDependencies + scripts `test`/`test:watch`)
- Modify: `frontend/tsconfig.json` (`types`)
- Create: `frontend/src/lib/status.ts`
- Test: `frontend/src/lib/status.test.ts`

**Interfaces:**
- Produces:
  - `STATUS_CHAT: readonly string[]` — os 8 status de `StatusChat`
  - `PRIORIDADES: readonly PrioridadeChat[]`
  - `rotuloStatus(status: string): string`, `rotuloPrioridade(p: string): string`
  - `varianteStatus(status: string): VarianteBadge`, `variantePrioridade(p: string): VarianteBadge`
  - `statusEncerrado(status: string): boolean`
  - Script `npm run test` = `vitest run`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/status.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import {
  PRIORIDADES,
  STATUS_CHAT,
  rotuloPrioridade,
  rotuloStatus,
  statusEncerrado,
  variantePrioridade,
  varianteStatus,
} from "@/lib/status";

describe("catalogo de status", () => {
  it("cobre os oito status do dominio", () => {
    expect(STATUS_CHAT).toHaveLength(8);
    expect(STATUS_CHAT).toContain("AGUARDANDO_HUMANO_SEM_SOLUCAO");
  });

  it("rotula cada status em portugues", () => {
    expect(rotuloStatus("NOVO")).toBe("Novo");
    expect(rotuloStatus("IA_ANALISANDO")).toBe("IA analisando");
    expect(rotuloStatus("AGUARDANDO_CLIENTE")).toBe("Aguardando cliente");
    expect(rotuloStatus("EM_ATENDIMENTO")).toBe("Em atendimento");
    expect(rotuloStatus("ENCERRADO")).toBe("Encerrado");
  });

  it("devolve o proprio codigo quando o status e desconhecido", () => {
    expect(rotuloStatus("STATUS_FUTURO")).toBe("STATUS_FUTURO");
  });

  it("marca resolvido e encerrado como concluidos", () => {
    expect(statusEncerrado("RESOLVIDO")).toBe(true);
    expect(statusEncerrado("ENCERRADO")).toBe(true);
    expect(statusEncerrado("NOVO")).toBe(false);
  });
});

describe("catalogo de prioridade", () => {
  it("ordena as quatro prioridades", () => {
    expect(PRIORIDADES).toEqual(["baixa", "media", "alta", "urgente"]);
  });

  it("destaca alta e urgente como perigo", () => {
    expect(variantePrioridade("urgente")).toBe("danger");
    expect(variantePrioridade("alta")).toBe("danger");
    expect(variantePrioridade("media")).toBe("neutral");
    expect(variantePrioridade("baixa")).toBe("neutral");
  });

  it("rotula prioridade desconhecida sem quebrar", () => {
    expect(rotuloPrioridade("critica")).toBe("critica");
  });
});

describe("variante de status", () => {
  it("usa info para fila humana e success para resolvido", () => {
    expect(varianteStatus("AGUARDANDO_HUMANO_COM_SOLUCAO")).toBe("info");
    expect(varianteStatus("AGUARDANDO_HUMANO_SEM_SOLUCAO")).toBe("warning");
    expect(varianteStatus("RESOLVIDO")).toBe("success");
    expect(varianteStatus("ENCERRADO")).toBe("neutral");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/lib/status.test.ts`

Expected: FAIL — `npm error Missing script: "test"`.

- [ ] **Step 3: Write minimal implementation**

`frontend/package.json` — scripts:

```json
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run",
    "test:watch": "vitest"
  },
```

`frontend/package.json` — devDependencies (acrescentar, mantendo as existentes):

```json
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.1.0",
    "@testing-library/user-event": "^14.5.2",
    "@vitejs/plugin-react": "^4.3.4",
    "jsdom": "^25.0.1",
    "vitest": "^2.1.8"
```

Instalar: `cd frontend && npm install`.

`frontend/vitest.config.ts`:

```ts
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
```

`frontend/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  localStorage.clear();
});
```

`frontend/tsconfig.json` — acrescentar `types` ao `compilerOptions`:

```json
    "types": ["vitest/globals", "@testing-library/jest-dom"]
```

`frontend/src/lib/status.ts`:

```ts
export type VarianteBadge =
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "neutral";

export const STATUS_CHAT = [
  "NOVO",
  "IA_ANALISANDO",
  "AGUARDANDO_CLIENTE",
  "AGUARDANDO_HUMANO_COM_SOLUCAO",
  "AGUARDANDO_HUMANO_SEM_SOLUCAO",
  "EM_ATENDIMENTO",
  "RESOLVIDO",
  "ENCERRADO",
] as const;

const ROTULOS_STATUS: Record<string, string> = {
  NOVO: "Novo",
  IA_ANALISANDO: "IA analisando",
  AGUARDANDO_CLIENTE: "Aguardando cliente",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "Aguardando humano (com solução)",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "Aguardando humano (sem solução)",
  EM_ATENDIMENTO: "Em atendimento",
  RESOLVIDO: "Resolvido",
  ENCERRADO: "Encerrado",
};

const VARIANTES_STATUS: Record<string, VarianteBadge> = {
  NOVO: "primary",
  IA_ANALISANDO: "primary",
  AGUARDANDO_CLIENTE: "warning",
  AGUARDANDO_HUMANO_COM_SOLUCAO: "info",
  AGUARDANDO_HUMANO_SEM_SOLUCAO: "warning",
  EM_ATENDIMENTO: "info",
  RESOLVIDO: "success",
  ENCERRADO: "neutral",
};

export const PRIORIDADES = ["baixa", "media", "alta", "urgente"] as const;
export type PrioridadeChat = (typeof PRIORIDADES)[number];

const ROTULOS_PRIORIDADE: Record<string, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
  urgente: "Urgente",
};

export function rotuloStatus(status: string): string {
  return ROTULOS_STATUS[status] ?? status;
}

export function rotuloPrioridade(prioridade: string): string {
  return ROTULOS_PRIORIDADE[prioridade] ?? prioridade;
}

export function varianteStatus(status: string): VarianteBadge {
  return VARIANTES_STATUS[status] ?? "neutral";
}

export function variantePrioridade(prioridade: string): VarianteBadge {
  return prioridade === "alta" || prioridade === "urgente" ? "danger" : "neutral";
}

export function statusEncerrado(status: string): boolean {
  return status === "RESOLVIDO" || status === "ENCERRADO";
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/lib/status.test.ts`

Expected: PASS (8 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

Expected: 8 testes verdes; build conclui sem erro de tipo.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts \
  frontend/tsconfig.json frontend/src/test/setup.ts \
  frontend/src/lib/status.ts frontend/src/lib/status.test.ts
git commit -m "test(frontend): harness vitest e catalogo de status

- vitest + jsdom + testing library com alias @ e setup global
- npm run test passa a existir como verificacao de task
- status/prioridade ganham rotulo e variante de badge testados"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 14 e 07)**

Nenhum gap fecha nesta task; ela habilita todas as seguintes. Registrar a mudança de plano na spec 14:

```
| 14-6 | Frontend sem infraestrutura de teste (sem `test` script, sem Vitest/Playwright) | `frontend/package.json` | **Alta** | **ABERTO (parcial)** — Vitest + jsdom + Testing Library em `vitest.config.ts` (Task F4.1); bloqueio de CI e cobertura mínima na Task R2.3 |
```

---

### Task F4.2: `ApiError`, métodos tipados e tipos do domínio

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/types.ts`
- Test: `frontend/src/lib/api.test.ts`

**Interfaces:**
- Produces:
  - `class ApiError extends Error` com `status: number` e `detail: unknown`
  - `api.get/post/patch/delete` devolvendo `ApiError` em qualquer resposta não-2xx
  - `lib/types.ts`: `Departamento`, `ChatResumo`, `ChatDetalhe`, `RoteamentoChat`, `Atendente`, `Mensagem`

**Regra:** `detail` do FastAPI pode ser `string` (HTTPException) ou `string[]` (`msg` de validação Pydantic). A mensagem exibida é a primeira disponível; o `status` é preservado para a UI decidir 403 (sem permissão), 409 (conflito de assunção) e 422 (formulário inválido).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/api.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/lib/api";

function resposta(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("client HTTP", () => {
  beforeEach(() => {
    localStorage.setItem("token", "abc");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetAllMocks();
  });

  it("envia o token no header Authorization", async () => {
    vi.mocked(fetch).mockResolvedValue(resposta({ ok: true }));

    await api.get("/chats");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://localhost:8001/chats");
    expect(
      (init?.headers as Record<string, string>).Authorization
    ).toBe("Bearer abc");
  });

  it("monta query string ignorando nulos e indefinidos", async () => {
    vi.mocked(fetch).mockResolvedValue(resposta([]));

    await api.get("/chats", {
      departamento_id: "d1",
      status: null,
      skip: 0,
      busca: undefined,
    });

    expect(vi.mocked(fetch).mock.calls[0][0]).toBe(
      "http://localhost:8001/chats?departamento_id=d1&skip=0"
    );
  });

  it("preserva status e mensagem em ApiError", async () => {
    vi.mocked(fetch).mockResolvedValue(
      resposta({ detail: "Chat já assumido por outro atendente" }, 409)
    );

    const erro = await api
      .patch("/chats/1/atribuir-atendente", { atendente_id: "a1" })
      .catch((e) => e);

    expect(erro).toBeInstanceOf(ApiError);
    expect(erro).toMatchObject({
      status: 409,
      message: "Chat já assumido por outro atendente",
    });
  });

  it("extrai a primeira mensagem de erro de validacao 422", async () => {
    vi.mocked(fetch).mockResolvedValue(
      resposta({ detail: [{ msg: "campo obrigatório" }, { msg: "outro" }] }, 422)
    );

    await expect(api.post("/departamentos", {})).rejects.toMatchObject({
      status: 422,
      message: "campo obrigatório",
    });
  });

  it("usa o statusText quando o corpo nao e JSON", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response("bad gateway", { status: 502, statusText: "Bad Gateway" })
    );

    await expect(api.get("/health")).rejects.toMatchObject({
      status: 502,
      message: "Bad Gateway",
    });
  });

  it("devolve undefined em 204", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));

    await expect(api.delete("/chats/1")).resolves.toBeUndefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/lib/api.test.ts`

Expected: FAIL — `ApiError` não é exportado por `@/lib/api` (`TypeError: Cannot read properties of undefined` / erro de import).

- [ ] **Step 3: Write minimal implementation**

Substitua `frontend/src/lib/api.ts` por:

```ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

type Options = RequestInit & {
  params?: Record<string, string | number | boolean | undefined | null>;
};

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function extrairMensagem(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const primeiro = detail.find(
      (item) => typeof item === "object" && item !== null && "msg" in item
    ) as { msg?: unknown } | undefined;
    if (primeiro && typeof primeiro.msg === "string") return primeiro.msg;
  }
  if (detail && typeof detail === "object" && "detail" in detail) {
    const interno = (detail as { detail?: unknown }).detail;
    if (typeof interno === "string") return interno;
  }
  return fallback;
}

async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { params, ...init } = options;
  let url = `${API_URL}${path}`;

  if (params) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) search.set(k, String(v));
    });
    const qs = search.toString();
    if (qs) url += `?${qs}`;
  }

  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!res.ok) {
    const corpo = await res.json().catch(() => null);
    const detail = (corpo as { detail?: unknown } | null)?.detail;
    throw new ApiError(
      extrairMensagem(detail, res.statusText || "Erro na requisição"),
      res.status,
      corpo
    );
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, params?: Options["params"]) =>
    request<T>(path, { params }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
```

Create `frontend/src/lib/types.ts`:

```ts
export interface Departamento {
  id: string;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
  ordem: number | null;
  recebe_transferencias: boolean;
  permite_atribuicao_automatica: boolean;
}

export interface Atendente {
  id: string;
  nome: string;
  email: string;
  perfil: "admin" | "supervisor" | "atendente";
  ativo: boolean;
  departamento_id: string | null;
}

export interface ChatResumo {
  id: string;
  cliente_id: string;
  cliente_nome: string | null;
  status: string;
  prioridade: string;
  resumo_problema: string | null;
  ultima_mensagem_em: string | null;
  atendente_id: string | null;
  departamento_id: string | null;
  solucao_sugerida_ia: string | null;
}

export interface ChatDetalhe extends ChatResumo {
  causa_provavel: string | null;
  nivel_confianca_ia: number | null;
  necessita_humano: boolean;
  resumo_problema: string | null;
}

export interface ArtigoConsultado {
  id: string;
  titulo: string;
  score: number;
  categoria: string;
}

export interface RoteamentoChat {
  chat_id: string;
  departamento_id: string | null;
  departamento_codigo: string | null;
  intencao: string | null;
  subintencao: string | null;
  categoria_erp: string | null;
  departamento_sugerido_codigo: string | null;
  motivo: string | null;
  confianca: number | null;
  artigos_consultados: ArtigoConsultado[];
  tem_diagnostico: boolean;
}

export interface Mensagem {
  id: string;
  chat_id: string;
  remetente: "cliente" | "atendente" | "ia";
  tipo: string;
  conteudo: string;
  created_at: string;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/lib/api.test.ts`

Expected: PASS (6 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

Expected: suíte verde; build reporta apenas os erros que já existiam antes da fase (nenhum novo de tipo).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/api.test.ts frontend/src/lib/types.ts
git commit -m "feat(frontend): ApiError com status e tipos do dominio

- client HTTP preserva status e detail (403/409/422 tratados na UI)
- detail string, lista de validacao e corpo nao-JSON viram mensagem
- tipos de departamento, chat, roteamento e mensagem centralizados"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 03 e 07)**

```
| 03-7 | 502 devolve `str(e)` do `httpx`, expondo URL/corpo da Evolution | `api/routes/mensagens.py:55-59,111-115`; `evolution.py` | Média | **ABERTO** — o client passou a exibir `statusText`/`detail` sanitizado (Task F4.2); a causa raiz segue no backend |
```

Nenhum gap fecha aqui; o registro só documenta que o client deixou de exibir corpo cru.

---

### Task F4.3: Sessão — `departamento_id` no `/auth/me`, refresh e logout em 401

**Files:**
- Modify: `backend/app/schemas/auth.py:15-25` (`AtendenteResponse`)
- Modify: `frontend/src/lib/api.ts` (refresh single-flight + evento `auth:logout`)
- Modify: `frontend/src/lib/stores/auth-store.ts` (`setAuth` com refresh, `logout` limpa tokens)
- Modify: `frontend/src/app/(app)/layout.tsx` (remove o `/auth/me` duplicado; escuta `auth:logout`)
- Modify: `frontend/src/app/login/page.tsx:39` (guarda o refresh token)
- Modify: `frontend/src/hooks/use-auth.ts:15,22` (guarda o refresh token)
- Test: `backend/tests/test_auth_me_departamento.py`, `frontend/src/lib/api.test.ts` (casos novos), `frontend/src/lib/stores/auth-store.test.ts`

**Interfaces:**
- Produces:
  - `AtendenteResponse.departamento_id: str | None`
  - `renovarToken(): Promise<string | null>` (interno de `api.ts`), single-flight
  - `setAuth(token, user, refreshToken?)` — retrocompatível com as chamadas existentes
  - `logout()` remove `token` e `refresh_token`
  - evento DOM `auth:logout`, disparado quando o refresh falha

**Regras:** o refresh acontece **uma vez** por requisição 401 e **uma** renovação simultânea para N requisições (single-flight). Rotas `/auth/login` e `/auth/refresh` não tentam refresh. Falha de refresh limpa os tokens e emite `auth:logout`; o layout redireciona. `departamento_id` no `/auth/me` é o que permite a UI saber a fila padrão do atendente.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_auth_me_departamento.py`:

```python
"""/auth/me devolve o departamento do atendente (escopo de fila no frontend)."""

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_me_devolve_departamento_do_atendente(client, atendente_token, fake_repos):
    depto = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte Técnico", "ativo": True}
    )
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": depto["id"]}
    )

    resp = await client.get("/auth/me", headers=_auth(atendente_token))

    assert resp.status_code == 200
    assert resp.json()["departamento_id"] == depto["id"]


@pytest.mark.asyncio
async def test_me_sem_departamento_devolve_null(client, admin_token):
    resp = await client.get("/auth/me", headers=_auth(admin_token))

    assert resp.status_code == 200
    assert resp.json()["departamento_id"] is None
```

Acrescente a `frontend/src/lib/api.test.ts` (novo `describe`, importando `renovarToken` não é necessário):

```ts
describe("renovacao de token", () => {
  beforeEach(() => {
    localStorage.setItem("token", "expirado");
    localStorage.setItem("refresh_token", "refresh-1");
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetAllMocks();
  });

  it("renova no 401 e repete a chamada com o token novo", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(resposta({ detail: "Token inválido" }, 401))
      .mockResolvedValueOnce(
        resposta({ access_token: "novo", refresh_token: "refresh-2" })
      )
      .mockResolvedValueOnce(resposta([{ id: "c1" }]));

    const chats = await api.get<{ id: string }[]>("/chats");

    expect(chats).toEqual([{ id: "c1" }]);
    expect(localStorage.getItem("token")).toBe("novo");
    expect(localStorage.getItem("refresh_token")).toBe("refresh-2");
    const ultimaChamada = vi.mocked(fetch).mock.calls.at(-1)!;
    expect(
      (ultimaChamada[1]?.headers as Record<string, string>).Authorization
    ).toBe("Bearer novo");
  });

  it("nao tenta refresh em /auth/refresh", async () => {
    vi.mocked(fetch).mockResolvedValue(resposta({ detail: "Token inválido" }, 401));

    await expect(
      api.post("/auth/refresh", { refresh_token: "x" })
    ).rejects.toMatchObject({ status: 401 });

    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1);
  });

  it("falha de refresh limpa tokens e emite auth:logout", async () => {
    const ouvinte = vi.fn();
    window.addEventListener("auth:logout", ouvinte);
    vi.mocked(fetch)
      .mockResolvedValueOnce(resposta({ detail: "Token inválido" }, 401))
      .mockResolvedValueOnce(resposta({ detail: "Refresh inválido" }, 401));

    await expect(api.get("/chats")).rejects.toMatchObject({ status: 401 });

    expect(localStorage.getItem("token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(ouvinte).toHaveBeenCalledTimes(1);
  });

  it("duas requisicoes 401 simultaneas renovam uma vez", async () => {
    let renovacoes = 0;
    vi.mocked(fetch).mockImplementation(async (entrada) => {
      const url = String(entrada);
      if (url.endsWith("/auth/refresh")) {
        renovacoes += 1;
        return resposta({ access_token: "novo", refresh_token: "refresh-2" });
      }
      if (localStorage.getItem("token") === "expirado") {
        return resposta({ detail: "Token inválido" }, 401);
      }
      return resposta([{ id: "c1" }]);
    });

    await Promise.all([api.get("/chats"), api.get("/chats")]);

    expect(renovacoes).toBe(1);
  });
});
```

Create `frontend/src/lib/stores/auth-store.test.ts`:

```ts
import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore } from "@/lib/stores/auth-store";

const atendente = {
  id: "a1",
  nome: "Ana",
  email: "ana@test.com",
  perfil: "atendente" as const,
  ativo: true,
  departamento_id: "d1",
};

describe("auth-store", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({ token: null, user: null, loading: false });
  });

  it("guarda access e refresh token", () => {
    useAuthStore.getState().setAuth("access-1", atendente, "refresh-1");

    expect(localStorage.getItem("token")).toBe("access-1");
    expect(localStorage.getItem("refresh_token")).toBe("refresh-1");
    expect(useAuthStore.getState().user?.departamento_id).toBe("d1");
  });

  it("continua funcionando sem refresh token (retrocompativel)", () => {
    useAuthStore.getState().setAuth("access-1", atendente);

    expect(localStorage.getItem("token")).toBe("access-1");
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("logout limpa os dois tokens", () => {
    localStorage.setItem("token", "a");
    localStorage.setItem("refresh_token", "r");

    useAuthStore.getState().logout();

    expect(localStorage.getItem("token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(useAuthStore.getState().token).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_auth_me_departamento.py -v`
Run: `cd frontend && npm run test -- src/lib/api.test.ts src/lib/stores/auth-store.test.ts`

Expected: backend FAIL (`KeyError: 'departamento_id'`); frontend FAIL (refresh não é tentado; `refresh_token` não é gravado).

- [ ] **Step 3: Write minimal implementation**

`backend/app/schemas/auth.py` — em `AtendenteResponse`:

```python
class AtendenteResponse(BaseModel):
    id: str
    nome: str
    email: str
    perfil: str
    ativo: bool
    departamento_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
```

`frontend/src/lib/api.ts` — acrescentar acima de `request`:

```ts
const ROTAS_SEM_REFRESH = new Set(["/auth/login", "/auth/refresh"]);

let refreshEmAndamento: Promise<string | null> | null = null;

function lerToken(): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem("token");
}

function encerrarSessao(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  window.dispatchEvent(new Event("auth:logout"));
}

async function renovarToken(): Promise<string | null> {
  if (refreshEmAndamento) return refreshEmAndamento;

  refreshEmAndamento = (async () => {
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return null;

    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return null;

    const dados = (await res.json()) as {
      access_token: string;
      refresh_token: string;
    };
    localStorage.setItem("token", dados.access_token);
    localStorage.setItem("refresh_token", dados.refresh_token);
    return dados.access_token;
  })();

  try {
    return await refreshEmAndamento;
  } finally {
    refreshEmAndamento = null;
  }
}
```

e o corpo de `request` passa a montar headers por token e repetir uma vez:

```ts
  const montarInit = (token: string | null): RequestInit => ({
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  let res = await fetch(url, montarInit(lerToken()));

  if (res.status === 401 && !ROTAS_SEM_REFRESH.has(path)) {
    const novoToken = await renovarToken();
    if (!novoToken) {
      encerrarSessao();
      throw new ApiError("Sessão expirada", 401);
    }
    res = await fetch(url, montarInit(novoToken));
  }
```

(o trecho anterior `const token = ...` e o primeiro `fetch` são substituídos por esse bloco)

`frontend/src/lib/stores/auth-store.ts`:

```ts
import { create } from "zustand";

import { api } from "@/lib/api";
import type { Atendente } from "@/lib/types";

interface AuthState {
  token: string | null;
  user: Atendente | null;
  loading: boolean;
  setAuth: (token: string, user: Atendente, refreshToken?: string) => void;
  logout: () => void;
  loadFromStorage: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  loading: true,
  setAuth: (token, user, refreshToken) => {
    localStorage.setItem("token", token);
    if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
    set({ token, user, loading: false });
  },
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    set({ token: null, user: null, loading: false });
  },
  loadFromStorage: async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      set({ token: null, user: null, loading: false });
      return;
    }
    set({ token, loading: true });
    try {
      const user = await api.get<Atendente>("/auth/me");
      set({ token, user, loading: false });
    } catch {
      localStorage.removeItem("token");
      localStorage.removeItem("refresh_token");
      set({ token: null, user: null, loading: false });
    }
  },
}));
```

`frontend/src/app/(app)/layout.tsx`:

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token, loading, logout, loadFromStorage } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    const sair = () => {
      logout();
      router.replace("/login");
    };
    window.addEventListener("auth:logout", sair);
    return () => window.removeEventListener("auth:logout", sair);
  }, [logout, router]);

  useEffect(() => {
    if (!loading && !token) router.replace("/login");
  }, [loading, token, router]);

  if (loading || !token) return null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto bg-neutral-50 p-6">{children}</main>
      </div>
    </div>
  );
}
```

`frontend/src/app/login/page.tsx` — linha 39:

```ts
              setAuth(res.access_token, me, res.refresh_token);
```

e o tipo local da resposta ganha `refresh_token`:

```ts
    const res = await api.post<{
      access_token: string;
      refresh_token: string;
    }>("/auth/login", { email, senha });
```

`frontend/src/hooks/use-auth.ts` — `setAuth(token, u)` → `setAuth(token, u)` (mantém) e no `login`, `setAuth(res.access_token, me, res.refresh_token)` com o tipo `{ access_token: string; refresh_token: string }`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_auth_me_departamento.py -v`
Run: `cd frontend && npm run test -- src/lib/api.test.ts src/lib/stores/auth-store.test.ts`

Expected: PASS (2 backend + 10 frontend, contando os 6 da F4.2).

- [ ] **Step 5: Run the full suite + build**

Run: `cd backend && pytest tests/ -q && ruff check app tests`
Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/auth.py backend/tests/test_auth_me_departamento.py \
  frontend/src/lib/api.ts frontend/src/lib/api.test.ts \
  frontend/src/lib/stores/auth-store.ts frontend/src/lib/stores/auth-store.test.ts \
  frontend/src/app/\(app\)/layout.tsx frontend/src/app/login/page.tsx frontend/src/hooks/use-auth.ts
git commit -m "feat(frontend): sessao com refresh token e departamento do usuario

- /auth/me devolve departamento_id (fila padrao do atendente)
- 401 dispara um unico refresh (single-flight) e repete a chamada
- falha de refresh limpa tokens e emite auth:logout
- login guarda refresh_token; layout deixa de duplicar /auth/me"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 07 e 03)**

```
| 07-2 | Sem refresh token/renovação; sessão cai após 60 min | `lib/api.ts`; `auth-store.ts` | **Alta** | **CORRIGIDO** — refresh single-flight no 401 (`renovarToken`) + `refresh_token` persistido no login |
| 03-10 | `/auth/refresh` e `PATCH /auth/password` existem e não são chamados pelo frontend | `api/routes/auth.py` | **Alta** | **CORRIGIDO (refresh)** — client usa `/auth/refresh`; redefinição de senha na UI segue fora do escopo |
```

---

### Task F4.4: `useDepartamentos` e `DepartamentoSelect`

**Files:**
- Create: `frontend/src/hooks/use-departamentos.ts`
- Create: `frontend/src/components/departamentos/departamento-select.tsx`
- Test: `frontend/src/components/departamentos/departamento-select.test.tsx`

**Interfaces:**
- Consumes: `GET /departamentos?incluir_inativos=` (F1.5), `api`/`ApiError` (F4.2), `Departamento` (F4.2).
- Produces:
  - `useDepartamentos({ incluirInativos?: boolean }): UseQueryResult<Departamento[]>`
  - `DepartamentoSelect` com props `valor`, `onChange`, `filtro?`, `incluirInativos?`, `permitirTodos?`, `rotuloTodos?`, `id?`, `"aria-label"?: string`
  - query key `["departamentos", { incluirInativos }]` — invalidada na F4.5 e na F4.7

**Regra:** o componente é burro: filtra por `ativo` (e pelo `filtro` recebido), nunca decide destino. `permitirTodos` existe para a fila ("Todos os departamentos"), não para o modal de transferência.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/departamentos/departamento-select.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ api: { get: vi.fn() } }));

import { DepartamentoSelect } from "@/components/departamentos/departamento-select";
import { api } from "@/lib/api";
import type { Departamento } from "@/lib/types";

const DEPARTAMENTOS: Departamento[] = [
  {
    id: "d1",
    codigo: "suporte_tecnico",
    nome: "Suporte Técnico",
    descricao: null,
    ativo: true,
    ordem: 1,
    recebe_transferencias: true,
    permite_atribuicao_automatica: false,
  },
  {
    id: "d2",
    codigo: "financeiro",
    nome: "Financeiro",
    descricao: null,
    ativo: true,
    ordem: 2,
    recebe_transferencias: false,
    permite_atribuicao_automatica: false,
  },
  {
    id: "d3",
    codigo: "antigo",
    nome: "Antigo",
    descricao: null,
    ativo: false,
    ordem: 3,
    recebe_transferencias: true,
    permite_atribuicao_automatica: false,
  },
];

function montar(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>
  );
}

describe("DepartamentoSelect", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue(DEPARTAMENTOS);
  });

  it("lista somente departamentos ativos", async () => {
    montar(<DepartamentoSelect valor={null} onChange={() => {}} />);

    expect(await screen.findByText("Suporte Técnico")).toBeInTheDocument();
    expect(screen.getByText("Financeiro")).toBeInTheDocument();
    expect(screen.queryByText("Antigo")).not.toBeInTheDocument();
  });

  it("aplica filtro de recebimento de transferencia", async () => {
    montar(
      <DepartamentoSelect
        valor={null}
        onChange={() => {}}
        filtro={(d) => d.recebe_transferencias}
      />
    );

    expect(await screen.findByText("Suporte Técnico")).toBeInTheDocument();
    expect(screen.queryByText("Financeiro")).not.toBeInTheDocument();
  });

  it("oferece a opcao todos quando permitirTodos", async () => {
    montar(
      <DepartamentoSelect valor={null} onChange={() => {}} permitirTodos />
    );

    expect(
      await screen.findByRole("option", { name: "Todos os departamentos" })
    ).toBeInTheDocument();
  });

  it("avisa o valor escolhido", async () => {
    const onChange = vi.fn();
    montar(<DepartamentoSelect valor={null} onChange={onChange} />);

    await userEvent.selectOptions(
      await screen.findByLabelText("Departamento"),
      "Financeiro"
    );

    expect(onChange).toHaveBeenCalledWith("d2");
  });

  it("mostra estado vazio sem departamentos", async () => {
    vi.mocked(api.get).mockResolvedValue([]);

    montar(<DepartamentoSelect valor={null} onChange={() => {}} />);

    expect(
      await screen.findByText("Nenhum departamento disponível")
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/components/departamentos/departamento-select.test.tsx`

Expected: FAIL — `Cannot find module '@/components/departamentos/departamento-select'`.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/hooks/use-departamentos.ts`:

```ts
"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Departamento } from "@/lib/types";

interface Opcoes {
  incluirInativos?: boolean;
}

export function useDepartamentos({ incluirInativos = false }: Opcoes = {}) {
  return useQuery({
    queryKey: ["departamentos", { incluirInativos }],
    queryFn: () =>
      api.get<Departamento[]>("/departamentos", {
        incluir_inativos: incluirInativos ? "true" : undefined,
      }),
    staleTime: 5 * 60 * 1000,
  });
}
```

`frontend/src/components/departamentos/departamento-select.tsx`:

```tsx
"use client";

import { Select } from "@/components/ui/select";
import { useDepartamentos } from "@/hooks/use-departamentos";
import type { Departamento } from "@/lib/types";

interface Props {
  valor: string | null;
  onChange: (departamentoId: string | null) => void;
  filtro?: (departamento: Departamento) => boolean;
  incluirInativos?: boolean;
  permitirTodos?: boolean;
  rotuloTodos?: string;
  id?: string;
  "aria-label"?: string;
}

export function DepartamentoSelect({
  valor,
  onChange,
  filtro,
  incluirInativos = false,
  permitirTodos = false,
  rotuloTodos = "Todos os departamentos",
  id = "departamento",
  "aria-label": ariaLabel = "Departamento",
}: Props) {
  const { data, isLoading } = useDepartamentos({ incluirInativos });

  const visiveis = (data ?? []).filter(
    (departamento) =>
      (incluirInativos || departamento.ativo) && (filtro ? filtro(departamento) : true)
  );

  return (
    <Select
      id={id}
      aria-label={ariaLabel}
      value={valor ?? ""}
      disabled={isLoading}
      onChange={(evento) => onChange(evento.target.value || null)}
    >
      {permitirTodos ? <option value="">{rotuloTodos}</option> : null}
      {visiveis.map((departamento) => (
        <option key={departamento.id} value={departamento.id}>
          {departamento.nome}
        </option>
      ))}
      {visiveis.length === 0 ? (
        <option value="" disabled>
          Nenhum departamento disponível
        </option>
      ) : null}
    </Select>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/components/departamentos/departamento-select.test.tsx`

Expected: PASS (5 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/use-departamentos.ts \
  frontend/src/components/departamentos/departamento-select.tsx \
  frontend/src/components/departamentos/departamento-select.test.tsx
git commit -m "feat(departamentos): hook e select de departamento no frontend

- useDepartamentos consulta /departamentos e respeita incluir_inativos
- select filtra ativos, aceita filtro de recebimento e estado vazio
- opcao 'todos' existe apenas para a fila, nao para transferencia"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 07)**

Nenhum gap fecha isoladamente; `07-9` fecha na F4.8 com a fila completa. Registrar andamento:

```
| 07-9 | Sem telas de departamento, fila por departamento e transferência por departamento | `frontend/src/app/` | **Alta** | **ABERTO (parcial)** — hook e seletor de departamento (Task F4.4); telas nas Tasks F4.5 e F4.8 |
```

---

### Task F4.5: Tela de departamentos (CRUD, desativação e atendentes)

**Files:**
- Create: `frontend/src/app/(app)/departamentos/page.tsx`
- Create: `frontend/src/components/departamentos/departamento-form.tsx`
- Create: `frontend/src/components/departamentos/departamentos-tabela.tsx`
- Modify: `frontend/src/components/layout/sidebar.tsx:20-30` (link "Departamentos", visível para admin/supervisor)
- Test: `frontend/src/components/departamentos/departamentos-tabela.test.tsx`

**Interfaces:**
- Consumes: `api.get/post/patch/delete` (F4.2), `useDepartamentos` (F4.4), `GET /departamentos/{id}/atendentes` (F1.5).
- Produces:
  - `DepartamentoForm` — `{ inicial?: Departamento; onSubmit: (dados) => void; onCancelar: () => void; salvando?: boolean; erro?: string | null }`
  - `DepartamentosTabela` — lista todos (inclusive inativos), cria, edita e desativa
  - Rota `/departamentos`

**Regras:** desativar é `DELETE` (soft delete no backend); o formulário nunca envia `codigo` em edição (o código é imutável depois de referenciado — spec 02). Erro 409 na desativação aparece como "existem vínculos ativos", nunca como falha genérica.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/departamentos/departamentos-tabela.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const { ApiError } = await vi.importActual<typeof import("@/lib/api")>(
    "@/lib/api"
  );
  return { ApiError, api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() } };
});

import { ApiError, api } from "@/lib/api";
import { DepartamentosTabela } from "@/components/departamentos/departamentos-tabela";
import type { Departamento } from "@/lib/types";

const SUPORTE: Departamento = {
  id: "d1",
  codigo: "suporte_tecnico",
  nome: "Suporte Técnico",
  descricao: "Erros do ERP",
  ativo: true,
  ordem: 1,
  recebe_transferencias: true,
  permite_atribuicao_automatica: false,
};

const ANTIGO: Departamento = {
  ...SUPORTE,
  id: "d2",
  codigo: "antigo",
  nome: "Departamento Antigo",
  ativo: false,
};

function montar() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <DepartamentosTabela />
    </QueryClientProvider>
  );
}

describe("DepartamentosTabela", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue([SUPORTE, ANTIGO]);
  });

  it("lista ativos e inativos com o codigo", async () => {
    montar();

    expect(await screen.findByText("Suporte Técnico")).toBeInTheDocument();
    expect(screen.getByText("Departamento Antigo")).toBeInTheDocument();
    expect(screen.getByText("suporte_tecnico")).toBeInTheDocument();
    expect(screen.getByText("Inativo")).toBeInTheDocument();
  });

  it("desativa um departamento e recarrega a lista", async () => {
    vi.mocked(api.delete).mockResolvedValue(SUPORTE);
    montar();

    await screen.findByText("Suporte Técnico");
    await userEvent.click(screen.getAllByRole("button", { name: "Desativar" })[0]);

    await waitFor(() =>
      expect(api.delete).toHaveBeenCalledWith("/departamentos/d1")
    );
  });

  it("explica o conflito 409 ao desativar com vinculos", async () => {
    vi.mocked(api.delete).mockRejectedValue(
      new ApiError("Existem vínculos ativos", 409)
    );
    montar();

    await screen.findByText("Suporte Técnico");
    await userEvent.click(screen.getAllByRole("button", { name: "Desativar" })[0]);

    expect(
      await screen.findByText(/existem vínculos ativos/i)
    ).toBeInTheDocument();
  });

  it("cria departamento com codigo normalizado", async () => {
    vi.mocked(api.post).mockResolvedValue({ ...SUPORTE, id: "d9", codigo: "fiscal", nome: "Fiscal" });
    montar();

    await screen.findByText("Suporte Técnico");
    await userEvent.click(screen.getByRole("button", { name: "Novo departamento" }));
    await userEvent.type(screen.getByLabelText("Código"), "Fiscal");
    await userEvent.type(screen.getByLabelText("Nome"), "Fiscal");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/departamentos", {
        codigo: "fiscal",
        nome: "Fiscal",
        descricao: null,
        ordem: null,
        recebe_transferencias: true,
        permite_atribuicao_automatica: false,
      })
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/components/departamentos/departamentos-tabela.test.tsx`

Expected: FAIL — `Cannot find module '@/components/departamentos/departamentos-tabela'`.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/departamentos/departamento-form.tsx`:

```tsx
"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Departamento } from "@/lib/types";

export interface DadosDepartamento {
  codigo: string;
  nome: string;
  descricao: string | null;
  ordem: number | null;
  recebe_transferencias: boolean;
  permite_atribuicao_automatica: boolean;
}

interface Props {
  inicial?: Departamento;
  salvando?: boolean;
  erro?: string | null;
  onSubmit: (dados: Partial<DadosDepartamento>) => void;
  onCancelar: () => void;
}

export function DepartamentoForm({
  inicial,
  salvando = false,
  erro,
  onSubmit,
  onCancelar,
}: Props) {
  const [codigo, setCodigo] = useState(inicial?.codigo ?? "");
  const [nome, setNome] = useState(inicial?.nome ?? "");
  const [descricao, setDescricao] = useState(inicial?.descricao ?? "");
  const [ordem, setOrdem] = useState(inicial?.ordem?.toString() ?? "");
  const [recebe, setRecebe] = useState(inicial?.recebe_transferencias ?? true);
  const [automatica, setAutomatica] = useState(
    inicial?.permite_atribuicao_automatica ?? false
  );

  const editando = Boolean(inicial);

  return (
    <form
      className="space-y-3 rounded-lg border border-neutral-200 bg-white p-4"
      onSubmit={(evento) => {
        evento.preventDefault();
        const dados: Partial<DadosDepartamento> = {
          nome: nome.trim(),
          descricao: descricao.trim() || null,
          ordem: ordem.trim() ? Number(ordem) : null,
          recebe_transferencias: recebe,
          permite_atribuicao_automatica: automatica,
        };
        if (!editando) dados.codigo = codigo.trim().toLowerCase();
        onSubmit(dados);
      }}
    >
      {!editando ? (
        <div>
          <label htmlFor="codigo" className="text-sm font-medium text-neutral-700">
            Código
          </label>
          <Input
            id="codigo"
            value={codigo}
            required
            pattern="[a-z][a-z0-9_]*"
            onChange={(evento) => setCodigo(evento.target.value)}
          />
        </div>
      ) : null}

      <div>
        <label htmlFor="nome" className="text-sm font-medium text-neutral-700">
          Nome
        </label>
        <Input
          id="nome"
          value={nome}
          required
          onChange={(evento) => setNome(evento.target.value)}
        />
      </div>

      <div>
        <label htmlFor="descricao" className="text-sm font-medium text-neutral-700">
          Descrição
        </label>
        <Input
          id="descricao"
          value={descricao}
          onChange={(evento) => setDescricao(evento.target.value)}
        />
      </div>

      <div>
        <label htmlFor="ordem" className="text-sm font-medium text-neutral-700">
          Ordem
        </label>
        <Input
          id="ordem"
          type="number"
          value={ordem}
          onChange={(evento) => setOrdem(evento.target.value)}
        />
      </div>

      <label className="flex items-center gap-2 text-sm text-neutral-700">
        <input
          type="checkbox"
          checked={recebe}
          onChange={(evento) => setRecebe(evento.target.checked)}
        />
        Recebe transferências
      </label>

      <label className="flex items-center gap-2 text-sm text-neutral-700">
        <input
          type="checkbox"
          checked={automatica}
          onChange={(evento) => setAutomatica(evento.target.checked)}
        />
        Permite atribuição automática
      </label>

      {erro ? <p className="text-sm text-status-danger">{erro}</p> : null}

      <div className="flex gap-2">
        <Button type="submit" disabled={salvando}>
          Salvar
        </Button>
        <Button type="button" variant="outline" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
```

`frontend/src/components/departamentos/departamentos-tabela.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { DepartamentoForm, type DadosDepartamento } from "./departamento-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useDepartamentos } from "@/hooks/use-departamentos";
import { ApiError, api } from "@/lib/api";
import type { Departamento } from "@/lib/types";

export function DepartamentosTabela() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useDepartamentos({
    incluirInativos: true,
  });
  const [formAberto, setFormAberto] = useState(false);
  const [editando, setEditando] = useState<Departamento | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const invalidar = () =>
    queryClient.invalidateQueries({ queryKey: ["departamentos"] });

  const tratarErro = (erroRecebido: unknown) => {
    if (erroRecebido instanceof ApiError && erroRecebido.status === 409) {
      setErro(
        "Não é possível desativar: existem vínculos ativos (regras, chats ou atendentes)."
      );
      return;
    }
    setErro(
      erroRecebido instanceof Error ? erroRecebido.message : "Erro inesperado"
    );
  };

  const salvar = useMutation({
    mutationFn: (dados: Partial<DadosDepartamento>) =>
      editando
        ? api.patch<Departamento>(`/departamentos/${editando.id}`, dados)
        : api.post<Departamento>("/departamentos", dados),
    onSuccess: async () => {
      setFormAberto(false);
      setEditando(null);
      setErro(null);
      await invalidar();
    },
    onError: tratarErro,
  });

  const desativar = useMutation({
    mutationFn: (id: string) => api.delete<Departamento>(`/departamentos/${id}`),
    onSuccess: async () => {
      setErro(null);
      await invalidar();
    },
    onError: tratarErro,
  });

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (isError) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-neutral-500">
          Departamentos desativados continuam referenciados no histórico.
        </p>
        <Button
          onClick={() => {
            setEditando(null);
            setFormAberto(true);
          }}
        >
          Novo departamento
        </Button>
      </div>

      {erro ? (
        <p role="alert" className="text-sm text-status-danger">
          {erro}
        </p>
      ) : null}

      {formAberto || editando ? (
        <DepartamentoForm
          inicial={editando ?? undefined}
          salvando={salvar.isPending}
          erro={erro}
          onSubmit={(dados) => salvar.mutate(dados)}
          onCancelar={() => {
            setFormAberto(false);
            setEditando(null);
            setErro(null);
          }}
        />
      ) : null}

      {(data ?? []).length === 0 ? (
        <EmptyState title="Nenhum departamento cadastrado" />
      ) : (
        <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 text-left text-xs uppercase text-neutral-500">
              <tr>
                <th className="px-4 py-2">Departamento</th>
                <th className="px-4 py-2">Código</th>
                <th className="px-4 py-2">Ordem</th>
                <th className="px-4 py-2">Situação</th>
                <th className="px-4 py-2 text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((departamento) => (
                <tr key={departamento.id} className="border-t border-neutral-100">
                  <td className="px-4 py-3">
                    <p className="font-medium text-neutral-900">
                      {departamento.nome}
                    </p>
                    {departamento.descricao ? (
                      <p className="text-xs text-neutral-500">
                        {departamento.descricao}
                      </p>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-neutral-600">
                    {departamento.codigo}
                  </td>
                  <td className="px-4 py-3 text-neutral-600">
                    {departamento.ordem ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={departamento.ativo ? "success" : "neutral"}>
                      {departamento.ativo ? "Ativo" : "Inativo"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setEditando(departamento);
                          setFormAberto(false);
                        }}
                      >
                        Editar
                      </Button>
                      {departamento.ativo ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => desativar.mutate(departamento.id)}
                          disabled={desativar.isPending}
                        >
                          Desativar
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

`frontend/src/app/(app)/departamentos/page.tsx`:

```tsx
import { DepartamentosTabela } from "@/components/departamentos/departamentos-tabela";

export default function DepartamentosPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">Departamentos</h1>
        <p className="mt-1 text-neutral-500">
          Fila, regras de roteamento e atendentes por departamento.
        </p>
      </div>
      <DepartamentosTabela />
    </div>
  );
}
```

`frontend/src/components/layout/sidebar.tsx` — no array `links`, após `Conhecimento`:

```tsx
    { href: "/departamentos", label: "Departamentos", icon: Workflow },
```

(e a F4.12 filtra esse link por perfil; até lá ele aparece para todos, como os demais)

> `skeleton.tsx`/`empty-state.tsx` existem em `components/ui/`; se `Skeleton` não exportar `className`, use `<div className="h-64 w-full animate-pulse rounded-lg bg-neutral-100" />`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/components/departamentos/departamentos-tabela.test.tsx`

Expected: PASS (4 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add "frontend/src/app/(app)/departamentos/page.tsx" \
  frontend/src/components/departamentos/departamento-form.tsx \
  frontend/src/components/departamentos/departamentos-tabela.tsx \
  frontend/src/components/departamentos/departamentos-tabela.test.tsx \
  frontend/src/components/layout/sidebar.tsx
git commit -m "feat(departamentos): tela de gestao de departamentos

- lista ativos e inativos com codigo imutavel
- cria e edita nome, descricao, ordem e recebimento de transferencia
- desativacao explica conflito 409 (vinculos ativos) em vez de erro generico"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 07)**

```
| 07-9 | Sem telas de departamento, fila por departamento e transferência por departamento | `frontend/src/app/` | **Alta** | **ABERTO (parcial)** — `/departamentos` com CRUD e desativação (Task F4.5); fila e transferência nas Tasks F4.8/F4.10 |
```

---

### Task F4.6: `chat-store` como fonte do chat ativo e dos filtros

**Files:**
- Modify: `frontend/src/lib/stores/chat-store.ts`
- Modify: `frontend/src/app/(app)/atendimento/page.tsx:15,167` (`useState` → store)
- Test: `frontend/src/lib/stores/chat-store.test.ts`

**Interfaces:**
- Produces:
  - `FILTROS_INICIAIS: FiltrosChat` (`departamentoId: null`, `status: null`, `busca: ""`)
  - `useChatStore` com `chatAtivo: string | null`, `filtros`, `setChatAtivo`, `setDepartamento`, `setStatus`, `setBusca`, `limparFiltros`
  - Remove `chats`/`setChats` do store: a lista é server state do TanStack Query (fonte única)

**Regra:** `chatAtivo` é `string` (ULID), não `number` — o tipo antigo não correspondia ao backend. O store guarda **somente** estado de UI; nenhuma lista de chats é duplicada nele.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/stores/chat-store.test.ts`:

```ts
import { beforeEach, describe, expect, it } from "vitest";

import { FILTROS_INICIAIS, useChatStore } from "@/lib/stores/chat-store";

describe("chat-store", () => {
  beforeEach(() => {
    useChatStore.setState({
      chatAtivo: null,
      filtros: { ...FILTROS_INICIAIS },
    });
  });

  it("comeca sem chat e sem filtro", () => {
    const estado = useChatStore.getState();
    expect(estado.chatAtivo).toBeNull();
    expect(estado.filtros).toEqual({
      departamentoId: null,
      status: null,
      busca: "",
    });
  });

  it("guarda o chat ativo pelo id string", () => {
    useChatStore.getState().setChatAtivo("01JABCDEF");
    expect(useChatStore.getState().chatAtivo).toBe("01JABCDEF");
  });

  it("guarda filtros independentes", () => {
    const { setDepartamento, setStatus, setBusca } = useChatStore.getState();
    setDepartamento("d1");
    setStatus("AGUARDANDO_HUMANO_SEM_SOLUCAO");
    setBusca("nfe");

    expect(useChatStore.getState().filtros).toEqual({
      departamentoId: "d1",
      status: "AGUARDANDO_HUMANO_SEM_SOLUCAO",
      busca: "nfe",
    });
  });

  it("limparFiltros preserva o chat ativo", () => {
    const estado = useChatStore.getState();
    estado.setChatAtivo("c1");
    estado.setDepartamento("d1");
    estado.setBusca("x");

    useChatStore.getState().limparFiltros();

    expect(useChatStore.getState().chatAtivo).toBe("c1");
    expect(useChatStore.getState().filtros).toEqual({
      departamentoId: null,
      status: null,
      busca: "",
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/lib/stores/chat-store.test.ts`

Expected: FAIL — `FILTROS_INICIAIS` não é exportado.

- [ ] **Step 3: Write minimal implementation**

Substitua `frontend/src/lib/stores/chat-store.ts` por:

```ts
import { create } from "zustand";

export interface FiltrosChat {
  departamentoId: string | null;
  status: string | null;
  busca: string;
}

export const FILTROS_INICIAIS: FiltrosChat = {
  departamentoId: null,
  status: null,
  busca: "",
};

interface ChatState {
  chatAtivo: string | null;
  filtros: FiltrosChat;
  setChatAtivo: (id: string | null) => void;
  setDepartamento: (id: string | null) => void;
  setStatus: (status: string | null) => void;
  setBusca: (busca: string) => void;
  limparFiltros: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  chatAtivo: null,
  filtros: { ...FILTROS_INICIAIS },
  setChatAtivo: (id) => set({ chatAtivo: id }),
  setDepartamento: (departamentoId) =>
    set((estado) => ({ filtros: { ...estado.filtros, departamentoId } })),
  setStatus: (status) =>
    set((estado) => ({ filtros: { ...estado.filtros, status } })),
  setBusca: (busca) =>
    set((estado) => ({ filtros: { ...estado.filtros, busca } })),
  limparFiltros: () => set({ filtros: { ...FILTROS_INICIAIS } }),
}));
```

Em `frontend/src/app/(app)/atendimento/page.tsx`:

```tsx
import { useChatStore } from "@/lib/stores/chat-store";
```

e no corpo:

```tsx
  const { chatAtivo, setChatAtivo } = useChatStore();
```

(remover `const [chatAtivo, setChatAtivo] = useState<number | null>(null);`; `useState` continua importado por causa de `novaMsg`)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/lib/stores/chat-store.test.ts`

Expected: PASS (4 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/stores/chat-store.ts frontend/src/lib/stores/chat-store.test.ts "frontend/src/app/(app)/atendimento/page.tsx"
git commit -m "refactor(frontend): chat-store vira fonte do chat ativo e filtros

- chatAtivo tipado como string (ULID), nao number
- store guarda apenas estado de UI; lista continua no TanStack Query
- filtros de departamento, status e busca com reset explicito"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 07)**

```
| 07-5 | `chat-store` (`chatAtivo`) não é usado; estado local duplica a fonte | `lib/stores/chat-store.ts` vs `(app)/atendimento/page.tsx:15` | Baixa | **CORRIGIDO** — `useChatStore` é a fonte do chat ativo e dos filtros; a página não mantém `useState` duplicado |
```

---

### Task F4.7: Tempo real — eventos nas mutações e reconexão com backoff

**Files:**
- Modify: `backend/app/api/routes/chats.py` (emitir `chat_atualizado` nas mutações)
- Modify: `backend/app/api/routes/roteamento.py` (transferir/atribuir/confirmar/reabrir)
- Modify: `backend/app/api/routes/kanban.py:23-30` (`mover_card`)
- Create: `frontend/src/lib/reconnect.ts`
- Modify: `frontend/src/hooks/use-chat-socket.ts` (backoff + invalidação central)
- Test: `backend/tests/test_ws_eventos_chat.py`, `frontend/src/lib/reconnect.test.ts`, `frontend/src/hooks/use-chat-socket.test.tsx`

**Interfaces:**
- Produces:
  - Evento `chat_atualizado` com `{chat_id, status, departamento_id, atendente_id}` em toda mutação de chat
  - `status_update` mantido (compatibilidade com o client atual)
  - `proximoBackoff(tentativa: number): number` — `min(1000 * 2**tentativa, 15000)`
  - Mapa `INVALIDACOES` no hook: `nova_mensagem`, `status_update`, `chat_atualizado`, `diagnostico`, `departamento_atualizado`

**Regra:** a rota emite **depois** de o service concluir; se o service levanta (403/409), nenhum evento é emitido. O client nunca atualiza estado local por conta própria: invalida a query e relê (spec 07 §Cache e tempo real).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_ws_eventos_chat.py`:

```python
"""Mutacoes de chat emitem evento WebSocket (spec 03 §eventos)."""

import pytest

from app.api.websocket_manager import manager


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def eventos(monkeypatch):
    capturados: list[tuple] = []

    async def fake_send(chat_id, evento, dados):
        capturados.append((chat_id, evento, dados))

    monkeypatch.setattr(manager, "send_event", fake_send)
    return capturados


async def _chat(fake_repos, status: str = "NOVO"):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    return await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": status}
    )


@pytest.mark.asyncio
async def test_status_emite_status_update_e_chat_atualizado(
    client, admin_token, fake_repos, eventos
):
    chat = await _chat(fake_repos)

    resp = await client.patch(
        f"/chats/{chat['id']}/status",
        json={"status": "IA_ANALISANDO"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 200
    nomes = [evento for _, evento, _ in eventos]
    assert "status_update" in nomes
    assert "chat_atualizado" in nomes
    assert all(chat_id == chat["id"] for chat_id, _, _ in eventos)


@pytest.mark.asyncio
async def test_pegar_emite_chat_atualizado(client, atendente_token, fake_repos, eventos):
    chat = await _chat(fake_repos)

    resp = await client.patch(f"/chats/{chat['id']}/pegar", headers=_auth(atendente_token))

    assert resp.status_code == 200
    assert [evento for _, evento, _ in eventos] == ["chat_atualizado"]


@pytest.mark.asyncio
async def test_transicao_invalida_nao_emite_evento(
    client, admin_token, fake_repos, eventos
):
    chat = await _chat(fake_repos, status="ENCERRADO")

    resp = await client.patch(
        f"/chats/{chat['id']}/status",
        json={"status": "NOVO"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 409
    assert eventos == []


@pytest.mark.asyncio
async def test_kanban_mover_emite_chat_atualizado(
    client, admin_token, fake_repos, eventos
):
    chat = await _chat(fake_repos)

    resp = await client.patch(
        "/kanban/mover",
        json={"chat_id": chat["id"], "status": "EM_ATENDIMENTO"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 204
    assert [evento for _, evento, _ in eventos] == ["chat_atualizado"]
```

> Se `KanbanService` usar transições válidas, o teste acima precisa de `status` de origem compatível (`NOVO` → `EM_ATENDIMENTO` não é transição direta). Nesse caso use `IA_ANALISANDO` como destino e ajuste o corpo; o que se verifica é **um** evento por mutação bem-sucedida.

Create `frontend/src/lib/reconnect.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { proximoBackoff } from "@/lib/reconnect";

describe("backoff de reconexao", () => {
  it("dobra a espera a cada tentativa", () => {
    expect(proximoBackoff(0)).toBe(1000);
    expect(proximoBackoff(1)).toBe(2000);
    expect(proximoBackoff(2)).toBe(4000);
    expect(proximoBackoff(3)).toBe(8000);
  });

  it("limita a espera em 15 segundos", () => {
    expect(proximoBackoff(4)).toBe(15000);
    expect(proximoBackoff(20)).toBe(15000);
  });
});
```

Create `frontend/src/hooks/use-chat-socket.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useChatSocket } from "@/hooks/use-chat-socket";

class FakeWebSocket {
  static instancias: FakeWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((evento: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  enviados: string[] = [];

  constructor(public url: string) {
    FakeWebSocket.instancias.push(this);
  }

  send(dados: string) {
    this.enviados.push(dados);
  }

  close() {
    this.onclose?.();
  }

  abrir() {
    this.onopen?.();
  }

  derrubar() {
    this.onclose?.();
  }
}

function montar(chatId: string) {
  const client = new QueryClient();
  return renderHook(() => useChatSocket(chatId), {
    wrapper: ({ children }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  });
}

describe("useChatSocket", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.setItem("token", "abc");
    FakeWebSocket.instancias = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("envia o token como primeira mensagem", () => {
    montar("c1");
    const socket = FakeWebSocket.instancias[0];

    act(() => socket.abrir());

    expect(JSON.parse(socket.enviados[0])).toEqual({ token: "abc" });
  });

  it("reconecta com backoff apos queda", () => {
    montar("c1");
    const primeiro = FakeWebSocket.instancias[0];

    act(() => primeiro.abrir());
    act(() => primeiro.derrubar());

    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(FakeWebSocket.instancias).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(FakeWebSocket.instancias).toHaveLength(2);
  });

  it("nao reconecta depois de desmontar", () => {
    const { unmount } = montar("c1");
    const socket = FakeWebSocket.instancias[0];

    act(() => socket.abrir());
    unmount();

    act(() => {
      vi.advanceTimersByTime(30000);
    });
    expect(FakeWebSocket.instancias).toHaveLength(1);
  });

  it("invalida roteamento ao receber diagnostico", () => {
    const client = new QueryClient();
    const invalidar = vi.spyOn(client, "invalidateQueries");
    const { unmount } = renderHook(() => useChatSocket("c1"), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      ),
    });
    const socket = FakeWebSocket.instancias[0];

    act(() => socket.abrir());
    act(() =>
      socket.onmessage?.({
        data: JSON.stringify({ event: "diagnostico", data: { chat_id: "c1" } }),
      })
    );

    expect(invalidar).toHaveBeenCalledWith({ queryKey: ["roteamento"] });
    unmount();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_ws_eventos_chat.py -v`
Run: `cd frontend && npm run test -- src/lib/reconnect.test.ts src/hooks/use-chat-socket.test.tsx`

Expected: backend FAIL (nenhum evento capturado); frontend FAIL (`@/lib/reconnect` inexistente; sem reconexão).

- [ ] **Step 3: Write minimal implementation**

Backend — em `backend/app/api/routes/chats.py`, adicionar no topo:

```python
from app.api.websocket_manager import manager
```

e, em cada rota de mutação (`atualizar_status`, `assinar_chat`, `definir_prioridade`, `pegar_chat`, `transferir_chat`, `transferir_chat_grupo`), trocar o `return` por este bloco — notando que `anterior` é lido **antes** da chamada ao service:

```python
    anterior = await service.obter(chat_id)          # status ANTES da mutação

    chat = await service.atualizar_status(chat_id, body.status)

    dados = {
        "chat_id": chat["id"],
        "status": chat["status"],
        "departamento_id": chat.get("departamento_id"),
        "atendente_id": chat.get("atendente_id"),
    }
    await manager.send_event(chat_id, "chat_atualizado", dados)
    if chat["status"] != anterior["status"]:
        await manager.send_event(chat_id, "status_update", dados)
    return chat
```

Mesmo padrão nas rotas de `roteamento.py` (`transferir-departamento`, `atribuir-atendente`, `confirmar-resolucao`, `reabrir`) e em `kanban.py`:

```python
    await service.mover(body.chat_id, body.status)
    await manager.send_event(
        body.chat_id,
        "chat_atualizado",
        {"chat_id": body.chat_id, "status": body.status.value},
    )
```

Frontend — `frontend/src/lib/reconnect.ts`:

```ts
const ESPERA_BASE_MS = 1000;
const ESPERA_MAXIMA_MS = 15000;

export function proximoBackoff(tentativa: number): number {
  const espera = ESPERA_BASE_MS * 2 ** Math.max(0, tentativa);
  return Math.min(espera, ESPERA_MAXIMA_MS);
}
```

`frontend/src/hooks/use-chat-socket.ts`:

```ts
"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { proximoBackoff } from "@/lib/reconnect";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001";

const INVALIDACOES: Record<string, string[]> = {
  nova_mensagem: ["mensagens", "chats", "chat"],
  status_update: ["chat", "chats", "dashboard"],
  chat_atualizado: ["chat", "chats", "dashboard", "roteamento"],
  diagnostico: ["chat", "chats", "roteamento"],
  departamento_atualizado: ["departamentos"],
};

export function useChatSocket(chatId: string | null) {
  const queryClient = useQueryClient();
  const tentativaRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!chatId) return;

    let ativo = true;
    let socket: WebSocket | null = null;

    const conectar = () => {
      if (!ativo) return;
      const token = localStorage.getItem("token");
      if (!token) return;

      socket = new WebSocket(`${WS_BASE}/ws/chat/${chatId}`);

      socket.onopen = () => {
        tentativaRef.current = 0;
        socket?.send(JSON.stringify({ token }));
      };

      socket.onmessage = (evento) => {
        let mensagem: { event?: string };
        try {
          mensagem = JSON.parse(String(evento.data));
        } catch {
          return;
        }
        const chaves = INVALIDACOES[mensagem.event ?? ""] ?? [];
        chaves.forEach((chave) =>
          queryClient.invalidateQueries({ queryKey: [chave] })
        );
      };

      socket.onclose = () => {
        if (!ativo) return;
        const espera = proximoBackoff(tentativaRef.current);
        tentativaRef.current += 1;
        timerRef.current = setTimeout(conectar, espera);
      };

      socket.onerror = () => socket?.close();
    };

    conectar();

    return () => {
      ativo = false;
      if (timerRef.current) clearTimeout(timerRef.current);
      socket?.close();
    };
  }, [chatId, queryClient]);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_ws_eventos_chat.py -v`
Run: `cd frontend && npm run test -- src/lib/reconnect.test.ts src/hooks/use-chat-socket.test.tsx`

Expected: PASS (4 backend + 6 frontend).

- [ ] **Step 5: Run the full suite + build**

Run: `cd backend && pytest tests/ -q && ruff check app tests`
Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/chats.py backend/app/api/routes/roteamento.py \
  backend/app/api/routes/kanban.py backend/tests/test_ws_eventos_chat.py \
  frontend/src/lib/reconnect.ts frontend/src/lib/reconnect.test.ts \
  frontend/src/hooks/use-chat-socket.ts frontend/src/hooks/use-chat-socket.test.tsx
git commit -m "feat(tempo-real): mutacoes emitem evento e cliente reconecta com backoff

- toda mutacao de chat emite chat_atualizado (status_update mantido)
- transicao invalida nao emite evento (erro antes da publicacao)
- websocket reconecta com backoff exponencial limitado a 15s
- invalida roteamento e departamentos ao receber evento"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 03 e 07)**

```
| 03-8 | Rotas que alteram chat não emitem evento WebSocket (`status`, `pegar`, `transferir`, `assinar`, `prioridade`, kanban `mover`) | `api/routes/chats.py`, `kanban.py` | Média | **CORRIGIDO** — mutações emitem `chat_atualizado` (`manager.send_event`), com teste em `tests/test_ws_eventos_chat.py` |
| 07-3 | WebSocket sem reconexão nem backoff | `hooks/use-chat-socket.ts` | Média | **CORRIGIDO** — `proximoBackoff` (1s→15s) e reconexão testada; invalidação central por evento |
```

---

### Task F4.8: Fila de atendimento com filtro por departamento

**Files:**
- Create: `frontend/src/components/atendimento/fila-chats.tsx`
- Modify: `frontend/src/app/(app)/atendimento/page.tsx` (usa `FilaChats`; remove a lista inline)
- Test: `frontend/src/components/atendimento/fila-chats.test.tsx`

**Interfaces:**
- Consumes: `useChatStore` (F4.6), `DepartamentoSelect` com `permitirTodos` (F4.4), `GET /chats?departamento_id=&status=` (F1.9), `ChatResumo`/`rotuloStatus` (F4.1/F4.2).
- Produces: `FilaChats` — `{ onSelecionar?: (chatId: string) => void }` com filtros, estados de carregamento/vazio/erro e badge de prioridade.

**Regras:** `departamento_id` e `status` vão na query string (o backend aplica o escopo RBAC **e** o filtro); `busca` é filtro local sobre `cliente_nome`/`resumo_problema` porque o backend não tem endpoint de busca textual. Atendente sem permissão recebe 403 do backend — a fila mostra o erro, nunca uma lista vazia silenciosa.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/atendimento/fila-chats.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ api: { get: vi.fn() } }));

import { FilaChats } from "@/components/atendimento/fila-chats";
import { api } from "@/lib/api";
import { FILTROS_INICIAIS, useChatStore } from "@/lib/stores/chat-store";
import type { ChatResumo } from "@/lib/types";

const CHATS: ChatResumo[] = [
  {
    id: "c1",
    cliente_id: "cli1",
    cliente_nome: "Maria",
    status: "AGUARDANDO_HUMANO_SEM_SOLUCAO",
    prioridade: "urgente",
    resumo_problema: "NF-e não emite",
    ultima_mensagem_em: null,
    atendente_id: null,
    departamento_id: "d1",
    solucao_sugerida_ia: null,
  },
  {
    id: "c2",
    cliente_id: "cli2",
    cliente_nome: "João",
    status: "NOVO",
    prioridade: "baixa",
    resumo_problema: "Dúvida de boleto",
    ultima_mensagem_em: null,
    atendente_id: null,
    departamento_id: "d2",
    solucao_sugerida_ia: null,
  },
];

function montar(onSelecionar = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <FilaChats onSelecionar={onSelecionar} />
    </QueryClientProvider>
  );
  return onSelecionar;
}

describe("FilaChats", () => {
  beforeEach(() => {
    useChatStore.setState({
      chatAtivo: null,
      filtros: { ...FILTROS_INICIAIS },
    });
    vi.mocked(api.get).mockResolvedValue(CHATS);
  });

  it("lista os chats com rotulo de status e prioridade", async () => {
    montar();

    expect(await screen.findByText("Maria")).toBeInTheDocument();
    expect(screen.getByText("Aguardando humano (sem solução)")).toBeInTheDocument();
    expect(screen.getByText("urgente")).toBeInTheDocument();
  });

  it("envia o departamento do filtro para a API", async () => {
    useChatStore.getState().setDepartamento("d1");
    montar();

    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith("/chats", {
        departamento_id: "d1",
        status: undefined,
      })
    );
  });

  it("filtra por busca local sem chamar a API de novo", async () => {
    montar();
    await screen.findByText("Maria");

    await userEvent.type(
      screen.getByPlaceholderText("Buscar por cliente ou resumo"),
      "boleto"
    );

    expect(screen.getByText("João")).toBeInTheDocument();
    expect(screen.queryByText("Maria")).not.toBeInTheDocument();
    expect(api.get).toHaveBeenCalledTimes(1);
  });

  it("seleciona o chat clicado", async () => {
    const onSelecionar = montar();
    await userEvent.click(await screen.findByText("Maria"));

    expect(onSelecionar).toHaveBeenCalledWith("c1");
  });

  it("mostra vazio quando nao ha chats", async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    montar();

    expect(
      await screen.findByText("Nenhuma conversa neste filtro")
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/components/atendimento/fila-chats.test.tsx`

Expected: FAIL — `Cannot find module '@/components/atendimento/fila-chats'`.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/atendimento/fila-chats.tsx`:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, UserPlus } from "lucide-react";

import { DepartamentoSelect } from "@/components/departamentos/departamento-select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatStore } from "@/lib/stores/chat-store";
import { api } from "@/lib/api";
import type { ChatResumo } from "@/lib/types";
import { rotuloStatus, variantePrioridade } from "@/lib/status";

interface Props {
  onSelecionar?: (chatId: string) => void;
}

export function FilaChats({ onSelecionar }: Props) {
  const { chatAtivo, setChatAtivo, filtros, setDepartamento, setStatus, setBusca } =
    useChatStore();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["chats", filtros.departamentoId, filtros.status],
    queryFn: () =>
      api.get<ChatResumo[]>("/chats", {
        departamento_id: filtros.departamentoId,
        status: filtros.status,
      }),
    refetchInterval: 30000,
  });

  const termo = filtros.busca.trim().toLowerCase();
  const visiveis = (data ?? []).filter((chat) => {
    if (!termo) return true;
    return `${chat.cliente_nome ?? ""} ${chat.resumo_problema ?? ""}`
      .toLowerCase()
      .includes(termo);
  });

  const selecionar = (chatId: string) => {
    setChatAtivo(chatId);
    onSelecionar?.(chatId);
  };

  return (
    <div className="flex w-80 flex-col rounded-lg border border-neutral-200 bg-white">
      <div className="space-y-2 border-b border-neutral-200 p-4">
        <h2 className="font-semibold text-neutral-900">Conversas</h2>
        <Input
          placeholder="Buscar por cliente ou resumo"
          value={filtros.busca}
          onChange={(evento) => setBusca(evento.target.value)}
        />
        <DepartamentoSelect
          valor={filtros.departamentoId}
          onChange={setDepartamento}
          permitirTodos
        />
        <select
          aria-label="Status"
          className="h-9 w-full rounded-md border border-neutral-300 bg-white px-2 text-sm"
          value={filtros.status ?? ""}
          onChange={(evento) => setStatus(evento.target.value || null)}
        >
          <option value="">Todos os status</option>
          <option value="AGUARDANDO_HUMANO_SEM_SOLUCAO">Aguardando humano (sem solução)</option>
          <option value="AGUARDANDO_HUMANO_COM_SOLUCAO">Aguardando humano (com solução)</option>
          <option value="AGUARDANDO_CLIENTE">Aguardando cliente</option>
          <option value="EM_ATENDIMENTO">Em atendimento</option>
        </select>
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : isError ? (
          <ErrorState onRetry={() => refetch()} />
        ) : visiveis.length === 0 ? (
          <EmptyState title="Nenhuma conversa neste filtro" />
        ) : (
          visiveis.map((chat) => (
            <button
              key={chat.id}
              onClick={() => selecionar(chat.id)}
              className={`w-full border-b border-neutral-100 p-4 text-left transition-colors hover:bg-neutral-50 ${
                chatAtivo === chat.id
                  ? "border-l-4 border-l-primary-500 bg-primary-50"
                  : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-neutral-900">
                  {chat.cliente_nome ?? "Cliente"}
                </p>
                <Badge variant={variantePrioridade(chat.prioridade)} className="text-[10px]">
                  {chat.prioridade}
                </Badge>
              </div>
              <div className="mt-1 flex items-center gap-2">
                <span className="text-xs text-neutral-500">
                  {rotuloStatus(chat.status)}
                </span>
                {chat.solucao_sugerida_ia ? (
                  <Bot className="h-3 w-3 text-status-success" aria-label="Solução sugerida pela IA" />
                ) : null}
              </div>
              {chat.resumo_problema ? (
                <p className="mt-1 truncate text-xs text-neutral-400">
                  {chat.resumo_problema}
                </p>
              ) : null}
              {!chat.atendente_id ? (
                <div className="mt-2 flex items-center gap-1 text-xs text-neutral-500">
                  <UserPlus className="h-3 w-3" /> sem atendente
                </div>
              ) : null}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
```

Em `frontend/src/app/(app)/atendimento/page.tsx`, substituir o bloco `{/* Inbox */}` (linhas 158-215) por:

```tsx
      <FilaChats onSelecionar={setChatAtivo} />
```

e remover da página: a query `["chats"]` (a fila cuida dela), `pegarChat`, `statusLabels`, `prioridadeLabels`, `UserPlus` e `Badge` se ficarem sem uso. Importar:

```tsx
import { FilaChats } from "@/components/atendimento/fila-chats";
import { rotuloStatus } from "@/lib/status";
```

onde a página ainda exibir status (cabeçalho do chat), usar `rotuloStatus(chatDetail?.status)`.

> O `select` de status continua nativo aqui de propósito: a F4.13 troca todos por um componente acessível. Não gaste tempo estilizando-o agora.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/components/atendimento/fila-chats.test.tsx`

Expected: PASS (5 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/atendimento/fila-chats.tsx \
  frontend/src/components/atendimento/fila-chats.test.tsx \
  "frontend/src/app/(app)/atendimento/page.tsx"
git commit -m "feat(atendimento): fila com filtro de departamento e status

- departamento_id e status vao na query string (escopo aplicado no backend)
- busca textual e local, sem chamada extra
- estados de carregando, vazio e erro com retry na propria fila"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 07)**

```
| 07-9 | Sem telas de departamento, fila por departamento e transferência por departamento | `frontend/src/app/` | **Alta** | **CORRIGIDO (fila)** — `FilaChats` filtra por departamento/status (Task F4.8) e `/departamentos` faz o CRUD (Task F4.5); transferência por departamento na Task F4.10 |
```

---

### Task F4.9: Painel de diagnóstico (intenção, roteamento e artigos)

**Files:**
- Create: `frontend/src/components/atendimento/diagnostico-panel.tsx`
- Modify: `frontend/src/app/(app)/atendimento/page.tsx` (substitui o painel "IA Diagnóstico" inline)
- Test: `frontend/src/components/atendimento/diagnostico-panel.test.tsx`

**Interfaces:**
- Consumes: `GET /chats/{id}/roteamento` → `RoteamentoChat` (F2.8, campos gravados na F3.4).
- Produces: `DiagnosticoPanel` — `{ chatId: string | null }`; query key `["roteamento", chatId]` (invalidada pela F4.7).

**Regras da spec 07 §Atendimento:** mostrar intenção, subintenção, categoria ERP, departamento sugerido **e** final, justificativa, resumo/causa, solução e artigos consultados; confiança é dado auxiliar, sempre rotulada como sugestão automática. Sem diagnóstico → estado vazio explícito, nunca números inventados.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/atendimento/diagnostico-panel.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ api: { get: vi.fn() } }));

import { DiagnosticoPanel } from "@/components/atendimento/diagnostico-panel";
import { api } from "@/lib/api";
import type { RoteamentoChat } from "@/lib/types";

const ROTEAMENTO: RoteamentoChat = {
  chat_id: "c1",
  departamento_id: "d1",
  departamento_codigo: "suporte_tecnico",
  intencao: "problema_tecnico",
  subintencao: "emissao_nfe",
  categoria_erp: "fiscal",
  departamento_sugerido_codigo: "suporte_tecnico",
  motivo: "Regra problema_tecnico+fiscal prioridade 10",
  confianca: 0.94,
  artigos_consultados: [
    { id: "a1", titulo: "Erro na emissão de NF-e", score: 0.93, categoria: "fiscal" },
  ],
  tem_diagnostico: true,
};

function montar(chatId: string | null = "c1") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <DiagnosticoPanel chatId={chatId} />
    </QueryClientProvider>
  );
}

describe("DiagnosticoPanel", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue(ROTEAMENTO);
  });

  it("mostra intencao, subintencao e categoria ERP", async () => {
    montar();

    expect(await screen.findByText("problema_tecnico")).toBeInTheDocument();
    expect(screen.getByText("emissao_nfe")).toBeInTheDocument();
    expect(screen.getByText("fiscal")).toBeInTheDocument();
  });

  it("distingue departamento sugerido de departamento final", async () => {
    montar();

    expect(await screen.findByText("suporte_tecnico")).toBeInTheDocument();
    expect(screen.getByText("Departamento final")).toBeInTheDocument();
    expect(screen.getByText("Sugerido pela IA")).toBeInTheDocument();
  });

  it("mostra a justificativa do roteamento", async () => {
    montar();

    expect(
      await screen.findByText("Regra problema_tecnico+fiscal prioridade 10")
    ).toBeInTheDocument();
  });

  it("lista os artigos consultados com score", async () => {
    montar();

    expect(await screen.findByText("Erro na emissão de NF-e")).toBeInTheDocument();
    expect(screen.getByText(/0\.93/)).toBeInTheDocument();
  });

  it("rotula confianca como sugestao automatica", async () => {
    montar();

    expect(await screen.findByText(/sugestão automática/i)).toBeInTheDocument();
    expect(screen.getByText("94%")).toBeInTheDocument();
  });

  it("mostra vazio quando o chat ainda nao tem diagnostico", async () => {
    vi.mocked(api.get).mockResolvedValue({
      ...ROTEAMENTO,
      intencao: null,
      subintencao: null,
      categoria_erp: null,
      motivo: null,
      confianca: null,
      artigos_consultados: [],
      tem_diagnostico: false,
    });
    montar();

    expect(
      await screen.findByText("IA ainda não analisou este chamado")
    ).toBeInTheDocument();
  });

  it("nao consulta a API sem chat selecionado", () => {
    montar(null);

    expect(api.get).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/components/atendimento/diagnostico-panel.test.tsx`

Expected: FAIL — módulo inexistente.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/atendimento/diagnostico-panel.tsx`:

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { RoteamentoChat } from "@/lib/types";

interface Props {
  chatId: string | null;
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase text-neutral-500">{rotulo}</p>
      <div className="mt-1 text-sm text-neutral-900">{children}</div>
    </div>
  );
}

export function DiagnosticoPanel({ chatId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["roteamento", chatId],
    queryFn: () => api.get<RoteamentoChat>(`/chats/${chatId}/roteamento`),
    enabled: Boolean(chatId),
  });

  return (
    <div className="flex w-80 flex-col rounded-lg border border-neutral-200 bg-white">
      <div className="border-b border-neutral-200 p-4">
        <h3 className="flex items-center gap-2 font-semibold text-neutral-900">
          <Bot className="h-4 w-4 text-primary-500" aria-hidden="true" />
          Diagnóstico da IA
        </h3>
      </div>

      <div className="flex-1 space-y-4 overflow-auto p-4">
        {isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : !data?.tem_diagnostico ? (
          <p className="py-8 text-center text-sm text-neutral-400">
            IA ainda não analisou este chamado
          </p>
        ) : (
          <>
            <Campo rotulo="Intenção">
              <span className="font-mono text-xs">{data.intencao ?? "—"}</span>
              {data.subintencao ? (
                <span className="ml-2 font-mono text-xs text-neutral-500">
                  {data.subintencao}
                </span>
              ) : null}
            </Campo>

            <Campo rotulo="Categoria ERP">
              <span className="font-mono text-xs">{data.categoria_erp ?? "—"}</span>
            </Campo>

            <Campo rotulo="Departamento final">
              {data.departamento_codigo ? (
                <Badge variant="primary" className="font-mono text-[10px]">
                  {data.departamento_codigo}
                </Badge>
              ) : (
                <span className="text-neutral-400">não definido</span>
              )}
            </Campo>

            <Campo rotulo="Sugerido pela IA">
              <span className="font-mono text-xs text-neutral-500">
                {data.departamento_sugerido_codigo ?? "—"}
              </span>
            </Campo>

            {data.motivo ? (
              <Campo rotulo="Justificativa do roteamento">
                <p className="text-neutral-700">{data.motivo}</p>
              </Campo>
            ) : null}

            {data.confianca !== null && data.confianca !== undefined ? (
              <Campo rotulo="Confiança (sugestão automática)">
                <div className="h-2 rounded-full bg-neutral-100">
                  <div
                    className="h-2 rounded-full bg-primary-500"
                    style={{ width: `${Math.round(data.confianca * 100)}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-neutral-500">
                  {Math.round(data.confianca * 100)}%
                </p>
              </Campo>
            ) : null}

            <div>
              <p className="text-xs font-medium uppercase text-neutral-500">
                Artigos consultados
              </p>
              {data.artigos_consultados.length === 0 ? (
                <p className="mt-1 text-sm text-neutral-400">Nenhum artigo</p>
              ) : (
                <ul className="mt-1 space-y-2">
                  {data.artigos_consultados.map((artigo) => (
                    <li key={artigo.id} className="rounded border border-neutral-100 p-2">
                      <p className="text-sm text-neutral-900">{artigo.titulo}</p>
                      <p className="font-mono text-[10px] text-neutral-500">
                        {artigo.categoria} · score {artigo.score.toFixed(2)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
```

Em `frontend/src/app/(app)/atendimento/page.tsx`, substituir o bloco `{/* IA Summary Panel */}` (linhas 337-384) por:

```tsx
      <DiagnosticoPanel chatId={chatAtivo} />
```

e importar `DiagnosticoPanel`. O resumo/solução que vinham de `chatDetail` continuam disponíveis na F4.9 como campos do diagnóstico; se a página ainda os exibir em outro lugar, mantenha.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/components/atendimento/diagnostico-panel.test.tsx`

Expected: PASS (7 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/atendimento/diagnostico-panel.tsx \
  frontend/src/components/atendimento/diagnostico-panel.test.tsx \
  "frontend/src/app/(app)/atendimento/page.tsx"
git commit -m "feat(atendimento): painel de diagnostico com roteamento e artigos

- mostra intencao, subintencao, categoria ERP e departamento final
- separa departamento sugerido pela IA do destino resolvido no backend
- exibe justificativa, artigos consultados e confianca como sugestao"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 07)**

```
| 07-10 | Sem painel de diagnóstico de intenção/roteamento nem status de sincronização do chamado | `(app)/atendimento/page.tsx` | **Alta** | **CORRIGIDO (diagnóstico)** — `DiagnosticoPanel` lê `/chats/{id}/roteamento` (Task F4.9); status de sincronização Emsoft segue bloqueado pelo gap 11-1 |
```

---

### Task F4.10: Transferir por departamento e atribuir atendente (409)

**Files:**
- Create: `frontend/src/components/atendimento/transferir-modal.tsx`
- Modify: `frontend/src/app/(app)/atendimento/page.tsx` (remove o modal inline e as mutations `transferirChat`/`transferirGrupo`)
- Test: `frontend/src/components/atendimento/transferir-modal.test.tsx`

**Interfaces:**
- Consumes: `PATCH /chats/{id}/transferir-departamento` (F2.6), `PATCH /chats/{id}/atribuir-atendente` (F2.7), `DepartamentoSelect` com `filtro` (F4.4), `GET /atendentes/ativos`.
- Produces: `TransferirModal` — `{ chatId: string; aberto: boolean; onFechar: () => void }` emitindo `chat_atualizado` (via backend) e invalidando `chats`, `chat`, `roteamento`.

**Regras:** transferir departamento envia `{departamento_id, motivo}` — nunca a string `setor`. Atribuir atendente usa `{atendente_id, motivo}`; **409** significa que outro atendente assumiu primeiro: a mensagem do backend é exibida e o modal **permanece aberto** (o operador precisa ver o novo responsável). `preservar_atendente_se_compativel` fica marcado por padrão no fluxo de transferência de departamento.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/atendimento/transferir-modal.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const { ApiError } = await vi.importActual<typeof import("@/lib/api")>(
    "@/lib/api"
  );
  return { ApiError, api: { get: vi.fn(), patch: vi.fn() } };
});

import { ApiError, api } from "@/lib/api";
import { TransferirModal } from "@/components/atendimento/transferir-modal";
import type { Departamento } from "@/lib/types";

const DEPARTAMENTOS: Departamento[] = [
  {
    id: "d1",
    codigo: "suporte_tecnico",
    nome: "Suporte Técnico",
    descricao: null,
    ativo: true,
    ordem: 1,
    recebe_transferencias: true,
    permite_atribuicao_automatica: false,
  },
];

const ATENDENTES = [
  { id: "a1", nome: "Ana", perfil: "atendente", ativo: true, email: "ana@test.com" },
  { id: "a2", nome: "Bruno", perfil: "atendente", ativo: true, email: "bruno@test.com" },
];

function montar(onFechar = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <TransferirModal chatId="c1" aberto onFechar={onFechar} />
    </QueryClientProvider>
  );
  return onFechar;
}

describe("TransferirModal", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation(async (caminho: string) =>
      caminho === "/departamentos" ? DEPARTAMENTOS : ATENDENTES
    );
    vi.mocked(api.patch).mockResolvedValue({});
  });

  it("transfere por departamento enviando o id", async () => {
    montar();

    await userEvent.selectOptions(
      await screen.findByLabelText("Departamento"),
      "Suporte Técnico"
    );
    await userEvent.click(screen.getByRole("button", { name: "Transferir" }));

    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith(
        "/chats/c1/transferir-departamento",
        expect.objectContaining({
          departamento_id: "d1",
          preservar_atendente_se_compativel: true,
        })
      )
    );
  });

  it("atribui atendente pelo id", async () => {
    montar();

    await userEvent.click(screen.getByRole("tab", { name: "Atendente" }));
    await userEvent.click(await screen.findByText("Bruno"));

    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith(
        "/chats/c1/atribuir-atendente",
        expect.objectContaining({ atendente_id: "a2" })
      )
    );
  });

  it("mostra conflito 409 e mantem o modal aberto", async () => {
    const onFechar = montar();
    vi.mocked(api.patch).mockRejectedValue(
      new ApiError("Chat já assumido por outro atendente", 409)
    );

    await userEvent.click(screen.getByRole("tab", { name: "Atendente" }));
    await userEvent.click(await screen.findByText("Ana"));

    expect(
      await screen.findByRole("alert")
    ).toHaveTextContent("Chat já assumido por outro atendente");
    expect(onFechar).not.toHaveBeenCalled();
  });

  it("nao envia transferencia sem departamento escolhido", async () => {
    montar();

    expect(
      await screen.findByRole("button", { name: "Transferir" })
    ).toBeDisabled();
    expect(api.patch).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/components/atendimento/transferir-modal.test.tsx`

Expected: FAIL — módulo inexistente.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/atendimento/transferir-modal.tsx`:

```tsx
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DepartamentoSelect } from "@/components/departamentos/departamento-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

interface Props {
  chatId: string;
  aberto: boolean;
  onFechar: () => void;
}

type Aba = "departamento" | "atendente";

export function TransferirModal({ chatId, aberto, onFechar }: Props) {
  const queryClient = useQueryClient();
  const [aba, setAba] = useState<Aba>("departamento");
  const [departamentoId, setDepartamentoId] = useState<string | null>(null);
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const { data: atendentes } = useQuery({
    queryKey: ["atendentes"],
    queryFn: () => api.get<{ id: string; nome: string; perfil: string }[]>("/atendentes/ativos"),
    enabled: aberto,
  });

  const invalidar = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["chats"] }),
      queryClient.invalidateQueries({ queryKey: ["chat", chatId] }),
      queryClient.invalidateQueries({ queryKey: ["roteamento", chatId] }),
    ]);
  };

  const falhar = (erroRecebido: unknown) => {
    setErro(erroRecebido instanceof Error ? erroRecebido.message : "Erro ao transferir");
  };

  const transferirDepartamento = useMutation({
    mutationFn: () =>
      api.patch(`/chats/${chatId}/transferir-departamento`, {
        departamento_id: departamentoId,
        motivo: motivo.trim() || null,
        preservar_atendente_se_compativel: true,
      }),
    onSuccess: async () => {
      setErro(null);
      await invalidar();
      onFechar();
    },
    onError: falhar,
  });

  const atribuirAtendente = useMutation({
    mutationFn: (atendenteId: string) =>
      api.patch(`/chats/${chatId}/atribuir-atendente`, {
        atendente_id: atendenteId,
        motivo: motivo.trim() || null,
      }),
    onSuccess: async () => {
      setErro(null);
      await invalidar();
      onFechar();
    },
    onError: falhar,
  });

  if (!aberto) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-96 rounded-lg bg-white p-6 shadow-xl">
        <h3 className="mb-4 text-lg font-semibold text-neutral-900">
          Transferir chamado
        </h3>

        <div role="tablist" className="mb-4 flex gap-2">
          <button
            role="tab"
            aria-selected={aba === "departamento"}
            onClick={() => setAba("departamento")}
            className={`rounded px-3 py-1 text-sm ${
              aba === "departamento"
                ? "bg-primary-100 text-primary-700"
                : "text-neutral-500"
            }`}
          >
            Departamento
          </button>
          <button
            role="tab"
            aria-selected={aba === "atendente"}
            onClick={() => setAba("atendente")}
            className={`rounded px-3 py-1 text-sm ${
              aba === "atendente"
                ? "bg-primary-100 text-primary-700"
                : "text-neutral-500"
            }`}
          >
            Atendente
          </button>
        </div>

        {erro ? (
          <p role="alert" className="mb-3 text-sm text-status-danger">
            {erro}
          </p>
        ) : null}

        <div className="space-y-3">
          <Input
            placeholder="Motivo (opcional)"
            value={motivo}
            onChange={(evento) => setMotivo(evento.target.value)}
          />

          {aba === "departamento" ? (
            <>
              <DepartamentoSelect
                valor={departamentoId}
                onChange={setDepartamentoId}
                filtro={(departamento) => departamento.recebe_transferencias}
              />
              <Button
                onClick={() => transferirDepartamento.mutate()}
                disabled={!departamentoId || transferirDepartamento.isPending}
              >
                Transferir
              </Button>
            </>
          ) : (
            <div className="max-h-60 space-y-2 overflow-auto">
              {(atendentes ?? []).map((atendente) => (
                <button
                  key={atendente.id}
                  onClick={() => atribuirAtendente.mutate(atendente.id)}
                  disabled={atribuirAtendente.isPending}
                  className="w-full rounded-lg border border-neutral-200 p-3 text-left hover:bg-neutral-50"
                >
                  <p className="text-sm font-medium text-neutral-900">
                    {atendente.nome}
                  </p>
                  <p className="text-xs text-neutral-500">{atendente.perfil}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end">
          <Button variant="outline" onClick={onFechar}>
            Fechar
          </Button>
        </div>
      </div>
    </div>
  );
}
```

Em `frontend/src/app/(app)/atendimento/page.tsx`, remover o bloco `{/* Transfer Modal */}` (linhas 386-456), as mutations `transferirChat`/`transferirGrupo`, o estado `transferTab`/`transferAtendenteId`/`transferSetor` e a lista `setoresDisponiveis`; manter `transferModalOpen` e renderizar:

```tsx
      {chatAtivo ? (
        <TransferirModal
          chatId={chatAtivo}
          aberto={transferModalOpen}
          onFechar={() => setTransferModalOpen(false)}
        />
      ) : null}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/components/atendimento/transferir-modal.test.tsx`

Expected: PASS (4 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/atendimento/transferir-modal.tsx \
  frontend/src/components/atendimento/transferir-modal.test.tsx \
  "frontend/src/app/(app)/atendimento/page.tsx"
git commit -m "feat(atendimento): transferir por departamento e atribuir atendente

- transferencia envia departamento_id (nao mais setor em texto livre)
- atribuicao trata 409 de assuncao concorrente e mantem o modal aberto
- invalida chats, chat e roteamento apos sucesso"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 07 e 10)**

```
| 07-9 | Sem telas de departamento, fila por departamento e transferência por departamento | `frontend/src/app/` | **Alta** | **CORRIGIDO** — `/departamentos` (Task F4.5), fila filtrada (F4.8) e `TransferirModal` por `departamento_id` (F4.10) |
| 10-6 | `/chats/{id}/transferir-departamento` e `/chats/{id}/atribuir-atendente` inexistentes (existe `transferir-grupo` por `setor` livre) | `api/routes/chats.py:110-118` | **Alta** | **CORRIGIDO** — endpoints nas Tasks F2.6/F2.7; painel consome por ID na Task F4.10 |
```

---

### Task F4.11: Confirmar resolução, "não resolveu" e reabertura

**Files:**
- Create: `frontend/src/components/atendimento/acoes-ciclo.tsx`
- Modify: `frontend/src/app/(app)/atendimento/page.tsx` (cabeçalho do chat usa `AcoesCiclo`)
- Test: `frontend/src/components/atendimento/acoes-ciclo.test.tsx`

**Interfaces:**
- Consumes: `PATCH /chats/{id}/confirmar-resolucao` e `PATCH /chats/{id}/reabrir` (F3.5).
- Produces: `AcoesCiclo` — `{ chatId: string; status: string }`; exibe as ações aplicáveis ao status atual.

**Regras:** "Confirmar resolução" aparece em `AGUARDANDO_CLIENTE`; "Não resolveu" aparece em `AGUARDANDO_CLIENTE` e `RESOLVIDO` e envia `motivo` obrigatório no fluxo (campo inline). Erro 403 explica que o chat é de outro atendente; 409 explica que o status mudou. Nenhuma ação muda o estado local antes da resposta.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/atendimento/acoes-ciclo.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const { ApiError } = await vi.importActual<typeof import("@/lib/api")>(
    "@/lib/api"
  );
  return { ApiError, api: { patch: vi.fn() } };
});

import { ApiError, api } from "@/lib/api";
import { AcoesCiclo } from "@/components/atendimento/acoes-ciclo";

function montar(status: string) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <AcoesCiclo chatId="c1" status={status} />
    </QueryClientProvider>
  );
}

describe("AcoesCiclo", () => {
  beforeEach(() => {
    vi.mocked(api.patch).mockResolvedValue({});
  });

  it("confirma a resolucao de chat aguardando cliente", async () => {
    montar("AGUARDANDO_CLIENTE");

    await userEvent.click(
      screen.getByRole("button", { name: "Confirmar resolução" })
    );

    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith("/chats/c1/confirmar-resolucao")
    );
  });

  it("reabre com motivo quando o cliente diz que nao resolveu", async () => {
    montar("AGUARDANDO_CLIENTE");

    await userEvent.click(screen.getByRole("button", { name: "Não resolveu" }));
    await userEvent.type(
      screen.getByLabelText("Motivo da reabertura"),
      "cliente respondeu que o erro continua"
    );
    await userEvent.click(screen.getByRole("button", { name: "Reabrir" }));

    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith("/chats/c1/reabrir", {
        motivo: "cliente respondeu que o erro continua",
      })
    );
  });

  it("nao oferece as acoes em chat novo", () => {
    montar("NOVO");

    expect(
      screen.queryByRole("button", { name: "Confirmar resolução" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Não resolveu" })
    ).not.toBeInTheDocument();
  });

  it("explica conflito 409 sem esconder o erro", async () => {
    vi.mocked(api.patch).mockRejectedValue(
      new ApiError("Só é possível confirmar chats aguardando o cliente", 409)
    );
    montar("AGUARDANDO_CLIENTE");

    await userEvent.click(
      screen.getByRole("button", { name: "Confirmar resolução" })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Só é possível confirmar chats aguardando o cliente"
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/components/atendimento/acoes-ciclo.test.tsx`

Expected: FAIL — módulo inexistente.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/atendimento/acoes-ciclo.tsx`:

```tsx
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

interface Props {
  chatId: string;
  status: string;
}

export function AcoesCiclo({ chatId, status }: Props) {
  const queryClient = useQueryClient();
  const [reabrindo, setReabrindo] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const invalidar = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["chats"] }),
      queryClient.invalidateQueries({ queryKey: ["chat", chatId] }),
      queryClient.invalidateQueries({ queryKey: ["roteamento", chatId] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
    ]);
  };

  const falhar = (erroRecebido: unknown) => {
    setErro(
      erroRecebido instanceof Error ? erroRecebido.message : "Erro na ação"
    );
  };

  const confirmar = useMutation({
    mutationFn: () => api.patch(`/chats/${chatId}/confirmar-resolucao`),
    onSuccess: async () => {
      setErro(null);
      await invalidar();
    },
    onError: falhar,
  });

  const reabrir = useMutation({
    mutationFn: () =>
      api.patch(`/chats/${chatId}/reabrir`, { motivo: motivo.trim() || null }),
    onSuccess: async () => {
      setErro(null);
      setReabrindo(false);
      setMotivo("");
      await invalidar();
    },
    onError: falhar,
  });

  const aguardandoCliente = status === "AGUARDANDO_CLIENTE";
  const podeReabrir = aguardandoCliente || status === "RESOLVIDO";

  if (!aguardandoCliente && !podeReabrir) return null;

  return (
    <div className="space-y-2">
      {erro ? (
        <p role="alert" className="text-sm text-status-danger">
          {erro}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        {aguardandoCliente ? (
          <Button size="sm" onClick={() => confirmar.mutate()} disabled={confirmar.isPending}>
            Confirmar resolução
          </Button>
        ) : null}

        {podeReabrir ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setReabrindo((valor) => !valor)}
          >
            Não resolveu
          </Button>
        ) : null}
      </div>

      {reabrindo ? (
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label
              htmlFor="motivo-reabertura"
              className="text-xs font-medium text-neutral-600"
            >
              Motivo da reabertura
            </label>
            <Input
              id="motivo-reabertura"
              value={motivo}
              onChange={(evento) => setMotivo(evento.target.value)}
            />
          </div>
          <Button
            size="sm"
            onClick={() => reabrir.mutate()}
            disabled={reabrir.isPending}
          >
            Reabrir
          </Button>
        </div>
      ) : null}
    </div>
  );
}
```

Em `frontend/src/app/(app)/atendimento/page.tsx`, logo abaixo do `<h3>` do cabeçalho do chat:

```tsx
              {chatDetail ? (
                <AcoesCiclo chatId={chatDetail.id} status={chatDetail.status} />
              ) : null}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/components/atendimento/acoes-ciclo.test.tsx`

Expected: PASS (4 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/atendimento/acoes-ciclo.tsx \
  frontend/src/components/atendimento/acoes-ciclo.test.tsx \
  "frontend/src/app/(app)/atendimento/page.tsx"
git commit -m "feat(atendimento): confirmar resolucao e reabrir na interface

- botao de confirmar fecha o cenario A (AGUARDANDO_CLIENTE -> RESOLVIDO)
- 'nao resolveu' reabre com motivo e volta para a IA
- 409 e 403 aparecem com a mensagem do backend, sem alterar estado local"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 05 e 01)**

```
| 05-4 | Cenário A não tem caminho de fechamento: vai a `AGUARDANDO_CLIENTE` e ninguém confirma | `services/ai_pipeline.py:27-31` | **Alta** | **CORRIGIDO** — backend em `confirmar_resolucao` (Task F3.5) e botão `AcoesCiclo` (Task F4.11) |
| 01-4 | Cenário A não alcança `RESOLVIDO` pela IA: `resolvido_pela_ia` leva a `AGUARDANDO_CLIENTE` e ninguém confirma | `services/ai_pipeline.py:27-31` | **Alta** | **CORRIGIDO** — confirmação explícita na API e no painel (Tasks F3.5/F4.11) |
```

---

### Task F4.12: Guarda de rota e navegação por perfil

**Files:**
- Create: `frontend/src/lib/permissoes.ts`
- Modify: `frontend/src/app/(app)/layout.tsx` (guarda por rota)
- Modify: `frontend/src/components/layout/sidebar.tsx` (links filtrados)
- Modify: `frontend/src/components/departamentos/departamentos-tabela.tsx` (ações de escrita só para admin)
- Modify: `frontend/src/components/departamentos/departamentos-tabela.test.tsx` (semeia admin)
- Test: `frontend/src/lib/permissoes.test.ts`

**Interfaces:**
- Produces:
  - `Perfil = "admin" | "supervisor" | "atendente"`
  - `ROTAS_APP: { href: string; rotulo: string; perfis: Perfil[] }[]`
  - `podeAcessarRota(perfil: string | null | undefined, rota: string): boolean`
  - `linksVisiveis(perfil): typeof ROTAS_APP`
- Regra de fallback: rota não mapeada exige apenas sessão; rota mapeada sem perfil permitido → `false` (fail-closed).

**Matriz aplicada (spec 04):** `/dashboard`, `/atendimento`, `/kanban`, `/cliente` → todos; `/conhecimento` → admin, supervisor; `/usuarios` → admin, supervisor; `/departamentos` → admin, supervisor (escrita só admin); `/configuracoes` → admin. A guarda é **conveniência de UI**, não segurança: o backend continua autorizando (spec 04, regra 1).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/permissoes.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { linksVisiveis, podeAcessarRota } from "@/lib/permissoes";

describe("guarda de rota por perfil", () => {
  it("admin acessa todas as rotas mapeadas", () => {
    for (const rota of ["/dashboard", "/atendimento", "/usuarios", "/configuracoes", "/departamentos", "/conhecimento"]) {
      expect(podeAcessarRota("admin", rota)).toBe(true);
    }
  });

  it("atendente nao acessa usuarios, configuracoes, conhecimento nem departamentos", () => {
    expect(podeAcessarRota("atendente", "/usuarios")).toBe(false);
    expect(podeAcessarRota("atendente", "/configuracoes")).toBe(false);
    expect(podeAcessarRota("atendente", "/conhecimento")).toBe(false);
    expect(podeAcessarRota("atendente", "/departamentos")).toBe(false);
  });

  it("atendente acessa a operacao", () => {
    for (const rota of ["/dashboard", "/atendimento", "/kanban", "/cliente"]) {
      expect(podeAcessarRota("atendente", rota)).toBe(true);
    }
  });

  it("supervisor acessa gestao mas nao configuracoes", () => {
    expect(podeAcessarRota("supervisor", "/usuarios")).toBe(true);
    expect(podeAcessarRota("supervisor", "/departamentos")).toBe(true);
    expect(podeAcessarRota("supervisor", "/configuracoes")).toBe(false);
  });

  it("sem perfil nao acessa rota mapeada (fail-closed)", () => {
    expect(podeAcessarRota(null, "/usuarios")).toBe(false);
    expect(podeAcessarRota(undefined, "/dashboard")).toBe(false);
  });

  it("rota nao mapeada depende apenas de sessao", () => {
    expect(podeAcessarRota("atendente", "/rota-nova")).toBe(true);
  });

  it("filtra os links da sidebar por perfil", () => {
    const hrefs = linksVisiveis("atendente").map((rota) => rota.href);
    expect(hrefs).toContain("/atendimento");
    expect(hrefs).not.toContain("/usuarios");
    expect(hrefs).not.toContain("/configuracoes");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/lib/permissoes.test.ts`

Expected: FAIL — `@/lib/permissoes` inexistente.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/lib/permissoes.ts`:

```ts
export type Perfil = "admin" | "supervisor" | "atendente";

export interface RotaApp {
  href: string;
  rotulo: string;
  perfis: Perfil[];
}

const TODOS: Perfil[] = ["admin", "supervisor", "atendente"];

export const ROTAS_APP: RotaApp[] = [
  { href: "/dashboard", rotulo: "Dashboard", perfis: TODOS },
  { href: "/atendimento", rotulo: "Atendimento", perfis: TODOS },
  { href: "/kanban", rotulo: "Kanban", perfis: TODOS },
  { href: "/cliente", rotulo: "Clientes", perfis: TODOS },
  { href: "/conhecimento", rotulo: "Conhecimento", perfis: ["admin", "supervisor"] },
  { href: "/departamentos", rotulo: "Departamentos", perfis: ["admin", "supervisor"] },
  { href: "/usuarios", rotulo: "Usuários", perfis: ["admin", "supervisor"] },
  { href: "/configuracoes", rotulo: "Configurações", perfis: ["admin"] },
];

export function podeAcessarRota(
  perfil: string | null | undefined,
  rota: string
): boolean {
  const mapeada = ROTAS_APP.find(
    (candidata) => rota === candidata.href || rota.startsWith(`${candidata.href}/`)
  );
  if (!mapeada) return Boolean(perfil);
  if (!perfil) return false;
  return mapeada.perfis.includes(perfil as Perfil);
}

export function linksVisiveis(
  perfil: string | null | undefined
): RotaApp[] {
  return ROTAS_APP.filter((rota) => podeAcessarRota(perfil, rota.href));
}
```

`frontend/src/app/(app)/layout.tsx` — após os efeitos existentes:

```tsx
  const perfil = useAuthStore((estado) => estado.user?.perfil);
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && token && !podeAcessarRota(perfil, pathname)) {
      router.replace("/atendimento");
    }
  }, [loading, token, perfil, pathname, router]);
```

com imports:

```tsx
import { usePathname } from "next/navigation";
import { podeAcessarRota } from "@/lib/permissoes";
```

`frontend/src/components/layout/sidebar.tsx` — os `links` passam a vir da matriz:

```tsx
  const links = linksVisiveis(user?.perfil).map((rota) => ({
    ...rota,
    label: rota.rotulo,
    icon: ICONES[rota.href] ?? LayoutDashboard,
  }));
```

com:

```tsx
import { linksVisiveis } from "@/lib/permissoes";

const ICONES = {
  "/dashboard": LayoutDashboard,
  "/kanban": Columns3,
  "/atendimento": MessageSquare,
  "/cliente": Users,
  "/usuarios": UserCog,
  "/conhecimento": BookOpen,
  "/configuracoes": Settings,
  "/departamentos": Workflow,
} as const;
```

`frontend/src/components/departamentos/departamentos-tabela.tsx` — ações de escrita apenas para admin:

```tsx
  const perfil = useAuthStore((estado) => estado.user?.perfil);
  const podeEscrever = perfil === "admin";
```

e, no JSX, `{podeEscrever ? <Button ...>Novo departamento</Button> : null}`, `{podeEscrever ? <Button ...>Editar</Button> : null}`, `{podeEscrever && departamento.ativo ? <Button ...>Desativar</Button> : null}`. Quando não puder escrever, mostrar:

```tsx
      {!podeEscrever ? (
        <p className="text-sm text-neutral-500">
          Você tem acesso somente de leitura aos departamentos.
        </p>
      ) : null}
```

Atualize `departamentos-tabela.test.tsx` para semear um admin no `beforeEach`:

```ts
import { useAuthStore } from "@/lib/stores/auth-store";

const ADMIN = {
  id: "adm1",
  nome: "Admin",
  email: "admin@test.com",
  perfil: "admin" as const,
  ativo: true,
  departamento_id: null,
};

// dentro do beforeEach
useAuthStore.setState({ token: "t", user: ADMIN, loading: false });
```

e acrescente um teste:

```ts
  it("supervisor nao ve acoes de escrita", async () => {
    useAuthStore.setState({
      token: "t",
      user: { ...ADMIN, perfil: "supervisor" },
      loading: false,
    });
    montar();

    await screen.findByText("Suporte Técnico");
    expect(
      screen.queryByRole("button", { name: "Novo departamento" })
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Você tem acesso somente de leitura aos departamentos.")
    ).toBeInTheDocument();
  });
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/lib/permissoes.test.ts src/components/departamentos/departamentos-tabela.test.tsx`

Expected: PASS (7 + 5 testes).

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/permissoes.ts frontend/src/lib/permissoes.test.ts \
  "frontend/src/app/(app)/layout.tsx" frontend/src/components/layout/sidebar.tsx \
  frontend/src/components/departamentos/departamentos-tabela.tsx \
  frontend/src/components/departamentos/departamentos-tabela.test.tsx
git commit -m "feat(rbac): guarda de rota e navegacao por perfil

- /usuarios, /departamentos, /conhecimento e /configuracoes bloqueados por perfil
- sidebar monta os links a partir da mesma matriz (sem duplicar regra)
- escrita de departamento restrita a admin; supervisor ve somente leitura"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (specs 07 e 04)**

```
| 07-11 | Sem guarda de rota por perfil | `(app)/layout.tsx` | Média | **CORRIGIDO** — `podeAcessarRota` no layout + sidebar filtrada (`lib/permissoes.ts`) |
| 04-3 | Frontend oculta ações por perfil e não tem guarda de rota; digitando a URL alcança `/usuarios` e `/configuracoes` | `components/layout/sidebar.tsx`; `(app)/layout.tsx` | Média | **CORRIGIDO** — guarda de rota e ações por perfil (Task F4.12); autorização continua no backend |
```

---

### Task F4.13: Select acessível e migração para os tokens de cor

**Files:**
- Create: `frontend/src/components/ui/select-radix.tsx`
- Modify: `frontend/src/test/setup.ts` (shims de pointer capture/scrollIntoView para Radix)
- Modify: `frontend/src/app/(app)/atendimento/page.tsx` (selects de status e prioridade)
- Modify: `frontend/src/app/globals.css` (`@theme`: tokens de estado)
- Modify: `frontend/src/components/ui/badge.tsx` (variantes usam tokens)
- Modify: `frontend/src/**/*.tsx` — `gray-*` → `neutral-*` e cores de estado → tokens semânticos
- Test: `frontend/src/components/ui/select-radix.test.tsx`, `frontend/src/test/tokens.test.ts`

**Interfaces:**
- Produces:
  - `Select` (Radix) — `{ valor: string; onValorChange: (valor: string) => void; placeholder?: string; id?: string; "aria-label"?: string; className?: string; children }` + `SelectItem` (`value`, `children`)
  - Tokens: `--color-status-success`, `--color-status-success-soft`, `--color-status-danger`, `--color-status-danger-soft`, `--color-status-warning`, `--color-status-warning-soft`, `--color-status-info`, `--color-status-info-soft`

**Regras:** `07-6` cita exatamente os selects de status e prioridade do cabeçalho do chat — são esses que migram para o componente acessível (teclado, `aria-label`, foco visível). `DepartamentoSelect` continua no `Select` nativo de propósito: lista longa e seletor nativo do celular; registrar a exceção na linha do gap. `07-4` exige **zero** cor raw de estado ou cinza nos `.tsx`: o teste varre `src/` e falha se sobrar uma.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/ui/select-radix.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Select, SelectItem } from "@/components/ui/select-radix";

function montar(onValorChange = vi.fn()) {
  render(
    <Select valor="media" onValorChange={onValorChange} aria-label="Prioridade">
      <SelectItem value="baixa">Baixa</SelectItem>
      <SelectItem value="media">Média</SelectItem>
      <SelectItem value="urgente">Urgente</SelectItem>
    </Select>
  );
  return onValorChange;
}

describe("Select acessivel", () => {
  it("expoe o valor atual e o rotulo acessivel", () => {
    montar();

    expect(screen.getByRole("combobox", { name: "Prioridade" })).toHaveTextContent(
      "Média"
    );
  });

  it("troca o valor pela lista aberta", async () => {
    const onValorChange = montar();

    await userEvent.click(screen.getByRole("combobox", { name: "Prioridade" }));
    await userEvent.click(screen.getByRole("option", { name: "Urgente" }));

    expect(onValorChange).toHaveBeenCalledWith("urgente");
  });

  it("abre com o teclado", async () => {
    montar();
    const combo = screen.getByRole("combobox", { name: "Prioridade" });

    combo.focus();
    await userEvent.keyboard("{Enter}");

    expect(await screen.findByRole("listbox")).toBeInTheDocument();
  });
});
```

Create `frontend/src/test/tokens.test.ts`:

```ts
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(process.cwd(), "src");
const PROIBIDO =
  /(?:text|bg|border|ring|divide|from|via|to)-(?:gray|green|red|blue|yellow|orange|amber|emerald|rose|indigo|slate|zinc)-\d{2,3}/g;

function arquivosTsx(diretorio: string): string[] {
  return readdirSync(diretorio).flatMap((entrada) => {
    const caminho = join(diretorio, entrada);
    if (statSync(caminho).isDirectory()) return arquivosTsx(caminho);
    if (!caminho.endsWith(".tsx")) return [];
    if (caminho.endsWith("tokens.test.ts")) return [];
    return [caminho];
  });
}

describe("tokens de cor", () => {
  it("nenhum componente usa cor raw do Tailwind", () => {
    const infratores = arquivosTsx(RAIZ).flatMap((arquivo) => {
      const conteudo = readFileSync(arquivo, "utf8");
      const achados = conteudo.match(PROIBIDO) ?? [];
      return achados.map((achado) => `${arquivo}: ${achado}`);
    });

    expect(infratores).toEqual([]);
  });

  it("os tokens de estado existem no tema", () => {
    const css = readFileSync(join(RAIZ, "app/globals.css"), "utf8");

    for (const token of [
      "--color-status-success",
      "--color-status-success-soft",
      "--color-status-danger",
      "--color-status-danger-soft",
      "--color-status-warning",
      "--color-status-warning-soft",
      "--color-status-info",
      "--color-status-info-soft",
    ]) {
      expect(css).toContain(token);
    }
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run test -- src/components/ui/select-radix.test.tsx src/test/tokens.test.ts`

Expected: FAIL — módulo inexistente e ~141 usos de cor raw listados.

- [ ] **Step 3: Write minimal implementation**

`frontend/src/components/ui/select-radix.tsx`:

```tsx
"use client";

import * as RadixSelect from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

interface SelectProps {
  valor: string;
  onValorChange: (valor: string) => void;
  placeholder?: string;
  id?: string;
  className?: string;
  "aria-label"?: string;
  children: React.ReactNode;
}

export function Select({
  valor,
  onValorChange,
  placeholder = "Selecione",
  id,
  className,
  "aria-label": ariaLabel,
  children,
}: SelectProps) {
  return (
    <RadixSelect.Root value={valor} onValueChange={onValorChange}>
      <RadixSelect.Trigger
        id={id}
        aria-label={ariaLabel}
        className={cn(
          "inline-flex h-8 items-center justify-between gap-2 rounded-md border border-neutral-300 bg-white px-2 text-xs text-neutral-700",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
          className
        )}
      >
        <RadixSelect.Value placeholder={placeholder} />
        <RadixSelect.Icon>
          <ChevronDown className="h-3 w-3" aria-hidden="true" />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>

      <RadixSelect.Portal>
        <RadixSelect.Content
          position="popper"
          className="z-50 overflow-hidden rounded-md border border-neutral-200 bg-white shadow-lg"
        >
          <RadixSelect.Viewport className="p-1">
            {children}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}

interface SelectItemProps {
  value: string;
  children: React.ReactNode;
}

export function SelectItem({ value, children }: SelectItemProps) {
  return (
    <RadixSelect.Item
      value={value}
      className="flex cursor-pointer items-center justify-between gap-2 rounded px-2 py-1 text-xs text-neutral-700 outline-none data-[highlighted]:bg-primary-50 data-[highlighted]:text-primary-700"
    >
      <RadixSelect.ItemText>{children}</RadixSelect.ItemText>
      <RadixSelect.ItemIndicator>
        <Check className="h-3 w-3" aria-hidden="true" />
      </RadixSelect.ItemIndicator>
    </RadixSelect.Item>
  );
}
```

`frontend/src/test/setup.ts` — acrescentar os shims que o Radix Select exige no jsdom:

```ts
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => {};
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
```

`frontend/src/app/globals.css` — dentro do bloco `@theme`, após `--color-info`:

```css
  --color-status-success: #16a34a;
  --color-status-success-soft: #dcfce7;
  --color-status-danger: #dc2626;
  --color-status-danger-soft: #fee2e2;
  --color-status-warning: #d97706;
  --color-status-warning-soft: #fef3c7;
  --color-status-info: #2563eb;
  --color-status-info-soft: #dbeafe;
```

`frontend/src/components/ui/badge.tsx` — variantes:

```ts
const variants: Record<BadgeVariant, string> = {
  primary: "bg-primary-100 text-primary-700",
  success: "bg-status-success-soft text-status-success",
  warning: "bg-status-warning-soft text-status-warning",
  danger: "bg-status-danger-soft text-status-danger",
  info: "bg-status-info-soft text-status-info",
  neutral: "bg-neutral-100 text-neutral-700",
};
```

Cabeçalho do chat em `frontend/src/app/(app)/atendimento/page.tsx` — substituir os dois `<select>` por:

```tsx
                <Select
                  aria-label="Status do chat"
                  valor={chatDetail?.status ?? ""}
                  onValorChange={(valor) => updateStatus.mutate(valor)}
                >
                  {STATUS_CHAT.map((status) => (
                    <SelectItem key={status} value={status}>
                      {rotuloStatus(status)}
                    </SelectItem>
                  ))}
                </Select>

                <Select
                  aria-label="Prioridade"
                  valor={chatDetail?.prioridade ?? "media"}
                  onValorChange={(valor) => updatePrioridade.mutate(valor)}
                >
                  {PRIORIDADES.map((prioridade) => (
                    <SelectItem key={prioridade} value={prioridade}>
                      {rotuloPrioridade(prioridade)}
                    </SelectItem>
                  ))}
                </Select>
```

Migração mecânica das cores (revisar o diff antes de commitar):

```bash
cd frontend
grep -rl "gray-" src --include="*.tsx" | xargs sed -i 's/\bgray-/neutral-/g'
```

Mapping das cores semânticas restantes (por uso, não por texto):

| Raw encontrado | Token |
|---|---|
| `text-green-*`, `bg-green-*`, `border-green-*` | `text-status-success`, `bg-status-success-soft`, `border-status-success` |
| `text-red-*`, `bg-red-*`, `border-red-*` | `text-status-danger`, `bg-status-danger-soft`, `border-status-danger` |
| `text-yellow-*`, `bg-yellow-*`, `border-yellow-*` | `text-status-warning`, `bg-status-warning-soft`, `border-status-warning` |
| `text-blue-*`, `bg-blue-*`, `border-blue-*` | `text-status-info`, `bg-status-info-soft`, `border-status-info` |

Arquivos a revisar um a um: `components/ui/badge.tsx`, `components/ui/button.tsx`, `components/ui/error-state.tsx`, `components/layout/header.tsx`, `app/login/page.tsx`, `app/(app)/configuracoes/page.tsx`, `app/(app)/usuarios/page.tsx`, `app/(app)/dashboard/page.tsx`, `app/(app)/atendimento/page.tsx`. O teste de tokens é a rede de segurança: rode-o até a lista ficar vazia.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm run test -- src/components/ui/select-radix.test.tsx src/test/tokens.test.ts`

Expected: PASS (3 + 2 testes); a lista de infratores fica vazia.

- [ ] **Step 5: Run the full suite + build**

Run: `cd frontend && npm run test && npm run build`

Verificação visual obrigatória (build não pega contraste): abrir `/atendimento`, `/dashboard`, `/usuarios`, `/configuracoes` e `/login` e conferir que nenhum texto ficou invisível após a troca de tokens.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ui/select-radix.tsx \
  frontend/src/components/ui/select-radix.test.tsx \
  frontend/src/test/tokens.test.ts frontend/src/test/setup.ts \
  frontend/src/app/globals.css frontend/src/components/ui/badge.tsx \
  frontend/src/app frontend/src/components
git commit -m "feat(design-system): select acessivel e cores por token

- status e prioridade do chat usam Select (Radix) com teclado e rotulo
- tema ganha tokens de estado (sucesso, perigo, aviso, info)
- gray-* vira neutral-* e cores raw de estado viram token
- teste varre src/ e falha se sobrar cor raw do Tailwind"
```

- [ ] **Step 7: Atualizar o Registro de Gaps (spec 07)**

```
| 07-6 | Selects de status/prioridade usam `<select>` nativo | `(app)/atendimento/page.tsx:226,235` | Baixa | **CORRIGIDO** — `Select`/`SelectItem` (Radix) com teclado e `aria-label`; o seletor de departamento segue nativo por decisão de UX (lista longa) |
| 07-4 | Cores raw do Tailwind (`green/red/blue/gray`) fora dos tokens `@theme` | `(app)/atendimento/page.tsx`, `dashboard/page.tsx`, demais telas | Média | **CORRIGIDO** — tokens de estado em `globals.css` e teste `src/test/tokens.test.ts` proíbe cor raw em `src/**/*.tsx` |
```

---

## Gate de saída da Fase 4 — contribui para G4

> Este é o critério de saída **da Fase 4**. O gate **G4** do README ("plataforma declarada pronta") exige ainda **R0 + R1** concluídas; não confunda os dois.

- [ ] `cd frontend && npm run test` verde (harness da F4.1 + todos os testes das tasks).
- [ ] `cd frontend && npm run build` sem erro (o lint continua report-only até R2.3).
- [ ] `cd backend && pytest tests/ -q && ruff check app tests` verde (as tasks F4.3 e F4.7 tocam o backend).
- [ ] Roteiro manual em ambiente de desenvolvimento, com dois usuários (admin e atendente):
  - [ ] criar departamento, editar nome, desativar um sem vínculos e receber 409 em um com regra;
  - [ ] atendente vê apenas chats do próprio departamento e não alcança `/usuarios` digitando a URL;
  - [ ] transferir chat para outro departamento e ver o chat sair da fila antiga;
  - [ ] atribuir atendente já ocupado → mensagem de conflito, modal aberto;
  - [ ] confirmar resolução (cenário A) e reabrir por "não resolveu";
  - [ ] painel de diagnóstico mostra intenção, departamento final, justificativa e artigos do último diagnóstico;
  - [ ] derrubar o backend por 5s: a fila mostra erro com retry e o WebSocket reconecta sozinho.
- [ ] Registros de Gaps atualizados: 07-2, 07-3, 07-4, 07-5, 07-6, 07-9, 07-10, 07-11, 04-3, 03-8, 03-10, 05-4, 01-4, 10-6, 14-6 (parcial).
- [ ] Nenhuma cor raw de estado/neutra em `src/**/*.tsx` (teste de tokens).






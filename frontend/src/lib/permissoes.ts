// Spec 04 (regra 1): a guarda é conveniência de UI, não segurança — o
// backend continua autorizando (gaps 04-1/04-2). A matriz é a fonte única de
// verdade tanto para a guarda de rota (layout) quanto para o menu (sidebar).
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
  { href: "/conhecimento", rotulo: "Base de Conhecimento", perfis: ["admin", "supervisor"] },
  // Spec 04: atendente lê os departamentos e assume chamados na fila
  // (aba "fila" desta página); a escrita continua restrita ao backend.
  { href: "/departamentos", rotulo: "Departamentos", perfis: TODOS },
  { href: "/usuarios", rotulo: "Usuários", perfis: ["admin", "supervisor"] },
  { href: "/configuracoes", rotulo: "Configurações", perfis: ["admin"] },
];

/**
 * Rota mapeada só abre para perfis permitidos; rota não mapeada depende
 * apenas de sessão (perfil conhecido). Perfil ausente em rota mapeada →
 * `false` (fail-closed), para o layout decidir depois que `/auth/me` carregar.
 */
export function podeAcessarRota(
  perfil: string | null | undefined,
  rota: string
): boolean {
  const mapeada = ROTAS_APP.find(
    (candidata) =>
      rota === candidata.href || rota.startsWith(`${candidata.href}/`)
  );
  if (!mapeada) return Boolean(perfil);
  if (!perfil) return false;
  return mapeada.perfis.includes(perfil as Perfil);
}

/** Links da sidebar: mesma matriz da guarda, filtrada pelo perfil. */
export function linksVisiveis(perfil: string | null | undefined): RotaApp[] {
  return ROTAS_APP.filter((rota) => podeAcessarRota(perfil, rota.href));
}

/**
 * Spec 04 (gap 04-3): a ação "transferir chamado" depende de perfil E do
 * vínculo com o chamado. Admin/supervisor transferem qualquer chamado;
 * atendente só transfere o próprio (`chat.atendente_id === user.id`) —
 * não transfere chamado de colega. Sem usuário, fail-closed: `false`.
 */
export function podeTransferirChat(
  user: { id?: string; perfil?: string } | null | undefined,
  chat: { atendente_id?: string | null } | null | undefined
): boolean {
  if (!user) return false;
  if (user.perfil === "admin" || user.perfil === "supervisor") return true;
  return chat?.atendente_id != null && chat.atendente_id === user.id;
}

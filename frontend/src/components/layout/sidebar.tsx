"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Columns3,
  MessageSquare,
  Users,
  BookOpen,
  Settings,
  LogOut,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useSidebarStore } from "@/lib/stores/sidebar-store";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/kanban", label: "Kanban", icon: Columns3 },
  { href: "/atendimento", label: "Atendimento", icon: MessageSquare },
  { href: "/cliente", label: "Clientes", icon: Users },
  { href: "/conhecimento", label: "Base de Conhecimento", icon: BookOpen },
  { href: "/configuracoes", label: "Configurações", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const collapsed = useSidebarStore((s) => s.collapsed);

  return (
    <aside
      className={cn(
        "flex h-screen flex-col bg-primary-900 text-white transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div className={cn("flex items-center", collapsed ? "justify-center p-4" : "gap-2 p-6")}>
        <div className="h-8 w-8 shrink-0 rounded bg-accent-500" />
        {!collapsed && (
          <div className="overflow-hidden">
            <h1 className="text-lg font-bold">EMSoft</h1>
            <p className="text-xs text-primary-300">Support AI</p>
          </div>
        )}
      </div>
      <nav className={cn("flex-1 space-y-1", collapsed ? "px-2" : "px-3")}>
        {links.map(({ href, label, icon: Icon }) => {
          const isActive =
            pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={cn(
                "flex items-center rounded-lg transition-colors",
                collapsed
                  ? "justify-center p-2"
                  : "gap-3 px-3 py-2 text-sm",
                isActive
                  ? "bg-primary-700 text-white"
                  : "text-primary-200 hover:bg-primary-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && label}
            </Link>
          );
        })}
      </nav>
      <div className={cn("border-t border-primary-700", collapsed ? "p-2" : "p-4")}>
        {!collapsed && (
          <div className="mb-2 truncate text-xs text-primary-300">
            {user?.nome} <span className="capitalize">({user?.perfil})</span>
          </div>
        )}
        <button
          onClick={() => { logout(); window.location.href = "/login"; }}
          title={collapsed ? "Sair" : undefined}
          className={cn(
            "flex w-full items-center rounded-lg text-sm text-primary-200 hover:bg-primary-800 hover:text-white transition-colors",
            collapsed ? "justify-center p-2" : "gap-2 px-3 py-2"
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {!collapsed && "Sair"}
        </button>
      </div>
    </aside>
  );
}

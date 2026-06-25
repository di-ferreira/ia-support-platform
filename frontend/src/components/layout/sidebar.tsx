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
  LogOut,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth-store";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/kanban", label: "Kanban", icon: Columns3 },
  { href: "/atendimento", label: "Atendimento", icon: MessageSquare },
  { href: "/cliente", label: "Clientes", icon: Users },
  { href: "/conhecimento", label: "Base de Conhecimento", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <aside className="flex h-screen w-64 flex-col bg-primary-900 text-white">
      <div className="flex items-center gap-2 p-6">
        <div className="h-8 w-8 rounded bg-accent-500" />
        <div>
          <h1 className="text-lg font-bold">EMSoft</h1>
          <p className="text-xs text-primary-300">Support AI</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {links.map(({ href, label, icon: Icon }) => {
          const isActive =
            pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary-700 text-white"
                  : "text-primary-200 hover:bg-primary-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-primary-700 p-4">
        <div className="mb-2 text-xs text-primary-300">
          {user?.nome} <span className="capitalize">({user?.perfil})</span>
        </div>
        <button
          onClick={() => { logout(); window.location.href = "/login"; }}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-primary-200 hover:bg-primary-800 hover:text-white transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sair
        </button>
      </div>
    </aside>
  );
}

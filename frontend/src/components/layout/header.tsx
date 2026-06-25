"use client";

import { useAuthStore } from "@/lib/stores/auth-store";
import { Bell } from "lucide-react";

export function Header() {
  const { user } = useAuthStore();

  return (
    <header className="flex h-16 items-center justify-between border-b bg-white px-6">
      <div />
      <div className="flex items-center gap-4">
        <button className="relative rounded-full p-2 hover:bg-gray-100">
          <Bell className="h-5 w-5 text-gray-600" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-accent-500" />
        </button>
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-primary-100 flex items-center justify-center text-sm font-medium text-primary-700">
            {user?.nome?.charAt(0)?.toUpperCase() || "U"}
          </div>
          <div className="text-sm">
            <p className="font-medium text-gray-900">{user?.nome}</p>
            <p className="text-gray-500 capitalize text-xs">{user?.perfil}</p>
          </div>
        </div>
      </div>
    </header>
  );
}

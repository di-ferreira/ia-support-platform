import { create } from "zustand";

type SidebarState = {
  collapsed: boolean;
  toggle: () => void;
};

export const useSidebarStore = create<SidebarState>((set) => ({
  collapsed: typeof window !== "undefined"
    ? localStorage.getItem("sidebar-collapsed") === "true"
    : false,
  toggle: () =>
    set((state) => {
      const next = !state.collapsed;
      localStorage.setItem("sidebar-collapsed", String(next));
      return { collapsed: next };
    }),
}));

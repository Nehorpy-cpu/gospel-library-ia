"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Bot,
  Clock,
  Compass,
  Heart,
  Home,
  Library,
  Menu,
  Moon,
  NotebookPen,
  ScrollText,
  Search,
  Settings,
  Sun
} from "lucide-react";
import { useTheme } from "next-themes";

import { AudioDock } from "@/components/layout/audio-dock";
import { GlobalSearch } from "@/components/search/global-search";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";

const nav = [
  { href: "/", label: "Inicio", icon: Home },
  { href: "/search", label: "Busqueda", icon: Search },
  { href: "/chat", label: "Chat IA", icon: Bot },
  { href: "/library", label: "Biblioteca", icon: Library },
  { href: "/study", label: "Estudio", icon: NotebookPen },
  { href: "/talk-builder", label: "Discursos", icon: ScrollText },
  { href: "/collections", label: "Colecciones", icon: BookOpen },
  { href: "/favorites", label: "Favoritos", icon: Heart },
  { href: "/history", label: "Historial", icon: Clock },
  { href: "/admin", label: "Admin", icon: Settings }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { sidebarOpen, setSidebarOpen, setSearchOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-background">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 hidden border-r bg-card/95 backdrop-blur lg:block",
          sidebarOpen ? "w-64" : "w-20"
        )}
      >
        <div className="flex h-16 items-center gap-3 border-b px-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Compass className="h-5 w-5" />
          </div>
          {sidebarOpen ? <span className="font-semibold">Gospel Library IA</span> : null}
        </div>
        <nav className="space-y-1 p-3">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex h-10 items-center gap-3 rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  active && "bg-primary/10 text-primary"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {sidebarOpen ? <span>{item.label}</span> : null}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className={cn("min-h-screen transition-[padding]", sidebarOpen ? "lg:pl-64" : "lg:pl-20")}>
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/85 px-4 backdrop-blur">
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Menu">
            <Menu className="h-5 w-5" />
          </Button>
          <button
            onClick={() => setSearchOpen(true)}
            className="flex h-10 flex-1 items-center gap-3 rounded-md border bg-card px-3 text-left text-sm text-muted-foreground"
          >
            <Search className="h-4 w-4" />
            Buscar discursos, escrituras, autores o preguntar a IA
          </button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Tema"
          >
            <Sun className="h-4 w-4 dark:hidden" />
            <Moon className="hidden h-4 w-4 dark:block" />
          </Button>
        </header>
        <main className="mx-auto w-full max-w-[1680px] px-4 py-5 md:px-6 lg:px-8">{children}</main>
      </div>

      <GlobalSearch />
      <AudioDock />
    </div>
  );
}

"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookOpen,
  Bot,
  Clock,
  Compass,
  Heart,
  Home,
  Library,
  LogIn,
  LogOut,
  Menu,
  Moon,
  NotebookPen,
  ScrollText,
  Search,
  Settings,
  Sun,
  UserRoundCog
} from "lucide-react";
import { useTheme } from "next-themes";

import { AudioDock } from "@/components/layout/audio-dock";
import { FeedbackButton } from "@/components/beta/feedback-button";
import { GlobalSearch } from "@/components/search/global-search";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useLibraryStore } from "@/stores/library-store";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";
import { useUIStore } from "@/stores/ui-store";

const nav = [
  { href: "/", label: "Inicio", icon: Home },
  { href: "/beta", label: "Beta", icon: Compass },
  { href: "/search", label: "Busqueda", icon: Search },
  { href: "/chat", label: "Chat IA", icon: Bot },
  { href: "/library", label: "Biblioteca", icon: Library },
  { href: "/study", label: "Estudio", icon: NotebookPen },
  { href: "/talk-builder", label: "Discursos", icon: ScrollText },
  { href: "/collections", label: "Colecciones", icon: BookOpen },
  { href: "/favorites", label: "Favoritos", icon: Heart },
  { href: "/history", label: "Historial", icon: Clock },
  { href: "/preferences", label: "Preferencias", icon: UserRoundCog },
  { href: "/admin", label: "Admin", icon: Settings }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const { sidebarOpen, setSidebarOpen, setSearchOpen } = useUIStore();
  const { user, hydrated, signOut } = useAuthStore();
  const setStudyUserId = useStudyWorkspaceStore((state) => state.setUserId);
  const setLibraryUserId = useLibraryStore((state) => state.setUserId);
  const visibleNav = nav.filter((item) => item.href !== "/admin" || user?.role === "admin");

  useEffect(() => {
    if (user?.id) {
      setStudyUserId(user.id);
      setLibraryUserId(user.id);
    }
  }, [setLibraryUserId, setStudyUserId, user?.id]);

  function handleSignOut() {
    signOut();
    router.push("/");
    router.refresh();
  }

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
          {visibleNav.map((item) => {
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
          {!hydrated ? (
            <div className="hidden h-9 w-24 rounded-md bg-muted md:block" aria-label="Validando sesion" />
          ) : user ? (
            <div className="hidden items-center gap-2 md:flex">
              <div className="max-w-44 truncate text-right">
                <p className="truncate text-sm font-medium">{user.name}</p>
                <p className="truncate text-xs text-muted-foreground">{user.role === "admin" ? "Admin" : user.email}</p>
              </div>
              <Button variant="ghost" size="icon" onClick={handleSignOut} aria-label="Cerrar sesion">
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button variant="outline" size="sm" className="hidden md:inline-flex" onClick={() => router.push("/sign-in")}>
              <LogIn className="mr-2 h-4 w-4" />
              Entrar
            </Button>
          )}
        </header>
        <main className="mx-auto w-full max-w-[1680px] px-4 py-5 md:px-6 lg:px-8">{children}</main>
      </div>

      <GlobalSearch />
      <AudioDock />
      <FeedbackButton />
    </div>
  );
}

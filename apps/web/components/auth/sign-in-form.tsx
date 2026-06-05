"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LogIn, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuthStore, type AuthRole } from "@/stores/auth-store";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";

const DEFAULT_USER_ID = process.env.NEXT_PUBLIC_STUDY_USER_ID ?? "00000000-0000-4000-8000-000000000001";
const DEFAULT_ADMIN_ID = "00000000-0000-4000-8000-0000000000ad";

function displayNameFromEmail(email: string) {
  const name = email.split("@")[0]?.replace(/[._-]+/g, " ").trim();
  return name ? name.replace(/\b\w/g, (letter) => letter.toUpperCase()) : "Usuario";
}

export function SignInForm({ mode = "sign-in" }: { mode?: "sign-in" | "sign-up" }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { signIn } = useAuthStore();
  const setStudyUserId = useStudyWorkspaceStore((state) => state.setUserId);
  const [email, setEmail] = useState("demo@gospel-library.local");
  const [name, setName] = useState("Usuario demo");
  const next = searchParams.get("next") || "/study";

  function finishSignIn(role: AuthRole) {
    const cleanEmail = email.trim().toLowerCase();
    const user = {
      id: role === "admin" ? DEFAULT_ADMIN_ID : DEFAULT_USER_ID,
      name: name.trim() || displayNameFromEmail(cleanEmail),
      email: cleanEmail || "demo@gospel-library.local",
      role
    };
    signIn(user);
    setStudyUserId(user.id);
    router.push(role === "admin" && next === "/study" ? "/admin" : next);
    router.refresh();
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center">
      <div className="space-y-6 rounded-lg border bg-card p-6 shadow-sm">
        <div>
          <p className="text-sm text-muted-foreground">Gospel Library IA</p>
          <h1 className="mt-2 text-2xl font-semibold">
            {mode === "sign-up" ? "Crear cuenta local" : "Iniciar sesion"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            En produccion usa Clerk. En local esta sesion crea headers seguros para probar privacidad y roles.
          </p>
        </div>
        <label className="block space-y-2 text-sm">
          <span>Nombre</span>
          <input
            className="h-10 w-full rounded-md border bg-background px-3"
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoComplete="name"
          />
        </label>
        <label className="block space-y-2 text-sm">
          <span>Email</span>
          <input
            className="h-10 w-full rounded-md border bg-background px-3"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
          />
        </label>
        <div className="grid gap-3">
          <Button onClick={() => finishSignIn("user")}>
            <LogIn className="mr-2 h-4 w-4" />
            Entrar como usuario
          </Button>
          <Button variant="outline" onClick={() => finishSignIn("admin")}>
            <ShieldCheck className="mr-2 h-4 w-4" />
            Entrar como admin local
          </Button>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ragApi } from "@/lib/api";
import { canonicalSourceOptions } from "@/lib/source-filters";

const profiles = [
  "miembro",
  "maestro de Escuela Dominical",
  "maestro de Instituto/Seminario",
  "lider de jovenes",
  "obispo",
  "presidente de estaca",
  "Setenta de Area",
  "misionero",
  "investigador doctrinal"
];

const languages = [
  { value: "es", label: "Espanol" },
  { value: "en", label: "English" },
  { value: "pt", label: "Portugues" }
];

export function OnboardingForm() {
  const router = useRouter();
  const [callingProfile, setCallingProfile] = useState(profiles[0]);
  const [language, setLanguage] = useState("es");
  const [preferredSources, setPreferredSources] = useState<string[]>(["general_conference", "scriptures"]);
  const [message, setMessage] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => ragApi.completeOnboarding({ callingProfile, language, preferredSources }),
    onSuccess: (data) => {
      if (data.status === "pending") {
        setMessage("Tu solicitud beta queda en espera de aprobacion.");
        return;
      }
      router.push("/study");
      router.refresh();
    },
    onError: (error) => setMessage(error instanceof Error ? error.message : "No se pudo completar onboarding.")
  });

  function toggleSource(source: string) {
    setPreferredSources((current) =>
      current.includes(source) ? current.filter((item) => item !== source) : [...current, source]
    );
  }

  return (
    <div className="mx-auto grid max-w-4xl gap-5">
      <section className="rounded-lg border bg-card p-5">
        <h1 className="text-2xl font-semibold">Onboarding beta</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Configura tu perfil inicial. Esto ayuda a adaptar ejemplos, fuentes y enfoque sin cambiar doctrina ni prioridad de fuentes oficiales.
        </p>
      </section>

      <Card className="grid gap-5 p-5">
        <label className="grid gap-2 text-sm">
          Perfil de estudio o llamamiento
          <select
            className="h-10 rounded-md border bg-background px-3 text-sm"
            value={callingProfile}
            onChange={(event) => setCallingProfile(event.target.value)}
          >
            {profiles.map((profile) => (
              <option key={profile} value={profile}>
                {profile}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-2 text-sm">
          Idioma preferido
          <select
            className="h-10 rounded-md border bg-background px-3 text-sm"
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          >
            {languages.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <div>
          <h2 className="text-sm font-medium">Fuentes preferidas</h2>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {canonicalSourceOptions.map((source) => (
              <label key={source.key} className="flex items-center gap-2 rounded-md border p-3 text-sm">
                <input
                  type="checkbox"
                  checked={preferredSources.includes(source.key)}
                  onChange={() => toggleSource(source.key)}
                />
                {source.label}
              </label>
            ))}
          </div>
        </div>

        <div className="rounded-md border bg-muted/40 p-4 text-sm text-muted-foreground">
          <p className="flex gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            Las fuentes oficiales de la Iglesia tienen prioridad. La IA no se presenta como revelacion ni reemplaza la verificacion personal.
          </p>
        </div>

        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
        <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
          Entrar a la beta
        </Button>
      </Card>
    </div>
  );
}

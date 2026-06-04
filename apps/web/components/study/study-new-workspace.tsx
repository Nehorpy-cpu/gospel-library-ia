"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { studyApi } from "@/lib/api";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";

const referenceTypes = [
  { value: "topic", label: "Tema" },
  { value: "scripture", label: "Escritura" },
  { value: "talk", label: "Discurso" },
  { value: "manual", label: "Manual" }
];

export function StudyNewWorkspace() {
  const router = useRouter();
  const userId = useStudyWorkspaceStore((state) => state.userId);
  const setActiveWorkspaceId = useStudyWorkspaceStore((state) => state.setActiveWorkspaceId);
  const [form, setForm] = useState({
    title: "",
    mainReference: "",
    referenceType: "topic",
    language: "es"
  });

  const createWorkspace = useMutation({
    mutationFn: () =>
      studyApi.createWorkspace(userId, {
        name: form.title.trim(),
        description: form.mainReference.trim() || undefined,
        sourceFilters: {
          language: form.language,
          mainReference: form.mainReference.trim(),
          referenceType: form.referenceType
        },
        settings: {
          title: form.title.trim(),
          mainReference: form.mainReference.trim(),
          referenceType: form.referenceType,
          language: form.language
        }
      }),
    onSuccess: (workspace) => {
      setActiveWorkspaceId(workspace.id);
      router.push(`/study/${workspace.id}`);
    }
  });

  const canCreate = form.title.trim().length > 0;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link href="/study" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        Volver a StudyWorkspace
      </Link>
      <Card className="p-6">
        <div>
          <p className="text-sm font-medium text-primary">Nuevo espacio</p>
          <h1 className="mt-1 text-2xl font-semibold">Crear StudyWorkspace</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Define una referencia principal para sugerir documentos reales y mantener notas, citas y filtros juntos.
          </p>
        </div>
        <div className="mt-6 grid gap-4">
          <label className="grid gap-2 text-sm">
            Titulo
            <Input
              value={form.title}
              onChange={(event) => setForm((value) => ({ ...value, title: event.target.value }))}
              placeholder="Expiacion de Jesucristo"
            />
          </label>
          <label className="grid gap-2 text-sm">
            Referencia principal
            <Input
              value={form.mainReference}
              onChange={(event) => setForm((value) => ({ ...value, mainReference: event.target.value }))}
              placeholder="2 Nefi 2, convenio, discipulado..."
            />
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-sm">
              Tipo de referencia
              <select
                value={form.referenceType}
                onChange={(event) => setForm((value) => ({ ...value, referenceType: event.target.value }))}
                className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              >
                {referenceTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm">
              Idioma
              <select
                value={form.language}
                onChange={(event) => setForm((value) => ({ ...value, language: event.target.value }))}
                className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="es">Espanol</option>
                <option value="en">English</option>
              </select>
            </label>
          </div>
          <Button disabled={!canCreate || createWorkspace.isPending} onClick={() => createWorkspace.mutate()}>
            <Save className="h-4 w-4" />
            Crear workspace
          </Button>
          {createWorkspace.error ? (
            <p className="text-sm text-destructive">
              {createWorkspace.error instanceof Error ? createWorkspace.error.message : "No se pudo crear el workspace."}
            </p>
          ) : null}
        </div>
      </Card>
    </div>
  );
}

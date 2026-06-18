"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Save } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { studyApi } from "@/lib/api";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";

export function StudyNewWorkspace() {
  const router = useRouter();
  const userId = useStudyWorkspaceStore((state) => state.userId);
  const [form, setForm] = useState({
    title: "",
    scriptureReference: "",
    personalThought: "",
    topic: "",
    callingContext: ""
  });

  const createWorkspace = useMutation({
    mutationFn: () =>
      studyApi.createWorkspace(userId, {
        name: form.title.trim(),
        title: form.title.trim(),
        description: form.scriptureReference.trim() || undefined,
        scriptureReference: form.scriptureReference.trim() || undefined,
        personalThought: form.personalThought.trim() || undefined,
        topic: form.topic.trim() || undefined,
        callingContext: form.callingContext.trim() || undefined
      }),
    onSuccess: (workspace) => router.push(`/study/${workspace.id}`)
  });

  const canCreate = form.title.trim().length > 0;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <Link href="/study" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />
        Volver a Mis Estudios
      </Link>
      <Card className="p-6">
        <p className="text-sm font-medium text-primary">Mesa de Estudio Doctrinal</p>
        <h1 className="mt-1 text-2xl font-semibold">Crear estudio personal</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Empieza con una escritura, una impresion personal y un tema. La IA podra sugerir bloques editables despues.
        </p>

        <div className="mt-6 grid gap-4">
          <label className="grid gap-2 text-sm">
            Titulo del estudio
            <Input
              value={form.title}
              onChange={(event) => setForm((value) => ({ ...value, title: event.target.value }))}
              placeholder="Los nombres en Helaman 5:6"
            />
          </label>
          <label className="grid gap-2 text-sm">
            Escritura base
            <Input
              value={form.scriptureReference}
              onChange={(event) => setForm((value) => ({ ...value, scriptureReference: event.target.value }))}
              placeholder="Helaman 5:6"
            />
          </label>
          <label className="grid gap-2 text-sm">
            Mi pensamiento
            <textarea
              value={form.personalThought}
              onChange={(event) => setForm((value) => ({ ...value, personalThought: event.target.value }))}
              placeholder="Me impresiona que Helaman haya puesto esos nombres a sus hijos..."
              className="min-h-32 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-sm">
              Tema
              <Input
                value={form.topic}
                onChange={(event) => setForm((value) => ({ ...value, topic: event.target.value }))}
                placeholder="Convenios, memoria, identidad"
              />
            </label>
            <label className="grid gap-2 text-sm">
              Llamamiento o contexto
              <Input
                value={form.callingContext}
                onChange={(event) => setForm((value) => ({ ...value, callingContext: event.target.value }))}
                placeholder="Clase de jovenes, familia, ministerio..."
              />
            </label>
          </div>
          <Button disabled={!canCreate || createWorkspace.isPending} onClick={() => createWorkspace.mutate()}>
            <Save className="h-4 w-4" />
            Crear estudio
          </Button>
          {createWorkspace.error ? (
            <p className="text-sm text-destructive">
              {createWorkspace.error instanceof Error ? createWorkspace.error.message : "No se pudo crear el estudio."}
            </p>
          ) : null}
        </div>
      </Card>
    </div>
  );
}

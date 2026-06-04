"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Save, UserRoundCog } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { callingCatalog, categoryById, isOtherCalling, resolvedCallingName } from "@/lib/church-callings";
import { profileApi } from "@/lib/api";
import { useStudyWorkspaceStore } from "@/stores/study-workspace-store";
import { useUserPreferencesStore } from "@/stores/user-preferences-store";

export function CallingPreferences() {
  const { userId } = useStudyWorkspaceStore();
  const preferences = useUserPreferencesStore();
  const { setCallingFocus } = preferences;
  const [saved, setSaved] = useState(false);

  const { data } = useQuery({
    queryKey: ["profile-preferences", userId],
    queryFn: () => profileApi.preferences(userId),
    retry: false
  });

  useEffect(() => {
    if (data) {
      setCallingFocus({
        callingCategory: data.callingCategory ?? undefined,
        callingName: data.callingName ?? undefined,
        customCallingName: data.customCallingName ?? undefined,
        callingFocusEnabled: data.callingFocusEnabled
      });
    }
  }, [data, setCallingFocus]);

  const selectedCategory = useMemo(
    () => categoryById(preferences.callingCategory) ?? callingCatalog[0],
    [preferences.callingCategory]
  );
  const activeCalling = resolvedCallingName(preferences);

  const mutation = useMutation({
    mutationFn: () =>
      profileApi.updatePreferences(userId, {
        callingCategory: preferences.callingCategory,
        callingName: preferences.callingName,
        customCallingName: preferences.customCallingName,
        callingFocusEnabled: preferences.callingFocusEnabled
      }),
    onSuccess: () => {
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2200);
    }
  });

  return (
    <div className="mx-auto grid max-w-5xl gap-5">
      <section className="rounded-lg border bg-card p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
            <UserRoundCog className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">Preferencias de estudio</h1>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              Tu llamamiento nos ayuda a adaptar el analisis de las Escrituras a tu manera de servir.
              No cambia la doctrina; solo enfoca la aplicacion personal y de liderazgo segun tu responsabilidad actual.
            </p>
          </div>
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Enfoque por llamamiento</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5">
          <label className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border"
              checked={preferences.callingFocusEnabled}
              onChange={(event) => setCallingFocus({ callingFocusEnabled: event.target.checked })}
            />
            Usar mi llamamiento para enfocar la aplicacion doctrinal
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-sm">
              Categoria
              <select
                className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
                value={preferences.callingCategory ?? selectedCategory.id}
                onChange={(event) => {
                  const category = categoryById(event.target.value) ?? callingCatalog[0];
                  setCallingFocus({
                    callingCategory: category.id,
                    callingName: category.callings[0],
                    customCallingName: undefined
                  });
                }}
              >
                {callingCatalog.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-2 text-sm">
              Llamamiento
              <select
                className="h-10 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
                value={preferences.callingName ?? selectedCategory.callings[0]}
                onChange={(event) => setCallingFocus({ callingName: event.target.value })}
              >
                {selectedCategory.callings.map((calling) => (
                  <option key={calling} value={calling}>
                    {calling}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {isOtherCalling(preferences.callingName) ? (
            <label className="grid gap-2 text-sm">
              Escribir llamamiento
              <Input
                value={preferences.customCallingName ?? ""}
                onChange={(event) => setCallingFocus({ customCallingName: event.target.value })}
                placeholder="Ej. Especialista de autosuficiencia de distrito"
              />
            </label>
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
              <Save className="h-4 w-4" />
              Guardar preferencias
            </Button>
            <span className="text-sm text-muted-foreground">
              {saved
                ? "Preferencias guardadas."
                : activeCalling
                  ? `Enfoque activo: ${activeCalling}`
                  : "Sin llamamiento seleccionado; se usara discipulado general."}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function AppError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("frontend_error", { message: error.message, digest: error.digest });
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-xl items-center">
      <Card className="p-6">
        <AlertTriangle className="h-6 w-6 text-amber-600" />
        <h1 className="mt-4 text-xl font-semibold">Algo fallo en la beta</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          El error fue registrado sin datos sensibles. Puedes intentar de nuevo o enviar feedback con la pagina y pasos para reproducirlo.
        </p>
        <Button className="mt-4" onClick={reset}>
          <RefreshCw className="h-4 w-4" />
          Intentar de nuevo
        </Button>
      </Card>
    </div>
  );
}

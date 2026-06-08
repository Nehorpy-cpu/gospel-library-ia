"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ragApi } from "@/lib/api";

export function BetaAccessForm() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => ragApi.requestBetaAccess({ email, name: name || undefined, message: message || undefined }),
    onSuccess: () => {
      setStatus("Solicitud recibida. Un admin debe aprobar el acceso si la allowlist esta activa.");
      setMessage("");
    },
    onError: (error) => setStatus(error instanceof Error ? error.message : "No se pudo registrar la solicitud.")
  });

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 md:grid-cols-2">
        <Input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="email@dominio.com" type="email" />
        <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Nombre" />
      </div>
      <textarea
        className="min-h-24 resize-none rounded-md border bg-background p-2 text-sm"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder="Cuentanos brevemente por que quieres probar la beta."
      />
      {status ? <p className="text-sm text-muted-foreground">{status}</p> : null}
      <Button disabled={!email.includes("@") || mutation.isPending} onClick={() => mutation.mutate()}>
        <Send className="h-4 w-4" />
        Solicitar acceso
      </Button>
    </div>
  );
}

"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { MessageSquare, Send, X } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ragApi } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

const feedbackTypes = [
  { value: "bug", label: "Error" },
  { value: "suggestion", label: "Sugerencia" },
  { value: "doctrinal_source_issue", label: "Fuente doctrinal" },
  { value: "ui_issue", label: "Interfaz" },
  { value: "other", label: "Otro" }
];

export function FeedbackButton() {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const [open, setOpen] = useState(false);
  const [type, setType] = useState("suggestion");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () => ragApi.submitFeedback({ page: pathname, type, message }),
    onSuccess: () => {
      setMessage("");
      setStatus("Gracias. Feedback recibido para la beta.");
      window.setTimeout(() => setOpen(false), 900);
    },
    onError: (error) => setStatus(error instanceof Error ? error.message : "No se pudo enviar feedback.")
  });

  if (!user) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {open ? (
        <Card className="w-[min(92vw,360px)] p-4 shadow-lg">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Enviar feedback</h2>
              <p className="text-xs text-muted-foreground">No incluyas informacion privada o sensible.</p>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Cerrar feedback">
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="mt-3 grid gap-3">
            <select
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={type}
              onChange={(event) => setType(event.target.value)}
            >
              {feedbackTypes.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <textarea
              className="min-h-28 resize-none rounded-md border bg-background p-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              value={message}
              maxLength={4000}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Cuentanos que paso, que falto o que fuente deberiamos revisar."
            />
            {status ? <p className="text-xs text-muted-foreground">{status}</p> : null}
            <Button disabled={message.trim().length < 5 || mutation.isPending} onClick={() => mutation.mutate()}>
              <Send className="h-4 w-4" />
              Enviar feedback
            </Button>
          </div>
        </Card>
      ) : (
        <Button onClick={() => setOpen(true)} className="shadow-lg">
          <MessageSquare className="h-4 w-4" />
          Feedback
        </Button>
      )}
    </div>
  );
}

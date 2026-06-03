"use client";

import { Download, Highlighter, MessageSquare, ZoomIn, ZoomOut } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

export function PdfReader({ title }: { title: string }) {
  const [zoom, setZoom] = useState(100);

  return (
    <div className="overflow-hidden rounded-lg border bg-card">
      <div className="flex items-center justify-between border-b p-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold">{title}</h2>
          <p className="text-xs text-muted-foreground">PDF/text reader · notas · subrayados</p>
        </div>
        <div className="flex gap-1">
          <Button variant="ghost" size="icon" onClick={() => setZoom(Math.max(70, zoom - 10))} aria-label="Alejar">
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => setZoom(Math.min(160, zoom + 10))} aria-label="Acercar">
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Subrayar">
            <Highlighter className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Comentar">
            <MessageSquare className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Descargar">
            <Download className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="h-[calc(100vh-190px)] overflow-auto bg-muted p-4">
        <article
          style={{ maxWidth: `${Math.round(760 * (zoom / 100))}px` }}
          className="mx-auto min-h-full rounded-md bg-background p-8 shadow-soft"
        >
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">Fuente doctrinal indexada por Gospel Library IA</p>
          <div className="mt-8 space-y-5 leading-8">
            <p>
              Este lector esta preparado para PDFs, discursos, escrituras y transcripciones. En produccion puede
              recibir paginas renderizadas, texto OCR, notas por rango y referencias cruzadas.
            </p>
            <p>
              La experiencia prioriza lectura profunda: panel de citas, chat contextual, subrayados, exportacion y
              reproduccion sincronizada de audio cuando existe una transcripcion.
            </p>
            <p>
              Selecciona una seccion, crea una nota o pregunta a la IA sobre este documento para generar un resumen
              fundamentado con citas.
            </p>
          </div>
        </article>
      </div>
    </div>
  );
}

import type { Metadata } from "next";

import { Card } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Privacidad"
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto grid max-w-4xl gap-5">
      <section className="rounded-lg border bg-card p-5">
        <h1 className="text-2xl font-semibold">Privacidad beta</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Gospel Library IA Beta esta preparada para una beta privada con usuarios reales y datos personales acotados.
        </p>
      </section>
      <Card className="grid gap-4 p-5 text-sm text-muted-foreground">
        <section>
          <h2 className="font-semibold text-foreground">Notas personales privadas</h2>
          <p className="mt-1">
            Tus espacios de estudio, notas, citas guardadas y post-it se asocian a tu usuario y no deben compartirse con otros usuarios.
          </p>
        </section>
        <section>
          <h2 className="font-semibold text-foreground">Uso de IA</h2>
          <p className="mt-1">
            Las consultas IA pueden usar fuentes recuperadas, historial conversacional limitado y configuracion de estudio. No incluyas datos
            sensibles en prompts, notas o feedback.
          </p>
        </section>
        <section>
          <h2 className="font-semibold text-foreground">Fuentes consultadas</h2>
          <p className="mt-1">
            La app prioriza fuentes oficiales y muestra atribuciones cuando existen. El usuario debe verificar toda cita importante en su fuente.
          </p>
        </section>
        <section>
          <h2 className="font-semibold text-foreground">Errores y feedback</h2>
          <p className="mt-1">
            Los reportes capturan pagina, tipo y mensaje del usuario. No se capturan capturas de pantalla automaticamente ni claves secretas.
          </p>
        </section>
      </Card>
    </div>
  );
}

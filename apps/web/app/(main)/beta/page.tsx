import Link from "next/link";
import type { Metadata } from "next";
import { AlertTriangle, BookOpenCheck, CheckCircle2, LockKeyhole, MessageSquare } from "lucide-react";

import { Card } from "@/components/ui/card";
import { BetaAccessForm } from "@/components/beta/beta-access-form";

export const metadata: Metadata = {
  title: "Gospel Library IA Beta"
};

const benefits = [
  "Buscar discursos, escrituras y notas con filtros por fuente.",
  "Estudiar con espacios personales, citas guardadas y post-it.",
  "Usar chat y constructor de discursos con fuentes verificables.",
  "Trabajar en modo textual cuando los embeddings IA no esten disponibles."
];

const limitations = [
  "La beta privada no es un producto publico ni oficial de la Iglesia.",
  "Las respuestas IA deben verificarse siempre con las fuentes citadas.",
  "El acceso puede limitarse por allowlist, cuota diaria y revision manual.",
  "La busqueda semantica depende de disponibilidad de embeddings y credito OpenAI."
];

export default function BetaPage() {
  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <section className="grid gap-5 rounded-lg border bg-card p-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div>
          <div className="inline-flex items-center gap-2 rounded-md border px-3 py-1 text-xs text-muted-foreground">
            <BookOpenCheck className="h-3.5 w-3.5" />
            Gospel Library IA Beta 0.1.0-beta
          </div>
          <h1 className="mt-4 text-3xl font-semibold md:text-4xl">Beta privada para estudio doctrinal asistido por IA</h1>
          <p className="mt-3 max-w-3xl text-muted-foreground">
            Esta beta ayuda a probar busqueda, estudio personal, citas, fuentes y flujos de preparacion doctrinal con usuarios reales,
            manteniendo limites de uso, privacidad y prioridad absoluta para fuentes oficiales.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" href="/sign-in?next=/onboarding">
              Iniciar sesion
            </Link>
            <Link className="inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium" href="/beta#request-access">
              Solicitar acceso
            </Link>
          </div>
        </div>
        <Card className="p-4">
          <h2 className="font-semibold">Aviso de prueba</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            La app no reemplaza el estudio personal, la revelacion, los lideres autorizados ni las fuentes oficiales de La Iglesia de
            Jesucristo de los Santos de los Ultimos Dias.
          </p>
          <div className="mt-4 grid gap-2 text-sm">
            <span className="flex items-center gap-2"><LockKeyhole className="h-4 w-4 text-primary" /> Acceso controlado</span>
            <span className="flex items-center gap-2"><MessageSquare className="h-4 w-4 text-primary" /> Feedback activo</span>
            <span className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-primary" /> Limites de uso IA</span>
          </div>
        </Card>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-semibold">Beneficios de la beta</h2>
          <div className="mt-3 grid gap-2">
            {benefits.map((item) => (
              <p key={item} className="flex gap-2 text-sm text-muted-foreground">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                {item}
              </p>
            ))}
          </div>
        </Card>
        <Card className="p-5">
          <h2 className="font-semibold">Limitaciones conocidas</h2>
          <div className="mt-3 grid gap-2">
            {limitations.map((item) => (
              <p key={item} className="flex gap-2 text-sm text-muted-foreground">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                {item}
              </p>
            ))}
          </div>
        </Card>
      </div>

      <Card id="request-access" className="p-5">
        <h2 className="font-semibold">Solicitar acceso</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          En la beta local, inicia sesion y completa el onboarding. En produccion, activa `BETA_ALLOWLIST_ENABLED=true` y aprueba emails desde Admin.
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.7fr]">
          <BetaAccessForm />
          <div className="flex flex-col gap-3">
            <Link className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" href="/sign-in?next=/onboarding">
              Completar onboarding
            </Link>
            <Link className="inline-flex h-10 items-center justify-center rounded-md border px-4 text-sm font-medium" href="/privacy">
              Privacidad
            </Link>
            <Link className="inline-flex h-10 items-center justify-center rounded-md border px-4 text-sm font-medium" href="/terms">
              Terminos
            </Link>
          </div>
        </div>
      </Card>
    </div>
  );
}

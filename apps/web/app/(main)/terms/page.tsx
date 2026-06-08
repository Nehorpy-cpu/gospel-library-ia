import type { Metadata } from "next";

import { Card } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Terminos"
};

export default function TermsPage() {
  return (
    <div className="mx-auto grid max-w-4xl gap-5">
      <section className="rounded-lg border bg-card p-5">
        <h1 className="text-2xl font-semibold">Terminos de la beta</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Esta version es una beta privada de prueba. No es un producto oficial de La Iglesia de Jesucristo de los Santos de los Ultimos Dias.
        </p>
      </section>
      <Card className="grid gap-4 p-5 text-sm text-muted-foreground">
        <section>
          <h2 className="font-semibold text-foreground">Prioridad doctrinal</h2>
          <p className="mt-1">
            Las fuentes oficiales de la Iglesia tienen prioridad sobre respuestas IA, comentarios academicos, resumenes o reflexiones personales.
          </p>
        </section>
        <section>
          <h2 className="font-semibold text-foreground">Limitaciones de IA</h2>
          <p className="mt-1">
            La IA puede equivocarse. No presentes sus respuestas como revelacion, doctrina nueva ni declaracion oficial. Verifica las fuentes citadas.
          </p>
        </section>
        <section>
          <h2 className="font-semibold text-foreground">Uso controlado</h2>
          <p className="mt-1">
            La beta puede limitar busquedas IA, discursos, exportaciones y espacios de estudio por usuario. El acceso puede depender de allowlist.
          </p>
        </section>
        <section>
          <h2 className="font-semibold text-foreground">Estudio personal</h2>
          <p className="mt-1">
            Gospel Library IA no reemplaza el estudio personal, la oracion, las escrituras, los lideres autorizados ni los materiales oficiales.
          </p>
        </section>
      </Card>
    </div>
  );
}

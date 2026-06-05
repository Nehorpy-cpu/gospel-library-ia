import Link from "next/link";
import { ShieldAlert } from "lucide-react";

export default function AccessDeniedPage() {
  return (
    <div className="mx-auto flex min-h-[65vh] max-w-lg flex-col items-center justify-center text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-md bg-destructive/10 text-destructive">
        <ShieldAlert className="h-6 w-6" />
      </div>
      <h1 className="mt-5 text-2xl font-semibold">Acceso denegado</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Esta seccion requiere permisos de administrador o una sesion con acceso al recurso solicitado.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Volver al inicio
      </Link>
    </div>
  );
}

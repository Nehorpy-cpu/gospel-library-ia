import { Suspense } from "react";

import { SignInForm } from "@/components/auth/sign-in-form";

export default function SignInPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-sm text-muted-foreground">Cargando acceso...</div>}>
      <SignInForm />
    </Suspense>
  );
}

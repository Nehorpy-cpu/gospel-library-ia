import { Suspense } from "react";

import { SignInForm } from "@/components/auth/sign-in-form";

export default function SignUpPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-sm text-muted-foreground">Preparando registro...</div>}>
      <SignInForm mode="sign-up" />
    </Suspense>
  );
}

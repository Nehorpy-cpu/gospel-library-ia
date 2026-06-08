import type { Metadata } from "next";

import { OnboardingForm } from "@/components/beta/onboarding-form";

export const metadata: Metadata = {
  title: "Onboarding beta"
};

export default function OnboardingPage() {
  return <OnboardingForm />;
}

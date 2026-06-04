import type { Metadata } from "next";

import { CallingPreferences } from "@/components/preferences/calling-preferences";

export const metadata: Metadata = {
  title: "Preferencias"
};

export default function PreferencesPage() {
  return <CallingPreferences />;
}

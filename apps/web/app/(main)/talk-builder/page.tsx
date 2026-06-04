import type { Metadata } from "next";

import { TalkBuilderExperience } from "@/components/talk-builder/talk-builder-experience";

export const metadata: Metadata = {
  title: "Talk Builder",
  description: "Constructor de discursos doctrinales con citas y fuentes reales."
};

export default function TalkBuilderPage() {
  return <TalkBuilderExperience />;
}

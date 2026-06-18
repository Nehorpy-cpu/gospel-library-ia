import type { Metadata } from "next";

import { StudyWorkspaceExperience } from "@/components/study/study-workspace-experience";

export const metadata: Metadata = {
  title: "Mis Estudios"
};

export default function StudyPage() {
  return <StudyWorkspaceExperience />;
}

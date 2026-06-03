import type { Metadata } from "next";

import { StudyWorkspaceExperience } from "@/components/study/study-workspace-experience";

export const metadata: Metadata = {
  title: "StudyWorkspace"
};

export default function StudyPage() {
  return <StudyWorkspaceExperience />;
}

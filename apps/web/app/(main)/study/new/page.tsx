import type { Metadata } from "next";

import { StudyNewWorkspace } from "@/components/study/study-new-workspace";

export const metadata: Metadata = {
  title: "Nuevo StudyWorkspace"
};

export default function NewStudyWorkspacePage() {
  return <StudyNewWorkspace />;
}

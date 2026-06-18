import type { Metadata } from "next";

import { StudyNewWorkspace } from "@/components/study/study-new-workspace";

export const metadata: Metadata = {
  title: "Nuevo estudio"
};

export default function NewStudyWorkspacePage() {
  return <StudyNewWorkspace />;
}

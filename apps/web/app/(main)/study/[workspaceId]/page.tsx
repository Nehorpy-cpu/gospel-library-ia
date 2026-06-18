import type { Metadata } from "next";

import { StudyWorkspaceExperience } from "@/components/study/study-workspace-experience";

export const metadata: Metadata = {
  title: "Mesa de Estudio Doctrinal"
};

export default async function StudyWorkspacePage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return <StudyWorkspaceExperience workspaceId={workspaceId} />;
}

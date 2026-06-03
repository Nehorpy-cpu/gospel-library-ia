import type { Metadata } from "next";

import { DocumentReader } from "@/components/document/document-reader";

export const metadata: Metadata = {
  title: "Lector doctrinal"
};

export default async function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DocumentReader id={id} />;
}

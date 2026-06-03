import type { Metadata } from "next";

import { LibraryGrid } from "@/components/library/library-grid";

export const metadata: Metadata = {
  title: "Biblioteca",
  description: "Explorador responsive de documentos doctrinales."
};

export default function LibraryPage() {
  return <LibraryGrid />;
}

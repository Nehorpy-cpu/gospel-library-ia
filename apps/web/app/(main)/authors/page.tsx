import type { Metadata } from "next";

import { AuthorsIndex } from "@/components/authors/authors-index";

export const metadata: Metadata = {
  title: "Autores",
  description: "Indice navegable de autores derivados de documentos reales."
};

export default function AuthorsPage() {
  return <AuthorsIndex />;
}

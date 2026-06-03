import type { Metadata } from "next";

import { ChatExperience } from "@/components/chat/chat-experience";

export const metadata: Metadata = {
  title: "Chat doctrinal",
  description: "Chat IA doctrinal con RAG, streaming, memoria y citas verificables."
};

export default function ChatPage() {
  return <ChatExperience />;
}

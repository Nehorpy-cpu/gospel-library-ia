"use client";

import { Pause, Play, SkipBack, SkipForward, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useUIStore } from "@/stores/ui-store";

export function AudioDock() {
  const { audioOpen, activeAudioTitle, setAudio } = useUIStore();
  const [playing, setPlaying] = useState(false);

  if (!audioOpen) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 rounded-lg border bg-card p-3 shadow-soft lg:left-auto lg:w-[460px]">
      <div className="flex items-center gap-3">
        <Button variant="secondary" size="icon" onClick={() => setPlaying(!playing)} aria-label="Reproducir">
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">{activeAudioTitle ?? "Audio doctrinal"}</div>
          <div className="mt-2 h-1.5 rounded-full bg-muted">
            <div className="h-1.5 w-1/3 rounded-full bg-primary" />
          </div>
        </div>
        <Button variant="ghost" size="icon" aria-label="Retroceder">
          <SkipBack className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" aria-label="Avanzar">
          <SkipForward className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={() => setAudio(false)} aria-label="Cerrar">
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

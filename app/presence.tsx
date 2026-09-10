"use client";
import { useEffect } from "react";
export function Presence({ actorId }: { actorId: string }) {
  useEffect(() => {
    let stopped = false;
    let busy = false;
    let lastActivity = Date.now();
    const controller = new AbortController();
    const sessionEnded = () => { stopped = true; controller.abort(); };
    const storage = (event: StorageEvent) => { if (event.key === "asterion.session-ended") sessionEnded(); };
    const activity = () => { lastActivity = Date.now(); };
    const ping = async () => {
      if (stopped || busy || document.visibilityState !== "visible" || Date.now() - lastActivity > 300_000) return;
      busy = true;
      try {
        const response = await fetch("/api/friends", { method: "POST", cache: "no-store", signal: controller.signal,
          headers: { "Content-Type": "application/json", "X-Asterion-Actor": actorId }, body: JSON.stringify({ action: "heartbeat" }) });
        if ([401, 403, 409].includes(response.status)) stopped = true;
      } catch { /* Presence is best effort; never queue it for a later account. */ }
      finally { busy = false; }
    };
    document.addEventListener("pointerdown", activity);
    document.addEventListener("keydown", activity);
    document.addEventListener("visibilitychange", activity);
    window.addEventListener("storage", storage);
    window.addEventListener("asterion-session-ended", sessionEnded);
    void ping();
    const timer = setInterval(() => { void ping(); }, 30_000);
    return () => { stopped = true; controller.abort(); clearInterval(timer);
      document.removeEventListener("pointerdown", activity); document.removeEventListener("keydown", activity); document.removeEventListener("visibilitychange", activity);
      window.removeEventListener("storage", storage); window.removeEventListener("asterion-session-ended", sessionEnded); };
  }, [actorId]);
  return null;
}

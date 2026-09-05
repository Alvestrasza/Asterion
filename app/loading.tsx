"use client";

import { useInterface } from "./interface-provider";

export default function Loading() {
  const { errors: t } = useInterface();
  return (
    <main className="loading-shell" aria-live="polite">
      <span className="confirm-mark" aria-hidden="true">✦</span>
      <p>{t.loading}</p>
    </main>
  );
}

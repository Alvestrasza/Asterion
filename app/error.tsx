"use client";

import { useInterface } from "./interface-provider";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const { errors: t } = useInterface();
  return (
    <main className="loading-shell">
      <span className="confirm-mark" aria-hidden="true">✦</span>
      <h1>{t.title}</h1>
      <p>{t.description}</p>
      <button className="quiet-button" type="button" onClick={reset}>{t.retry}</button>
    </main>
  );
}

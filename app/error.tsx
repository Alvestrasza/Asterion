"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="loading-shell">
      <span className="confirm-mark" aria-hidden="true">✦</span>
      <h1>Die Verbindung zu den Sternen ist gerade still.</h1>
      <p>Asterion ist sicher. Bitte versuche es gleich noch einmal.</p>
      <button className="quiet-button" type="button" onClick={reset}>Erneut verbinden</button>
    </main>
  );
}

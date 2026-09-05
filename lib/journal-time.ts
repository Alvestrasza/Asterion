/** Match SSR and initial hydration before switching to the browser's timezone. */
export function formatJournalTime(at: number, timeZone?: string): string {
  const date = new Date(at);
  if (!timeZone) return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
  return new Intl.DateTimeFormat("de-DE", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone
  }).format(date).toUpperCase();
}

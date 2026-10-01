/** Asterion achievement collection. Version: 1.0.0 | License: UNLICENSED | Updated: 2026-10-01 */
import type { Locale } from "@/lib/i18n";
import { achievementCopy, type AchievementView } from "@/lib/achievements";

export function AchievementCollection({ achievements, locale }: { achievements: AchievementView[]; locale: Locale }) {
  const copy = achievementCopy(locale);
  const number = new Intl.NumberFormat(locale);
  return <details className="panel achievement-panel" lang={locale}>
    <summary><h2>{copy.heading} <small>{number.format(achievements.filter(entry => entry.earnedAt).length)} / {number.format(achievements.length)}</small></h2></summary>
    {(["account", "pet"] as const).map(scope => <div key={scope}>
      <h3>{copy[scope]}</h3>
      <ul className="achievement-grid">
        {achievements.filter(entry => entry.scope === scope).map(entry => <li className="achievement-card" key={entry.id} data-earned={Boolean(entry.earnedAt)}>
          {/* The adjacent text conveys the icon and status without relying on color. */}
          <img src={entry.icon} width="36" height="36" alt="" aria-hidden="true" />
          <div><h4>{entry.name}</h4><p>{entry.description}</p>
            <span className="achievement-status">{entry.earnedAt ? copy.earned : copy.locked}</span>
            <span className="achievement-progress">{number.format(entry.progress)} / {number.format(entry.target)}</span>
            <progress value={entry.progress} max={entry.target} aria-label={`${entry.name}: ${number.format(entry.progress)} / ${number.format(entry.target)}`} />
          </div>
        </li>)}
      </ul>
    </div>)}
  </details>;
}

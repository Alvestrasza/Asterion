/** Asterion achievement collection. Version: 1.1.0 | License: UNLICENSED | Updated: 2026-10-05 */
import type { Locale } from "@/lib/i18n";
import { achievementCopy, type AchievementView } from "@/lib/achievements";

export function AchievementCollection({ achievements, companionName, locale }: {
  achievements: AchievementView[]; companionName: string; locale: Locale;
}) {
  const copy = achievementCopy(locale);
  const number = new Intl.NumberFormat(locale);
  return <div className="achievement-collection" lang={locale}>
    {(["account", "pet"] as const).map(scope => {
      const entries = achievements.filter(entry => entry.scope === scope);
      return <section className="panel achievement-section" key={scope} aria-labelledby={`achievements-${scope}`}>
        <div className="achievement-section-heading">
          <h2 id={`achievements-${scope}`}>{copy[scope]}{scope === "pet" && <span className="achievement-companion">{companionName}</span>}</h2>
          <p className="achievement-total">{number.format(entries.filter(entry => entry.earnedAt).length)} / {number.format(entries.length)} <span>{copy.earned}</span></p>
        </div>
        <p className="achievement-hint">{scope === "account" ? copy.accountHint : copy.petHint}</p>
        <ul className="achievement-grid">
          {entries.map(entry => <li className="achievement-card" key={entry.id} data-earned={Boolean(entry.earnedAt)}>
            {/* The adjacent text conveys the icon and status without relying on color. */}
            <img src={entry.icon} width="36" height="36" alt="" aria-hidden="true" />
            <div><h3>{entry.name}</h3><p>{entry.description}</p>
              <span className="achievement-status">{entry.earnedAt ? copy.earned : copy.locked}</span>
              <span className="achievement-progress">{number.format(entry.progress)} / {number.format(entry.target)}</span>
              <progress value={entry.progress} max={entry.target} aria-label={`${entry.name}: ${number.format(entry.progress)} / ${number.format(entry.target)}`} />
            </div>
          </li>)}
        </ul>
      </section>;
    })}
  </div>;
}

/**
 * Asterion: versioned achievement catalog and public view contract.
 * Version: 1.0.0 | License: UNLICENSED | Updated: 2026-10-01
 */
import type { Locale } from "./i18n.ts";

export const ACHIEVEMENT_VERSION = 1;
export const ACHIEVEMENT_XP_REWARD = 0;
export const ACHIEVEMENTS = [
  { id: "v1.first-adoption", scope: "account", target: 1, icon: "star" },
  { id: "v1.companion-family", scope: "account", target: 2, icon: "friends" },
  { id: "v1.constellation", scope: "account", target: 5, icon: "friends" },
  { id: "v1.player-level-five", scope: "account", target: 5, icon: "star" },
  { id: "v1.first-care", scope: "pet", target: 1, icon: "heart" },
  { id: "v1.varied-care", scope: "pet", target: 3, icon: "heart" },
  { id: "v1.pet-level-five", scope: "pet", target: 5, icon: "star" },
  { id: "v1.healthy-bond", scope: "pet", target: 7, icon: "heart" }
] as const;
export type AchievementId = typeof ACHIEVEMENTS[number]["id"];
export type AchievementView = {
  id: AchievementId; scope: "account" | "pet"; name: string; description: string;
  icon: string; progress: number; target: number; earnedAt: string | null;
};

type Copy = { heading: string; account: string; pet: string; earned: string; locked: string; unlocked: string;
  entries: Record<AchievementId, readonly [string, string]> };
const COPY: Record<Locale, Copy> = {
  de: { heading: "Deine Erfolge", account: "Deine Sammlung", pet: "Dieser Begleiter", earned: "Erreicht", locked: "Noch unterwegs", unlocked: "Neuer Erfolg",
    entries: {
      "v1.first-adoption": ["Ein erster Stern", "Adoptiere deinen ersten Begleiter."],
      "v1.companion-family": ["Gemeinsam zu Hause", "Adoptiere zwei unterschiedliche Begleiter."],
      "v1.constellation": ["Ein kleines Sternbild", "Adoptiere fünf unterschiedliche Begleiter."],
      "v1.player-level-five": ["Dein Sternenweg", "Erreiche als Spieler Stufe 5."],
      "v1.first-care": ["Ein guter Anfang", "Pflege diesen Begleiter einmal mit einer XP-belohnten Aktion."],
      "v1.varied-care": ["Abwechslungsreiche Zeit", "Füttere, spiele und streichle diesen Begleiter mit jeweils einer XP-belohnten Aktion."],
      "v1.pet-level-five": ["Wir wachsen zusammen", "Erreiche mit diesem Begleiter Stufe 5."],
      "v1.healthy-bond": ["Vertraute Augenblicke", "Sammle 7 UTC-Tage mit XP-belohnter Pflege bei mindestens 50 Sättigung, Energie und Freude sowie 45 Bindung. Pausen sind willkommen."]
    } },
  en: { heading: "Your achievements", account: "Your collection", pet: "This companion", earned: "Earned", locked: "In progress", unlocked: "Achievement unlocked",
    entries: {
      "v1.first-adoption": ["A first star", "Adopt your first companion."],
      "v1.companion-family": ["At home together", "Adopt two different companions."],
      "v1.constellation": ["A little constellation", "Adopt five different companions."],
      "v1.player-level-five": ["Your star path", "Reach player level 5."],
      "v1.first-care": ["A kind beginning", "Give this companion one XP-rewarded care action."],
      "v1.varied-care": ["Varied moments", "Feed, play with and pet this companion with one XP-rewarded action of each kind."],
      "v1.pet-level-five": ["Growing together", "Reach level 5 with this companion."],
      "v1.healthy-bond": ["Familiar moments", "Collect 7 UTC days with XP-rewarded care at 50 or more satiety, energy and joy, and 45 bond. Breaks are welcome."]
    } },
  fr: { heading: "Tes réussites", account: "Ta collection", pet: "Ce compagnon", earned: "Obtenue", locked: "En chemin", unlocked: "Nouvelle réussite",
    entries: {
      "v1.first-adoption": ["Une première étoile", "Adopte ton premier compagnon."],
      "v1.companion-family": ["Chez nous, ensemble", "Adopte deux compagnons différents."],
      "v1.constellation": ["Une petite constellation", "Adopte cinq compagnons différents."],
      "v1.player-level-five": ["Ton chemin étoilé", "Atteins le niveau 5 de joueur."],
      "v1.first-care": ["Un doux début", "Offre à ce compagnon un soin récompensé par de l’XP."],
      "v1.varied-care": ["Des moments variés", "Nourris, caresse et joue avec ce compagnon, avec une action récompensée par de l’XP de chaque type."],
      "v1.pet-level-five": ["Grandir ensemble", "Atteins le niveau 5 avec ce compagnon."],
      "v1.healthy-bond": ["Des moments familiers", "Cumule 7 jours UTC avec un soin récompensé par de l’XP, au moins 50 de satiété, d’énergie et de joie, et 45 de lien. Les pauses sont bienvenues."]
    } },
  es: { heading: "Tus logros", account: "Tu colección", pet: "Este compañero", earned: "Conseguido", locked: "En camino", unlocked: "Nuevo logro",
    entries: {
      "v1.first-adoption": ["Una primera estrella", "Adopta a tu primer compañero."],
      "v1.companion-family": ["En casa, juntos", "Adopta a dos compañeros diferentes."],
      "v1.constellation": ["Una pequeña constelación", "Adopta a cinco compañeros diferentes."],
      "v1.player-level-five": ["Tu camino estelar", "Alcanza el nivel 5 de jugador."],
      "v1.first-care": ["Un comienzo amable", "Cuida a este compañero con una acción recompensada con XP."],
      "v1.varied-care": ["Momentos variados", "Alimenta, acaricia y juega con este compañero, con una acción recompensada con XP de cada tipo."],
      "v1.pet-level-five": ["Crecer juntos", "Alcanza el nivel 5 con este compañero."],
      "v1.healthy-bond": ["Momentos de confianza", "Acumula 7 días UTC con cuidados recompensados con XP, al menos 50 de saciedad, energía y alegría, y 45 de vínculo. Las pausas son bienvenidas."]
    } }
};
export function achievementCopy(locale: Locale | string): Copy {
  return COPY[locale as Locale] ?? COPY.en;
}
export function careBit(action: string): number {
  return action === "feed" ? 1 : action === "play" ? 2 : action === "pet" ? 4 : 0;
}
export function variedCareCount(mask: number): number {
  return [1, 2, 4].filter(bit => (mask & bit) !== 0).length;
}
export function healthyCare(stats: { satiety: number; energy: number; joy: number; bond: number }, sleeping: boolean) {
  return !sleeping && stats.satiety >= 50 && stats.energy >= 50 && stats.joy >= 50 && stats.bond >= 45;
}
export function achievementViews(locale: Locale, rows: Array<{ achievementId: string; progress: number; earnedAt: Date | null }>): AchievementView[] {
  return ACHIEVEMENTS.map(def => {
    const row = rows.find(entry => entry.achievementId === def.id);
    const [name, description] = achievementCopy(locale).entries[def.id];
    return { id: def.id, scope: def.scope, name, description, icon: `/assets/achievements/${def.icon}.svg`,
      progress: Math.min(def.target, Math.max(0, row?.progress ?? 0)), target: def.target,
      earnedAt: row?.earnedAt?.toISOString() ?? null };
  });
}

export const LOCALES = ["de", "en", "fr", "es"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "en";
export const LANGUAGE_COOKIE = "asterion-locale";

export function normalizeLocale(value: unknown): Locale | null {
  if (typeof value !== "string") return null;
  const tag = value.trim().toLowerCase();
  if (!/^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$/.test(tag)) return null;
  const language = tag.split("-")[0];
  return LOCALES.includes(language as Locale) ? language as Locale : null;
}

/** Manual preference wins; negotiate browser ranges only when it is absent. */
export function resolveLocale(saved: unknown, acceptLanguage?: string | null): Locale {
  const explicit = normalizeLocale(saved);
  if (explicit) return explicit;

  const ranges = (acceptLanguage ?? "").slice(0, 8192).split(",").flatMap((part, order) => {
    const [tag, quality, ...extra] = part.trim().split(";").map((item) => item.trim());
    const language = tag === "*" ? "*" : normalizeLocale(tag);
    if (!language || extra.length) return [];
    if (quality !== undefined && !/^q=(?:0(?:\.\d{0,3})?|1(?:\.0{0,3})?)$/i.test(quality)) return [];
    return [{ language, quality: quality === undefined ? 1 : Number(quality.slice(2)), order }];
  });
  const fallbackOrder: Locale[] = [DEFAULT_LOCALE, ...LOCALES.filter((locale) => locale !== DEFAULT_LOCALE)];
  const candidates = fallbackOrder.flatMap((locale) => {
    const exact = ranges.filter((range) => range.language === locale);
    // A specific q=0 excludes a language even when a wildcard permits others.
    const matches = exact.length ? exact : ranges.filter((range) => range.language === "*");
    const best = matches.sort((a, b) => b.quality - a.quality || a.order - b.order)[0];
    return best && best.quality > 0 ? [{ locale, ...best }] : [];
  });
  return candidates.sort((a, b) => b.quality - a.quality || a.order - b.order)[0]?.locale ?? DEFAULT_LOCALE;
}

/** Forms cannot turn a language change into an arbitrary redirect. */
export function languageReturnPath(value: unknown): "/" | "/login" | "/care" {
  return value === "/login" || value === "/care" ? value : "/";
}

export function languageCookieOptions(production: boolean, internalTestMode: boolean) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    // The isolated internal profile uses HTTP. This preference is not an auth cookie.
    secure: production && !internalTestMode,
    path: "/",
    maxAge: 60 * 60 * 24 * 365
  };
}

"use client";

import { LOCALES, localizedPath, type Locale } from "@/lib/i18n";
import type { Messages } from "@/lib/messages";
import { changeLanguage } from "./language-actions";

const languageNames = { de: "Deutsch", en: "English", fr: "Français", es: "Español" };

export function LanguageSelector({ locale, labels, returnTo }: {
  locale: Locale;
  labels: Messages["nav"];
  returnTo: "/" | "/login" | "/care" | "/friends" | "/admin" | "/access";
}) {
  return (
    <form action={changeLanguage} className="language-selector">
      <input type="hidden" name="returnTo" value={returnTo} />
      <label>
        <span className="visually-hidden">{labels.language}</span>
        <select name="locale" defaultValue={locale} key={locale} onChange={(event) => event.currentTarget.form?.requestSubmit()}>
          {LOCALES.map((language) => <option key={language} value={language} lang={language}>{languageNames[language]}</option>)}
        </select>
      </label>
      <noscript>{LOCALES.map((language) => <a key={language} href={localizedPath(returnTo, language)} lang={language}>{languageNames[language]} </a>)}</noscript>
    </form>
  );
}

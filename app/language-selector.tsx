import { LOCALES, type Locale } from "@/lib/i18n";
import type { Messages } from "@/lib/messages";
import { changeLanguage } from "./language-actions";

const languageNames = { de: "Deutsch", en: "English", fr: "Français", es: "Español" };

export function LanguageSelector({ locale, labels, returnTo }: {
  locale: Locale;
  labels: Messages["nav"];
  returnTo: "/" | "/login" | "/care";
}) {
  return (
    <form action={changeLanguage} className="language-selector">
      <input type="hidden" name="returnTo" value={returnTo} />
      <label>
        <span className="visually-hidden">{labels.language}</span>
        <select name="locale" defaultValue={locale} key={locale}>
          {LOCALES.map((language) => <option key={language} value={language} lang={language}>{languageNames[language]}</option>)}
        </select>
      </label>
      <button type="submit">{labels.apply}</button>
    </form>
  );
}

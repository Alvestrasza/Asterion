import { CompanionArt } from "../companion-art";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth, signIn } from "@/auth";
import { isInternalTestMode } from "@/lib/current-actor";
import { isKeycloakConfigured } from "@/lib/auth-config";
import { isPublicDeployment, publicRuntimeErrors } from "@/lib/deployment-config";
import { getRequestLocale } from "@/lib/request-locale";
import { getMessages } from "@/lib/messages";
import { keycloakLoginParameters, localizedPath } from "@/lib/i18n";
import { LanguageSelector } from "../language-selector";

export const dynamic = "force-dynamic";

export const metadata = { robots: { index: false, follow: false } };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const locale = await getRequestLocale();
  if (isInternalTestMode()) redirect(localizedPath("/care", locale));

  const configured = isPublicDeployment() && isKeycloakConfigured() && publicRuntimeErrors().length === 0;
  const session = configured ? await auth() : null;
  if (session?.user?.id) redirect(localizedPath("/access", locale));
  const t = getMessages(locale);
  const { error } = await searchParams;

  return (
    <main className="login-shell public-login">
      <section className="login-card" aria-labelledby="login-title">
        <LanguageSelector locale={locale} labels={t.nav} returnTo="/login" />
        <CompanionArt
          className="login-asterion"
          width={192}
          height={208}
          alt={t.companions.asterion.alt}
        />
        <p className="eyebrow">{t.login.eyebrow}</p>
        <h1 id="login-title">{configured ? t.login.title : t.login.unavailableTitle}</h1>
        <p>{configured ? t.login.description : t.login.unavailableText}</p>
        {error && <p role="alert">{error === "AccessDenied" ? t.login.denied : t.login.error}</p>}
        {configured && <form
          action={async () => {
            "use server";
            if (!isPublicDeployment() || !isKeycloakConfigured() || publicRuntimeErrors().length) redirect(localizedPath("/login", locale));
            await signIn("keycloak", { redirectTo: localizedPath("/care", locale) }, keycloakLoginParameters(locale));
          }}
        >
          <button className="login-button" type="submit">{t.login.submit}</button>
        </form>}
        {configured && <form className="login-registration" action={async () => {
          "use server";
          if (!isPublicDeployment() || !isKeycloakConfigured() || publicRuntimeErrors().length) redirect(localizedPath("/login", locale));
          await signIn("keycloak", { redirectTo: localizedPath("/care", locale) }, keycloakLoginParameters(locale, true));
        }}><button className="quiet-button" type="submit">{t.login.register}</button></form>}
        <Link className="public-back" href={localizedPath("/", locale)}>← {t.login.back}</Link>
      </section>
    </main>
  );
}

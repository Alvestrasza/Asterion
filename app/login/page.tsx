import Image from "next/image";
import Link from "next/link";
import { redirect } from "next/navigation";
import { auth, signIn } from "@/auth";
import { isInternalTestMode } from "@/lib/current-actor";
import { isKeycloakConfigured } from "@/lib/auth-config";
import { getRequestLocale } from "@/lib/request-locale";
import { getMessages } from "@/lib/messages";
import { LanguageSelector } from "../language-selector";

export const dynamic = "force-dynamic";

export const metadata = { robots: { index: false, follow: false } };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  if (isInternalTestMode()) redirect("/care");

  const configured = isKeycloakConfigured();
  const session = configured ? await auth() : null;
  if (session?.user?.id) redirect("/care");
  const locale = await getRequestLocale();
  const t = getMessages(locale);
  const { error } = await searchParams;

  return (
    <main className="login-shell public-login">
      <section className="login-card" aria-labelledby="login-title">
        <LanguageSelector locale={locale} labels={t.nav} returnTo="/login" />
        <Image
          className="login-asterion"
          src="/assets/companions/asterion.png"
          width={192}
          height={208}
          alt={t.companions.asterion.alt}
          priority
        />
        <p className="eyebrow">{t.login.eyebrow}</p>
        <h1 id="login-title">{configured ? t.login.title : t.login.unavailableTitle}</h1>
        <p>{configured ? t.login.description : t.login.unavailableText}</p>
        {error && <p role="alert">{error === "AccessDenied" ? t.login.denied : t.login.error}</p>}
        {configured && <form
          action={async () => {
            "use server";
            if (!isKeycloakConfigured()) redirect("/login");
            await signIn("keycloak", { redirectTo: "/care" });
          }}
        >
          <button className="login-button" type="submit">{t.login.submit}</button>
        </form>}
        <Link className="public-back" href="/">← {t.login.back}</Link>
      </section>
    </main>
  );
}
